import sys
import time
import webbrowser
import threading
import uvicorn
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

def open_browser(url: str, delay: float = 1.2):
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

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    uvicorn.run("web_app.backend.server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
