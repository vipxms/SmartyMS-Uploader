# local_push.py
import asyncio
import os
import psutil
import time
import json
import subprocess
from datetime import datetime

# Connections with other project modules
from force_close import run_with_stabilizer
from connection import get_active_sessions  # assume this util returns current yt-dlp sessions
from vars import TARGET_SPEED_MBPS

# Config
MONITOR_INTERVAL = 30        # seconds
LOW_SPEED_THRESHOLD = 0.7    # below 70% of target triggers boost
MAX_RUN_TIME = 5 * 60 * 60   # 5 hours in seconds
LOG_PATH = "logs/local_push.log"

# Logging utility
def log(msg):
    stamp = datetime.now().strftime("[%H:%M:%S]")
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")
    print(f"{stamp} {msg}")

async def flush_dns():
    try:
        if os.name == "nt":
            subprocess.run("ipconfig /flushdns", shell=True)
        else:
            subprocess.run("systemd-resolve --flush-caches", shell=True)
        log("✅ DNS cache flushed")
    except Exception as e:
        log(f"DNS flush failed: {e}")

async def monitor_speed():
    log("🚀 Local Push Booster started...")
    start_time = time.time()

    while True:
        # Stop after 5 hours continuous
        if time.time() - start_time > MAX_RUN_TIME:
            log("🕒 5-hour watchdog reached — stopping Local Push")
            break

        try:
            active_sessions = await get_active_sessions()
            if not active_sessions:
                log("ℹ️ No active download sessions found")
                await asyncio.sleep(MONITOR_INTERVAL)
                continue

            total_speed = 0
            for sess in active_sessions:
                total_speed += sess.get("speed", 0)

            avg_speed = total_speed / max(1, len(active_sessions))
            mbps = avg_speed / (1024 * 1024)

            log(f"📊 Current avg speed: {mbps:.2f} MB/s  (target: {TARGET_SPEED_MBPS})")

            if mbps < TARGET_SPEED_MBPS * LOW_SPEED_THRESHOLD:
                log("⚠️ Low speed detected — applying boost...")
                await flush_dns()
                await run_with_stabilizer([s["url"] for s in active_sessions])

                # temporary rate patch for yt-dlp
                patch = {"rate_limit": f"{TARGET_SPEED_MBPS * 1024 * 1024}B"}
                with open("temp_rate_patch.json", "w") as f:
                    json.dump(patch, f)
                log("🔥 Booster patch applied to yt-dlp config")

        except Exception as e:
            log(f"Monitor error: {e}")

        await asyncio.sleep(MONITOR_INTERVAL)

async def start_local_push():
    await monitor_speed()

if __name__ == "__main__":
    asyncio.run(start_local_push())
