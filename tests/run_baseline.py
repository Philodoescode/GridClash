"""
Baseline Test Runner for GridClash with CPU Monitoring
------------------------------------------------------
Runs the server and multiple clients locally, collects logs, and prints summary.
"""

import os
import subprocess
import time
import csv
from threading import Thread
import psutil

# Configuration
RUN_DURATION = 30       # seconds
NUM_CLIENTS = 4         # number of clients to simulate
LOG_DIR = "logs"
CPU_LOG_FILE = os.path.join(LOG_DIR, "server_cpu_usage.csv")

# CALCULATE ABSOLUTE PATHS FOR ROBUSTNESS (FIXES Errno 2: No such file)
# os.path.dirname(__file__) gets the directory of run_baseline.py (i.e., '.../GridClash/tests')
# os.path.join(..., os.pardir) moves up one level to the project root ('.../GridClash')
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

SERVER_PATH = os.path.join(PROJECT_ROOT, "src", "server.py")
CLIENT_PATH = os.path.join(PROJECT_ROOT, "src", "client.py")

SERVER_CMD = ["python", SERVER_PATH]
CLIENT_CMD = ["python", CLIENT_PATH]


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
    POLL_INTERVAL = 0.5  # Sample every half second
    
    print(f"[MONITOR] Starting CPU monitoring of PID {pid}, logging to {log_filename}")

    with open(log_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp_s', 'Relative_Time_s', 'CPU_Usage_Percent'])  # Header

        start_time = time.time()
        
        while time.time() < end_time and process.is_running():
            try:
                # cpu_percent waits for the interval and measures usage over that period
                cpu_percent = process.cpu_percent(interval=POLL_INTERVAL) 
                
                current_time = time.time()
                relative_time = current_time - start_time
                
                writer.writerow([current_time, relative_time, cpu_percent])
            except psutil.NoSuchProcess:
                print("[MONITOR] Server process terminated during monitoring.")
                break


def start_server():
    """Start the server process and return its PID."""
    print("[BASELINE] Starting server...")
    # Open log file with standard parameters (subprocess handles writing)
    server_log = open(os.path.join(LOG_DIR, "server.log"), "w")
    
    # ADDED '-u' FLAG to Python command (unbuffered mode)
    server_cmd_unbuffered = ["python", "-u", SERVER_PATH]
    
    # Store the subprocess object
    server_proc = subprocess.Popen(server_cmd_unbuffered, stdout=server_log, stderr=server_log)
    
    server_pid = server_proc.pid  # Captured PID
    print(f"[MONITOR] Server PID: {server_pid}")

    time.sleep(1.0)  # Give the server time to start up
    return server_proc, server_pid  # Return process object and PID


def start_clients(num_clients=2):
    """Start multiple clients."""
    print(f"[BASELINE] Launching {num_clients} clients...")
    clients = []
    for i in range(num_clients):
        log_path = os.path.join(LOG_DIR, f"client_{i}.log")
        client_log = open(log_path, "w")
        cmd = CLIENT_CMD + ["--id", str(i), "--duration", str(RUN_DURATION)]
        proc = subprocess.Popen(cmd, stdout=client_log, stderr=client_log)
        clients.append(proc)
        time.sleep(0.3)
    return clients


def terminate_all(server_proc, client_procs):
    """Terminate all subprocesses cleanly (cross-platform)."""
    print("[BASELINE] Stopping all processes...")

    # Attempt graceful termination first
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

    # Force kill any that are still alive
    for p in client_procs:
        if p.poll() is None:
            p.kill()

    if server_proc.poll() is None:
        server_proc.kill()


def main():
    ensure_log_dir()
    
    # 1. Start Server and get PID
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
    time.sleep(RUN_DURATION)  # Wait for the test duration
    end_time = time.time()

    # 4. Terminate all processes
    terminate_all(server_proc, client_procs)
    
    # 5. Wait for the monitoring thread to finish its logging
    monitor_thread.join()

    print("\n✅ BASELINE TEST COMPLETE")
    print(f"Duration: {end_time - start_time:.2f} seconds")
    print(f"Logs are saved in the '{LOG_DIR}/' directory.")
    print("Check client_*.log for packet counts and latency averages.")
    print(f"**Check {os.path.basename(CPU_LOG_FILE)} for raw CPU utilization data.**")


if __name__ == "__main__":
    # Ensure this script is run from the 'tests/' directory for path resolution to work.
    main()