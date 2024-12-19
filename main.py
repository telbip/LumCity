import asyncio
from os import system
import sys

if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from bot.utils.launcher import process

async def main():
    await process()

if __name__ == '__main__':
    system('title Boinker')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("<r>Bot stopped by user...</r>")
        sys.exit(2)
