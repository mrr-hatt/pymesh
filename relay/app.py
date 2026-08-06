"""
PyMesh Relay Server standalone application entrypoint.
"""

import asyncio
import sys
import logging
from pymesh.relay.server import RelayServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    port = 51830
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    server = RelayServer("0.0.0.0", port)
    await server.start()
    
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        server.stop()

if __name__ == "__main__":
    asyncio.run(main())
