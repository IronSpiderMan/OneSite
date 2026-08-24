import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_utils import write_file_with_status


def generate_locale_files(
    models: List[Dict[str, Any]],
    locale_dir: Path,
    navigation_groups: List[Dict[str, Any]] | None = None,
):

    zh_field_defaults: Dict[str, str] = {
        "language": "语言",
        "timezone": "时区",
        "theme": "主题",
        "theme_style": "主题样式",
        "theme_mode": "主题模式",
        "site_name": "站点名称",
        "logo": "站点 Logo",
        "allow_registration": "允许注册",
        "announcement_content": "公告内容",
    }

    en_translations: Dict[str, Any] = {
        "common": {
            "welcome": "Welcome",
            "login": "Login",
            "logout": "Logout",
            "settings": "Settings",
            "language": "Language",
            "timezone": "Timezone",
            "theme": "Theme",
            "save": "Save",
            "cancel": "Cancel",
            "create": "Create",
            "edit": "Edit",
            "delete": "Delete",
            "enable": "Enable",
            "disable": "Disable",
            "actions": "Actions",
            "search": "Search",
            "filters": "Filters",
            "reset": "Reset",
            "all": "All",
            "yes": "Yes",
            "no": "No",
            "loading": "Loading...",
            "success": "Success",
            "error": "Error",
            "confirm_delete": "Are you sure you want to delete this item?",
            "upload": "Upload",
            "no_result": "No result",
            "previous": "Previous",
            "next": "Next",
            "first": "First",
            "last": "Last",
            "page_info": "Page",
            "of_page": "of",
            "page_size": "Page size",
            "select": "Select",
            "auto_refresh": "Auto Refresh",
            "realtime": "Realtime",
            "property_data": "Property data",
            "last_100": "Last 100",
            "compact": "Compact",
            "comfortable": "Comfortable",
            "history": "History",
            "time_range": "Time range",
            "select_all": "Select all",
            "clear": "Clear",
            "show_more": "Show more",
            "show_less": "Show less",
            "no_matching_metric": "No matching metric",
            "no_realtime_data": "No realtime data",
            "no_matching_point": "No matching point",
            "refresh_interval": "Refresh Interval",
            "local_storage": "Local Storage",
            "back": "Back",
            "back_home": "Back Home",
            "retry": "Retry",
            "profile": "Profile",
            "bulk_delete": "Bulk Delete",
            "export": "Export",
            "import": "Import",
            "template": "Template",
            "export_started": "Export started, you will be notified when complete",
            "export_complete": "Export completed",
            "export_failed": "Export failed",
            "navigation": "Navigation",
            "system": "System",
            "expand": "Expand",
            "collapse": "Collapse",
            "remove": "Remove",
            "details": "Details",
            "basic_information": "Basic Information",
            "related_information": "Related Information",
        },
        "location": {
            "latitude": "Latitude",
            "longitude": "Longitude",
            "use_current": "Use current location",
            "locating": "Locating...",
            "choose_on_map": "Choose on map",
            "hide_map": "Hide map",
            "map_hint": "Click the map to select a location.",
            "tiles_unavailable": "Map tiles could not be loaded. Check the network or configure VITE_MAP_TILE_URL.",
            "unsupported": "Geolocation is not supported by this browser.",
            "permission_denied": "Location permission was denied.",
            "timeout": "Getting the current location timed out.",
            "unavailable": "Unable to get the current location.",
        },
        "video_stream": {
            "stream": "Video stream",
            "url_placeholder": "Enter a video stream URL",
            "preview": "Preview stream",
            "hide_preview": "Hide preview",
            "detected": "Detected: {{type}}",
            "loading": "Connecting to video stream...",
            "empty": "No video stream URL",
            "unsupported_protocol": "{{type}} streams cannot be played directly in a browser. Convert the source to HLS or WebRTC first.",
            "unsupported_browser": "This browser cannot play this HLS stream.",
            "playback_error": "The stream could not be played. Check its availability, CORS settings, authentication, and codec.",
            "retry": "Reconnect",
            "types": {
                "hls": "HLS",
                "native": "Browser video",
                "rtsp": "RTSP",
                "rtmp": "RTMP",
                "srt": "SRT",
                "unknown": "Unknown",
            },
        },
        "json_editor": {
            "object": "JSON object",
            "array": "JSON array",
            "form_mode": "Form",
            "source_mode": "JSON source",
            "add_item": "Add item",
            "item_added": "New item added",
            "add_entry": "Add entry",
            "item": "Item {{index}}",
            "entry": "Entry {{index}}",
            "key": "Key",
            "key_placeholder": "Enter a unique key",
            "valid": "Valid",
            "invalid": "Needs fixing",
            "format": "Format",
            "format_shortcut": "Format (Ctrl/Cmd + Enter)",
            "copy": "Copy",
            "copied": "Copied",
            "ready": "Changes are synced automatically",
            "empty_hint": "Enter JSON or leave empty",
            "syntax_error": "Invalid JSON syntax",
            "syntax_error_at": "Invalid JSON near line {{line}}, column {{column}}",
            "object_required": "The value must be a JSON object",
            "array_required": "The value must be a JSON array",
            "line_count": "{{count}} line",
            "line_count_plural": "{{count}} lines",
        },
        "menu": {
            "dashboard": "Dashboard",
            "external_resources": "External Resources",
            "task_center": "Task Center",
            "reports": "Data Explorer",
        },
        "reports": {
            "title": "Data Explorer", "description": "Explore, aggregate, visualize, and export time-series data",
            "export_csv": "Export CSV", "filters": "Filters", "report": "Report", "entities": "Devices",
            "metrics": "Metrics", "start_time": "Start", "end_time": "End", "bucket": "Interval",
            "aggregation": "Aggregation", "query": "Query", "trend": "Trend", "results": "Results",
            "entity": "Device", "metric": "Metric", "time": "Time", "value": "Value",
            "explorer": "Data explorer", "settings": "Analysis settings", "settings_hint": "Select a range and run the query",
            "clear": "Clear", "select": "Select {{label}}", "all": "All {{label}}", "selected": "{{count}} selected",
            "search": "Search {{label}}", "select_all": "Select all", "no_match": "No matching options",
            "range": "Time range", "run": "Run analysis", "reset": "Reset filters", "connect_error": "Unable to connect to the service",
            "selection_required": "Select at least one entity and one metric", "empty_title": "Start exploring your data",
            "empty_hint": "Select dimensions and measures, then choose a time range to produce charts and detailed results.",
            "select_data": "Select data", "run_analysis": "Run analysis", "export_result": "Export result",
            "points": "Data points", "minimum": "Minimum", "average": "Average", "maximum": "Maximum",
            "view": "Data view", "truncated": "The result reached the {{limit}} row limit. Shorten the range or increase the interval.",
            "details": "Data details", "row_count": "{{count}} results", "raw": "Raw", "aggregate": "Aggregated",
        },
        "dashboard": {
            "total": "total",
            "no_models": "No models available for dashboard",
            "no_visualizations": "No visualizations or tasks configured",
            "overview_description": "A clear overview of your key data and recent activity",
            "no_data": "No data available",
            "metric_new": "New",
            "vs_previous_period": "vs previous period",
            "period_day": "Daily",
            "period_week": "Weekly",
            "period_month": "Monthly",
            "refresh_success": "Tasks refreshed",
            "shift_left": "Previous period",
            "shift_right": "Next period",
            "reset_today": "Reset to today",
            "app_logs": "Application Logs",
            "all_levels": "All Levels",
            "no_logs": "No log entries",
            "scheduled_tasks": "Scheduled Tasks",
            "no_tasks": "No scheduled tasks configured",
            "enabled": "Enabled",
            "disabled": "Disabled",
            "next_run": "Next run",
            "run_now": "Run now",
            "edit_task": "Edit Task",
            "task_name": "Task Name",
            "schedule_type": "Schedule Type",
            "type_cron": "Scheduled Time",
            "type_interval": "Interval",
            "scheduled_times": "Scheduled Times",
            "add_time": "Add Time",
            "cron_help": "Select the times to run each day",
            "interval_value": "Run Every",
            "minutes": "minutes",
            "hours": "hours",
            "days": "days",
            "description": "Description",
            "description_placeholder": "Task description",
            "parameters": "Parameters",
            "task_updated": "Task \"{{name}}\" updated",
            "every_day_at": "Every day at",
            "task_run_success": "Task \"{{name}}\" executed successfully",
            "task_run_error": "Task \"{{name}}\" failed: {{message}}",
            "task_enabled": "Task \"{{name}}\" enabled",
            "task_disabled": "Task \"{{name}}\" disabled",
            "every": "Every",
            "seconds_short": "s",
            "minutes_short": "m",
            "hours_short": "h",
            "days_short": "d",
        },
        "tools": {
            "title": "Tools",
            "subtitle": "Run workspace utilities and track their progress",
            "available": "available",
            "inputs": "inputs",
            "any_file": "Any file type",
            "no_file_selected": "No file selected",
            "files_selected": "{{count}} files selected",
            "status": {"queued": "Queued", "running": "Running", "succeeded": "Completed", "failed": "Failed"},
            "execute": "Execute",
            "queued": "Tool queued",
            "submit_failed": "Failed to start tool",
            "download": "Download result",
        },
        "task_center": {
            "title": "Task center",
            "description": "Track all work submitted to the background task queue.",
            "view_progress": "View progress",
            "refresh": "Refresh",
            "loading": "Loading tasks...",
            "empty": "No background tasks found.",
            "load_failed": "Unable to load background tasks",
            "detail_load_failed": "Unable to load task details",
            "kinds": {
                "import": "Import",
                "export": "Export",
                "tool": "Tool",
                "scheduled_task": "Scheduled task",
            },
            "statuses": {
                "queued": "Queued",
                "running": "Running",
                "succeeded": "Completed",
                "failed": "Failed",
            },
            "stages": {
                "queued": "Waiting in queue",
                "running": "Running",
                "failed": "Failed",
                "preparing_export": "Preparing export",
                "exporting_records": "Exporting {{current}} of {{total}} records",
                "finalizing_export": "Finalizing export file",
                "running_custom_export": "Running custom export",
                "reading_import_file": "Reading import file",
                "validating_import": "Validating {{total}} rows and relations",
                "importing_records": "Importing {{current}} of {{total}} rows",
                "finalizing_import": "Finalizing import result",
                "running_custom_import": "Running custom import",
                "completed": "Completed",
                "interrupted": "Interrupted by application restart",
            },
            "filters": {
                "kind": "Type",
                "all_kinds": "All types",
                "model": "Task",
                "all_models": "All tasks",
                "status": "Status",
                "all_statuses": "All statuses",
            },
            "columns": {
                "kind": "Type",
                "model": "Task",
                "status": "Status",
                "progress": "Progress",
                "stage": "Current stage",
                "created_at": "Created",
                "actions": "Actions",
            },
            "actions": {"download": "Download", "details": "View details"},
            "pagination": {
                "summary": "Page {{page}} of {{totalPages}} · {{total}} tasks",
                "previous": "Previous",
                "next": "Next",
            },
            "details": {
                "title": "Task details",
                "loading": "Loading details...",
                "task_id": "Task ID",
                "trigger": "Trigger",
                "kind": "Type",
                "model": "Task",
                "status": "Status",
                "stage": "Current stage",
                "progress": "Progress",
                "created_at": "Created",
                "started_at": "Started",
                "completed_at": "Completed",
                "import_result": "Import result",
                "success": "Succeeded",
                "failed": "Failed",
                "created": "Created",
                "updated": "Updated",
                "error": "Error",
                "row_errors": "Row errors",
                "errors_truncated": "Showing the first errors from {{count}} failed rows.",
                "inputs": "Inputs",
            },
        },
        "notifications": {
            "title": "Notifications",
            "empty": "No notifications",
            "detail": "Notification",
            "new": "New notification",
            "mark_all_read": "Mark all read",
        },
        "errors": {
            "403": {"title": "Access denied", "desc": "You don't have permission to view this page."},
            "404": {"title": "Page not found", "desc": "The page you’re looking for doesn’t exist."},
            "500": {"title": "Something went wrong", "desc": "Please try again or return to the home page."},
            "offline": {
                "code": "OFFLINE",
                "title": "You are offline",
                "desc": "Network connection failed. Please check your connection and try again.",
            },
        },
        "login": {
            "title": "Sign in",
            "description": "Enter your email and password to access the admin panel",
            "email": "Email",
            "emailPlaceholder": "m@example.com",
            "password": "Password",
            "signIn": "Sign In",
            "signingIn": "Signing in...",
            "error": "Login failed. Please check your credentials.",
            "demo": "Demo: admin@example.com / admin",
            "system_access": "System Access",
            "no_account": "Don't have an account?",
            "register": "Create account",
        },
        "register": {
            "title": "Create account",
            "description": "Enter the required information to create your account",
            "confirm_password": "Confirm Password",
            "submit": "Register",
            "submitting": "Creating account...",
            "success": "Registration successful. You can now sign in.",
            "error": "Registration failed. Please check your information.",
            "password_mismatch": "Passwords do not match",
            "disabled": "Registration is currently disabled.",
            "have_account": "Already have an account?",
            "back_to_login": "Back to sign in",
        },
        "settings": {
            "system_title": "System Settings",
            "save_system": "Save System Settings",
            "custom_title": "Personal Settings",
            "save_custom": "Save Personal Settings",
        },
        "profile": {
            "basic": "Basic Info",
            "full_name_placeholder": "Enter your name",
            "change_password": "Change Password",
            "old_password": "Old Password",
            "new_password": "New Password",
            "confirm_password": "Confirm Password",
            "password_mismatch": "Passwords do not match",
            "password_changed": "Password changed successfully",
        },
        "alert": {
            "delete_title": "Confirm deletion",
            "bulk_delete_confirm": "Are you sure you want to delete these items?",
        },
        "toast": {
            "create_success": "Created",
            "update_success": "Updated",
            "delete_success": "Deleted",
            "delete_failed": "Delete failed",
            "save_failed": "Save failed",
        },
        "models": {},
    }

    zh_translations: Dict[str, Any] = {
        "common": {
            "welcome": "欢迎",
            "login": "登录",
            "logout": "退出登录",
            "settings": "设置",
            "language": "语言",
            "timezone": "时区",
            "theme": "主题",
            "save": "保存",
            "cancel": "取消",
            "create": "创建",
            "edit": "编辑",
            "delete": "删除",
            "enable": "启用",
            "disable": "停用",
            "actions": "操作",
            "search": "搜索",
            "filters": "筛选",
            "reset": "重置",
            "all": "全部",
            "yes": "是",
            "no": "否",
            "loading": "加载中...",
            "success": "成功",
            "error": "错误",
            "confirm_delete": "确定要删除此项吗？",
            "upload": "上传",
            "no_result": "暂无数据",
            "previous": "前一页",
            "next": "后一页",
            "first": "首页",
            "last": "末页",
            "page_info": "第",
            "of_page": "页，共",
            "page_size": "每页条数",
            "select": "选择",
            "auto_refresh": "自动刷新",
            "realtime": "实时数据",
            "property_data": "属性数据",
            "last_100": "最近 100 条",
            "compact": "紧凑",
            "comfortable": "舒适",
            "history": "历史数据",
            "time_range": "时间范围",
            "select_all": "全选",
            "clear": "清空",
            "show_more": "显示更多",
            "show_less": "收起",
            "no_matching_metric": "没有匹配的指标",
            "no_realtime_data": "暂无实时数据",
            "no_matching_point": "没有匹配的点位",
            "refresh_interval": "刷新频率",
            "local_storage": "本地存储",
            "back": "返回",
            "back_home": "返回首页",
            "retry": "重试",
            "profile": "个人信息",
            "bulk_delete": "批量删除",
            "export": "导出",
            "import": "导入",
            "template": "模板",
            "export_started": "导出已开始，完成后将通知您",
            "export_complete": "导出完成",
            "export_failed": "导出失败",
            "navigation": "导航",
            "system": "系统",
            "expand": "展开",
            "collapse": "收起",
            "remove": "移除",
            "details": "详情",
            "basic_information": "基础信息",
            "related_information": "关联信息",
        },
        "location": {
            "latitude": "纬度",
            "longitude": "经度",
            "use_current": "获取当前位置",
            "locating": "正在定位...",
            "choose_on_map": "在地图上选择",
            "hide_map": "收起地图",
            "map_hint": "点击地图选择位置。",
            "tiles_unavailable": "地图瓦片加载失败，请检查网络或配置 VITE_MAP_TILE_URL。",
            "unsupported": "当前浏览器不支持定位。",
            "permission_denied": "定位权限被拒绝。",
            "timeout": "获取当前位置超时。",
            "unavailable": "无法获取当前位置。",
        },
        "video_stream": {
            "stream": "视频流",
            "url_placeholder": "输入视频流地址",
            "preview": "预览视频流",
            "hide_preview": "收起预览",
            "detected": "识别类型：{{type}}",
            "loading": "正在连接视频流……",
            "empty": "暂无视频流地址",
            "unsupported_protocol": "浏览器无法直接播放 {{type}} 视频流，请先将视频源转换为 HLS 或 WebRTC。",
            "unsupported_browser": "当前浏览器无法播放此 HLS 视频流。",
            "playback_error": "视频流无法播放，请检查可用性、跨域配置、鉴权和编码格式。",
            "retry": "重新连接",
            "types": {
                "hls": "HLS",
                "native": "浏览器视频",
                "rtsp": "RTSP",
                "rtmp": "RTMP",
                "srt": "SRT",
                "unknown": "未知",
            },
        },
        "json_editor": {
            "object": "JSON 对象",
            "array": "JSON 数组",
            "form_mode": "表单编辑",
            "source_mode": "JSON 源码",
            "add_item": "添加一项",
            "item_added": "已添加新项目",
            "add_entry": "添加条目",
            "item": "第 {{index}} 项",
            "entry": "第 {{index}} 个条目",
            "key": "键名",
            "key_placeholder": "输入唯一键名",
            "valid": "格式正确",
            "invalid": "需要修正",
            "format": "格式化",
            "format_shortcut": "格式化（Ctrl/Cmd + Enter）",
            "copy": "复制",
            "copied": "已复制",
            "ready": "修改会自动同步",
            "empty_hint": "输入 JSON，或留空",
            "syntax_error": "JSON 语法不正确",
            "syntax_error_at": "JSON 在第 {{line}} 行、第 {{column}} 列附近有误",
            "object_required": "必须输入 JSON 对象",
            "array_required": "必须输入 JSON 数组",
            "line_count": "{{count}} 行",
        },
        "menu": {
            "dashboard": "仪表盘",
            "external_resources": "外部资源同步",
            "task_center": "任务中心",
            "reports": "数据探索",
        },
        "reports": {
            "title": "数据探索", "description": "探索、聚合、可视化和导出时序数据",
            "export_csv": "导出 CSV", "filters": "筛选条件", "report": "报表", "entities": "设备",
            "metrics": "点位", "start_time": "开始时间", "end_time": "结束时间", "bucket": "统计周期",
            "aggregation": "聚合方式", "query": "查询", "trend": "趋势", "results": "查询结果",
            "entity": "设备", "metric": "点位", "time": "时间", "value": "数值",
            "explorer": "数据探索", "settings": "分析设置", "settings_hint": "选择范围并运行查询",
            "clear": "清除", "select": "选择{{label}}", "all": "全部{{label}}", "selected": "已选 {{count}} 个",
            "search": "搜索{{label}}", "select_all": "全选", "no_match": "没有匹配项",
            "range": "时间范围", "run": "运行分析", "reset": "重置条件", "connect_error": "无法连接到服务",
            "selection_required": "请至少选择一个实体和一个指标", "empty_title": "开始探索数据",
            "empty_hint": "选择维度和指标并设置时间范围，生成图表和详细结果。",
            "select_data": "选择数据", "run_analysis": "运行分析", "export_result": "导出结果",
            "points": "数据点", "minimum": "最小值", "average": "平均值", "maximum": "最大值",
            "view": "数据视图", "truncated": "结果已达到 {{limit}} 条上限，请缩短时间范围或增大统计周期。",
            "details": "数据明细", "row_count": "共 {{count}} 条结果", "raw": "原始", "aggregate": "聚合",
        },
        "dashboard": {
            "total": "总计",
            "no_models": "没有可用于仪表盘的模型",
            "no_visualizations": "未配置可视化或定时任务",
            "overview_description": "清晰掌握关键数据与近期动态",
            "no_data": "暂无数据",
            "metric_new": "新增",
            "vs_previous_period": "较上一周期",
            "period_day": "按日",
            "period_week": "按周",
            "period_month": "按月",
            "refresh_success": "任务已刷新",
            "shift_left": "上一时段",
            "shift_right": "下一时段",
            "reset_today": "重置为今天",
            "app_logs": "应用日志",
            "all_levels": "全部级别",
            "no_logs": "暂无日志",
            "scheduled_tasks": "定时任务",
            "no_tasks": "未配置定时任务",
            "enabled": "已启用",
            "disabled": "已禁用",
            "next_run": "下次运行",
            "run_now": "立即运行",
            "edit_task": "编辑任务",
            "task_name": "任务名称",
            "schedule_type": "调度类型",
            "type_cron": "定时时间",
            "type_interval": "间隔执行",
            "scheduled_times": "执行时间",
            "add_time": "添加时间",
            "cron_help": "选择每天执行的时间",
            "interval_value": "每隔",
            "minutes": "分钟",
            "hours": "小时",
            "days": "天",
            "description": "描述",
            "description_placeholder": "任务描述",
            "parameters": "参数",
            "task_updated": "任务\"{{name}}\"已更新",
            "every_day_at": "每天",
            "task_run_success": "任务\"{{name}}\"执行成功",
            "task_run_error": "任务\"{{name}}\"执行失败：{{message}}",
            "task_enabled": "任务\"{{name}}\"已启用",
            "task_disabled": "任务\"{{name}}\"已禁用",
            "every": "每隔",
            "seconds_short": "秒",
            "minutes_short": "分钟",
            "hours_short": "小时",
            "days_short": "天",
        },
        "tools": {
            "title": "工具",
            "subtitle": "运行工作区工具并跟踪执行进度",
            "available": "个可用",
            "inputs": "项输入",
            "any_file": "支持所有文件类型",
            "no_file_selected": "尚未选择文件",
            "files_selected": "已选择 {{count}} 个文件",
            "status": {"queued": "等待执行", "running": "执行中", "succeeded": "已完成", "failed": "执行失败"},
            "execute": "执行",
            "queued": "工具已加入队列",
            "submit_failed": "工具启动失败",
            "download": "下载结果",
        },
        "task_center": {
            "title": "任务中心",
            "description": "统一查看后台任务队列中所有任务的进度、结果、错误和下载文件。",
            "view_progress": "查看进度",
            "refresh": "刷新",
            "loading": "正在加载任务...",
            "empty": "暂无后台任务。",
            "load_failed": "无法加载后台任务",
            "detail_load_failed": "无法加载任务详情",
            "kinds": {
                "import": "导入",
                "export": "导出",
                "tool": "工具",
                "scheduled_task": "定时任务",
            },
            "statuses": {
                "queued": "等待执行",
                "running": "执行中",
                "succeeded": "已完成",
                "failed": "执行失败",
            },
            "stages": {
                "queued": "正在队列中等待",
                "running": "执行中",
                "failed": "执行失败",
                "preparing_export": "正在准备导出",
                "exporting_records": "正在导出第 {{current}} / {{total}} 条记录",
                "finalizing_export": "正在生成最终导出文件",
                "running_custom_export": "正在执行自定义导出",
                "reading_import_file": "正在读取导入文件",
                "validating_import": "正在校验 {{total}} 行数据及关联关系",
                "importing_records": "正在导入第 {{current}} / {{total}} 行",
                "finalizing_import": "正在汇总导入结果",
                "running_custom_import": "正在执行自定义导入",
                "completed": "已完成",
                "interrupted": "应用重启导致任务中断",
            },
            "filters": {
                "kind": "类型",
                "all_kinds": "全部类型",
                "model": "任务",
                "all_models": "全部任务",
                "status": "状态",
                "all_statuses": "全部状态",
            },
            "columns": {
                "kind": "类型",
                "model": "任务",
                "status": "状态",
                "progress": "进度",
                "stage": "当前阶段",
                "created_at": "发起时间",
                "actions": "操作",
            },
            "actions": {"download": "下载", "details": "查看详情"},
            "pagination": {
                "summary": "第 {{page}} / {{totalPages}} 页，共 {{total}} 个任务",
                "previous": "上一页",
                "next": "下一页",
            },
            "details": {
                "title": "任务详情",
                "loading": "正在加载详情...",
                "task_id": "任务 ID",
                "trigger": "触发方式",
                "kind": "类型",
                "model": "任务",
                "status": "状态",
                "stage": "当前阶段",
                "progress": "进度",
                "created_at": "发起时间",
                "started_at": "开始时间",
                "completed_at": "完成时间",
                "import_result": "导入结果",
                "success": "成功",
                "failed": "失败",
                "created": "新建",
                "updated": "更新",
                "error": "错误",
                "row_errors": "逐行错误",
                "errors_truncated": "共 {{count}} 行失败，当前仅显示前面的错误。",
                "inputs": "任务输入",
            },
        },
        "notifications": {
            "title": "消息通知",
            "empty": "暂无消息",
            "detail": "消息详情",
            "new": "收到新消息",
            "mark_all_read": "全部已读",
        },
        "errors": {
            "403": {"title": "无权限访问", "desc": "你没有权限访问此页面。"},
            "404": {"title": "页面不存在", "desc": "你访问的页面不存在或已被移除。"},
            "500": {"title": "服务异常", "desc": "发生了一些错误，请稍后重试或返回首页。"},
            "offline": {"code": "离线", "title": "网络不可用", "desc": "网络连接失败，请检查网络后重试。"},
        },
        "login": {
            "title": "登录",
            "description": "输入您的邮箱和密码以访问管理面板",
            "email": "电子邮箱",
            "emailPlaceholder": "m@example.com",
            "password": "密码",
            "signIn": "登录",
            "signingIn": "登录中...",
            "error": "登录失败，请检查您的凭据。",
            "demo": "演示账号：admin@example.com / admin",
            "system_access": "系统访问",
            "no_account": "还没有账号？",
            "register": "立即注册",
        },
        "register": {
            "title": "创建账号",
            "description": "填写必填信息以创建您的账号",
            "confirm_password": "确认密码",
            "submit": "注册",
            "submitting": "正在创建账号...",
            "success": "注册成功，现在可以登录。",
            "error": "注册失败，请检查填写的信息。",
            "password_mismatch": "两次输入的密码不一致",
            "disabled": "当前未开放注册。",
            "have_account": "已经有账号？",
            "back_to_login": "返回登录",
        },
        "settings": {
            "system_title": "系统配置",
            "save_system": "保存系统配置",
            "custom_title": "个性化配置",
            "save_custom": "保存个性化配置",
        },
        "profile": {
            "basic": "基础信息",
            "full_name_placeholder": "请输入姓名",
            "change_password": "修改密码",
            "old_password": "当前密码",
            "new_password": "新密码",
            "confirm_password": "确认密码",
            "password_mismatch": "两次输入的密码不一致",
            "password_changed": "密码修改成功",
        },
        "alert": {
            "delete_title": "确认删除",
            "bulk_delete_confirm": "确定要删除这些项目吗？",
        },
        "toast": {
            "create_success": "创建成功",
            "update_success": "更新成功",
            "delete_success": "删除成功",
            "delete_failed": "删除失败",
            "save_failed": "保存失败",
        },
        "models": {},
    }

    def set_by_path(obj: Dict[str, Any], path: str, value: Any):
        parts = [p for p in path.split(".") if p]
        if not parts:
            return
        cur: Dict[str, Any] = obj
        for p in parts[:-1]:
            nxt = cur.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[p] = nxt
            cur = nxt
        cur[parts[-1]] = value

    for group in navigation_groups or []:
        key = group["key"].removeprefix("group:")
        labels = group.get("translations", {})
        set_by_path(en_translations, f"menu.groups.{key}", labels.get("en", key))
        set_by_path(zh_translations, f"menu.groups.{key}", labels.get("zh", key))

    def pick_model_name(pack: Any, fallback: str) -> str:
        if isinstance(pack, str):
            return pack
        if isinstance(pack, dict):
            name = pack.get("name")
            if isinstance(name, str) and name:
                return name
        return fallback

    def pick_model_field_label(pack: Any, field_name: str) -> Optional[str]:
        if not isinstance(pack, dict):
            return None
        fields = pack.get("fields")
        if not isinstance(fields, dict):
            return None
        v = fields.get(field_name)
        if isinstance(v, str) and v:
            return v
        return None

    def resolve_field_label(field_name: str, field: dict, en_pack, zh_pack) -> tuple[str, str]:
        """Resolve en/zh label for a field, checking translations, defaults, and auto-generating."""
        label_en = field_name.replace("_", " ").title()
        label_zh = label_en

        translations = field.get("translations", {})
        if "en" in translations:
            label_en = translations["en"]
        else:
            v = pick_model_field_label(en_pack, field_name)
            if v is not None:
                label_en = v
        if "zh" in translations:
            label_zh = translations["zh"]
        else:
            v = pick_model_field_label(zh_pack, field_name)
            if v is not None:
                label_zh = v
            elif field_name in zh_field_defaults:
                label_zh = zh_field_defaults[field_name]

        return label_en, label_zh

    for model in models:
        model_name = model["module_name"]
        model_name_en = model["name"]
        model_name_zh = model["name"]

        model_translations = model.get("translations")
        if not isinstance(model_translations, dict):
            model_translations = {}
        en_pack = model_translations.get("en")
        zh_pack = model_translations.get("zh")
        model_name_en = pick_model_name(en_pack, model_name_en)
        model_name_zh = pick_model_name(zh_pack, model_name_zh)

        en_model = {"name": model_name_en, "plural": f"{model_name_en}s", "fields": {}}
        zh_model = {"name": model_name_zh, "plural": model_name_zh, "fields": {}}

        # Add "my_name" translation for owner-scoped models (e.g., "My Items")
        if model.get("owner_field"):
            en_model["my_name"] = f"My {model_name_en}s"
            zh_model["my_name"] = f"我的{model_name_zh}"

        # Generate translations for model groups (e.g., settings.groups.general)
        site_props = model.get("site_props", {})
        groups = site_props.get("groups", [])
        for g in groups:
            group_key = g.get("key")
            if group_key:
                label_en = g.get("en", group_key)
                label_zh = g.get("zh", g.get("en", group_key))
                set_by_path(en_translations, f"settings.groups.{group_key}", label_en)
                set_by_path(zh_translations, f"settings.groups.{group_key}", label_zh)

        # Build field label lookup for filter i18n
        field_label_lookup: dict[str, tuple[str, str]] = {}
        for field in model["fields"]:
            field_label_lookup[field["name"]] = resolve_field_label(field["name"], field, en_pack, zh_pack)

        for field in model["fields"]:
            field_name = field["name"]
            label_en, label_zh = resolve_field_label(field_name, field, en_pack, zh_pack)

            en_model["fields"][field_name] = label_en
            zh_model["fields"][field_name] = label_zh

            label_key = field.get("label_key")
            if isinstance(label_key, str) and label_key:
                set_by_path(en_translations, label_key, label_en)
                set_by_path(zh_translations, label_key, label_zh)

            # Enum value translations — collected into model dict
            if field.get("is_enum") and field.get("enum_values"):
                enum_trans = field.get("enum_translations", {})
                en_enums = en_model.setdefault("enums", {})
                zh_enums = zh_model.setdefault("enums", {})
                en_field_enum: dict[str, str] = {}
                zh_field_enum: dict[str, str] = {}
                for enum_val in field["enum_values"]:
                    en_field_enum[enum_val] = enum_trans.get("en", {}).get(enum_val) or str(enum_val)
                    zh_field_enum[enum_val] = enum_trans.get("zh", {}).get(enum_val) or str(enum_val)
                en_enums[field_name] = en_field_enum
                zh_enums[field_name] = zh_field_enum

        # Visualize filter i18n (dashboard.filter_{name})
        viz = model.get("visualize")
        if viz and viz.get("resolved_filters"):
            for rf in viz["resolved_filters"]:
                filter_name = rf.get("name", "")
                if not filter_name:
                    continue
                i18n_key = f"dashboard.filter_{filter_name}"
                # Skip if already set
                if i18n_key in en_translations.get("dashboard", {}):
                    continue
                # Try to resolve label from field translations
                filter_field = rf.get("filter_field", filter_name)
                # Enum filters: filter_field == field name, direct lookup
                # FK filters: filter_field="category_id", name="category"
                labels = field_label_lookup.get(filter_field) or field_label_lookup.get(filter_name)
                if labels:
                    en_label, zh_label = labels
                else:
                    en_label = filter_name.replace("_", " ").title()
                    # Try zh from model field translations or field defaults
                    zh_label = (pick_model_field_label(zh_pack, filter_name)
                                or zh_field_defaults.get(filter_name, en_label))
                set_by_path(en_translations, i18n_key, en_label)
                set_by_path(zh_translations, i18n_key, zh_label)

        # Dashboard KPI titles. A model translation can override the declared title:
        # translations.{lang}.dashboard_metrics.{key}
        for metric in model.get("dashboard_metrics", []):
            key = metric["key"]
            fallback = metric["title"]
            en_metric_titles = en_pack.get("dashboard_metrics") if isinstance(en_pack, dict) else None
            zh_metric_titles = zh_pack.get("dashboard_metrics") if isinstance(zh_pack, dict) else None
            en_title = en_metric_titles.get(key, fallback) if isinstance(en_metric_titles, dict) else fallback
            zh_title = zh_metric_titles.get(key, fallback) if isinstance(zh_metric_titles, dict) else fallback
            metric_i18n_key = metric.get(
                "i18n_key", f"dashboard.metrics.{model_name}.{key}"
            )
            set_by_path(en_translations, metric_i18n_key, en_title)
            set_by_path(zh_translations, metric_i18n_key, zh_title)

        en_translations["models"][model_name] = en_model
        zh_translations["models"][model_name] = zh_model

    write_file_with_status(locale_dir / "en.json", json.dumps(en_translations, indent=2))
    write_file_with_status(locale_dir / "zh.json", json.dumps(zh_translations, indent=2, ensure_ascii=False))
