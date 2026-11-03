from datetime import datetime, timezone

from pydantic import BaseModel


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseSchema(BaseModel):
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
