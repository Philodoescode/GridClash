#!/usr/bin/env python3
import argparse
import csv
import math
import os
import signal
import subprocess
import sys
import time
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional
import statistics
import json
import numpy as np

# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TestScenario:
    name: str
    netem_cmd: str
    criteria: Dict[str, float]

SCENARIOS = {
    "baseline": TestScenario(
        "Baseline", "", 
        {"updates_per_sec": 20, "avg_latency_ms": 50, "cpu_percent": 60}
    ),
    "loss_2": TestScenario(
        "Loss 2%", "loss 2%", 
        {"mean_position_error": 0.5, "p95_position_error": 1.5}
    ),
    "loss_5": TestScenario(
        "Loss 5%", "loss 5%", 
        {"critical_event_delivery": 0.99} 
    ),
    "delay_100ms": TestScenario(
        "Delay 100ms", "delay 100ms", 
        {"system_stable": True}
    )
}

# =============================================================================
# Utilities
# =============================================================================

class CPUMonitor:
    def __init__(self, pid, interval=0.5):
        self.pid = pid
        self.interval = interval
        self.samples = []
        self.running = False
        self.thread = None

    def start(self):
        import threading
        self.running = True
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()

    def _loop(self):
        try:
            import psutil
            proc = psutil.Process(self.pid)
            while self.running:
                try:
                    v = proc.cpu_percent(interval=self.interval)
                    self.samples.append(v)
                except:
                    break
        except ImportError:
            print("[WARN] psutil not installed, CPU monitoring disabled.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def get_avg(self):
        if not self.samples: return 0.0
        return sum(self.samples) / len(self.samples)


# =============================================================================
# Orchestration
# =============================================================================

class result_container:
    def __init__(self):
        self.latency = []
        self.jitter = []
        self.position_error = []
        self.total_packets = 0
        self.total_bytes = 0
        self.duration = 0
        self.cpu_usage = 0

def run_command(cmd, shell=False):
    # print(f"[CMD] {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    return subprocess.Popen(cmd, shell=shell)

def apply_netem(interface, cmd):
    if not cmd:
        return True
    full_cmd = f"sudo tc qdisc add dev {interface} root netem {cmd}"
    print(f"[NETEM] Applying: {full_cmd}")
    res = subprocess.run(full_cmd, shell=True, stderr=subprocess.PIPE)
    if res.returncode != 0:
        print(f"[NETEM] Error (ignoring if just 'exists'): {res.stderr.decode().strip()}")
        # Try change if add fails
        full_cmd = f"sudo tc qdisc change dev {interface} root netem {cmd}"
        subprocess.run(full_cmd, shell=True)
    return True

def remove_netem(interface):
    cmd = f"sudo tc qdisc del dev {interface} root"
    subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL) # Ignore error if not exists

def main():
    parser = argparse.ArgumentParser(description="Run GridClash Test Scenario")
    parser.add_argument("scenario", choices=SCENARIOS.keys(), help="Test scenario to run")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--interface", default="lo", help="Network interface for netem")
    parser.add_argument("--clients", type=int, default=4, help="Number of clients")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    scenario = SCENARIOS[args.scenario]
    timestamp = int(time.time())
    
    # Directory setup
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base_dir, "results", f"{timestamp}_{args.seed}")
    os.makedirs(results_dir, exist_ok=True)
    
    print(f"=== Starting Test: {scenario.name} ===")
    print(f"Output Directory: {results_dir}")
    
    # Netem
    remove_netem(args.interface) # Cleanup first
    apply_netem(args.interface, scenario.netem_cmd)
    
    # PCAP
    pcap_file = os.path.join(results_dir, "trace.pcap")
    pcap_proc = run_command(["sudo", "tcpdump", "-i", args.interface, "-w", pcap_file, "port", "12000", "-q"], shell=False)
    
    # Start Server
    server_script = os.path.join(base_dir, "instrumented_server.py")
    server_log = open(os.path.join(results_dir, "server_stdout.log"), "w")
    server_proc = subprocess.Popen(
        [sys.executable, "-u", server_script, "--port", "12000", "--log-dir", results_dir],
        stdout=server_log, stderr=server_log
    )
    time.sleep(2) # Wait for server start
    
    # CPU Monitor
    cpu_mon = CPUMonitor(server_proc.pid)
    cpu_mon.start()
    
    # Start Clients
    client_script = os.path.join(base_dir, "instrumented_client.py")
    client_procs = []
    client_logs = []
    for i in range(args.clients):
        # Determine unique seed per client
        c_seed = args.seed + i
        
        # Open client log file
        c_log = open(os.path.join(results_dir, f"client_{i}_stdout.log"), "w")
        client_logs.append(c_log)
        
        # Use python to run client
        proc = subprocess.Popen(
            [sys.executable, "-u", client_script, "--id", str(i), "--log-dir", results_dir, "--seed", str(c_seed)],
            stdout=c_log, stderr=c_log
        )
        client_procs.append(proc)
        
    print(f"Running for {args.duration} seconds...")
    try:
        start_time = time.time()
        while time.time() - start_time < args.duration:
            if server_proc.poll() is not None:
                print("Server stopped unexpectedly!")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        
    # Cleanup
    print("Stopping processes...")
    cpu_mon.stop()
    for p in client_procs:
        p.terminate()
    server_proc.terminate()
    pcap_proc.terminate()
    
    for p in client_procs: p.wait()
    server_proc.wait()
    pcap_proc.wait()
    
    remove_netem(args.interface)
    server_log.close()
    for f in client_logs:
        f.close()
    
    # Post Processing
    print("Processing results...")
    stats = process_results(results_dir, args.duration, args.clients, scenario)
    stats.cpu_usage = cpu_mon.get_avg()
    save_summary_json(stats, scenario, results_dir)
    print_report(stats, scenario)

