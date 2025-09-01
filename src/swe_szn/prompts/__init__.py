from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> dict:
    """load a prompt YAML by name"""
    path = PROMPTS_DIR / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
