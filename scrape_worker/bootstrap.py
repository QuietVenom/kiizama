from __future__ import annotations

import os
import sys
from pathlib import Path


def setup_backend_context() -> None:
    """Make backend modules importable and align cwd for existing .env lookup."""
    root_dir = Path(__file__).resolve().parents[1]
    backend_dir = root_dir / "backend"

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    os.chdir(backend_dir)


__all__ = ["setup_backend_context"]
