import asyncio
import json
import os
from collections.abc import Coroutine
from typing import Any
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore

from app.common.logger import Logger

DATA_DIRECTORY = os.environ.get("DATA_DIRECTORY", "/app/data")

logger = Logger(
    "ISeeTV-Scheduler",
    os.environ.get("VERBOSE", "false"),
    os.environ.get("LOG_LEVEL", "INFO"),
    color="PINK",
)


def get_cron_schedule() -> tuple[str, str]:
    with open(os.path.join(DATA_DIRECTORY, "config.json")) as f:
        config = json.load(f)

    epg_cron = get_epg_cron_schedule(config)
    m3u_cron = get_m3u_cron_schedule(config)

    return epg_cron, m3u_cron


def get_m3u_cron_schedule(config: dict[str, Any]) -> str:
    m3u_time = config["m3u_update_time"].split(":")
    return f"{m3u_time[1]} {m3u_time[0]} */{config['m3u_update_interval']} * *"


def get_epg_cron_schedule(config: dict[str, Any]) -> str:
    epg_time = config["epg_update_time"].split(":")
    return f"{epg_time[1]} {epg_time[0]} */{config['epg_update_interval']} * *"


def start_scheduler(
    epg_updater: Callable[[], Coroutine[Any, Any, None]],
    m3u_updater: Callable[[], Coroutine[Any, Any, None]],
) -> BackgroundScheduler:
    # Wrap async functions in sync functions
    def run_epg() -> None:
        asyncio.create_task(epg_updater())

    def run_m3u() -> None:
        asyncio.create_task(m3u_updater())

    scheduler = BackgroundScheduler()
    epg_cron, m3u_cron = get_cron_schedule()

    scheduler.add_job(run_epg, CronTrigger.from_crontab(epg_cron))
    logger.info(f"EPG updater scheduled to run at {epg_cron}")

    scheduler.add_job(run_m3u, CronTrigger.from_crontab(m3u_cron))
    logger.info(f"M3U updater scheduled to run at {m3u_cron}")

    scheduler.start()
    return scheduler
