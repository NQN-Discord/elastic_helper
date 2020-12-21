from typing import List, Optional
from datetime import datetime

from .base_model import Model


class User(Model):
    index = "nqn_users"

    vote_times: List[int]
    vote_total: int
    alias_message: Optional[int]
    ignored_commands: List[str]
    commands_ran: Optional[int]

    last_request: Optional[datetime]

