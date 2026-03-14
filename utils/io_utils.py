from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json
import yaml

def load_config(config_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load YAML configuration, falling back to `config.yml` in the project root."""
    if config_path is None:
        candidate = Path("config.yml")
    else:
        candidate = Path(config_path)

    if not candidate.is_file():
        # Fallback for when running from a subfolder
        root_candidate = Path(__file__).resolve().parent.parent / "config.yml"
        if root_candidate.is_file():
            candidate = root_candidate
        else:
            raise FileNotFoundError(f"Config file not found: {candidate}")

    with candidate.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg

def get_nested(cfg: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Safely get a nested key using dotted path notation."""
    parts = path.split(".")
    cur: Any = cfg
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def resolve_debug_dir(cfg: Dict[str, Any], override_dir: Optional[str | Path] = None) -> Path:
    """Determine debug directory path."""
    if override_dir is not None:
        return Path(override_dir)
    base = get_nested(cfg, "paths.debug_dir", default="debug")
    return Path(base)

def write_json(data: Any, path: str | Path) -> None:
    """Write a Python object as UTF-8 JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
