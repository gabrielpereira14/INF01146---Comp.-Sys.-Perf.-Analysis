import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns

script_dir = os.path.dirname(os.path.abspath(__file__))
file_name = "vpn_test_results.csv"
person = "gabriel"
image_dir = f"{script_dir}/images/{person}/"
os.makedirs(image_dir, exist_ok=True)

date_fmt = mdates.DateFormatter("%d/%m")

df = pd.read_csv(f"{script_dir}/{file_name}", parse_dates=["timestamp"])
df["date"] = df["timestamp"].dt.date

vpn_fixed_day = df[df['test_label'] == 'VPN_ON']['timestamp'].min()

####################################################################################################################

df_jitter = df.query('timestamp >= "2025.10.01"')

df_jitter = df_jitter.copy()

jitter_data = df_jitter['ping_jitter_ms']

upper_bound = jitter_data.quantile(0.99)

print(f"Jitter Upper Bound: {upper_bound:.2f}")

initial_rows = len(df_jitter)

df_jitter["timestamp"] = pd.to_datetime(df_jitter["timestamp"])

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

sns.lineplot(
    data=df_jitter.query("test_label == 'VPN_ON'"),
    x="timestamp", y="ping_jitter_ms", ax=axes[0], label="Jitter"
)
axes[0].set_title("Jitter with VPN")
axes[0].set_ylabel("ms")
axes[0].set_xlabel("Date")

# VPN OFF
sns.lineplot(
    data=df_jitter.query("test_label == 'VPN_OFF'"),
    x="timestamp", y="ping_jitter_ms", ax=axes[1], label="Jitter"
)

axes[1].set_title("Jitter without VPN")
axes[1].set_ylabel("ping_jitter_ms")
axes[1].set_xlabel("Date")


print(len(df_jitter))
for ax in axes:
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(date_fmt)
    ax.tick_params(axis='x', rotation=45)
    

plt.tight_layout()
plt.savefig(f"{image_dir}/jitter_comparison_{person}.png", dpi=300)
plt.close()

df_jitter = df_jitter[(jitter_data <= upper_bound)]
plt.figure(figsize=(8, 6))

sns.violinplot(data=df_jitter, x='test_label', y='ping_jitter_ms', cut=0)

plt.title('Jitter Comparison: VPN ON vs. VPN OFF')
plt.xlabel('Test Condition')
plt.ylabel('Ping Jitter (ms)')
plt.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig(f"{image_dir}/jitter_comparison_violin_{person}.png", dpi=300)
plt.close()



###########################################################################################################################

df_tcp_throughput = df.query("tcp_throughput_mbps.notna()")

df_tcp_throughput = df_tcp_throughput.copy()

df_tcp_throughput["timestamp"] = pd.to_datetime(df_tcp_throughput["timestamp"])

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

#VPN_ON
sns.lineplot(
    data=df_tcp_throughput.query("test_label == 'VPN_ON'"),
    x="timestamp", y="tcp_throughput_mbps", ax=axes[0], label="Throughput"
)

axes[0].set_title("Throughput with VPN")
axes[0].set_ylabel("Mbps")
axes[0].set_xlabel("Date")

# VPN OFF
sns.lineplot(
    data=df_tcp_throughput.query("test_label == 'VPN_OFF'"),
    x="timestamp", y="tcp_throughput_mbps", ax=axes[1], label="Throughput"
)
axes[1].set_title("Throughput without VPN")
axes[1].set_ylabel("Mbps")


for ax in axes:
    ax.xaxis.set_major_formatter(date_fmt)
    ax.tick_params(axis='x', rotation=45)
    ax.xaxis.set_major_locator(mdates.DayLocator())

plt.tight_layout()
plt.savefig(f"{image_dir}/throughput_comparison_{person}.png", dpi=300)
plt.close()

###########################################################################################################################

df_latency = df[ df['timestamp'] >= vpn_fixed_day].copy()

latency_data = df['ping_latency_ms']

lower_bound = latency_data.quantile(0.01)
upper_bound = latency_data.quantile(0.99)