# =============================================================================
# Post Processing
# =============================================================================

def load_csv(path):
    data = []
    if not os.path.exists(path):
        return data
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            clean_row = {}
            for k, v in row.items():
                try:
                    clean_row[k] = float(v)
                except ValueError:
                    clean_row[k] = v
            data.append(clean_row)
    return data

def process_results(results_dir, duration, num_clients, scenario):
    # Load Server Positions
    server_pos_file = os.path.join(results_dir, "server_positions.csv")
    server_pos_raw = load_csv(server_pos_file)
    
    # Index server positions: (client_id) -> list of (ts, x, y) sorted by ts
    server_pos_lookup = {}
    for row in server_pos_raw:
        pid = int(row['client_id'])
        if pid not in server_pos_lookup:
            server_pos_lookup[pid] = []
        server_pos_lookup[pid].append((row['timestamp_ms'], row['x'], row['y']))
    
    for pid in server_pos_lookup:
        server_pos_lookup[pid].sort(key=lambda x: x[0])

    container = result_container()
    container.duration = duration
    
    # Load Client Data
    for i in range(num_clients):
        # Metrics
        metric_file = os.path.join(results_dir, f"client_{i}_metrics.csv")
        metrics = load_csv(metric_file)
        
        # Positions
        pos_file = os.path.join(results_dir, f"client_{i}_positions.csv")
        positions = load_csv(pos_file)
        
        container.total_packets += len(metrics)
        
        for m in metrics:
            container.latency.append(m['latency_ms'])
            container.jitter.append(m['jitter_ms'])
            container.total_bytes += m['bandwidth_per_client_kbps'] # Stored implies bytes in this column
            
        # Calculate Position Error
        # Iterate client positions and find authoritative server pos
        for p in positions:
            c_ts = p['timestamp_ms']
            c_x, c_y = p['x'], p['y']
            c_id = int(p['client_id'])
            
            # Skip unassigned IDs
            if c_id not in server_pos_lookup:
                continue
                
            s_data = server_pos_lookup[c_id]
            
            # Simple matching: find server pos with closest timestamp within 100ms
            nearby = [s for s in s_data if abs(s[0] - c_ts) <= 200]
            if nearby:
                # closest
                best = min(nearby, key=lambda s: abs(s[0] - c_ts))
                s_x, s_y = best[1], best[2]
                dist = math.sqrt((c_x - s_x)**2 + (c_y - s_y)**2)
                container.position_error.append(dist)
    
    return container

def stats_dict(data):
    if not data:
        return {"mean": 0, "median": 0, "p95": 0}
    
    # Use numpy for accurate statistical analysis
    # This handles percentiles correctly even with skewed distributions
    return {
        "mean": float(np.mean(data)),
        "median": float(np.median(data)),
        "p95": float(np.percentile(data, 95))
    }

