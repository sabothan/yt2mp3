import os
import sys
from pathlib import Path
from configparser import ConfigParser

CONFIG_FILE = Path(__file__).resolve().parent.parent / "yt2mp3.config"

def get_config() -> ConfigParser:
    config = ConfigParser()
    print(CONFIG_FILE)



def set_config():
    pass
