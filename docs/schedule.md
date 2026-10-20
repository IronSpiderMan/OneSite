# Schedule calendar

Schedule is an optional built-in model for assigning one project model to days and shifts. It is separate from `scheduled_tasks`, which runs background jobs.

In a Python project configuration:

```python
from onesite.config import ScheduleConfig, SiteConfig

config = SiteConfig(
    project_name="roster",
    schedule=ScheduleConfig(
        enabled=True,
        target_model="Employee",
        display_field="name",
    ),
)
```

In `site_config.json`, use the equivalent object:

```json
{
  "schedule": {
    "enabled": true,
    "target_model": "Employee",
    "display_field": "name"
  }
}
```

The target must be a stored SQLModel with a single `id` primary key of type `int` or `str`. Run `site sync` after enabling the feature. OneSite then generates the Schedule table, CRUD and enable/disable action, a calendar API, `/schedules` month view, and `/schedules/rules` management list. User roles that can read both the target model and its display field can read schedules; admins and developers with that access can change rules. The calendar shows enabled rules only.

Shifts are `day`, `night`, and `full_day`. Recurrence values are `daily`, `weekly`, `monthly`, and `dates`. Weekly rules use `weekdays` numbered Monday `0` through Sunday `6`; monthly rules use `month_days` numbered `1` through `31`; selected-date rules use `date` values in `dates` (serialized as ISO `YYYY-MM-DD` strings by the API). The generated forms show each rule field only for its recurrence type. Weekdays and month days use numeric multi-select controls; weekday labels follow the browser locale. In the schedule list, selected weekdays and month days appear as compact labels showing their actual values. A monthly day absent from a month is skipped. `start_date` defaults to the server's current date, `end_date` is optional and inclusive, and `enabled` defaults to true.

The calendar API accepts `GET /api/v1/schedules/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`. `end` is exclusive, and requests are limited to 62 days. Disabling a rule removes its occurrences from the calendar without deleting the rule.
