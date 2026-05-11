from __future__ import annotations

import sys
from pathlib import Path

# Add the scripts directory to sys.path so test modules can import them directly.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "session" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
