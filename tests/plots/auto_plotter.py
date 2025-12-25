#!/usr/bin/env python3
"""
Auto Plotter - Generates all plots from plotter.py and plotter2.py
Saves output to a timestamped folder in the plots directory.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def get_timestamp_folder_name():
    """Generate a human-readable timestamp folder name like '25-12_09-00'"""
    now = datetime.now()
    return now.strftime("%d-%m_%H-%M")


def create_output_dir():
    """Create the timestamped output directory"""
    plots_dir = Path(__file__).parent
    timestamp = get_timestamp_folder_name()
    output_dir = plots_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[+] Output directory: {output_dir}")
    return output_dir


def load_summary_data():
    """Load all summary.json files from results directory"""
    base_dir = Path(__file__).parent.parent
    results_root = base_dir / "results"
    
    # Try to load consolidated summary first
    consolidated_file = results_root / "all_scenarios_summary.json"
    if consolidated_file.exists():
        with open(consolidated_file, 'r') as f:
            data = json.load(f)
            if 'scenarios' in data and len(data['scenarios']) > 0:
                print(f"[+] Loaded consolidated summary with {len(data['scenarios'])} scenarios")
                return data['scenarios']
    
    # Fallback: Load individual summary.json files
    summaries = []
    for root, dirs, files in os.walk(results_root):
        if "summary.json" in files:
            with open(os.path.join(root, "summary.json"), 'r') as f:
                try:
                    data = json.load(f)
                    summaries.append(data)
                except Exception as e:
                    print(f"[WARN] Error loading {root}/summary.json: {e}")
    
    # Sort by timestamp (newest last) and get latest for each scenario
    summaries.sort(key=lambda x: x.get('timestamp', 0))
    
    latest_scenarios = {}
    for s in summaries:
        latest_scenarios[s['scenario']] = s
    
    print(f"[+] Loaded {len(latest_scenarios)} scenarios from individual summary files")
    return list(latest_scenarios.values())


def load_csv_data():
    """Load suite_report_latest.csv if exists"""
    base_dir = Path(__file__).parent.parent
    csv_file = base_dir / "results" / "suite_report_latest.csv"
    
    if csv_file.exists():
        try:
            df = pd.read_csv(csv_file)
            print(f"[+] Loaded CSV with {len(df)} scenarios")
            return df
        except Exception as e:
            print(f"[WARN] Error loading CSV: {e}")
    return None


# ==============================================================================
# Plots from plotter.py - Suite Report Analysis
# ==============================================================================

def plot_suite_report(df, output_dir):
    """Generate suite report plots (from plotter.py)"""
    if df is None or len(df) == 0:
        print("[WARN] No CSV data available for suite report plots")
        return
    
    # Set up the figure with 3 subplots (rows)
    fig, ax = plt.subplots(3, 1, figsize=(10, 15))
    fig.suptitle('Test Suite Summary Analysis', fontsize=16)
    
    # X-axis positions
    scenarios = df['Scenario']
    x = np.arange(len(scenarios))
    width = 0.35

    # --- Plot 1: Latency vs Jitter ---
    rects1 = ax[0].bar(x - width/2, df['Latency_Avg'], width, label='Avg Latency (ms)', color='royalblue')
    rects2 = ax[0].bar(x + width/2, df['Jitter_Avg'], width, label='Avg Jitter (ms)', color='orange')
    
    ax[0].set_ylabel('Time (ms)')
    ax[0].set_title('Network Performance (Lower is Better)')
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(scenarios)
    ax[0].legend()
    ax[0].grid(axis='y', linestyle='--', alpha=0.7)
    ax[0].bar_label(rects1, padding=3, fmt='%.1f')
    ax[0].bar_label(rects2, padding=3, fmt='%.1f')

    # --- Plot 2: Error Rates ---
    rects3 = ax[1].bar(x - width/2, df['Error_Avg'], width, label='Error Avg', color='crimson')
    rects4 = ax[1].bar(x + width/2, df['Error_95'], width, label='Error 95th %', color='salmon')

    ax[1].set_ylabel('Error Metric')
    ax[1].set_title('Error Rates (Lower is Better)')
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(scenarios)
    ax[1].legend()
    ax[1].grid(axis='y', linestyle='--', alpha=0.7)
    ax[1].bar_label(rects3, padding=3, fmt='%.2f')
    ax[1].bar_label(rects4, padding=3, fmt='%.2f')

    # --- Plot 3: CPU Usage ---
    rects5 = ax[2].bar(x, df['CPU_Percent'], width*1.5, label='CPU Usage %', color='green')

    ax[2].set_ylabel('CPU Percent')
    ax[2].set_title('System Resource Usage')
    ax[2].set_xticks(x)
    ax[2].set_xticklabels(scenarios)
    ax[2].legend()
    ax[2].grid(axis='y', linestyle='--', alpha=0.7)
    ax[2].bar_label(rects5, padding=3, fmt='%.1f%%')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    output_file = output_dir / "suite_report_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_file}")
    plt.close()


# ==============================================================================
# Plots from plotter2.py - Scenario Comparison and Individual Analysis
# ==============================================================================

def create_comparison_plots(scenarios, output_dir):
    """Create comprehensive comparison plots across all scenarios (from plotter2.py)"""
    if not scenarios or len(scenarios) == 0:
        print("[WARN] No scenario data available for comparison plots")
        return
    
    scenario_names = [s['scenario'] for s in scenarios]
    colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6'][:len(scenarios)]

    fig = plt.figure(figsize=(16, 12))

    # 1. Updates Per Second Comparison
    ax1 = plt.subplot(3, 3, 1)
    updates = [s['metrics']['updates_per_sec'] for s in scenarios]
    bars = ax1.bar(scenario_names, updates, color=colors, alpha=0.7, edgecolor='black')
    ax1.axhline(y=20, color='red', linestyle='--', linewidth=2, label='Target (20 ups)')
    ax1.set_ylabel('Updates/Sec', fontweight='bold')
    ax1.set_title('Update Rate Performance', fontweight='bold', fontsize=12)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    for bar, val in zip(bars, updates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=8)

    # 2. Bandwidth Consumption
    ax2 = plt.subplot(3, 3, 2)
    bandwidth = [s['metrics']['bandwidth_kbps'] for s in scenarios]
    bars = ax2.bar(scenario_names, bandwidth, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Bandwidth (kbps)', fontweight='bold')
    ax2.set_title('Network Bandwidth Usage', fontweight='bold', fontsize=12)
    ax2.grid(axis='y', alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    for bar, val in zip(bars, bandwidth):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f'{val:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=8)

    # 3. CPU Utilization
    ax3 = plt.subplot(3, 3, 3)
    cpu = [s['metrics']['cpu_percent'] for s in scenarios]
    bars = ax3.bar(scenario_names, cpu, color=colors, alpha=0.7, edgecolor='black')
    ax3.axhline(y=60, color='red', linestyle='--', linewidth=2, label='Limit (60%)')
    ax3.set_ylabel('CPU Usage (%)', fontweight='bold')
    ax3.set_title('Server CPU Utilization', fontweight='bold', fontsize=12)
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    for bar, val in zip(bars, cpu):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f'{val:.2f}%', ha='center', va='bottom', fontweight='bold', fontsize=8)

    # 4. Latency Distribution
    ax4 = plt.subplot(3, 3, 4)
    x = np.arange(len(scenario_names))
    width = 0.25

    mean_latency = [s['metrics']['latency']['mean'] for s in scenarios]
    median_latency = [s['metrics']['latency']['median'] for s in scenarios]
    p95_latency = [s['metrics']['latency']['p95'] for s in scenarios]

    ax4.bar(x - width, mean_latency, width, label='Mean', color='#3498db', alpha=0.8)
    ax4.bar(x, median_latency, width, label='Median', color='#9b59b6', alpha=0.8)
    ax4.bar(x + width, p95_latency, width, label='95th %ile', color='#e67e22', alpha=0.8)

    ax4.set_ylabel('Latency (ms)', fontweight='bold')
    ax4.set_title('Latency Distribution', fontweight='bold', fontsize=12)
    ax4.set_xticks(x)
    ax4.set_xticklabels(scenario_names, rotation=45, ha='right')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)

    # 5. Jitter Distribution
    ax5 = plt.subplot(3, 3, 5)
    mean_jitter = [s['metrics']['jitter']['mean'] for s in scenarios]
    median_jitter = [s['metrics']['jitter']['median'] for s in scenarios]
    p95_jitter = [s['metrics']['jitter']['p95'] for s in scenarios]

    ax5.bar(x - width, mean_jitter, width, label='Mean', color='#3498db', alpha=0.8)
    ax5.bar(x, median_jitter, width, label='Median', color='#9b59b6', alpha=0.8)
    ax5.bar(x + width, p95_jitter, width, label='95th %ile', color='#e67e22', alpha=0.8)

    ax5.set_ylabel('Jitter (ms)', fontweight='bold')
    ax5.set_title('Timing Jitter Distribution', fontweight='bold', fontsize=12)
    ax5.set_xticks(x)
    ax5.set_xticklabels(scenario_names, rotation=45, ha='right')
    ax5.legend()
    ax5.grid(axis='y', alpha=0.3)

    # 6. Position Error Distribution
    ax6 = plt.subplot(3, 3, 6)
    mean_error = [s['metrics']['position_error']['mean'] for s in scenarios]
    median_error = [s['metrics']['position_error']['median'] for s in scenarios]
    p95_error = [s['metrics']['position_error']['p95'] for s in scenarios]

    ax6.bar(x - width, mean_error, width, label='Mean', color='#3498db', alpha=0.8)
    ax6.bar(x, median_error, width, label='Median', color='#9b59b6', alpha=0.8)
    ax6.bar(x + width, p95_error, width, label='95th %ile', color='#e67e22', alpha=0.8)

    ax6.set_ylabel('Position Error (units)', fontweight='bold')
    ax6.set_title('Synchronization Error', fontweight='bold', fontsize=12)
    ax6.set_xticks(x)
    ax6.set_xticklabels(scenario_names, rotation=45, ha='right')
    ax6.legend()
    ax6.grid(axis='y', alpha=0.3)

    # 7. Performance Degradation (normalized to baseline)
    ax7 = plt.subplot(3, 3, 7)
    baseline_updates = scenarios[0]['metrics']['updates_per_sec'] if scenarios else 1
    normalized_updates = [(s['metrics']['updates_per_sec'] / baseline_updates * 100)
                          for s in scenarios]

    bars = ax7.bar(scenario_names, normalized_updates, color=colors, alpha=0.7, edgecolor='black')
    ax7.axhline(y=100, color='green', linestyle='--', linewidth=2, label='Baseline')
    ax7.set_ylabel('Performance (%)', fontweight='bold')
    ax7.set_title('Relative Performance (Update Rate)', fontweight='bold', fontsize=12)
    ax7.legend()
    ax7.grid(axis='y', alpha=0.3)
    ax7.tick_params(axis='x', rotation=45)
    for bar, val in zip(bars, normalized_updates):
        ax7.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f'{val:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=8)

    # 8. Resource Efficiency (Updates per CPU%)
    ax8 = plt.subplot(3, 3, 8)
    efficiency = []
    for s in scenarios:
        cpu_val = s['metrics']['cpu_percent']
        if cpu_val > 0:
            efficiency.append(s['metrics']['updates_per_sec'] / cpu_val)
        else:
            efficiency.append(0)
    bars = ax8.bar(scenario_names, efficiency, color=colors, alpha=0.7, edgecolor='black')
    ax8.set_ylabel('Updates/Sec per CPU%', fontweight='bold')
    ax8.set_title('CPU Efficiency', fontweight='bold', fontsize=12)
    ax8.grid(axis='y', alpha=0.3)
    ax8.tick_params(axis='x', rotation=45)
    for bar, val in zip(bars, efficiency):
        ax8.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f'{val:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=8)

    # 9. Latency vs Position Error scatter
    ax9 = plt.subplot(3, 3, 9)
    latencies = [s['metrics']['latency']['mean'] for s in scenarios]
    errors = [s['metrics']['position_error']['mean'] for s in scenarios]

    for i, (lat, err, name, color) in enumerate(zip(latencies, errors, scenario_names, colors)):
        ax9.scatter(lat, err, s=300, color=color, alpha=0.6, edgecolor='black', linewidth=2)
        ax9.annotate(name, (lat, err), xytext=(10, 10), textcoords='offset points',
                     fontweight='bold', fontsize=9)

    ax9.set_xlabel('Mean Latency (ms)', fontweight='bold')
    ax9.set_ylabel('Mean Position Error (units)', fontweight='bold')
    ax9.set_title('Latency vs Synchronization Error', fontweight='bold', fontsize=12)
    ax9.grid(True, alpha=0.3)

    plt.tight_layout()
    
    output_file = output_dir / "all_scenarios_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_file}")
    plt.close()


def create_individual_scenario_plots(scenarios, output_dir):
    """Create detailed plots for each scenario (from plotter2.py)"""
    if not scenarios or len(scenarios) == 0:
        print("[WARN] No scenario data available for individual plots")
        return
    
    colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']

    for idx, scenario in enumerate(scenarios):
        color = colors[idx % len(colors)]
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Detailed Analysis: {scenario["scenario"]}',
                     fontsize=16, fontweight='bold')

        # Latency metrics
        ax1 = axes[0, 0]
        latency_data = scenario['metrics']['latency']
        metrics = ['Mean', 'Median', '95th %ile']
        values = [latency_data['mean'], latency_data['median'], latency_data['p95']]
        bars = ax1.bar(metrics, values, color=[color] * 3, alpha=0.7, edgecolor='black')
        ax1.set_ylabel('Latency (ms)', fontweight='bold')
        ax1.set_title('Latency Metrics', fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        for bar, val in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                     f'{val:.2f}', ha='center', va='bottom', fontweight='bold')

        # Jitter metrics
        ax2 = axes[0, 1]
        jitter_data = scenario['metrics']['jitter']
        values = [jitter_data['mean'], jitter_data['median'], jitter_data['p95']]
        bars = ax2.bar(metrics, values, color=[color] * 3, alpha=0.7, edgecolor='black')
        ax2.set_ylabel('Jitter (ms)', fontweight='bold')
        ax2.set_title('Timing Jitter Metrics', fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        for bar, val in zip(bars, values):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                     f'{val:.2f}', ha='center', va='bottom', fontweight='bold')

        # Position error metrics
        ax3 = axes[1, 0]
        error_data = scenario['metrics']['position_error']
        values = [error_data['mean'], error_data['median'], error_data['p95']]
        bars = ax3.bar(metrics, values, color=[color] * 3, alpha=0.7, edgecolor='black')
        ax3.set_ylabel('Position Error (units)', fontweight='bold')
        ax3.set_title('Synchronization Error Metrics', fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        for bar, val in zip(bars, values):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.05,
                     f'{val:.4f}' if val < 1 else f'{val:.2f}',
                     ha='center', va='bottom', fontweight='bold')

        # Summary metrics
        ax4 = axes[1, 1]
        summary_metrics = ['Updates/Sec', 'Bandwidth\n(kbps)', 'CPU Usage\n(%)']
        summary_values = [
            scenario['metrics']['updates_per_sec'],
            scenario['metrics']['bandwidth_kbps'],
            scenario['metrics']['cpu_percent']
        ]
        bars = ax4.bar(summary_metrics, summary_values, color=[color] * 3, alpha=0.7, edgecolor='black')
        ax4.set_title('System Resource Metrics', fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)
        for bar, val in zip(bars, summary_values):
            ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(summary_values) * 0.02,
                     f'{val:.2f}', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()

        # Save the figure
        safe_name = scenario["scenario"].replace(" ", "_").replace("%", "pct").lower()
        filename = output_dir / f'scenario_{safe_name}_detailed.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f'[+] Saved: {filename}')
        plt.close()


def main():
    print("=" * 60)
    print("    AUTO PLOTTER - GridClash Test Suite Visualization")
    print("=" * 60)
    
    # Create output directory
    output_dir = create_output_dir()
    
    # Load data
    scenarios = load_summary_data()
    csv_df = load_csv_data()
    
    # Generate all plots
    print("\n[*] Generating suite report analysis...")
    plot_suite_report(csv_df, output_dir)
    
    print("\n[*] Generating scenario comparison plots...")
    create_comparison_plots(scenarios, output_dir)
    
    print("\n[*] Generating individual scenario detailed plots...")
    create_individual_scenario_plots(scenarios, output_dir)
    
    print("\n" + "=" * 60)
    print(f"[+] All plots generated successfully in: {output_dir}")
    print("=" * 60)
    
    return output_dir


if __name__ == "__main__":
    main()
