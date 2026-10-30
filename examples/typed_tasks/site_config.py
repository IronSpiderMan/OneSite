from onesite.config import SiteConfig, Theme

from app.tasks.daily_summary import DailySummaryTask


config = SiteConfig(
    project_name="TypedTasks",
    style=Theme.INDUSTRIAL,
    scheduled_tasks=[DailySummaryTask],
)
