import logging
from pathlib import Path
from dotenv import load_dotenv

def load_config(env_path: str | None = None) -> None:
    env_file = Path(env_path) if env_path else Path(".env")
    if not env_file.exists():
        logging.warning("'.env' not found – using defaults. Copy '.env.template' to '.env'.")
    load_dotenv(dotenv_path=env_file if env_file.exists() else None)
    logging.info("Configuration loaded.")
