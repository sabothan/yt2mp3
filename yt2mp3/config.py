import os
import sys
from pathlib import Path
from configparser import ConfigParser

CONFIG_FILE = Path(__file__).resolve().parent / ".yt2mp3.config"

SUPPORTED_KEYS = {'ouptut.default_path', 'audio.format'}

def get_config() -> ConfigParser:
    config = ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    
    return config

def _save_config(config: ConfigParser):
    """Write configurations to the config file

    Args:
        config (ConfigParser): The configuration object
    """
    with open(CONFIG_FILE, 'w') as file:
        config.write(file)

def set_config(key: str, value: str):
    # Split key into section and option
    section, _, option = key.partition('.')
    if not section or not _ or not option:
        raise ValueError("Config key must be in the form 'section.option'.")
    
    # Check if options are valid
    if(key not in SUPPORTED_KEYS):
        raise ValueError(f'Config key must match: {SUPPORTED_KEYS}')

    # Load config file
    config = get_config()

    # Update configurations
    if not config.has_section(section):
        config.add_section(section)
    config.set(section=section, option=option, value=value)

    # Save configurations
    _save_config(config)
    print('Configuration saved')
