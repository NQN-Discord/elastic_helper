from typing import Optional, List, Tuple
from discord import Emoji
from itertools import chain
from aiohttp import ClientSession

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
        if self.emote:
            return emote.name
        return next(i for i in chain(self.names, [self.names[0][:32], self.names[0] + "__", "emoji"]) if 1 < len(i) <= 32 and not i.startswith("emoji_")).replace(" ", "")

    @property
    def emote(self) -> Optional[Emoji]:
        emoji_ = None
        for id in map(int, self.ids):
            if id in bot.bot.emoji_ids:
                emote = bot.bot.get_emoji(id)
                if emote is None:
                    log.warning("Desyncronised emote id list!")
                    bot.bot.emoji_ids.remove(id)
                    continue
                if emote.available:
                    if emote.name.startswith("emoji_"):
                        emoji_ = emote
                    else:
                        return emote
        return emoji_

    @property
    def url(self) -> str:
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.is_animated else 'png'}"

    @classmethod
    async def get_hashes(cls, id: int, is_animated: bool) -> Tuple[str, str]:
        async with ClientSession() as session:
            results = await session.get(
                f"{bot.bot.config.hasher_url}/emoji",
                params={"id": id, "a": int(is_animated)}
            )
            results = await results.json()
            return results["sha"], results["perceptual"]

    @classmethod
    async def update_from_discord_emote(cls, target: Emoji) -> Optional["ExtraEmote"]:
        """
        First checks in the database to see if this emoji has already been accounted for before downloading the emote if needed
        """
        async with bot.bot.elastic as db:
            emote = await db.search_single(cls, ids=target.id)
            if emote:
                return emote

            sha, perceptual = await cls.get_hashes(target.id, target.animated)
            if sha == perceptual == "":
                return None

            if target.available:
                async with bot.bot.postgres() as pg:
                    await pg.set_emote_perceptual_data(
                        emote_id=target.id,
                        emote_hash=perceptual,
                        animated=target.animated
                    )

            emote = await db.get(cls, perceptual)
            if emote is None:
                rtn = cls(
                    _id=perceptual,
                    shas=[sha],
                    names=[target.name],
                    times_used=0,
                    filtered=False,
                    is_animated=target.animated,
                    ids=[str(target.id)]
                )
                await rtn.set_redis_data()
                return rtn
            if str(target.id) not in emote.ids:
                emote.ids.append(str(target.id))
            if target.name not in emote.names:
                emote.names.append(target.name)
            if sha not in emote.shas:
                emote.shas.append(sha)
            await emote.set_redis_data(ids=[target.id], include_times_used=False)
            return emote

    @classmethod
    async def migrate(cls, old_emotes: List["ExtraEmote"], new: "ExtraEmote"):
        log.info(f"Migrating '{[old._id for old in old_emotes]}' to '{new._id}'")
        async with bot.bot.elastic as db:
            for old in old_emotes:
                new.shas.extend(old.shas)
                new.ids.extend(old.ids)
                new.names = list(set(old.names) | set(new.names))
                new.filtered |= old.filtered
                new.times_used += old.times_used

                await db.delete(old)
                await old.delete_redis_data()
            await db.add(new, op_type="index")
        await new.set_redis_data()

    async def set_redis_data(self, ids=None, include_times_used: bool = True):
        if ids is None:
            ids = self.ids
        await bot.bot.redis.set_emote_ids(self._id, ids, self.times_used if include_times_used else None)

    async def delete_redis_data(self):
        await bot.bot.redis.delete_emote_ids(self)
