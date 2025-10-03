import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from graph_utils import *

script_dir = os.path.dirname(os.path.abspath(__file__))
file_name = "vpn_test_results.csv"

df = pd.read_csv(f"{script_dir}/{file_name}", parse_dates=["timestamp"])
df["date"] = df["timestamp"].dt.date

#df_vpn_on = df.query("test_label == 'VPN_ON' and timestamp > '2025-10-01'")
df_vpn_on = df.query("test_label == 'VPN_ON'")
df_vpn_off = df.query("test_label == 'VPN_OFF'")
import matplotlib.pyplot as plt
import seaborn as sns


def plot_daily_latency_barplot(df, date_col, latency_col, output_filename="latency_barplot.png"):
    plt.figure(figsize=(10, 6))
    sorted_dates = sorted(df[date_col].unique())
    sns.barplot(x=date_col, y=latency_col, data=df, order=sorted_dates, palette="viridis")
    
    plt.xlabel("Date")
    plt.ylabel(f"Average {latency_col}")
    plt.title(f"Daily Average Latency ({latency_col})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Saved bar plot to {output_filename}")
    plt.close()

def plot_latency_timeseries(df, timestamp_col, latency_col, output_filename="latency_timeseries.png"):
    plt.figure(figsize=(12, 7))
    
    df_copy = df.copy()
    df_copy['hour'] = df_copy[timestamp_col].dt.hour

    sns.boxplot(x='hour', y=latency_col, data=df_copy, palette="magma")
    
    plt.xlabel("Hour of the Day (24-Hour Clock)")
    plt.ylabel(latency_col.replace('_', ' ').title())
    plt.title(f"Hourly Distribution of {latency_col.replace('_', ' ').title()}")
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Saved hourly box plot to {output_filename}")
    plt.close()

def plot_daily_latency_boxplot(df, date_col, latency_col, output_filename="latency_boxplot.png"):
    plt.figure(figsize=(10, 6))
    sorted_dates = sorted(df[date_col].unique())
    sns.boxplot(x=date_col, y=latency_col, data=df, order=sorted_dates, palette="coolwarm")
    
    plt.xlabel("Date")
    plt.ylabel(latency_col)
    plt.title(f"Daily Variability of Latency ({latency_col})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Saved box plot to {output_filename}")
    plt.close()
    
    
def plot_daily_hourly_heatmap(df, timestamp_col, latency_col, output_filename="latency_heatmap.png"):

    df_copy = df.copy()
    df_copy['date'] = df_copy[timestamp_col].dt.date
    df_copy['hour'] = df_copy[timestamp_col].dt.hour
    
    pivot_table = df_copy.pivot_table(
        values=latency_col, 
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
    plt.title(f"Heatmap of Average Latency ({latency_col})")
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Saved heatmap to {output_filename}")
    plt.close()

def plot_daily_hourly_jitter_heatmap(df, timestamp_col, jitter_col, output_filename="jitter_heatmap.png"):
    df_copy = df.copy()
    
    df_copy['date'] = df_copy[timestamp_col].dt.date
    df_copy['hour'] = df_copy[timestamp_col].dt.hour
    
    pivot_table = df_copy.pivot_table(
        values=jitter_col, 
        index='date', 
        columns='hour', 
        aggfunc='mean'
    )
    
    plt.figure(figsize=(14, 8))
    sns.heatmap(
        pivot_table, 
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        linewidths=.5
    )
    
    plt.xlabel("Hour of the Day")
    plt.ylabel("Date")
    plt.title(f"Heatmap of Average Jitter ({jitter_col})")
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Saved jitter heatmap to {output_filename}")
    plt.close()


plot_daily_latency_barplot(df_vpn_on, date_col='date', latency_col='ping_latency_ms')
plot_latency_timeseries(df_vpn_on, timestamp_col='timestamp', latency_col='ping_latency_ms')
plot_daily_latency_boxplot(df_vpn_on, date_col='date', latency_col='ping_latency_ms')
plot_daily_hourly_heatmap( df_vpn_on, timestamp_col='timestamp', latency_col='ping_latency_ms')

df_jitter_on = df_vpn_on.query('timestamp >= "2025.10.01"')
plot_daily_hourly_jitter_heatmap(df_jitter_on, timestamp_col='timestamp', jitter_col = 'ping_jitter_ms')
print(df_vpn_on.head())