"""
PyMesh background daemon process entrypoint.
"""

import asyncio
import sys
import logging
from pathlib import Path
from pymesh.daemon.lifecycle import DaemonLifecycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    config_dir = Path("/etc/pymesh")
    if len(sys.argv) > 1:
        config_dir = Path(sys.argv[1])

    lifecycle = DaemonLifecycle(config_dir)
    await lifecycle.start()

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await lifecycle.stop()

if __name__ == "__main__":
    asyncio.run(main())
