"""Imports every model so SQLAlchemy metadata (and Alembic) see all tables."""

from app.attendance.models import Attendance, QrToken  # noqa: F401
from app.auth.models import User  # noqa: F401
from app.common.audit import AuditLog  # noqa: F401
from app.common.database import Base  # noqa: F401
from app.members.models import Member  # noqa: F401
from app.notifications.models import Notification, PushSubscription  # noqa: F401
from app.packages.models import Package  # noqa: F401
from app.payments.models import Payment  # noqa: F401
from app.subscriptions.models import Subscription  # noqa: F401
from app.trainers.models import Trainer  # noqa: F401
