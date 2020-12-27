from typing import Optional, List, Callable
from discord import Emoji, PartialEmoji
from itertools import chain

from .base_model import Model
from logging import getLogger
import copy


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


def _warn(message):
    try:
        raise Exception(message)
    except Exception:
        log.warning(message, exc_info=True)


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
        return next(i for i in chain(self.names, [self.names[0][:32], self.names[0] + "__", "emoji"]) if 1 < len(i) <= 32 and not i.startswith("emoji_")).replace(" ", "")

    def get_emote_from_ids(self, lookup: Callable[[int], Optional[Emoji]]) -> Optional[Emoji]:
        for id in map(int, self.ids):
            emote = lookup(id)
            if emote and emote.available:
                rtn = copy.copy(emote)
                rtn.name = self.name
                return rtn

    @property
    def url(self) -> str:
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.is_animated else 'png'}"

    def to_partial(self, lookup: Callable[[int], Optional[Emoji]]) -> PartialEmoji:
        emoji = self.get_emote_from_ids(lookup)
        return PartialEmoji(
            name=self.name,
            id=emoji.id if emoji else self.id,
            animated=self.is_animated
        )
