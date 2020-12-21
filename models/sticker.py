from .base_model import Model
from .emote import db_init


class Sticker(Model):
    index = "sticker"
    initialise = db_init("name")

    name: str
    url: str
    owner_id: int
