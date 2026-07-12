from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.date import DateTrigger  # type: ignore[import-untyped]

AsyncJob = Callable[[], Awaitable[None]]


class JobScheduler:
    def __init__(self, timezone_name: str) -> None:
        self._timezone = ZoneInfo(timezone_name)
        self._scheduler = AsyncIOScheduler(timezone=self._timezone)  # type: ignore[no-any-unimported]

    def add_weekday_cron(
        self,
        job_id: str,
        callback: AsyncJob,
        *,
        hour: int,
        minute: int,
    ) -> None:
        self._scheduler.add_job(
            callback,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=hour,
                minute=minute,
                timezone=self._timezone,
            ),
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def add_date(self, job_id: str, callback: AsyncJob, run_at: datetime) -> None:
        self._scheduler.add_job(
            callback,
            trigger=DateTrigger(run_date=run_at),
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def remove(self, job_id: str) -> None:
        if self._scheduler.get_job(job_id) is not None:
            self._scheduler.remove_job(job_id)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
