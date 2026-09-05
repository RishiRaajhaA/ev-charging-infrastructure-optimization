"""
1-Click Launcher for the Full-Stack EV Optimization Decision Support Suite
-------------------------------------------------------------------------
Runs the high-performance FastAPI server and automatically launches
the modern Glassmorphic web dashboard in your default browser.
"""

import sys
import time
import webbrowser
import threading
import uvicorn
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

def open_browser(url: str, delay: float = 1.2):
    """Wait for server boot and open the browser."""
    time.sleep(delay)
    print(f"\n🚀 Launching web application at: {url}")
    webbrowser.open(url)

def main():
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print("=" * 70)
    print("⚡ EV OPTIMA — Full-Stack Decision Support Suite")
    print("=" * 70)
    print(f"[*] Starting FastAPI backend engine on {url}")
    print("[*] Launching modern reactive Glassmorphic SPA frontend...")
    print("=" * 70)

    # Open browser in a separate background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Run Uvicorn server
    uvicorn.run("web_app.backend.server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
