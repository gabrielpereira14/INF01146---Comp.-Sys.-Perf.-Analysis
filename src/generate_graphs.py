import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_ROOT = f"{PROJECT_ROOT}/data"

USER_FOLDERS = [
    name for name in os.listdir(DATA_ROOT)
    if os.path.isdir(os.path.join(DATA_ROOT, name))
]

if not USER_FOLDERS:
    sys.stderr.write("No user folders found inside /data.\n")
    sys.exit(1)

DATE_FMT = mdates.DateFormatter("%d/%m")

for user_name in USER_FOLDERS:
    print(f"\nProcessing user: {user_name}")

    image_dir = f"{PROJECT_ROOT}/{user_name}/images"
    os.makedirs(image_dir, exist_ok=True)

    csv_file_name = "vpn_test_results.csv"
    csv_file_path = f"{DATA_ROOT}/{user_name}/{csv_file_name}"

    if not os.path.exists(csv_file_path):
        print(f"Skipping {user_name}: missing CSV.")
        continue

    df = pd.read_csv(csv_file_path, parse_dates=["timestamp"])
    df["date"] = df["timestamp"].dt.date

    vpn_fixed_day = df[df['test_label'] == 'VPN_ON']['timestamp'].min()

    df_jitter = df.query('timestamp >= "2025.10.01"').copy()
    jitter_data = df_jitter['ping_jitter_ms']
    upper_bound = jitter_data.quantile(0.99)

    df_jitter["timestamp"] = pd.to_datetime(df_jitter["timestamp"])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.lineplot(data=df_jitter.query("test_label == 'VPN_ON'"),
                 x="timestamp", y="ping_jitter_ms", ax=axes[0])
    axes[0].set_title("Jitter with VPN")
    axes[0].set_ylabel("ms")
    axes[0].set_xlabel("Date")

    sns.lineplot(data=df_jitter.query("test_label == 'VPN_OFF'"),
                 x="timestamp", y="ping_jitter_ms", ax=axes[1])
    axes[1].set_title("Jitter without VPN")
    axes[1].set_ylabel("ms")
    axes[1].set_xlabel("Date")

    for ax in axes:
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(DATE_FMT)
        ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig(f"{image_dir}/jitter_comparison_{user_name}.png", dpi=300)
    plt.close()

    df_jitter = df_jitter[(jitter_data <= upper_bound)]
    plt.figure(figsize=(8, 6))
    sns.violinplot(data=df_jitter, x='test_label', y='ping_jitter_ms', cut=0)
    plt.title('Jitter Comparison: VPN ON vs VPN OFF')
    plt.xlabel('Test Condition')
    plt.ylabel('Ping Jitter (ms)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"{image_dir}/jitter_comparison_violin_{user_name}.png", dpi=300)
    plt.close()

    df_tcp = df.query("tcp_throughput_mbps.notna()").copy()
    df_tcp["timestamp"] = pd.to_datetime(df_tcp["timestamp"])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.lineplot(data=df_tcp.query("test_label == 'VPN_ON'"),
                 x="timestamp", y="tcp_throughput_mbps", ax=axes[0])
    axes[0].set_title("Throughput with VPN")
    axes[0].set_ylabel("Mbps")
    axes[0].set_xlabel("Date")

    sns.lineplot(data=df_tcp.query("test_label == 'VPN_OFF'"),
                 x="timestamp", y="tcp_throughput_mbps", ax=axes[1])
    axes[1].set_title("Throughput without VPN")
    axes[1].set_ylabel("Mbps")
    axes[1].set_xlabel("Date")

    for ax in axes:
        ax.xaxis.set_major_formatter(DATE_FMT)
        ax.tick_params(axis='x', rotation=45)
        ax.xaxis.set_major_locator(mdates.DayLocator())

    plt.tight_layout()
    plt.savefig(f"{image_dir}/throughput_comparison_{user_name}.png", dpi=300)
    plt.close()

    df_latency = df[df['timestamp'] >= vpn_fixed_day].copy()
    latency_data = df['ping_latency_ms']
    lb = latency_data.quantile(0.01)
    ub = latency_data.quantile(0.99)
    df_latency = df_latency[(latency_data >= lb) & (latency_data <= ub)]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.violinplot(
        data=df_latency.query("test_label == 'VPN_ON'"),
        x="test_label", y="ping_latency_ms", ax=axes[0], cut=0
    )
    axes[0].set_title("Latency with VPN")

    sns.violinplot(
        data=df_latency.query("test_label == 'VPN_OFF'"),
        x="test_label", y="ping_latency_ms", ax=axes[1], cut=0
    )
    axes[1].set_title("Latency without VPN")

    plt.tight_layout()
    plt.savefig(f"{image_dir}/latency_violin_{user_name}.png", dpi=300)
    plt.close()

    df_latency['date'] = df_latency['timestamp'].dt.date
    df_latency['hour'] = df_latency['timestamp'].dt.hour

    pivot = df_latency.pivot_table(
        values='ping_latency_ms',
        index='date',
        columns='hour',
        aggfunc='mean'
    )

    plt.figure(figsize=(14, 8))
    sns.heatmap(
        pivot, annot=True, fmt=".1f",
        cmap="rocket_r", linewidths=.5
    )
    plt.xlabel("Hour of the Day")
    plt.ylabel("Date")
    plt.title("Heatmap of Average Latency")
    plt.tight_layout()
    plt.savefig(f"{image_dir}/latency_heatmap_{user_name}.png", dpi=300)
    plt.close()

    df_loss = df.query("`ping_loss_%` != 0.0 ")
    df_res = df[df['timestamp'] >= vpn_fixed_day].copy()
    df_res = df_res.set_index('timestamp')
    avg_on = df_res.query("test_label == 'VPN_ON'").resample('H').mean(numeric_only=True)
    avg_off = df_res.query("test_label == 'VPN_OFF'").resample('H').mean(numeric_only=True)

    print(
        f"[{user_name}] Loss events: VPN_ON -> "
        f"{len(df_loss.query('test_label == \"VPN_ON\"'))}   "
        f"VPN_OFF -> {len(df_loss.query('test_label == \"VPN_OFF\"'))}"
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    sns.scatterplot(
        data=df_latency.query("test_label == 'VPN_ON'"),
        x="timestamp", y="ping_loss_%", ax=axes[0], alpha=0.8, s=50
    )
    axes[0].set_title("Loss with VPN")
    axes[0].set_ylim(bottom=0)

    sns.scatterplot(
        data=df_latency.query("test_label == 'VPN_OFF'"),
        x="timestamp", y="ping_loss_%", ax=axes[1], alpha=0.8, s=50
    )
    axes[1].set_title("Loss without VPN")
    axes[1].set_ylim(bottom=0)

    for ax in axes:
        ax.xaxis.set_major_formatter(DATE_FMT)
        ax.grid(True, linestyle='--', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(f"{image_dir}/loss_{user_name}.png", dpi=300)

    sns.lineplot(data=avg_on, x="timestamp", y="ping_loss_%",
                 ax=axes[0], color="red", marker="o")
    sns.lineplot(data=avg_off, x="timestamp", y="ping_loss_%",
                 ax=axes[1], color="red", marker="o")

    plt.tight_layout()
    plt.savefig(f"{image_dir}/loss_{user_name}_avg.png", dpi=300)
    plt.close()

print("\nAll users processed successfully.")
