from .base_model import Model
from .emote import db_init


class Sticker(Model):
    index = "sticker"
    initialise = db_init("prefix", "suffix")

    prefix: str
    suffix: str
    url: str
    owner_id: int

    @property
    def name(self):
        return f"{self.prefix}.{self.suffix}"
