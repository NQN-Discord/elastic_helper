from typing import Dict, Any, Optional, Union
from datetime import datetime

from .base_model import Model


class Logging(Model):
    index = "logs_*"

    type: str
    guild: Optional[Union[int, str]]
    user: Optional[str]
    time: datetime

    meta: Dict[str, Any]

    initialise = {
        "mappings": {
            "properties": {
                "time": {
                    "type": "date",
                    "format": "date_hour_minute_second"
                }
            }
        },
        "settings": {
            "index.lifecycle.name": "30_day_deletion"
        }
    }
