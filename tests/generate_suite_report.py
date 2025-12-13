import os
import json
import glob
import sys
from datetime import datetime

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_root = os.path.join(base_dir, "results")
    
    # Find all summary.json files in subdirectories
    summaries = []
    for root, dirs, files in os.walk(results_root):
        if "summary.json" in files:
            with open(os.path.join(root, "summary.json"), 'r') as f:
                try:
                    data = json.load(f)
                    data['path'] = root # Store path to sort by time if needed
                    summaries.append(data)
                except:
                    pass
    
    # Sort by timestamp (newest last)
    summaries.sort(key=lambda x: x.get('timestamp', 0))
    
    # We might have multiple runs. The user wants "average results".
    # We will display the *latest* run for each scenario.
    latest_scenarios = {}
    for s in summaries:
        latest_scenarios[s['scenario']] = s

    # Order of Scenarios
    order = ["Baseline", "Loss 2%", "Loss 5%", "Delay 100ms"]
    
    print("\n" + "="*100)
    print(f"GRIDCLASH TEST SUITE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    # Header
    # Scenario | Latency (Avg) | Jitter (Avg) | Error (Avg) | Error (95%) | CPU% | Pass?
    header = f"{'Scenario':<15} | {'Lat(Avg)':<10} | {'Jit(Avg)':<10} | {'Err(Avg)':<10} | {'Err(95%)':<10} | {'CPU%':<6} | {'Status'}"
    print(header)
    print("-" * 100)
    
    csv_rows = []
    csv_rows.append(["Scenario", "Latency_Avg", "Jitter_Avg", "Error_Avg", "Error_95", "CPU_Percent", "Status"])

    for name in order:
        if name in latest_scenarios:
            data = latest_scenarios[name]
            m = data['metrics']
            
            lat = m['latency']['mean']
            jit = m['jitter']['mean']
            err_avg = m['position_error']['mean']
            err_95 = m['position_error']['p95']
            cpu = m['cpu_percent']
            
            # Simple Pass/Fail check redone here or trust the runner?
            # The runner doesn't save "Pass/Fail" explicitly in the json boolean, but we can infer or just print stats.
            # We'll just print stats.
            
            status = "DONE" # Placeholder, real check requires re-evaluating criteria stored in json
            
            # Check criteria
            passed = True
            c = data.get('criteria', {})
            if "avg_latency_ms" in c and lat > c["avg_latency_ms"]: passed = False
            if "mean_position_error" in c and err_avg > c["mean_position_error"]: passed = False
            if "p95_position_error" in c and err_95 > c["p95_position_error"]: passed = False
            if "cpu_percent" in c and cpu >= c["cpu_percent"]: passed = False
            
            status = "PASS" if passed else "FAIL"

            line = f"{name:<15} | {lat:<10.2f} | {jit:<10.2f} | {err_avg:<10.4f} | {err_95:<10.4f} | {cpu:<6.1f} | {status}"
            print(line)
            
            csv_rows.append([name, lat, jit, err_avg, err_95, cpu, status])
        else:
            print(f"{name:<15} | {'N/A':<10} | {'N/A':<10} | {'N/A':<10} | {'N/A':<10} | {'N/A':<6} | N/A")

    print("-" * 100)
    
    # Save to file
    summary_file = os.path.join(results_root, "suite_report_latest.csv")
    import csv
    with open(summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"\nSaved suite report to: {summary_file}")
    print("="*100)

if __name__ == "__main__":
    main()
