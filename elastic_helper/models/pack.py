from typing import List, Dict, Union

from .base_model import Model


class Pack(Model):
    index = "packs"
    initialise = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "camel": {
                        "type": "pattern",
                        "pattern": r"([^\p{L}\d]+)|(?<=\D)(?=\d)|(?<=\d)(?=\D)|(?<=[\p{L}&&[^\p{Lu}]])(?=\p{Lu})|(?<=\p{Lu})(?=\p{Lu}[\p{L}&&[^\p{Lu}]])"
                        }
                    }
                }
            },
        "mappings": {
            "properties": {
                "name": {
                    "type": "text",
                    "analyzer": "camel",
                    "search_analyzer": "camel"
                },
                "emote_names": {
                    "type": "text",
                    "analyzer": "camel",
                    "search_analyzer": "camel"
                },
                "member_count": {
                    "type": "integer"
                },
                "public": {
                    "type": "boolean"
                }
            }
        }
    }

    name: str
    public: bool
    emote_names: List[str]
    member_count: int


class GuildGroup(Model):
    index = "guild_groups"

    max_emotes: int
    emotes: List[Dict[str, Union[str, int]]]
    packs: List[str]
