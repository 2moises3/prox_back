"""Preferences control visibility in the in-app notification centre only."""
from pydantic import BaseModel, ConfigDict, StrictBool


class NotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommendations: StrictBool | None = None
    new_destinations: StrictBool | None = None
    announcements: StrictBool | None = None
