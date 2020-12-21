from .base_model import Model
from datetime import datetime


class GuildMessage(Model):
    index = "guild_message_*"

    channel: str
    guild: str
    author: str
    content: str
    time: datetime

    initialise = {
        "settings": {
            "index.lifecycle.name": "30_day_deletion"
        }
    }