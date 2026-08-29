import subprocess
import time
import os
import signal
from pathlib import Path

# ── Config ─────────────────────────────────────────────

BOT_SCRIPT = Path(__file__).parent / "telegram_bot.py"
LOG_FILE = Path(__file__).parent / "bot.log"
PID_FILE = Path(__file__).parent / "bot.pid"

# ── Helper Functions ───────────────────────────────────

def is_bot_running():
    """Check if the bot process is still alive."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # Signal 0 checks if process exists
        return True
    except (ValueError, OSError, ProcessLookupError):
        return False

def start_bot():
    """Start the bot in background and save its PID."""
    print("🚀 Starting bot...")
    
    # Kill any existing bot processes
    subprocess.run(["pkill", "-f", "telegram_bot.py"], capture_output=True)
    time.sleep(1)
    
    # Start fresh
    proc = subprocess.Popen(
        ["python3", str(BOT_SCRIPT)],
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    
    print(f"✅ Bot started with PID {proc.pid}")

def main():
    print("👀 Watchdog is watching...")
    
    while True:
        if not is_bot_running():
            print("⚠️ Bot is down! Restarting...")
            start_bot()
        else:
            print("✅ Bot is running fine.")
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()