# =========================================================
# Connection.py
# ---------------------------------------------------------
# Central bridge between core.py, main.py, and force_close.py
# Auto-manages imports, async connections, and stabilizer calls.
# Keeps download speed stable (~20MB/s) using force_close.py.
# =========================================================

import asyncio
import logging

# Import the speed stabilizer & high-speed session
from force_close import run_with_stabilizer, reset_speed_now, network_test

# Optional: if you want to connect directly with your core/main modules
import importlib

# Define default integration targets
CORE_MODULE = "core"
MAIN_MODULE = "main"


async def connect_and_run(urls=None, module_name=None):
    """
    Connects the stabilizer (force_close.py) with core or main module.
    Automatically calls the high-speed download manager.
    """
    logging.info("🔗 Initializing Connection Bridge...")
    try:
        # Dynamically import the module (core or main)
        if not module_name:
            module_name = CORE_MODULE

        module = importlib.import_module(module_name)
        logging.info(f"✅ Connected to {module_name}.py successfully")

        # Reset system speed before any new batch
        reset_speed_now()

        # If the module has a 'get_video_urls' or similar function, fetch URLs
        if hasattr(module, "get_video_urls") and not urls:
            urls = await module.get_video_urls()
        elif not urls:
            raise ValueError("❌ No URL list provided and module has no 'get_video_urls'")

        # Run download batch via force_close stabilizer
        await run_with_stabilizer(urls)

        logging.info("🎯 All downloads completed via Connection Bridge.")

    except Exception as e:
        logging.error(f"⚠️ Connection Bridge Error: {e}")


def quick_speed_check():
    """Run a quick speed test (optional manual trigger)."""
    asyncio.run(network_test())


# Standalone example usage (test bridge)
if __name__ == "__main__":
    sample_urls = [
        "https://speed.hetzner.de/100MB.bin",
        "https://speed.hetzner.de/10MB.bin"
    ]
    asyncio.run(connect_and_run(sample_urls, module_name="core"))