import asyncio
import logging
from datetime import datetime, timedelta

import discord
import httpx2

from bot.backend import BackendClient
from bot.messages import message_text

logger = logging.getLogger(__name__)
CATCH_UP_DELAY = 2.0


class PromoBot(discord.Client):
    def __init__(
        self,
        backend: BackendClient,
        channel_ids: frozenset[int],
        history_days: int = 7,
        catch_up_delay: float = CATCH_UP_DELAY,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.backend = backend
        self.channel_ids = channel_ids
        self.history_days = history_days
        self.catch_up_delay = catch_up_delay

    async def on_ready(self) -> None:
        logger.info("Logged in as %s", self.user)
        await self.catch_up()

    async def on_message(self, message: discord.Message) -> None:
        if message.channel.id not in self.channel_ids:
            return
        await self._forward(message)

    async def catch_up(self) -> None:
        after = discord.utils.utcnow() - timedelta(days=self.history_days)
        for channel_id in self.channel_ids:
            await self._catch_up_channel(channel_id, after)

    async def _forward(self, message: discord.Message) -> None:
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

    async def _catch_up_channel(self, channel_id: int, after: datetime) -> None:
        channel = self.get_channel(channel_id)
        if channel is None:
            logger.warning("channel %s is not available", channel_id)
            return

        count = 0
        try:
            async for message in channel.history(after=after, limit=None, oldest_first=True):
                await self._forward(message)
                count += 1
                await asyncio.sleep(self.catch_up_delay)
        except discord.HTTPException:
            logger.exception("history of channel %s was not read", channel_id)
            return
        logger.info("channel %s checked %s messages from history", channel_id, count)
