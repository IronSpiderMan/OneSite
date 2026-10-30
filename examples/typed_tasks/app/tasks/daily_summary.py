from pydantic import BaseModel, Field

from onesite_runtime.tasks import (
    BaseScheduledTask,
    CronSchedule,
    ExecutionOptions,
    NotifyOptions,
    ResultUI,
    ScheduledTaskContext,
)


class SummaryInputs(BaseModel):
    __i18n__ = {"zh": {"fields": {"days": "统计天数"}}}

    days: int = Field(default=7, ge=1, le=30, title="Days")


class SummaryRow(BaseModel):
    __i18n__ = {"zh": {"fields": {"day": "天数", "message": "摘要"}}}

    day: int
    message: str


class SummaryResult(BaseModel):
    __i18n__ = {"zh": {"fields": {"rows": "统计明细"}}}

    rows: list[SummaryRow]


class DailySummaryTask(BaseScheduledTask):
    name = "daily_summary"
    title = "Daily summary"
    description = "Generate an example summary for the selected number of days."
    inputs = SummaryInputs
    result = SummaryResult
    schedule = CronSchedule(cron="0 3 * * *")
    enabled = False  # Enable automatic scheduling from the Dashboard when ready.
    overlap = "skip"
    execution = ExecutionOptions(timeout_seconds=120)
    manual_permissions = ("admin", "developer")
    notify = NotifyOptions(on_failure=True, roles=["developer"])
    result_ui = ResultUI(renderer="table", field="rows")
    translations = {
        "zh": {"title": "每日摘要", "description": "按配置天数生成示例摘要。"},
    }

    async def run(self, inputs: SummaryInputs, context: ScheduledTaskContext) -> SummaryResult:
        await context.set_progress(50, "Building summary")
        return SummaryResult(rows=[
            SummaryRow(day=day, message=f"Summary for day {day}")
            for day in range(1, inputs.days + 1)
        ])
