"""
Celery application for background task processing
"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery application
celery_app = Celery(
    "ai_project_monitoring",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.services.tasks"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=settings.celery_accept_content,
    timezone=settings.celery_timezone,
    enable_utc=settings.celery_enable_utc,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks"""
    from celery.schedules import crontab
    
    # Run agent analysis every 6 hours
    sender.add_periodic_task(
        crontab(minute=0, hour='*/6'),
        run_agent_analysis.s(),
        name='Run agent analysis every 6 hours'
    )
    
    # Update project health metrics every hour
    sender.add_periodic_task(
        crontab(minute=0),
        update_project_health.s(),
        name='Update project health every hour'
    )
    
    # Generate daily reports at midnight
    sender.add_periodic_task(
        crontab(minute=0, hour=0),
        generate_daily_reports.s(),
        name='Generate daily reports at midnight'
    )


@celery_app.task
def run_agent_analysis():
    """Run agent analysis for all active projects"""
    from app.services.tasks import run_agent_analysis_task
    return run_agent_analysis_task()


@celery_app.task
def update_project_health():
    """Update health metrics for all active projects"""
    from app.services.tasks import update_project_health_task
    return update_project_health_task()


@celery_app.task
def generate_daily_reports():
    """Generate daily reports for all active projects"""
    from app.services.tasks import generate_daily_reports_task
    return generate_daily_reports_task()
