"""Application configuration.

Every client decision listed in section 13 of the scope document is a setting
here, so the gym can change policy without code changes. Values come from
environment variables (or a ``.env`` file); secrets must never be committed.
"""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Gym Management System"
    environment: str = "development"

    # --- Database ---------------------------------------------------------
    database_url: str = "postgresql+psycopg://gym:gym@localhost:5432/gym"

    # --- Auth -------------------------------------------------------------
    jwt_secret: str = Field(default=_DEFAULT_SECRET, min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 12 * 60

    # Optional bootstrap admin, created at startup if no admin exists yet.
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None

    cors_origins: list[str] = ["http://localhost:4200"]

    # --- Gym business day (scope 13.3) ------------------------------------
    gym_timezone: str = "Asia/Kolkata"
    # Hour (0-23, gym local time) at which a new gym day begins. 0 = midnight.
    # E.g. 4 means a check-in at 02:30 still counts for the previous day.
    gym_day_start_hour: int = Field(default=0, ge=0, le=23)

    # --- Attendance policy (scope 13.2, 13.4, 13.5) -----------------------
    # Maximum successful check-ins per member per gym day. 0 = unlimited.
    attendance_max_checkins_per_day: int = Field(default=1, ge=0)
    # Block check-in when the member has no subscription covering today
    # (expired, upcoming-only, suspended or cancelled).
    attendance_require_active_subscription: bool = True
    # Rotating gym QR code: lifetime of each token and grace after expiry so a
    # member who scanned just before rotation is not rejected.
    qr_token_ttl_seconds: int = Field(default=60, ge=10)
    qr_token_grace_seconds: int = Field(default=15, ge=0)

    # --- Notifications (scope 13.6) ---------------------------------------
    reminder_days_before_expiry: list[int] = [7, 1]
    # Gym-local hour at which the daily reminder job runs.
    reminder_run_hour: int = Field(default=8, ge=0, le=23)
    scheduler_enabled: bool = True
    # Days ahead shown as "upcoming expiries" on the Admin dashboard.
    upcoming_expiry_window_days: int = 7

    # Web Push (VAPID). Push is skipped when these are not configured; in-app
    # notifications are always stored.
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"

    # --- Uploaded files (profile photos) ----------------------------------
    media_dir: str = "media"
    max_photo_bytes: int = 2 * 1024 * 1024

    # --- Member self-service (scope 13.7) ---------------------------------
    member_editable_fields: list[str] = ["email", "address", "gender", "date_of_birth", "photo_url"]

    # --- Rate limits (requests per window, per client IP) ----------------
    rate_limit_enabled: bool = True
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 60
    checkin_rate_limit: int = 10
    checkin_rate_window_seconds: int = 60

    @field_validator("gym_timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        ZoneInfo(v)  # raises if unknown
        return v

    @field_validator("reminder_days_before_expiry")
    @classmethod
    def _positive_days(cls, v: list[int]) -> list[int]:
        if any(d < 0 for d in v):
            raise ValueError("reminder days must be >= 0")
        return sorted(set(v), reverse=True)

    @model_validator(mode="after")
    def _production_secrets(self):
        if self.environment.lower() in ("production", "prod"):
            weak = self.jwt_secret == _DEFAULT_SECRET or len(self.jwt_secret) < 32
            if weak:
                raise ValueError("JWT_SECRET must be set to a random value of at least 32 characters in production")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.gym_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
