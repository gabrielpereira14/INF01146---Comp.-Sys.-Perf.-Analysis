import subprocess
import json
import csv
import time
import sys
from datetime import datetime
import os
import argparse

def load_env_manual(env_path):
    """Carrega manualmente as variáveis de um arquivo .env"""
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Error: .env file not found at {env_path}")
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# carregamento do .env
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, '.env') 
    
    load_env_manual(dotenv_path)

    user_name = os.getenv('USER_NAME')

    if user_name:
        print(f"Hello, {user_name}!")
    else:
        print("Could not find the 'USER_NAME' variable in the .env file.")

except FileNotFoundError as e:
    sys.stderr.write(f"{e}\n")
    sys.exit(1)
except Exception as e:
    sys.stderr.write(f"An unexpected error occurred: {e}\n")
    sys.exit(1)

user_name = user_name.lower()

script_dir = os.path.dirname(os.path.abspath(__file__))
open_config_name = "ufrgs.ovpn"
pass_path = "pass.txt"

os.makedirs(f"{script_dir}/{user_name}", exist_ok=True)

DEBUG = False

PING_HOST = "moodle.ufrgs.br"      
IPERF_SERVER = "pcad.inf.ufrgs.br" 
IPERF_PORT = 8787                  
LOCAL_OUTPUT_CSV = os.path.join(script_dir, user_name, "vpn_test_results.csv")
COMMON_OUTPUT_CSV = os.path.join(script_dir, "common_vpn_test_results.csv")
INTERVAL = 5 
IPERF_DURATION = 10      
OPENVPN_CMD = ["sudo", "openvpn", "--config", open_config_name, "--auth-user-pass", pass_path ]
WAIT_AFTER_VPN = 10
SESSION_DURATION_SECONDS = 1800 
LONG_PING_OUTPUT_VPN_ON = os.path.join(script_dir, user_name, "long_ping_results_ON.txt")
LONG_PING_OUTPUT_VPN_OFF = os.path.join(script_dir, user_name, "long_ping_results_OFF.txt")

def kill_vpn():
    """Mata qualquer processo OpenVPN em execução."""
    subprocess.run(["pkill", "-f", "openvpn"], capture_output=True)
    
