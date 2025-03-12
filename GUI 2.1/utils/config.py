import os
import json
import yaml

def load_config(file_path=None):
    """
    Load configuration from YAML file.
    If file doesn't exist, returns default configuration.
    """
    if file_path is None:
        file_path = os.path.join('resources', 'config.yaml')
    
    default_config = {
        'serial': {
            'baud_rate': 115200,
            'timeout': 1,
        },
        'ui': {
            'max_data_points': 1000,
            'update_interval': 100,  # ms
        },
        'map': {
            'default_location': {
                'lat': 45.5017,  # Montreal
                'lon': -73.5673,
            },
            'default_zoom': 13,
        },
    }
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif file_path.endswith('.json'):
                    return json.load(f)
        return default_config
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        return default_config

def save_config(config, file_path=None):
    """Save configuration to YAML file."""
    if file_path is None:
        file_path = os.path.join('resources', 'config.yaml')
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                yaml.dump(config, f, default_flow_style=False)
            elif file_path.endswith('.json'):
                json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")
        return False