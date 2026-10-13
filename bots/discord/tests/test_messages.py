from types import SimpleNamespace

import discord

from bot.messages import message_text


def make_message(content: str = "", embeds: list[discord.Embed] | None = None):
    return SimpleNamespace(content=content, embeds=embeds or [])


def test_takes_message_content() -> None:
    assert message_text(make_message("Промокод RUST2026")) == "Промокод RUST2026"


def test_collects_text_from_embeds() -> None:
    embed = discord.Embed(title="Вайп!", description="Лови промокод")
    embed.add_field(name="Код", value="RUST2026")
    embed.set_footer(text="Действует до пятницы")

    text = message_text(make_message("@everyone", [embed]))

    assert text == "@everyone\nВайп!\nЛови промокод\nКод\nRUST2026\nДействует до пятницы"


def test_skips_empty_parts() -> None:
    assert message_text(make_message("", [discord.Embed(description="RUST2026")])) == "RUST2026"
    assert message_text(make_message("", [discord.Embed()])) == ""