df_latency = df_latency[ (latency_data >= lower_bound) & (latency_data <= upper_bound)]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

#VPN_ON
sns.violinplot(
    data=df_latency.query("test_label == 'VPN_ON'"),
    x="test_label", y="ping_latency_ms", ax=axes[0], label="Latency", cut=0
)

axes[0].set_title("Latency with VPN")
axes[0].set_ylabel("ms")
axes[0].set_xlabel("")

# VPN OFF
sns.violinplot(
    data=df_latency.query("test_label == 'VPN_OFF'"),
    x="test_label", y="ping_latency_ms", ax=axes[1], label="Latency", cut=0
)
axes[1].set_title("Latency without VPN")
axes[1].set_ylabel("ms")
axes[1].set_xlabel("")


plt.tight_layout()
plt.savefig(f"{image_dir}//latency_violin_{person}.png", dpi=300)
plt.close()


df_latency['date'] = df_latency['timestamp'].dt.date
df_latency['hour'] = df_latency['timestamp'].dt.hour

pivot_table = df_latency.pivot_table(
    values='ping_latency_ms', 
    index='date', 
    columns='hour', 
    aggfunc='mean'
)

plt.figure(figsize=(14, 8))
sns.heatmap(
    pivot_table, 
    annot=True,          
    fmt=".1f",           
    cmap="rocket_r",    
    linewidths=.5
)

plt.xlabel("Hour of the Day")
plt.ylabel("Date")
plt.title(f"Heatmap of Average Latency")
plt.tight_layout()
plt.savefig(f"{image_dir}/latency_heatmap_{person}.png", dpi=300)
plt.close()


########################################################################################

df_loss = df.query("`ping_loss_%` != 0.0 ")

df_resample = df.query('timestamp >= @vpn_fixed_day').copy()
df_resample = df_resample.set_index('timestamp')
avg_loss_on = df_resample.query("test_label == 'VPN_ON'").resample('h').mean(numeric_only=True)
avg_loss_off = df_resample.query("test_label == 'VPN_OFF'").resample('h').mean(numeric_only=True)

print(f" Loss events: VPN_ON -> {len(df_loss.query('test_label == "VPN_ON"'))} VPN_OFF -> {len(df_loss.query('test_label == "VPN_OFF"'))}")

fig, axes = plt.subplots(1, 2, figsize=(15, 6)) 

sns.scatterplot(
    data=df_latency.query("test_label == 'VPN_ON'"),
    x="timestamp", y="ping_loss_%", ax=axes[0], label="Individual Loss Event",
    alpha=0.8, s=50 
)

axes[0].set_title("Loss with VPN")
axes[0].set_ylabel("Ping Loss (%)")
axes[0].set_xlabel("Date")
axes[0].legend()

sns.scatterplot(
    data=df_latency.query("test_label == 'VPN_OFF'"),
    x="timestamp", y="ping_loss_%", ax=axes[1], label="Individual Loss Event",
    alpha=0.8, s=50
)

axes[1].set_title("Loss without VPN")
axes[1].set_ylabel("Ping Loss (%)")
axes[1].set_xlabel("Date")
axes[1].legend()

for ax in axes:
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(date_fmt)

    ax.set_ylim(bottom=0) 

    ax.grid(True, which='both', linestyle='--', linewidth=0.5)


plt.tight_layout()
plt.savefig(f"{image_dir}/loss_{person}.png", dpi=300)

sns.lineplot(
    data=avg_loss_on,
    x="timestamp", y="ping_loss_%", ax=axes[0], label="Hourly Average",
    color='red', marker='o', linewidth=2, alpha=0.5 
)

sns.lineplot(
    data=avg_loss_off,
    x="timestamp", y="ping_loss_%", ax=axes[1], label="Hourly Average",
    color='red', marker='o', linewidth=2, alpha=0.5
)

plt.tight_layout()
plt.savefig(f"{image_dir}/loss_{person}_avg.png", dpi=300)
plt.close()

######################################################################################