"""AlarmHub-style integration example for the built-in OPC UA plugin."""

from onesite.config import NavBuiltin, NavGroup, NavModel, SiteConfig, Theme, env

config = SiteConfig(
    project_name="AlarmHub OPC UA Demo",
    style=Theme.ARCO,
    plugins=["opcua", "site_logger"],
    database_url=env("DATABASE_URI", default="sqlite:///./app.db"),
    secret_key=env("SECRET_KEY", default="alarmhub-local-demo"),
    extra={"TIMEZONE": "Asia/Shanghai"},
    allowed_origins=["http://localhost:15273", "http://127.0.0.1:15273"],
    navigation=[
        NavBuiltin.dashboard(),
        NavGroup(
            key="alarm_management",
            label={"zh": "告警管理", "en": "Alarm Management"},
            icon="BellRing",
            default_open=True,
            children=[
                NavModel(model="alarm_record"),
                NavModel(model="rule"),
                NavModel(model="category"),
            ],
        ),
        NavModel(model="opcua_server"),
    ],
)
