import subprocess
import time
import sys
import os
import argparse
import platform
from utils.env_loader import load_env_manual

import csv     
from datetime import datetime     
        
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCE_FOLDER = f"{PROJECT_ROOT}/src"  
DATA_DIR = f"{PROJECT_ROOT}/data"  
    
load_env_manual(os.path.join(PROJECT_ROOT, '.env') ) # carregamento do .env

USER_NAME = os.getenv('USER_NAME')
if USER_NAME:
    print(f"Hello, {USER_NAME}!")
    USER_NAME = USER_NAME.lower()
else:
    print("Could not find the 'USER_NAME' variable in the .env file.")
    
os.makedirs(f"{DATA_DIR}/{USER_NAME}", exist_ok=True)

OPEN_VPN_CONFIG_PATH = os.path.join(SCRIPT_DIR, "ufrgs.ovpn")
PASS_PATH = os.path.join(SCRIPT_DIR, "pass.txt")
OPENVPN_CMD = ["sudo", "openvpn", "--config", OPEN_VPN_CONFIG_PATH , "--auth-user-pass", PASS_PATH]

WAIT_TIME_AFTER_VPN_TOGGLE = 10
SESSION_DURATION_SECONDS = 900 
IPERF_DURATION = 180
INTERVAL = 5  

PING_TEST_OUTPUT_FILE_PATH = os.path.join(DATA_DIR, USER_NAME, "ping_results.csv")
IPERF_TEST_OUTPUT_FILE_PATH = os.path.join(DATA_DIR, USER_NAME, "iperf_results.csv")   

IPERF_SERVER = "pcad.inf.ufrgs.br" 
IPERF_PORT = 8787     

def kill_vpn() -> None:
    """Mata qualquer processo OpenVPN em execução."""
    subprocess.run(["pkill", "-f", "openvpn"], capture_output=True)
    
def start_vpn() -> subprocess.Popen:
    """Inicia o OpenVPN."""
    stdout = subprocess.PIPE
    stderr = None
    if DEBUG:
        stdout = None
    return subprocess.Popen(OPENVPN_CMD, stdout=stdout, stderr=stderr)

def start_ping_test(duration: int, label : str) -> subprocess.Popen:
    cmd = [sys.executable, os.path.join(SOURCE_FOLDER, "run_ping_test.py"), "--duration", str(duration), "--output_path", PING_TEST_OUTPUT_FILE_PATH, "--label", label]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=None,
    )
    return process

def stop_ping_test(process):
    """Para o processo de ping."""
    print("--- [PING] Parando ping... ---")
    try:
        if process.poll() is None:
            process.terminate()
            process.wait()
    except Exception as e:
        print(f"[ERRO ao parar o ping] {e}")
    
    print("--- [PING] Parado. ---")

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

def write_to_csv(row, file):
    """Adiciona uma linha de resultado ao arquivo CSV."""
    file_exists = os.path.isfile(file)

    with open(file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "test_label", "tcp_throughput_mbps",
            ])
        writer.writerow(row)
            
def start_iperf_test(label : str):
    tcp_throughput = run_iperf_tcp(IPERF_SERVER, IPERF_PORT, IPERF_DURATION)

    if tcp_throughput is not None:
        print(f" [IPERF TCP] Throughput: {tcp_throughput:.2f} Mbps")
        timestamp = datetime.now().isoformat()
        row = [
            timestamp, label, tcp_throughput,
        ]
        write_to_csv(row, IPERF_TEST_OUTPUT_FILE_PATH)           
        print(f"[IPERF TCP]: Resultado salvo com sucesso")
    else:
        print("[IPERF TCP] Teste falhou.")

    return

def ensure_privileges():
    system = platform.system()

    print(f"Running on {system}")

    if system == "Windows":
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        if not is_admin:
            args = " ".join(f'"{a}"' for a in sys.argv[1:])
            cmd = [
                "powershell",
                "-Command",
                (
                    f'Start-Process "{sys.executable}" '
                    f'-ArgumentList "{args}" '
                    f'-Verb RunAs -Wait'
                )
            ]

            result = subprocess.run(cmd)
            sys.exit(result.returncode or 0)

    elif hasattr(os, "geteuid") and os.geteuid() != 0:
        try:
            result = subprocess.run(["sudo", sys.executable, *sys.argv])
            sys.exit(result.returncode or 0)
        except KeyboardInterrupt:
            pass
        sys.exit(1) 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script with debug flag")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    DEBUG = args.debug
    
    if DEBUG:
        print("Debug: ON")
        
    ensure_privileges()
    
    print("=== VPN Impact Test ===")
    print(f"Resultados do iperf serão salvos em: {IPERF_TEST_OUTPUT_FILE_PATH}")
    print(f"Resultados do ping serão salvos em: {PING_TEST_OUTPUT_FILE_PATH}")
    print("Pressione Ctrl+C para parar.\n")
    
    skip_udp = True
    ping_proc = None
    ping_file = None

    try:
        while True:
            kill_vpn()
            
            print("\n[SESSÃO VPN ON] Iniciando VPN...")
            vpn_proc = start_vpn()
            time.sleep(WAIT_TIME_AFTER_VPN_TOGGLE) 

            ping_proc = start_ping_test(SESSION_DURATION_SECONDS, "VPN_ON")
            
            session_start_time = time.time()
            print(f"[SESSÃO VPN ON] Rodando iperf (a cada {IPERF_DURATION + INTERVAL}s) por {IPERF_DURATION}s...")
            
            while (time.time() - session_start_time) < SESSION_DURATION_SECONDS:
                start_iperf_test("VPN_ON")
                
                poll = ping_proc.poll()
                
                if poll is not None:
                    print(f"[AVISO] Ping longo (ON) parou inesperadamente. {poll}")
                    break
                
                time.sleep(INTERVAL)

            print(f"[SESSÃO VPN ON] Sessão de {SESSION_DURATION_SECONDS / 60} min finalizada.")
            stop_ping_test(ping_proc)
            kill_vpn()
            time.sleep(INTERVAL)

            print("\n[SESSÃO VPN OFF] Garantindo que VPN está parada.")
            kill_vpn()
            
            ping_proc =  start_ping_test(SESSION_DURATION_SECONDS, "VPN_OFF")

            session_start_time = time.time()
            print(f"[SESSÃO VPN OFF] Rodando iperf (a cada {IPERF_DURATION + INTERVAL}s) por {SESSION_DURATION_SECONDS}s...")
            
            while (time.time() - session_start_time) < SESSION_DURATION_SECONDS:
                start_iperf_test("VPN_OFF")

                if ping_proc.poll() is not None:
                    print("[AVISO] Ping longo (OFF) parou inesperadamente.")
                    break

                time.sleep(INTERVAL)
            
            print(f"[SESSÃO VPN OFF] Sessão de {SESSION_DURATION_SECONDS / 60} min finalizada.")
            stop_ping_test(ping_proc)
            
            print(f"\n=== Ciclo completo (ON/OFF). Reiniciando em {INTERVAL}s... ===")
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nParado pelo usuário.")
        if ping_proc:
            stop_ping_test(ping_proc)
        kill_vpn()
        print("Script finalizado.")
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        line = tb.tb_lineno
        print(f"\n[ERRO FATAL] Ocorreu um erro: {e} na linha {line}")
        if ping_proc:
            stop_ping_test(ping_proc)
        kill_vpn()