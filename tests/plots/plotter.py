import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Configuration
FILE_NAME = '../results/suite_report_latest.csv'
OUTPUT_IMAGE = 'suite_visualization.png'

def main():
    # 1. Check if file exists
    if not os.path.exists(FILE_NAME):
        print(f"Error: '{FILE_NAME}' not found.")
        print("Please ensure the CSV file is in the same directory as this script.")
        return

    # 2. Load the data
    try:
        df = pd.read_csv(FILE_NAME)
        # Strip whitespace from column names just in case
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # 3. Setup the figure (2x2 Grid)
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(14, 10))
    fig.suptitle('Test Suite Report Analysis', fontsize=16)

    # Styles
    colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3'] # Seaborn-ish muted colors
    grid_alpha = 0.3

    # --- Plot 1: Average Latency ---
    ax1 = axes[0, 0]
    bars1 = ax1.bar(df['Scenario'], df['Latency_Avg'], color=colors[0])
    ax1.set_title('Average Latency (ms)')
    ax1.set_ylabel('Time (ms)')
    ax1.grid(axis='y', alpha=grid_alpha)
    
    # Add values on top of bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom')

    # --- Plot 2: Average Jitter ---
    ax2 = axes[0, 1]
    bars2 = ax2.bar(df['Scenario'], df['Jitter_Avg'], color=colors[1])
    ax2.set_title('Average Jitter (ms)')
    ax2.set_ylabel('Time (ms)')
    ax2.grid(axis='y', alpha=grid_alpha)
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom')

    # --- Plot 3: Error Metrics (Avg vs 95th Percentile) ---
    ax3 = axes[1, 0]
    # Width of a single bar
    bar_width = 0.35
    import numpy as np
    indices = np.arange(len(df['Scenario']))
    
    rects1 = ax3.bar(indices - bar_width/2, df['Error_Avg'], bar_width, label='Error Avg', color=colors[2])
    rects2 = ax3.bar(indices + bar_width/2, df['Error_95'], bar_width, label='Error 95%', color='#E99695')
    
    ax3.set_title('Perceived Error (Avg vs 95%)')
    ax3.set_xticks(indices)
    ax3.set_xticklabels(df['Scenario'])
    ax3.legend()
    ax3.grid(axis='y', alpha=grid_alpha)

    # --- Plot 4: CPU Percent (Bandwidth substitute) ---
    # Note: Bandwidth column was missing in CSV, using CPU_Percent
    ax4 = axes[1, 1]
    bars4 = ax4.bar(df['Scenario'], df['CPU_Percent'], color=colors[3])
    ax4.set_title('CPU Usage (%)')
    ax4.set_ylabel('Percent')
    ax4.set_ylim(0, 100) # Assuming CPU is 0-100
    # Auto-scale if CPU is very low to make it readable, comment out above line if needed
    if df['CPU_Percent'].max() < 10:
        ax4.set_ylim(0, df['CPU_Percent'].max() * 1.5)
        
    ax4.grid(axis='y', alpha=grid_alpha)
    
    for bar in bars4:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom')

    # 4. Final Layout Adjustments
    # Rotate x-axis labels for all subplots to prevent overlap
    for ax in axes.flat:
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Make room for suptitle

    # 5. Save and Show
    print(f"Generating plot to {OUTPUT_IMAGE}...")
    plt.savefig(OUTPUT_IMAGE)
    print("Done. Displaying plot window...")
    plt.show()

if __name__ == "__main__":
    main()