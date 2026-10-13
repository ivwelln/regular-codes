import logging

import discord
import httpx2

from bot.backend import BackendClient
from bot.messages import message_text

logger = logging.getLogger(__name__)


class PromoBot(discord.Client):
    def __init__(self, backend: BackendClient, channel_ids: frozenset[int]) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.backend = backend
        self.channel_ids = channel_ids

    async def on_ready(self) -> None:
        logger.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.channel.id not in self.channel_ids:
            return

        text = message_text(message)
        if not text:
            return

        try:
            codes = await self.backend.send_message(str(message.id), text)
        except httpx2.HTTPError:
            logger.exception("message %s was not sent to backend", message.id)
            return

        if codes:
            logger.info("message %s: found codes: %s", message.id, codes)
