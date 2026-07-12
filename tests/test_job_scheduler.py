import asyncio

from office_food_bot.services.job_scheduler import JobScheduler


def test_daily_cron_runs_on_every_day_including_weekends() -> None:
    scheduler = JobScheduler("Europe/Belgrade")

    scheduler.add_daily_cron(
        "daily",
        lambda: asyncio.sleep(0),
        hour=11,
        minute=30,
    )

    job = scheduler._scheduler.get_job("daily")
    assert job is not None
    assert str(job.trigger) == "cron[hour='11', minute='30']"
