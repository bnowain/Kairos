#!/usr/bin/env python3
"""
Kairos startup script.

Starts the Kairos API server on port 8400.
Workers must be started separately — see instructions printed below.
"""

import os
import subprocess
import sys

# Ensure we run from the project root regardless of where this script is called from
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

port = os.environ.get("KAIROS_PORT", "8400")

print("=" * 60)
print("  Kairos — Local AI Video Clipping Platform")
print("=" * 60)
print(f"\n  API:  http://localhost:{port}")
print(f"  Docs: http://localhost:{port}/api/docs\n")
print("  To start workers in separate terminals:")
print("    huey_consumer kairos.worker.huey_gpu  -w 1 -k thread")
print("    huey_consumer kairos.worker.huey_light -w 2 -k thread")
print("=" * 60)
print()

subprocess.run(
    [
        sys.executable, "-m", "uvicorn",
        "kairos.main:app",
        "--host", "0.0.0.0",
        "--port", port,
        "--reload",
    ]
)
