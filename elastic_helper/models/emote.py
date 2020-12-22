from typing import Optional, List
from discord import Emoji
from itertools import chain

from .base_model import Model
from discord_bot import bot
from logging import getLogger


log = getLogger(__name__)


def db_init(name):
    return {
        "settings": {
            "analysis": {
                "analyzer": {
                    "camel_ngram": {
                        "type": "custom",
                        "tokenizer": "camel",
                        "filter": ["lowercase", "word_ngram_filter"]
                    },
                    "camel": {
                        "type": "custom",
                        "tokenizer": "camel",
                        "filter": ["lowercase"]
                    }
                },
                "tokenizer": {
                    "camel": {
                        "type": "pattern",
                        "pattern": "([^\\p{L}\\d]+)|(?<=\\D)(?=\\d)|(?<=\\d)(?=\\D)|(?<=[\\p{L}&&[^\\p{Lu}]])(?=\\p{Lu})|(?<=\\p{Lu})(?=\\p{Lu}[\\p{L}&&[^\\p{Lu}]])"
                    }
                },
                "filter": {
                    "word_ngram_filter": {
                        "type": "ngram",
                        "min_gram": 2,
                        "max_gram": 10,
                        "token_chars": []
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                name: {
                    "type": "text",
                    "analyzer": "camel_ngram",
                    "search_analyzer": "camel",
                    "fields": {
                        "raw": {
                            "type": "keyword"
                        }
                    }
                }
            }
        }
    }


class ExtraEmote(Model):
    index = "extra_emote"
    is_animated: bool

    shas: List[str]
    ids: List[str]
    names: List[str]
    filtered: bool

    times_used: int

    initialise = db_init("names")

    def __str__(self):
        a = "a" if self.is_animated else ""
        return f"<{a}:{self.name}:{self.id}>"

    @property
    def id(self):
        if self.ids:
            return int(self.ids[0])
        return None

    @property
    def name(self):
        emote = self.emote
        if emote:
            return emote.name
        return next(i for i in chain(self.names, [self.names[0][:32], self.names[0] + "__", "emoji"]) if 1 < len(i) <= 32 and not i.startswith("emoji_")).replace(" ", "")

    @property
    def emote(self) -> Optional[Emoji]:
        emoji_ = None
        for id in map(int, self.ids):
            emote = bot.bot.get_emoji(id)
            if emote and emote.available:
                if emote.name.startswith("emoji_"):
                    emoji_ = emote
                else:
                    return emote
        return emoji_

    @property
    def url(self) -> str:
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.is_animated else 'png'}"
