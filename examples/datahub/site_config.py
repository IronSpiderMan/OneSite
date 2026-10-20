"""OneSite project configuration.

This file is executed by ``site sync``. Keep it as trusted project code and
export exactly one variable named ``config``.
"""

from onesite.config import (
    CustomDashboardWidget,
    CustomFeature,
    CustomFeatureMenu,
    CustomOverride,
    CustomPage,
    DesktopConfig,
    NavBuiltin,
    NavGroup,
    NavModel,
    NavRoute,
    SiteConfig,
    env,
    sqlite_url,
)


config = SiteConfig(
    project_name='datahub',
    theme="neuron",
    database_url=sqlite_url(),
    upload_dir="uploads",
    # Set SECRET_KEY in the shell or deployment environment for production.
    secret_key=env("SECRET_KEY", default="changeme"),
    access_token_expire_minutes=11520,
    extra={"TIMEZONE": "Asia/Shanghai"},
    allowed_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    desktop=DesktopConfig(
        identifier='com.onesite.datahub',
        version="0.1.0",
        api_url="http://127.0.0.1:8000/api/v1",
        width=1280,
        height=800,
    ),
    custom_features=[
        CustomFeature(
            name="ops_dashboard",
            frontend_only=True,
            pages=[
                CustomPage(
                    id="workspace",
                    path="/operations",
                    component="pages/OperationsWorkspace.tsx",
                    menu=CustomFeatureMenu(
                        title={"zh": "运营工作台", "en": "Operations Workspace"},
                        icon="Activity",
                    ),
                ),
                CustomPage(
                    id="connector_detail",
                    path="/operations/connectors/:connectorId",
                    component="pages/ConnectorDetail.tsx",
                ),
                CustomPage(
                    id="public_status",
                    path="/public/datahub-status",
                    component="pages/PublicStatus.tsx",
                    layout="public",
                ),
            ],
            overrides=[
                CustomOverride(
                    target="model.sync_task.detail",
                    component="pages/SyncTaskDetailOverride.tsx",
                ),
            ],
            dashboard_widgets=[
                CustomDashboardWidget(
                    id="platform_pulse",
                    component="components/PlatformPulseWidget.tsx",
                    title={"zh": "平台运行脉搏", "en": "Platform Pulse"},
                    span={"md": 12, "xl": 8},
                    order=10,
                ),
                CustomDashboardWidget(
                    id="recent_activity",
                    component="components/RecentActivityWidget.tsx",
                    title={"zh": "最近数据活动", "en": "Recent Data Activity"},
                    span={"md": 12, "xl": 4},
                    order=20,
                ),
            ],
        ),
    ],
    navigation=[
        NavBuiltin.dashboard(),
        NavGroup(
            key="operations",
            label={"zh": "运营工作区", "en": "Operations"},
            icon="Activity",
            default_open=True,
            children=[
                NavRoute(route="ops_dashboard.workspace"),
            ],
        ),
        NavGroup(
            key="assets",
            label={"zh": "数据资产", "en": "Data Assets"},
            icon="Database",
            default_open=True,
            children=[
                NavModel(model="data_source"),
                NavModel(model="dataset"),
                NavModel(model="asset_folder"),
                NavModel(model="asset_document"),
                NavModel(model="tag"),
            ],
        ),
        NavGroup(
            key="services",
            label={"zh": "数据服务", "en": "Data Services"},
            icon="Plug",
            children=[
                NavModel(model="data_service"),
                NavModel(model="data_quality_rule"),
            ],
        ),
        NavGroup(
            key="integration",
            label={"zh": "数据集成", "en": "Data Integration"},
            icon="RefreshCw",
            children=[
                NavModel(model="sync_task"),
            ],
        ),
        NavBuiltin.reports(),
        NavModel(model="hub_settings"),
    ],
)
