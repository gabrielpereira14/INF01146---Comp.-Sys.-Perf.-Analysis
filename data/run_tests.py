import subprocess
import json
import csv
import time
import sys
from datetime import datetime
import os
import argparse

script_dir = os.path.dirname(os.path.abspath(__file__))
open_config_name = "ufrgs.ovpn"
pass_path = "pass.txt"

person = 'gabriel'

os.makedirs(f"{script_dir}/{person}", exist_ok=True)

DEBUG = False

PING_HOST = "moodle.ufrgs.br"       
IPERF_SERVER = "pcad.inf.ufrgs.br"  
IPERF_PORT = 8787            
LOCAL_OUTPUT_CSV = os.path.join(script_dir, person, "vpn_test_results.csv")
COMMON_OUTPUT_CSV = os.path.join(script_dir, "common_vpn_test_results.csv")
INTERVAL = 5
IPERF_DURATION = 10       
PING_COUNT = 10
OPENVPN_CMD = ["sudo", "openvpn", "--config", open_config_name, "--auth-user-pass", pass_path ] 
OPENVPN_CONFIG = "/path/to/config.ovpn" 
WAIT_AFTER_VPN = 10      
TRACEROUTE_CMD = ["sudo", "traceroute", PING_HOST] 


def kill_vpn():
    """Kill any running OpenVPN processes."""
    subprocess.run(["pkill", "-f", "openvpn"], capture_output=True)
    
def start_vpn():
    return subprocess.Popen(OPENVPN_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def is_vpn_running():
    """Check if OpenVPN is already running."""
    try:
        subprocess.run(["pgrep", "openvpn"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def run_ping(host, count=10):
    """Run ping and parse latency, jitter, packet loss."""
    try:
        
        if DEBUG:
            result = subprocess.run(
                TRACEROUTE_CMD,
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
            
            print(output)
                
        result = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout

        # Parse packet loss
        loss_line = [l for l in output.splitlines() if "packet loss" in l][0]
        packet_loss = float(loss_line.split("%")[0].split()[-1])

        # Parse rtt stats
        rtt_line = [l for l in output.splitlines() if "rtt" in l or "round-trip" in l][0]
        stats = rtt_line.split("=")[1].split()[0].split("/")
        latency_avg = float(stats[1])  # avg latency (ms)
        latency_jitter = float(stats[3]) 

        return latency_avg, latency_jitter, packet_loss
    except Exception as e:
        print(f"[PING ERROR] {e}")
        return None, None, None


def run_iperf_tcp(server, port=8787, duration=10):
    """Run iperf TCP test and return throughput in Mbps."""
    try:
        result = subprocess.run(
            ["iperf", "-c", server, "-p", str(port), "-y", "C", "-t", str(duration)],
            capture_output=True,
            text=True,
            check=True
        )
        output_csv = result.stdout.strip()
        values = output_csv.split(',')
        
        bps = float(values[-1])
        
        throughput_mbps = bps / 1e6
        return throughput_mbps
    except Exception as e:
        print(f"[IPERF TCP ERROR] {e}")
        return None


def run_iperf_udp(server, port=8787, duration=10, bitrate="10M"):
    """Run iperf UDP test and return throughput, jitter, loss."""
    try:
        result = subprocess.run(
            ["iperf", "-c", server, "-p", str(port), "-J", "-t", str(duration), "-u", "-b", bitrate],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        summary = data["end"]["sum"]

        throughput_mbps = summary["bits_per_second"] / 1e6
        jitter_ms = summary["jitter_ms"]
        lost_percent = summary["lost_percent"]

        return throughput_mbps, jitter_ms, lost_percent
    except Exception as e:
        print(f"[IPERF UDP ERROR] {e}")
        return None, None, None


def write_to_csv(row, file):
    """Append results to CSV file."""
    file_exists = os.path.isfile(file)

    with open(file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "test_label",
                "ping_latency_ms", "ping_jitter_ms", "ping_loss_%",
                "tcp_throughput_mbps",
                "udp_throughput_mbps", "udp_jitter_ms", "udp_loss_%"
            ])
        writer.writerow(row)


def run_all_tests(label, skip_udp = False):
    """Run ping + iperf TCP + iperf UDP and log results."""
    timestamp = datetime.now().isoformat()
    pretty_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    latency, jitter, loss = run_ping(PING_HOST, PING_COUNT)
    
    print("=" * 70)
    print(f"Time: {pretty_time} | Test: {label}")
    print(f"PING -> Latency: {latency:.2f} ms | Jitter: {jitter:.2f} ms | Loss: {loss:.2f} %")
    
    result = [
        timestamp, label,
        latency, jitter, loss,
        
    ]
    
    tcp_throughput = run_iperf_tcp(IPERF_SERVER, IPERF_PORT, IPERF_DURATION)
    
    if tcp_throughput is not None: 
        print(f"iperf TCP  -> Throughput: {tcp_throughput:.2f} Mbps")
        result.extend([tcp_throughput])
    else:
        print("Could not run iperf tcp test, check if the server is online")
    
    if not skip_udp: 
        udp_throughput, udp_jitter, udp_loss = run_iperf_udp(IPERF_SERVER, IPERF_PORT, IPERF_DURATION)
        print(f"iperf UDP  -> Throughput: {udp_throughput:.2f} Mbps | Jitter: {udp_jitter:.2f} ms | Loss: {udp_loss:.2f} %")
        
        result.extend([tcp_throughput, udp_throughput, udp_jitter, udp_loss])
    
    write_to_csv(result, LOCAL_OUTPUT_CSV)
    write_to_csv(result, COMMON_OUTPUT_CSV)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script with debug flag")

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    args = parser.parse_args()
    DEBUG = args.debug
    
    if DEBUG:
        print("Debug: ON")
        
    if os.geteuid() != 0:
        print("This script requires sudo. Re-launching...")
        
        args = ['sudo', sys.executable] + sys.argv
        
        # Replace the current process with the new one
        os.execvp(args[0], args)
    
    print("=== VPN Impact Test ===")
    print("Results will be saved to:", LOCAL_OUTPUT_CSV)
    print("Press Ctrl+C to stop.\n")
    
    skip_udp = True

    try:
        while True:
            kill_vpn()
            
            print("\n[VPN ON] Starting VPN...")
            vpn_proc = start_vpn()
            time.sleep(INTERVAL)

            run_all_tests("VPN_ON", skip_udp= skip_udp)

            kill_vpn()

            time.sleep(INTERVAL)
            
            print("\n[VPN OFF] Running tests...")
            run_all_tests("VPN_OFF", skip_udp= skip_udp)

            time.sleep(INTERVAL)
            
            kill_vpn()

    except KeyboardInterrupt:
        print("\nStopped by user.")
        kill_vpn()