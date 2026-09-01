import asyncio
import logging
import sys

from app.bot.bot import main


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
