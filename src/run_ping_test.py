import subprocess
import re
import signal
import sys
import statistics
import os 
import platform
import argparse
import csv
from datetime import datetime
from utils.env_loader import load_env_manual

parser = argparse.ArgumentParser(description="Script with debug flag")
parser.add_argument("--duration", help="Defines ping test duration", type=int)
parser.add_argument("--output_path", help="Defines the output path", type=str)
parser.add_argument("--label", help="Defines the label to be printed along the results", type=str)
args = parser.parse_args()

SESSION_DURATION_SECONDS = args.duration
OUTPUT_PATH = args.output_path
VPN_STATE = args.label

PING_HOST = "moodle.ufrgs.br"                     
PING_INTERVAL = 1.0 

WAIT_AFTER_VPN = 10
REGEX_RTT = re.compile(r'time[=<]([\d\.]+)\s*ms')

def get_next_session(file_path: str) -> int:
    """Reads the CSV file and finds the next session number."""
    if not os.path.isfile(file_path):
        return 1
    try:
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            sessions = [int(row["session"]) for row in reader if "session" in row and row["session"].isdigit()]
            return max(sessions) + 1 if sessions else 1
    except Exception:
        return 1

CURRENT_SESSION = get_next_session(OUTPUT_PATH)

rtts = []       # store all RTTs
jitter = 0.0    # RFC3550-like running jitter
last_rtt = None

def calc_jitter(prev_rtt, cur_rtt, jitter):
    """RFC3550-style jitter"""
    if prev_rtt is None:
        return jitter
    D = cur_rtt - prev_rtt
    jitter += (abs(D) - jitter) / 16.0
    return jitter

def cleanup_and_exit():
    if not rtts:
        print("\nNo ping data collected.")
        sys.exit(0)
    mean_latency = statistics.mean(rtts)
    print("\n--- Results ---")
    print(f"Samples: {len(rtts)}")
    print(f"Mean latency: {mean_latency:.3f} ms")
    print(f"Jitter (RFC3550-style): {jitter:.3f} ms")
    sys.exit(0)

def write_to_csv(row, file):
    """Adiciona uma linha de resultado ao arquivo CSV."""
    file_exists = os.path.isfile(file)

    with open(file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "session", "test_label", "ping_latency_ms", "ping_jitter_ms", "ping_loss_%",
            ])
        writer.writerow(row)

def get_ping_cmd(host: str) -> str:
    system = platform.system().lower()

    if system == "windows":
        # -n: number of echo requests
        count = SESSION_DURATION_SECONDS  
        return ["ping", "-n", str(count), host]
    elif system in ("linux", "darwin"):  # macOS reports as 'Darwin'
        # -c: number of pings
        count = SESSION_DURATION_SECONDS
        return ["ping", "-c", str(count), host]
    else:
        raise OSError(f"Unsupported OS: {system}")

# Handle Ctrl+C gracefully
signal.signal(signal.SIGINT, lambda s, f: cleanup_and_exit())

proc = subprocess.Popen(get_ping_cmd(PING_HOST), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

print(f"Pinging {PING_HOST} — press Ctrl+C to stop...\n")

total_pings_sent = 0

for line in proc.stdout:
    if "time=" in line or "time<" in line:
        total_pings_sent += 1
        match = REGEX_RTT.search(line)
        if match:
            rtt = float(match.group(1))
            rtts.append(rtt)
            jitter = calc_jitter(last_rtt, rtt, jitter)
            last_rtt = rtt
            
            loss_percent = (1 - len(rtts) / total_pings_sent) * 100 if total_pings_sent > 0 else 0
            
            timestamp = datetime.now().isoformat()
            pretty_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
            row = [timestamp, CURRENT_SESSION, VPN_STATE, f"{rtt:.2f}", f"{jitter:.2f}", f"{loss_percent:.2f}"]
            write_to_csv(row, OUTPUT_PATH)

            print(f"RTT = {rtt:.2f} ms, jitter = {jitter:.2f} ms   ", end="\r", flush=True)

cleanup_and_exit()