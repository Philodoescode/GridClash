"""
Simplified Baseline Test Runner for GridClash (no psutil dependency)
--------------------------------------------------------------------
Runs the server and multiple clients locally, collects logs, and prints summary.
"""

import os
import subprocess
import time
import signal

# Configuration
RUN_DURATION = 30      # seconds
NUM_CLIENTS = 4        # number of clients to simulate
SERVER_CMD = ["python", "src/server.py"]
CLIENT_CMD = ["python", "src/client.py"]
LOG_DIR = "logs"


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def start_server():
    """Start the server process."""
    print("[BASELINE] Starting server...")
    server_log = open(os.path.join(LOG_DIR, "server.log"), "w")
    server_proc = subprocess.Popen(SERVER_CMD, stdout=server_log, stderr=server_log)
    time.sleep(1.0)
    return server_proc


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

    for p in client_procs:
        try:
            p.terminate()  # Windows-safe
        except Exception:
            pass

    try:
        server_proc.terminate()  # Windows-safe
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
    server_proc = start_server()
    client_procs = start_clients(NUM_CLIENTS)

    print(f"[BASELINE] Running test for {RUN_DURATION} seconds...")
    start_time = time.time()
    time.sleep(RUN_DURATION)
    end_time = time.time()

    terminate_all(server_proc, client_procs)

    print("\n✅ BASELINE TEST COMPLETE")
    print(f"Duration: {end_time - start_time:.2f} seconds")
    print("Logs are saved in the 'logs/' directory.")
    print("Check client_*.log for packet counts and latency averages.")


if __name__ == "__main__":
    main()
