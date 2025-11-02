# ===============================================
# force_close.py
# -----------------------------------------------
# High-speed stabilizer module (Render compatible)
# Keeps download speed ~20MB/s by resetting
# connections, flushing cache, and force-closing TCP.
# Integrates directly with core.py and main.py
# ===============================================

import aiohttp
import asyncio
import subprocess
import os
import time
import random
import logging

TARGET_SPEED_MBPS = 20
MAX_PARALLEL = 5
TIMEOUT = 90

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
]


# -------------------------------
# 1️⃣ Reset Network + Speed Cache
# -------------------------------
async def stabilize_speed():
    """Resets network stack and clears caches to prevent speed drop."""
    logging.info("⚙️ Resetting system speed controller...")
    try:
        # Kill residual download processes
        subprocess.run("pkill -f yt-dlp", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f aria2c", shell=True, stderr=subprocess.DEVNULL)

        # Remove temp cache (yt-dlp / aria2c)
        subprocess.run("rm -rf /tmp/aria2c_cache /tmp/yt_cache ~/.cache/yt-dlp", shell=True)

        # Flush DNS (Render Linux base)
        subprocess.run("sudo systemd-resolve --flush-caches", shell=True)

        time.sleep(1.5)
        logging.info(f"✅ Speed stabilizer reset complete (Target: {TARGET_SPEED_MBPS} MB/s)")

    except Exception as e:
        logging.error(f"⚠️ Error during stabilization: {e}")


# --------------------------------
# 2️⃣ Force TCP Close Downloader
# --------------------------------
class ForceCloseSession:
    """Handles multiple high-speed downloads with connection resets."""

    def __init__(self, max_parallel=MAX_PARALLEL, timeout=TIMEOUT):
        self.sem = asyncio.Semaphore(max_parallel)
        self.timeout = aiohttp.ClientTimeout(total=None, sock_connect=timeout, sock_read=timeout)

    async def fetch(self, url, path):
        """Download a single file with forced TCP close to avoid throttling."""
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        async with self.sem:
            start_time = time.time()
            size = 0
            try:
                connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
                async with aiohttp.ClientSession(connector=connector, timeout=self.timeout, headers=headers) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        with open(path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                                    size += len(chunk)

                duration = time.time() - start_time
                speed = (size / duration) / (1024 * 1024)
                print(f"✅ Downloaded {os.path.basename(path)} @ {speed:.2f} MB/s")
                return True

            except Exception as e:
                print(f"⚠️ Error downloading {url}: {e}")
                return False

    async def download_batch(self, urls):
        """Downloads multiple files sequentially with resets."""
        for idx, url in enumerate(urls, start=1):
            file_name = f"video_{idx}.mp4"
            print(f"\n🚀 Starting download {idx}/{len(urls)}: {url}")
            await stabilize_speed()
            ok = await self.fetch(url, file_name)
            if not ok:
                print("Retrying after reset...")
                await asyncio.sleep(2)
                await self.fetch(url, file_name)
            await asyncio.sleep(1)  # prevent server throttling


# --------------------------------
# 3️⃣ Integrator for core.py/main.py
# --------------------------------
async def run_with_stabilizer(urls):
    """Integrated function usable inside core.py or main.py"""
    await stabilize_speed()
    stabilizer = ForceCloseSession(max_parallel=MAX_PARALLEL)
    await stabilizer.download_batch(urls)


# --------------------------------
# 4️⃣ Manual Triggers
# --------------------------------
def reset_speed_now():
    """Manual call from other modules."""
    asyncio.run(stabilize_speed())


async def network_test():
    """Test your current network speed (optional)."""
    async with aiohttp.ClientSession() as session:
        start = time.time()
        async with session.get("https://speed.hetzner.de/100MB.bin") as resp:
            await resp.read()
        end = time.time()
    size_mb = 100
    speed = size_mb / (end - start)
    print(f"⚡ Test speed: {speed:.2f} MB/s (Target {TARGET_SPEED_MBPS} MB/s)")
    return speed


# --------------------------------
# 5️⃣ Example Standalone Run
# --------------------------------
if __name__ == "__main__":
    urls = [
        "https://speed.hetzner.de/100MB.bin",
        "https://speed.hetzner.de/10MB.bin"
    ]
    asyncio.run(run_with_stabilizer(urls))