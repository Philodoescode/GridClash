import os
import json
import glob
import sys
import csv
import subprocess
from datetime import datetime


def load_summaries(results_root):
    """
    Load test summaries. Prioritizes the consolidated all_scenarios_summary.json
    file but falls back to individual summary.json files if needed.
    """
    # Try consolidated file first
    consolidated_file = os.path.join(results_root, "all_scenarios_summary.json")
    if os.path.exists(consolidated_file):
        try:
            with open(consolidated_file, 'r') as f:
                data = json.load(f)
                if 'scenarios' in data and len(data['scenarios']) > 0:
                    print(f"[+] Loaded consolidated summary: {len(data['scenarios'])} scenarios")
                    # Convert to dict keyed by scenario name
                    return {s['scenario']: s for s in data['scenarios']}
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Error loading consolidated summary: {e}")
    
    # Fallback: Find all individual summary.json files in subdirectories
    print("[*] Falling back to individual summary.json files...")
    summaries = []
    for root, dirs, files in os.walk(results_root):
        if "summary.json" in files:
            with open(os.path.join(root, "summary.json"), 'r') as f:
                try:
                    data = json.load(f)
                    data['path'] = root
                    summaries.append(data)
                except:
                    pass
    
    # Sort by timestamp (newest last)
    summaries.sort(key=lambda x: x.get('timestamp', 0))
    
    # Get latest run for each scenario
    latest_scenarios = {}
    for s in summaries:
        latest_scenarios[s['scenario']] = s
    
    print(f"[+] Loaded {len(latest_scenarios)} scenarios from individual files")
    return latest_scenarios


def run_auto_plotter():
    """Run the auto plotter to generate all graphs."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    auto_plotter = os.path.join(base_dir, "plots", "auto_plotter.py")
    
    if os.path.exists(auto_plotter):
        print("\n" + "=" * 50)
        print("[*] Running Auto Plotter to generate graphs...")
        print("=" * 50)
        try:
            result = subprocess.run(
                [sys.executable, auto_plotter],
                capture_output=True,
                text=True,
                cwd=base_dir
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"[WARN] Auto plotter errors:\n{result.stderr}")
        except Exception as e:
            print(f"[WARN] Failed to run auto plotter: {e}")
    else:
        print(f"[WARN] Auto plotter not found at: {auto_plotter}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_root = os.path.join(base_dir, "results")
    
    # Load summaries (prefers consolidated file)
    latest_scenarios = load_summaries(results_root)

    # Order of Scenarios
    order = ["Baseline", "Loss 2%", "Loss 5%", "Delay 100ms"]
    
    print("\n" + "="*100)
    print(f"GRIDCLASH TEST SUITE REPORT - {datetime.now().strftime('%d/%m %H:%M')}")
    print("="*100)
    
    # Header
    header = f"{'Scenario':<15} | {'Lat(Avg)':<10} | {'Jit(Avg)':<10} | {'Err(Avg)':<10} | {'Err(95%)':<10} | {'CPU%':<6} | {'Status'}"
    print(header)
    print("-" * 100)
    
    csv_rows = []
    csv_rows.append(["Scenario", "Latency_Avg", "Jitter_Avg", "Error_Avg", "Error_95", "CPU_Percent", "Status"])

    scenarios_found = 0
    for name in order:
        if name in latest_scenarios:
            scenarios_found += 1
            data = latest_scenarios[name]
            m = data['metrics']
            
            lat = m['latency']['mean']
            jit = m['jitter']['mean']
            err_avg = m['position_error']['mean']
            err_95 = m['position_error']['p95']
            cpu = m['cpu_percent']
            
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
    print(f"Total scenarios: {scenarios_found}/{len(order)}")
    
    # Save to file
    summary_file = os.path.join(results_root, "suite_report_latest.csv")
    with open(summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"\nSaved suite report to: {summary_file}")
    print("="*100)
    
    # Run auto plotter to generate all graphs
    run_auto_plotter()

if __name__ == "__main__":
    main()
