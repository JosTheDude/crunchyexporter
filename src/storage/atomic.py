import json
import os
import shutil
import tempfile
from pathlib import Path


def save_json(path: Path, data: dict) -> None:
    """Atomically replace a JSON file, retaining its previous version as .bak."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = path.with_name(f"{path.name}.bak")

    if path.exists():
        shutil.copy2(path, backup_path)

    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise
