import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (register all tables)
from app.attendance.router import me_router as attendance_me_router
from app.attendance.router import router as attendance_router
from app.auth.router import router as auth_router
from app.common.config import get_settings
from app.common.router import router as system_router
from app.dashboard.router import router as dashboard_router
from app.members.router import me_router as members_me_router
from app.members.router import router as members_router
from app.notifications.router import router as notifications_router
from app.packages.router import router as packages_router
from app.payments.router import router as payments_router
from app.reports.router import router as reports_router
from app.subscriptions.router import me_router as subscriptions_me_router
from app.subscriptions.router import router as subscriptions_router
from app.trainers.router import router as trainers_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    if s.bootstrap_admin_username and s.bootstrap_admin_password:
        from app.auth.service import ensure_admin
        from app.common.database import SessionLocal

        with SessionLocal() as db:
            ensure_admin(db, s.bootstrap_admin_username, s.bootstrap_admin_password)
    from app.notifications.scheduler import start_scheduler, stop_scheduler

    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title=s.app_name,
        version="1.0.0",
        description="REST API for the Gym Management System (Admin and Member roles).",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (
        system_router,
        auth_router,
        members_router,
        members_me_router,
        trainers_router,
        packages_router,
        subscriptions_router,
        subscriptions_me_router,
        attendance_router,
        attendance_me_router,
        payments_router,
        dashboard_router,
        reports_router,
        notifications_router,
    ):
        app.include_router(r, prefix="/api")
    return app


app = create_app()
