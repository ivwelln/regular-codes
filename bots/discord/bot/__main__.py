import asyncio
import logging
from contextlib import suppress

import discord

from bot.backend import BackendClient, create_backend_http_client
from bot.client import PromoBot
from bot.config import Settings


async def main() -> None:
    settings = Settings()

    async with create_backend_http_client(settings) as http:
        bot = PromoBot(BackendClient(http), settings.channel_ids, settings.history_days)
        async with bot:
            await bot.start(settings.discord_token.get_secret_value())


if __name__ == "__main__":
    discord.utils.setup_logging(level=logging.INFO)
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
