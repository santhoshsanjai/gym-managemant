import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.common.config import get_settings
from app.common.database import SessionLocal

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def run_reminder_job() -> None:
    from app.notifications.service import generate_reminders

    with SessionLocal() as db:
        try:
            created = generate_reminders(db)
            log.info("Reminder job created %d notification(s)", len(created))
        except Exception:  # pragma: no cover - logged for ops
            log.exception("Reminder job failed")


def start_scheduler() -> None:
    global _scheduler
    s = get_settings()
    if not s.scheduler_enabled or _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=s.tz)
    _scheduler.add_job(
        run_reminder_job,
        CronTrigger(hour=s.reminder_run_hour, minute=0, timezone=s.tz),
        id="subscription-reminders",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    # Catch up once at startup in case the server was down at the scheduled time.
    _scheduler.add_job(run_reminder_job, id="subscription-reminders-startup")
    _scheduler.start()
    log.info("Scheduler started (reminders daily at %02d:00 %s)", s.reminder_run_hour, s.gym_timezone)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