def start_vpn():
    """Inicia o OpenVPN."""
    return subprocess.Popen(OPENVPN_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def is_vpn_running():
    """Verifica se o OpenVPN já está rodando."""
    try:
        subprocess.run(["pgrep", "openvpn"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

# novas funcoes pro ping paralelo

def start_long_ping(host, duration, output_file):
    """Inicia um ping longo em paralelo e salva a saída em um arquivo."""
    print(f"--- [PING PARALELO] Iniciando ping longo para {host} ({duration}s) ---")
    print(f"--- [PING PARALELO] Saída será salva em: {output_file} ---")
    
    # mudei pra -t (tempo)
    cmd = ["ping", "-t", str(duration), host]
    
    f_out = open(output_file, 'w', buffering=1) 
    process = subprocess.Popen(
        cmd,
        stdout=f_out,
        stderr=subprocess.PIPE,
        text=True
    )
    return process, f_out #

def stop_long_ping(process, file_handle):
    """Para o processo de ping longo e fecha o arquivo."""
    print("--- [PING PARALELO] Parando ping longo... ---")
    try:
        if process.poll() is None:
            process.terminate()
            process.wait()
    except Exception as e:
        print(f"[ERRO ao parar o ping] {e}")
        
    if not file_handle.closed:
        file_handle.close()
    print("--- [PING PARALELO] Parado. ---")

# iperf

def run_iperf_tcp(server, port=8787, duration=10):
    """Roda o iperf TCP e retorna o throughput em Mbps."""
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
    """Roda o iperf UDP e retorna throughput, jitter, loss."""
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

# funcao de log

def write_to_csv(row, file):
    """Adiciona uma linha de resultado ao arquivo CSV."""
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

# teste principal

def run_all_tests(label, skip_udp = False):
    """Roda APENAS o iperf TCP/UDP e loga os resultados."""
    timestamp = datetime.now().isoformat()
    pretty_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ping removido daqui
    latency, jitter, loss = None, None, None
    
    tcp_throughput = run_iperf_tcp(IPERF_SERVER, IPERF_PORT, IPERF_DURATION)
    
    if not skip_udp:
        udp_throughput, udp_jitter, udp_loss = run_iperf_udp(IPERF_SERVER, IPERF_PORT, IPERF_DURATION)
    else:
        udp_throughput, udp_jitter, udp_loss = None, None, None

    print("=" * 70)
    print(f"Time: {pretty_time} | Test: {label}")
    if tcp_throughput is not None:
        print(f"iperf TCP  -> Throughput: {tcp_throughput:.2f} Mbps")
    else:
        print("iperf TCP  -> Teste falhou.")

    # monta a linha do csv com none pro ping
    row = [
        timestamp, label,
        latency, jitter, loss,
        tcp_throughput,
        udp_throughput, udp_jitter, udp_loss
    ]
    
    write_to_csv(row, LOCAL_OUTPUT_CSV)
    write_to_csv(row, COMMON_OUTPUT_CSV)

# loop principal

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script with debug flag")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    DEBUG = args.debug
    
    if DEBUG:
        print("Debug: ON")
        
    if os.geteuid() != 0:
        print("This script requires sudo. Re-launching...")
        python_path = sys.executable
        if 'VIRTUAL_ENV' in os.environ:
             python_path = os.path.join(os.environ['VIRTUAL_ENV'], 'bin', 'python3')

        args = ['sudo', python_path] + sys.argv
        os.execvp(args[0], args)
    
    print("=== VPN Impact Test (Parallel Ping) ===")
    print(f"Resultados do iperf serão salvos em: {LOCAL_OUTPUT_CSV}")
    print(f"Ping longo (VPN ON) será salvo em: {LONG_PING_OUTPUT_VPN_ON}")
    print(f"Ping longo (VPN OFF) será salvo em: {LONG_PING_OUTPUT_VPN_OFF}")
    print("Pressione Ctrl+C para parar.\n")
    
    skip_udp = True
    ping_proc = None
    ping_file = None

    try:
        while True:
            kill_vpn()
            
            print("\n[SESSÃO VPN ON] Iniciando VPN...")
            vpn_proc = start_vpn()
            time.sleep(WAIT_AFTER_VPN) 

            # inico ping paralelo
            ping_proc, ping_file = start_long_ping(PING_HOST, SESSION_DURATION_SECONDS, LONG_PING_OUTPUT_VPN_ON)
            
            session_start_time = time.time()
            print(f"[SESSÃO VPN ON] Rodando iperf (a cada {IPERF_DURATION + INTERVAL}s) por {SESSION_DURATION_SECONDS}s...")
            
            while (time.time() - session_start_time) < SESSION_DURATION_SECONDS:
                run_all_tests("VPN_ON", skip_udp=skip_udp)
                
                if ping_proc.poll() is not None:
                    print("[AVISO] Ping longo (ON) parou inesperadamente.")
                    break
                
                time.sleep(INTERVAL)

            print("[SESSÃO VPN ON] Sessão de 30 min finalizada.")
            stop_long_ping(ping_proc, ping_file)
            kill_vpn()
            time.sleep(INTERVAL)

            print("\n[SESSÃO VPN OFF] Garantindo que VPN está parada.")
            kill_vpn()
            
            # inico ping paralelo
            ping_proc, ping_file = start_long_ping(PING_HOST, SESSION_DURATION_SECONDS, LONG_PING_OUTPUT_VPN_OFF)

            session_start_time = time.time()
            print(f"[SESSÃO VPN OFF] Rodando iperf (a cada {IPERF_DURATION + INTERVAL}s) por {SESSION_DURATION_SECONDS}s...")
            
            while (time.time() - session_start_time) < SESSION_DURATION_SECONDS:
                run_all_tests("VPN_OFF", skip_udp=skip_udp)

                if ping_proc.poll() is not None:
                    print("[AVISO] Ping longo (OFF) parou inesperadamente.")
                    break

                time.sleep(INTERVAL)
            
            print("[SESSÃO VPN OFF] Sessão de 30 min finalizada.")
            stop_long_ping(ping_proc, ping_file)
            
            print(f"\n=== Ciclo completo (ON/OFF). Reiniciando em {INTERVAL}s... ===")
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nParado pelo usuário.")
        if ping_proc and ping_file:
            stop_long_ping(ping_proc, ping_file)
        kill_vpn()
        print("Script finalizado.")
    except Exception as e:
        print(f"\n[ERRO FATAL] Ocorreu um erro: {e}")
        if ping_proc and ping_file:
            stop_long_ping(ping_proc, ping_file)
        kill_vpn()