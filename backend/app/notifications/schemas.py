from datetime import datetime

from pydantic import BaseModel, Field

from app.notifications.models import NotificationType


class NotificationOut(BaseModel):
    id: int
    type: NotificationType
    title: str
    body: str
    subscription_id: int | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PushKeys(BaseModel):
    p256dh: str = Field(max_length=255)
    auth: str = Field(max_length=255)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=2000, pattern=r"^https://")
    keys: PushKeys


class ReminderRunResult(BaseModel):
    created: int
