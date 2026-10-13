import discord


def message_text(message: discord.Message) -> str:
    parts = [message.content]
    for embed in message.embeds:
        parts += [embed.title, embed.description]
        parts += [f"{field.name}\n{field.value}" for field in embed.fields]
        parts.append(embed.footer.text)
    return "\n".join(part for part in parts if part)
