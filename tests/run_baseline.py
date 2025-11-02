"""
Baseline Test Runner for GridClash with CPU Monitoring and Metrics Reporting
--------------------------------------------------------------------------------
Runs the server and multiple clients, collects raw logs, and prints a final summary to the terminal 
and saves it to a .txt file.
"""

import os
import subprocess
import time
import csv
import re
from threading import Thread
import psutil
import statistics

# Configuration
RUN_DURATION = 30       # seconds
NUM_CLIENTS = 4         # number of clients to simulate
LOG_DIR = "logs"

# Output Files
CPU_LOG_FILE = os.path.join(LOG_DIR, "server_cpu_usage.csv")
SUMMARY_TEXT_FILE = os.path.join(LOG_DIR, "final_summary_report.txt")

# CALCULATE ABSOLUTE PATHS FOR ROBUSTNESS (Fixes [Errno 2])
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SERVER_PATH = os.path.join(PROJECT_ROOT, "src", "server.py")
CLIENT_PATH = os.path.join(PROJECT_ROOT, "src", "client.py")

# Use -u flag for unbuffered output (Fixes empty server.log)
SERVER_CMD = ["python", "-u", SERVER_PATH] 
CLIENT_CMD = ["python", CLIENT_PATH]


# --- Core Process Management and Monitoring Functions ---

def ensure_log_dir():
    """Ensures the log directory exists."""
    os.makedirs(LOG_DIR, exist_ok=True)