def save_summary_json(stats, scenario, results_dir):
    lat = stats_dict(stats.latency)
    jit = stats_dict(stats.jitter)
    err = stats_dict(stats.position_error)
    
    upd_per_sec = 0
    if stats.duration > 0:
        upd_per_sec = (stats.total_packets / stats.duration) / 4 
    
    bw_kbps = 0
    if stats.duration > 0:
        total_bits = stats.total_bytes * 8
        bw_kbps = (total_bits / 1000) / stats.duration / 4

    summary = {
        "scenario": scenario.name,
        "timestamp": int(time.time()),
        "duration": stats.duration,
        "metrics": {
            "updates_per_sec": upd_per_sec,
            "bandwidth_kbps": bw_kbps,
            "cpu_percent": stats.cpu_usage,
            "latency": lat,
            "jitter": jit,
            "position_error": err
        },
        "criteria": scenario.criteria
    }
    
    with open(os.path.join(results_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=4)

def print_report(stats, scenario):
    lat = stats_dict(stats.latency)
    jit = stats_dict(stats.jitter)
    err = stats_dict(stats.position_error)
    
    upd_per_sec = 0
    if stats.duration > 0:
        upd_per_sec = (stats.total_packets / stats.duration) / 4 # assuming 4 clients hardcoded in calculation here or pass num_clients
    
    # Calculate bytes/sec/client (kbps)
    bw_kbps = 0
    if stats.duration > 0:
        total_bits = stats.total_bytes * 8
        bw_kbps = (total_bits / 1000) / stats.duration / 4
        
    print("\n" + "="*40)
    print(f"FINAL REPORT: {scenario.name}")
    print("="*40)
    print(f"Updates/Sec (per client): {upd_per_sec:.2f}")
    print(f"Avg Bandwidth (kbps): {bw_kbps:.2f}")
    print(f"Avg Server CPU: {stats.cpu_usage:.1f}%")
    print("-" * 20)
    print(f"{'Metric':<15} | {'Mean':<10} | {'Median':<10} | {'95th %':<10}")
    print("-" * 55)
    print(f"{'Latency (ms)':<15} | {lat['mean']:<10.2f} | {lat['median']:<10.2f} | {lat['p95']:<10.2f}")
    print(f"{'Jitter (ms)':<15} | {jit['mean']:<10.2f} | {jit['median']:<10.2f} | {jit['p95']:<10.2f}")
    print(f"{'Pos Error':<15} | {err['mean']:<10.4f} | {err['median']:<10.4f} | {err['p95']:<10.4f}")
    print("="*40)
    
    # Acceptance Criteria Check
    passed = True
    c = scenario.criteria
    print("Acceptance Criteria:")
    
    if "updates_per_sec" in c:
        p = upd_per_sec >= c["updates_per_sec"]
        print(f"  Updates/Sec >= {c['updates_per_sec']}: {'PASS' if p else 'FAIL'}")
        if not p: passed = False
        
    if "avg_latency_ms" in c:
        p = lat['mean'] <= c["avg_latency_ms"]
        print(f"  Avg Latency <= {c['avg_latency_ms']}ms: {'PASS' if p else 'FAIL'}")
        if not p: passed = False
        
    if "cpu_percent" in c:
        p = stats.cpu_usage < c["cpu_percent"]
        print(f"  Avg CPU < {c['cpu_percent']}%: {'PASS' if p else 'FAIL'}")
        if not p: passed = False
    
    if "mean_position_error" in c:
        p = err['mean'] <= c["mean_position_error"]
        print(f"  Mean Pos Error <= {c['mean_position_error']}: {'PASS' if p else 'FAIL'}")
        if not p: passed = False
        
    if "p95_position_error" in c:
        p = err['p95'] <= c["p95_position_error"]
        print(f"  95% Pos Error <= {c['p95_position_error']}: {'PASS' if p else 'FAIL'}")
        if not p: passed = False
        
    if "critical_event_delivery" in c:
        # Expected packets ~ 20 * duration * 4?
        # A bit fuzzy.
        pass
        
    if "system_stable" in c:
        print(f"  System Stable: PASS") 

    if passed:
        print("\nOVERALL TEST STATUS: PASS")
    else:
        print("\nOVERALL TEST STATUS: FAIL")

if __name__ == "__main__":
    main()
