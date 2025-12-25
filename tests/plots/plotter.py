import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

def plot_suite_report(csv_file):
    if not os.path.exists(csv_file):
        print(f"[!] Error: File {csv_file} not found.")
        return

    # Load Data
    try:
        df = pd.read_csv(csv_file)
        print("Data Loaded Successfully:")
        print(df)
    except Exception as e:
        print(f"[!] Error reading CSV: {e}")
        return

    # Set up the figure with 3 subplots (rows)
    fig, ax = plt.subplots(3, 1, figsize=(10, 15))
    fig.suptitle(f'Test Suite Summary: {os.path.basename(csv_file)}', fontsize=16)
    
    # X-axis positions
    scenarios = df['Scenario']
    x = np.arange(len(scenarios))
    width = 0.35  # Width of bars

    # --- Plot 1: Latency vs Jitter ---
    # Grouped bar chart
    rects1 = ax[0].bar(x - width/2, df['Latency_Avg'], width, label='Avg Latency (ms)', color='royalblue')
    rects2 = ax[0].bar(x + width/2, df['Jitter_Avg'], width, label='Avg Jitter (ms)', color='orange')
    
    ax[0].set_ylabel('Time (ms)')
    ax[0].set_title('Network Performance (Lower is Better)')
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(scenarios)
    ax[0].legend()
    ax[0].grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add value labels on top of bars
    ax[0].bar_label(rects1, padding=3, fmt='%.1f')
    ax[0].bar_label(rects2, padding=3, fmt='%.1f')

    # --- Plot 2: Error Rates ---
    # Grouped bar chart for Average vs 95th Percentile errors
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

    # Adjust layout
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save output
    output_file = "suite_report_analysis.png"
    plt.savefig(output_file)
    print(f"\n[+] Analysis saved to: {output_file}")
    plt.show()

if __name__ == "__main__":
    # Check if a filename was provided, otherwise default to the name in your snippet
    target_file = "suite_report_latest.csv"
    
    if len(sys.argv) > 1:
        target_file = sys.argv[1]

    plot_suite_report(target_file)