def monitor_cpu_usage(pid, duration, log_filename):
    """Monitors a specific process PID for a given duration and logs its CPU usage."""
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"[MONITOR] Error: Server process with PID {pid} not found for monitoring.")
        return

    end_time = time.time() + duration
    POLL_INTERVAL = 0.5
    
    with open(log_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp_s', 'Relative_Time_s', 'CPU_Usage_Percent'])

        start_time = time.time()
        
        while time.time() < end_time and process.is_running():
            try:
                cpu_percent = process.cpu_percent(interval=POLL_INTERVAL) 
                current_time = time.time()
                relative_time = current_time - start_time
                writer.writerow([current_time, relative_time, cpu_percent])
            except psutil.NoSuchProcess:
                break


def start_server():
    """Start the server process and return its PID."""
    print("[BASELINE] Starting server...")
    server_log = open(os.path.join(LOG_DIR, "server.log"), "w")
    # Popen uses the unbuffered command list
    server_proc = subprocess.Popen(SERVER_CMD, stdout=server_log, stderr=server_log)
    
    server_pid = server_proc.pid
    print(f"[MONITOR] Server PID: {server_pid}")

    time.sleep(1.0)
    return server_proc, server_pid


def start_clients(num_clients=2):
    """Start multiple clients."""
    print(f"[BASELINE] Launching {num_clients} clients...")
    clients = []
    for i in range(num_clients):
        log_path = os.path.join(LOG_DIR, f"client_{i}.log")
        client_log = open(log_path, "w")
        # Assuming your client script takes --id and --duration arguments
        cmd = CLIENT_CMD + ["--id", str(i), "--duration", str(RUN_DURATION)]
        proc = subprocess.Popen(cmd, stdout=client_log, stderr=client_log)
        clients.append(proc)
        time.sleep(0.3)
    return clients


def terminate_all(server_proc, client_procs):
    """Terminate all subprocesses cleanly (cross-platform)."""
    print("[BASELINE] Stopping all processes...")

    for p in client_procs:
        try:
            p.terminate()
        except Exception:
            pass

    try:
        server_proc.terminate()
    except Exception:
            pass

    time.sleep(2)

    for p in client_procs:
        if p.poll() is None:
            p.kill()

    if server_proc.poll() is None:
        server_proc.kill()


# --- Analysis and Reporting Functions ---

def write_to_file(text, filename, mode='a'):
    """Prints text to console and writes to file simultaneously."""
    print(text)
    try:
        with open(filename, mode, encoding='utf-8') as f:
            f.write(text + '\n')
    except PermissionError:
        print(f"[ERROR] Could not write to {filename}. File may be locked.")


def analyze_cpu_data(cpu_log_file):
    """Reads the raw CPU data and calculates min, max, median, and mean."""
    cpu_values = []
    if not os.path.exists(cpu_log_file):
        return 0, 0, 0, 0

    with open(cpu_log_file, 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader) # Skip header
        for row in reader:
            try:
                cpu_values.append(float(row[2]))
            except (IndexError, ValueError):
                continue

    if not cpu_values:
        return 0, 0, 0, 0

    return min(cpu_values), statistics.median(cpu_values), max(cpu_values), statistics.mean(cpu_values)


def analyze_client_logs(num_clients):
    """Parses client text logs to extract final packet count and latency average."""
    all_client_latencies = []
    total_packets_received = 0
    
    # Regex to find the final cumulative average latency line
    latency_pattern = re.compile(r"Received\s+(\d+)\s+packets\.\s+Average latency:\s+([0-9.]+)\s+ms")

    for i in range(num_clients):
        client_log_path = os.path.join(LOG_DIR, f"client_{i}.log")
        if not os.path.exists(client_log_path):
            continue

        with open(client_log_path, 'r') as f:
            lines = f.readlines()
        
        # Search the log backwards for the last reported cumulative average
        for line in reversed(lines):
            match = latency_pattern.search(line)
            if match:
                packets_received = int(match.group(1))
                latency_ms = float(match.group(2))
                
                all_client_latencies.append(latency_ms)
                total_packets_received += packets_received
                break
    
    if not all_client_latencies:
        return 0, 0
        
    overall_avg_latency = statistics.mean(all_client_latencies)
    avg_packets_per_client = total_packets_received / num_clients

    return overall_avg_latency, avg_packets_per_client


def print_summary_report(num_clients):
    """Analyzes and prints the consolidated metrics to the terminal AND writes to file."""
    
    # 1. Clear the previous report file
    if os.path.exists(SUMMARY_TEXT_FILE):
        os.remove(SUMMARY_TEXT_FILE)

    min_cpu, median_cpu, max_cpu, avg_cpu = analyze_cpu_data(CPU_LOG_FILE)
    avg_latency, avg_packets = analyze_client_logs(num_clients)
    
    # Define the output format
    separator = "="*60
    
    write_to_file(separator, SUMMARY_TEXT_FILE, mode='w') # Use 'w' to start fresh
    write_to_file("✅ BASELINE TEST SUMMARY METRICS (Run Date: {})".format(time.strftime("%Y-%m-%d %H:%M:%S")), SUMMARY_TEXT_FILE)
    write_to_file(separator, SUMMARY_TEXT_FILE)

    # Define the data rows
    summary_data = [
        ["Overall Avg Latency", f"{avg_latency:.4f} ms", f"Target: <= 50 ms"],
        ["Avg Packets Received", f"{avg_packets:.0f}", f"Target: >= {RUN_DURATION * 20} (600)"],
        ["-------------------", "-------------------", "-------------------"],
        ["CPU Min", f"{min_cpu:.2f} %", ""],
        ["CPU Median", f"{median_cpu:.2f} %", ""],
        ["CPU Mean (Average)", f"{avg_cpu:.2f} %", f"Target: < 60 % "],
        ["CPU Max", f"{max_cpu:.2f} %", ""],
    ]

    # Print the formatted table
    write_to_file(f"{'Metric':<25}{'Value':<20}{'Acceptance Criteria'}", SUMMARY_TEXT_FILE)
    write_to_file("-" * 60, SUMMARY_TEXT_FILE)
    for metric, value, note in summary_data:
        write_to_file(f"{metric:<25}{value:<20}{note}", SUMMARY_TEXT_FILE)
    
    write_to_file(separator, SUMMARY_TEXT_FILE)
    write_to_file(f"Raw CPU utilization data is in: {os.path.basename(CPU_LOG_FILE)}", SUMMARY_TEXT_FILE)
    write_to_file(separator, SUMMARY_TEXT_FILE)


def main():
    ensure_log_dir()
    
    server_proc, server_pid = start_server()
    
    # Small delay and check to help psutil find the process reliably
    try:
        time.sleep(0.1) 
        psutil.Process(server_pid) 
        print(f"[MONITOR] Confirmed Server PID {server_pid} is active.")
    except psutil.NoSuchProcess:
        print("[MONITOR] WARNING: Server process not immediately found by psutil. Monitoring may fail.")
        
    # 2. Start CPU Monitoring Thread
    monitor_thread = Thread(
        target=monitor_cpu_usage, 
        args=(server_pid, RUN_DURATION, CPU_LOG_FILE)
    )
    monitor_thread.start()

    # 3. Start Clients
    client_procs = start_clients(NUM_CLIENTS)

    print(f"[BASELINE] Running test for {RUN_DURATION} seconds...")
    start_time = time.time()
    time.sleep(RUN_DURATION)
    end_time = time.time()

    # 4. Terminate all processes
    terminate_all(server_proc, client_procs)
    
    # 5. Wait for the monitoring thread to finish its logging
    monitor_thread.join()
    
    # 6. CONSOLIDATE AND PRINT ALL METRICS
    print_summary_report(NUM_CLIENTS)

    print("\n✅ BASELINE TEST COMPLETE")
    print(f"Duration: {end_time - start_time:.2f} seconds")
    print(f"Logs are saved in the '{LOG_DIR}/' directory.")
    print(f"Final Summary Report saved to: {os.path.basename(SUMMARY_TEXT_FILE)}")


if __name__ == "__main__":
    main()