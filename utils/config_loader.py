import json
import os

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: config.json not found at {config_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}")
        return {}

# 전역 설정 변수 (한 번만 로드)
CONFIG = load_config()