from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.triggers.interval import IntervalTrigger

from django.conf import settings

import random

# @util.close_old_connections
# def delete_old_job_executions(max_age=604_800):
#     DjangoJobExecution.objects.delete_old_job_executions(max_age)

def get_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    executor = ThreadPoolExecutor(max_workers=10)
    scheduler.add_executor(executor, "default")
    return scheduler

def create_scheduler_job(id, func, name):
    scheduler = get_scheduler()
    scheduler.add_job(
        func,
        trigger=IntervalTrigger(
            minutes=random.randint(60, 120)),
            id=f"{name}-{id}",
            max_instances=10,
            replace_existing=True,
        )

    # scheduler.add_job(
    #     delete_old_job_executions,
    #     trigger=CronTrigger(
    #         day_of_week="mon", hour="00", minute="00"
    #     ),  # Midnight on Monday, before start of the next work week.
    #     id=f"func{id}",
    #     max_instances=10,
    #     replace_existing=True,
    # )
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
