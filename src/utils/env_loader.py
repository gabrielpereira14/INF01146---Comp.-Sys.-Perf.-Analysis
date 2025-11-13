import os
import sys

def load_env_manual(env_path):
    """Carrega manualmente as variáveis de um arquivo .env"""
    try:
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

    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        sys.exit(1)