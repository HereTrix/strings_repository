import os
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env_path = BASE_DIR / ".env"
use_env = False
if os.path.isfile(env_path):
    env = environ.Env(DEBUG=(bool, False))
    env.read_env(str(env_path), overwrite=True)
    use_env = True
else:
    env = os.environ


def env_value(key):
    if use_env:
        return env(key)
    else:
        return env.get(key)
