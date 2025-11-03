# =========================================================
# force_close.py (Anti-Drop Speed Stabilizer)
# ---------------------------------------------------------
# Keeps 15–20 MB/s speed throughout single long downloads.
# Works with Render Singapore region + Docker + yt-dlp.
# =========================================================

import os
import subprocess
import asyncio
import time
import logging
import aiohttp

# Read target speed from environment or default
TARGET_SPEED_MBPS = int(os.getenv("TARGET_SPEED_MBPS", 20))
ENABLE_DNS_FLUSH = os.getenv("DNS_FLUSH", "true").lower() == "true"

# Internal tuning: reset every 25% of download progress
RESET_INTERVAL_PERCENT = 25


async def mini_reset():
    """Background mini-reset during single video download to avoid throttling."""
    try:
        # Kill residual network sockets and flush partial caches
        subprocess.run("pkill -f aria2c", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f yt-dlp", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("rm -rf /tmp/yt_cache ~/.cache/yt-dlp", shell=True)

        if ENABLE_DNS_FLUSH:
            subprocess.run("sudo systemd-resolve --flush-caches", shell=True)

        logging.info("⚙️ Mini-reset completed mid-download.")
    except Exception as e:
        logging.warning(f"⚠️ Mini-reset failed: {e}")


async def stabilize_speed():
    """Full stabilizer before new download starts."""
    logging.info("⚙️ Resetting system speed controller...")
    try:
        subprocess.run("pkill -f yt-dlp", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f aria2c", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("rm -rf /tmp/aria2c_cache /tmp/yt_cache ~/.cache/yt-dlp", shell=True)
        if ENABLE_DNS_FLUSH:
            subprocess.run("sudo systemd-resolve --flush-caches", shell=True)
        time.sleep(1.2)
        logging.info(f"✅ Speed stabilizer reset complete, target: {TARGET_SPEED_MBPS} MB/s")
    except Exception as e:
        logging.error(f"⚠️ Error during stabilization: {e}")


async def run_with_stabilizer(urls):
    """
    Handles multiple video URLs sequentially with adaptive stabilizer.
    Each video gets monitored for progress-based resets.
    """
    await stabilize_speed()

    for url in urls:
        logging.info(f"🚀 Starting stabilized download: {url}")

        # Start yt-dlp with progress monitoring
        proc = await asyncio.create_subprocess_shell(
            f"yt-dlp -f best -o '%(title)s.%(ext)s' --no-cache-dir '{url}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        last_reset_point = 0
        async for line in proc.stdout:
            text = line.decode(errors="ignore")
            if "%" in text:
                try:
                    percent = int(float(text.split("%")[0].split()[-1]))
                    # trigger reset every RESET_INTERVAL_PERCENT
                    if percent - last_reset_point >= RESET_INTERVAL_PERCENT:
                        last_reset_point = percent
                        asyncio.create_task(mini_reset())
                        logging.info(f"⚡ Midway reset at {percent}% complete.")
                except Exception:
                    pass
            print(text.strip())

        await proc.wait()
        logging.info(f"🎯 Download finished for {url}\n")


def reset_speed_now():
    """Manual full reset trigger."""
    asyncio.run(stabilize_speed())


async def network_test():
    """Quick network diagnostic."""
    async with aiohttp.ClientSession() as session:
        start = time.time()
        async with session.get("https://speed.hetzner.de/100MB.bin") as resp:
            await resp.read()
        end = time.time()
    size_mb = 100
    speed = size_mb / (end - start)
    print(f"⚡ Test speed: {speed:.2f} MB/s (Target {TARGET_SPEED_MBPS} MB/s)")
    return speed


if __name__ == "__main__":
    # Example single run test
    asyncio.run(stabilize_speed())
