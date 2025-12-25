import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load the JSON data for all scenarios
baseline_data = {
    "scenario": "Baseline",
    "timestamp": 1766649687,
    "duration": 60,
    "metrics": {
        "updates_per_sec": 20.2125,
        "bandwidth_kbps": 81.6566,
        "cpu_percent": 4.140350877192983,
        "latency": {
            "mean": 3.5419501133786846,
            "median": 1.0,
            "p95": 2.0
        },
        "jitter": {
            "mean": 1.7344724117651646,
            "median": 0.5940787623807813,
            "p95": 10.027223716914014
        },
        "position_error": {
            "mean": 0.017289820618111088,
            "median": 0.0,
            "p95": 0.0
        }
    }
}

loss_data = {
    "scenario": "Loss 2%",
   "timestamp": 1766686563,
    "duration": 60,
    "metrics": {
        "updates_per_sec": 19.8125,
        "bandwidth_kbps": 80.03996666666667,
        "cpu_percent": 2.257758620689655,
        "latency": {
            "mean": 2.6471083070452157,
            "median": 1.0,
            "p95": 1.0
        },
        "jitter": {
            "mean": 0.9025111153764117,
            "median": 0.5164413098106982,
            "p95": 0.8975583772335168
        },
        "position_error": {
            "mean": 0.005232177894048398,
            "median": 0.0,
            "p95": 0.0
        }
    }
}

delay_data = {
    "scenario": "Delay 100ms",
    "timestamp": 1766540503,
    "duration": 60,
    "metrics": {
        "updates_per_sec": 20.004166666666666,
        "bandwidth_kbps": 80.81493333333333,
        "cpu_percent": 2.9491666666666663,
        "latency": {
            "mean": 101.99583420120808,
            "median": 101.0,
            "p95": 102.0
        },
        "jitter": {
            "mean": 1.200678006016685,
            "median": 0.5384959005179737,
            "p95": 3.5484275893978605
        },
        "position_error": {
            "mean": 0.5019517018500483,
            "median": 0.0,
            "p95": 2.0
        }
    }
}

scenarios = [baseline_data, loss_data, delay_data]
scenario_names = ['Baseline', 'Loss 2%', 'Delay 100ms']
colors = ['#2ecc71', '#3498db', '#f39c12']


def create_comparison_plots():
    """Create comprehensive comparison plots across all scenarios"""

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
    for bar, val in zip(bars, updates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.2f}', ha='center', va='bottom', fontweight='bold')

    # 2. Bandwidth Consumption
    ax2 = plt.subplot(3, 3, 2)
    bandwidth = [s['metrics']['bandwidth_kbps'] for s in scenarios]
    bars = ax2.bar(scenario_names, bandwidth, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Bandwidth (kbps)', fontweight='bold')
    ax2.set_title('Network Bandwidth Usage', fontweight='bold', fontsize=12)
    ax2.grid(axis='y', alpha=0.3)
    for bar, val in zip(bars, bandwidth):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f'{val:.2f}', ha='center', va='bottom', fontweight='bold')

    # 3. CPU Utilization
    ax3 = plt.subplot(3, 3, 3)
    cpu = [s['metrics']['cpu_percent'] for s in scenarios]
    bars = ax3.bar(scenario_names, cpu, color=colors, alpha=0.7, edgecolor='black')
    ax3.axhline(y=60, color='red', linestyle='--', linewidth=2, label='Limit (60%)')
    ax3.set_ylabel('CPU Usage (%)', fontweight='bold')
    ax3.set_title('Server CPU Utilization', fontweight='bold', fontsize=12)
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)
    for bar, val in zip(bars, cpu):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f'{val:.2f}%', ha='center', va='bottom', fontweight='bold')

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
    ax4.set_xticklabels(scenario_names)
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
    ax5.set_xticklabels(scenario_names)
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
    ax6.set_xticklabels(scenario_names)
    ax6.legend()
    ax6.grid(axis='y', alpha=0.3)

    # 7. Performance Degradation (normalized to baseline)
    ax7 = plt.subplot(3, 3, 7)
    baseline_updates = baseline_data['metrics']['updates_per_sec']
    normalized_updates = [(s['metrics']['updates_per_sec'] / baseline_updates * 100)
                          for s in scenarios]

    bars = ax7.bar(scenario_names, normalized_updates, color=colors, alpha=0.7, edgecolor='black')
    ax7.axhline(y=100, color='green', linestyle='--', linewidth=2, label='Baseline')
    ax7.set_ylabel('Performance (%)', fontweight='bold')
    ax7.set_title('Relative Performance (Update Rate)', fontweight='bold', fontsize=12)
    ax7.legend()
    ax7.grid(axis='y', alpha=0.3)
    for bar, val in zip(bars, normalized_updates):
        ax7.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    # 8. Resource Efficiency (Updates per CPU%)
    ax8 = plt.subplot(3, 3, 8)
    efficiency = [s['metrics']['updates_per_sec'] / s['metrics']['cpu_percent']
                  for s in scenarios]
    bars = ax8.bar(scenario_names, efficiency, color=colors, alpha=0.7, edgecolor='black')
    ax8.set_ylabel('Updates/Sec per CPU%', fontweight='bold')
    ax8.set_title('CPU Efficiency', fontweight='bold', fontsize=12)
    ax8.grid(axis='y', alpha=0.3)
    for bar, val in zip(bars, efficiency):
        ax8.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f'{val:.2f}', ha='center', va='bottom', fontweight='bold')

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
    return fig


def create_individual_scenario_plots():
    """Create detailed plots for each scenario"""

    for scenario, color in zip(scenarios, colors):
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
        filename = f'scenario_{scenario["scenario"].replace(" ", "_").lower()}_detailed.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f'Saved: {filename}')


# Generate all plots
print("Generating comparison plots...")
comparison_fig = create_comparison_plots()
comparison_fig.savefig('all_scenarios_comparison.png', dpi=300, bbox_inches='tight')
print('Saved: all_scenarios_comparison.png')

print("\nGenerating individual scenario plots...")
create_individual_scenario_plots()

print("\nAll plots generated successfully!")
plt.show()