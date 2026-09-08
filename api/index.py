import sys
from pathlib import Path

# Vercel runs this file from api/; make the project root importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from investolingo_backend import create_app

app = create_app()
