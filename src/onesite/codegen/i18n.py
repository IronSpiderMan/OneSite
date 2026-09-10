import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_utils import write_file_with_status


def generate_locale_files(
    models: List[Dict[str, Any]],
    locale_dir: Path,
    navigation_groups: List[Dict[str, Any]] | None = None,
    frontend_features: List[Dict[str, Any]] | None = None,
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
            "saving": "Saving...",
            "cancel": "Cancel",
            "create": "Create",
            "click_to_create": "Click to create",
            "add": "Add",
            "adding": "Adding...",
            "add_existing": "Add existing",
            "select_existing": "Select existing records",
            "attach_existing_success": "Existing records added",
            "attach_existing_failed": "Failed to add existing records",
            "edit": "Edit",
            "delete": "Delete",
            "deleting": "Deleting...",
            "enable": "Enable",
            "disable": "Disable",
            "sort_ascending": "Sort ascending",
            "sort_descending": "Sort descending",
            "sort_default": "Use default order",
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
            "online_status": "Online status",
            "online": "Online",
            "offline": "Offline",
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
        "multi_display": {
            "view_mode": "View mode",
            "list_view": "List",
            "multi_view": "Multi-display",
            "search_items": "Search items",
            "selection_count": "Selected {{count}} / {{max}}",
            "empty_title": "Select items to display",
            "empty_description": "Use the checkboxes to add items to this view.",
            "max_selected": "You can display up to {{max}} items.",
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
            "external_resources": "External Providers",
            "task_center": "Task Center",
            "reports": "Reports",
        },
        "reports": {
            "editor": {"table_data": "Table data", "table_settings": "Table settings", "chart_settings": "Chart settings", "chart_settings_hint": "Configure data and filters, generate a preview, then apply it to this block.", "chart_tab_data": "Data & chart", "chart_tab_filters": "Filters", "chart_tab_preview": "Preview", "chart_run_preview": "Generate preview", "chart_apply": "Apply chart", "chart_apply_hint": "Apply the preview to update the report.", "table_settings_hint": "Changes appear in the report immediately. Save the report template to keep them.", "table_close_settings": "Close settings", "table_settings_sections": "Settings sections", "table_tab_data": "Data & paging", "table_tab_filters": "Filters", "table_tab_columns": "Fields", "table_fields_unit": "fields", "table_filters_unit": "filters", "table_source_hint": "Choose the model that supplies this table.", "table_size_hint": "Changing the row count returns to page 1.", "table_apply": "Apply", "table_search_fields": "Search fields", "table_selected": "selected", "table_no_matching_fields": "No matching fields.", "table_live_hint": "Preview updates automatically", "table_done": "Done", "table_rows_unit": "rows / page", "table_previous_page": "Previous page", "table_next_page": "Next page", "table_no_filters": "No filters available for this model.", "remove_table": "Remove table", "table_source": "Table data source", "table_size": "Rows per page", "table_columns": "Visible fields", "table_show_all": "Show all", "table_hide_all": "Hide all", "table_no_columns": "No fields selected for display.", "table_error": "Table could not be loaded. Check access and retry.", "table_no_sources": "No readable frontend data sources.", "table_select": "Select an available table data source.", "table_page": "Page", "table_total": "Total", "blank": "Blank page", "period": "Date range", "last_days": "Last {{count}} days", "fixed_dates": "Fixed dates", "storage_error": "Could not read saved templates.", "discard_action": "Discard changes", "discard": "Discard unsaved page changes?", "save_error": "Could not save templates. Browser storage may be full or disabled.", "title_required": "Enter a report title.", "saved": "Template saved in this browser.", "unavailable": "Model unavailable", "query_error": "Some charts could not be loaded. Check permissions and query settings.", "chart_added": "Chart inserted into the selected block.", "print_view": "Report print view", "chart": "Chart", "pdf_error": "Could not open the print view. Please try again in a browser.", "templates": "Templates", "new": "New page", "unsaved": "Unsaved changes", "up_to_date": "Saved", "save": "Save template", "save_copy": "Save as new template", "delete_template": "Delete template", "confirm_delete": "Delete this template?", "edit": "Edit", "focus_preview": "Focus preview", "pdf": "Export PDF", "dismiss": "Dismiss", "workspace": "Report workspace", "content_layout": "Content & layout", "chart_data": "Chart data", "title": "Report title", "subtitle": "Subtitle / description", "outline": "Page outline", "undo": "Undo layout", "drag_hint": "Drag the handle to reorder rows. Select a block to edit it.", "drag_row": "Drag row", "row": "Row", "up": "Move up", "down": "Move down", "duplicate": "Duplicate row", "remove_row": "Remove row", "block": "Block", "block_settings": "Selected block", "row_layout": "Row layout", "page_break": "Start row on a new PDF page", "insert_below": "Insert below", "format": "Content format", "plain_text": "Plain text", "text": "Block content", "text_placeholder": "Write your report content…", "html_hint": "Supports headings, tables, lists, links and basic text styling. Scripts and embedded pages are excluded.", "live_hint": "Changes appear instantly in the preview.", "swap": "Swap position with", "choose_position": "Choose another block", "add_chart_hint": "This block can also contain a chart.", "remove_chart": "Remove chart", "configure_chart": "Configure chart", "select_hint": "Select a block on the page.", "target": "Insert into", "insert_chart": "Insert / replace current chart", "storage_hint": "Templates are stored in this browser. Queries refresh when a template is opened.", "live_preview": "Preview", "refresh": "Refresh data", "document": "Report document", "report_label": "DATA REPORT", "untitled": "Untitled report", "report_date": "Report date", "sections": "sections", "empty_title": "Start with a blank page", "empty_hint": "Add a row on the left. Text, tables and charts appear here as you edit.", "first_row": "Add the first row", "page_break_marker": "New PDF page", "empty_block": "Select this block to add content", "no_data": "No data for these filters.", "loading": "Loading…", "needs_refresh": "Chart unavailable. Refresh to retry.", "footer_note": "Generated from current report data", "layout_single": "One column", "layout_halves": "Two columns", "layout_thirds": "Three columns", "layout_wide-left": "Wide left", "layout_wide-right": "Wide right", "new_sheet": "New page", "close_chart_panel": "Close chart panel", "canvas_hint": "Add rows on the page, then select a region to edit.", "chart_title_placeholder": "Add a title for this chart", "visual_title": "Title (optional)", "visual_title_placeholder": "Add a title for this diagram or image", "edit_visual": "Edit diagram / image", "insert_visual": "Diagram / image", "image_url": "Image URL", "image_alt": "Image description", "image_error": "Invalid image source or image could not be loaded.", "data_chart": "Data chart", "edit_text": "Edit text", "chart_image": "Chart / image", "apply_content": "Save content", "cancel_content": "Cancel", "draft_hint": "Save to render this region. Other regions stay rendered.", "canvas_empty_block": "Choose text or a chart for this region"},
            "export_csv": "Export CSV", "filters": "Filters", "aggregation": "Aggregation",
            "details": "Data details",
            "builder_kicker": "Report builder", "builder_title": "Reports",
            "builder_description": "Design report pages with text, charts, and reusable templates",
            "builder_settings": "Report settings", "builder_settings_hint": "Available choices are controlled by the model",
            "model": "Model", "category": "Chart category", "chart": "Chart style", "bin": "Bin",
            "x_axis": "X axis", "y_axis": "Y axis", "classification": "Classification", "count": "Count",
            "record_count": "Record count", "run_report": "Run report", "reset_report": "Reset",
            "builder_empty_title": "Build a report",
            "builder_empty_hint": "Select a model and chart, bind its inputs, then run the query.",
            "result_summary": "{{model}} · {{count}} rows", "truncated_badge": "Truncated",
            "categories": {
                "cartesian": "Trend & comparison", "multi_cartesian": "Multiple series",
                "composition": "Composition", "scatter": "Correlation",
            },
            "charts": {
                "line_basic": "Line", "line_smooth": "Smooth line", "line_area": "Area",
                "line_step": "Step line", "bar_basic": "Bar", "combo_bar_line": "Bar + line",
                "line_multi": "Multiple lines", "line_multi_smooth": "Multiple smooth lines",
                "area_multi": "Multiple areas", "bar_grouped": "Grouped bars", "bar_stacked": "Stacked bars",
                "line_multi_step": "Multiple step lines", "combo_multi_bar_line": "Multiple bars + line",
                "pie_basic": "Pie", "pie_donut": "Donut", "pie_half_donut": "Half donut",
                "pie_rose": "Nightingale rose", "scatter_basic": "Scatter",
                "scatter_category": "Categorized scatter",
            },
            "bins": {
                "none": "No bin", "auto": "Auto", "1m": "1 minute", "5m": "5 minutes",
                "15m": "15 minutes", "hour": "Hour", "day": "Day", "week": "Week", "month": "Month",
            },
            "aggregations": {
                "raw": "Raw", "sum": "Sum", "avg": "Average", "min": "Minimum", "max": "Maximum",
                "median": "Median", "count": "Count", "distinct_count": "Distinct count",
            },
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
            "saving": "正在保存...",
            "cancel": "取消",
            "create": "创建",
            "click_to_create": "点击创建",
            "add": "添加",
            "adding": "添加中...",
            "add_existing": "添加已有",
            "select_existing": "选择已有记录",
            "attach_existing_success": "已有记录添加成功",
            "attach_existing_failed": "添加已有记录失败",
            "edit": "编辑",
            "delete": "删除",
            "deleting": "正在删除...",
            "enable": "启用",
            "disable": "停用",
            "sort_ascending": "按此字段升序",
            "sort_descending": "按此字段降序",
            "sort_default": "恢复默认排序",
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
            "online_status": "在线状态",
            "online": "在线",
            "offline": "离线",
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
        "multi_display": {
            "view_mode": "浏览方式",
            "list_view": "普通列表",
            "multi_view": "多项展示",
            "search_items": "搜索项目",
            "selection_count": "已选择 {{count}} / {{max}}",
            "empty_title": "请选择要展示的项目",
            "empty_description": "使用复选框将项目添加到展示区域。",
            "max_selected": "最多可同时展示 {{max}} 项。",
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
            "external_resources": "外部 Provider 同步",
            "task_center": "任务中心",
            "reports": "数据报表",
        },
        "reports": {
            "editor": {"table_data": "数据表格", "table_settings": "表格设置", "chart_settings": "图表设置", "chart_settings_hint": "配置数据与筛选条件，生成预览后应用到当前区块。", "chart_tab_data": "数据与图表", "chart_tab_filters": "筛选条件", "chart_tab_preview": "图表预览", "chart_run_preview": "生成预览", "chart_apply": "应用图表", "chart_apply_hint": "点击「应用图表」后更新报表正文。", "table_settings_hint": "修改会即时更新到报表中，保存报表模板后可保留设置。", "table_close_settings": "关闭设置", "table_settings_sections": "设置分组", "table_tab_data": "数据与分页", "table_tab_filters": "筛选条件", "table_tab_columns": "显示字段", "table_fields_unit": "个字段", "table_filters_unit": "项筛选", "table_source_hint": "选择此表格的数据来源模型。", "table_size_hint": "修改条数后将回到第一页。", "table_apply": "应用", "table_search_fields": "搜索字段名称", "table_selected": "已选择", "table_no_matching_fields": "没有匹配的字段", "table_live_hint": "预览自动更新", "table_done": "完成", "table_rows_unit": "条 / 页", "table_previous_page": "上一页", "table_next_page": "下一页", "table_no_filters": "此模型暂无可用的筛选条件。", "remove_table": "移除表格", "table_source": "表格数据源", "table_size": "每页条数", "table_columns": "显示字段", "table_show_all": "全部显示", "table_hide_all": "全部隐藏", "table_no_columns": "当前没有选择要显示的字段。", "table_error": "表格加载失败，请检查权限后刷新重试。", "table_no_sources": "没有当前账号可读取的前端数据源。", "table_select": "请选择可用的表格数据源。", "table_page": "页码", "table_total": "总条数", "blank": "空白页面", "discard_action": "放弃修改", "discard": "放弃当前页面未保存的修改？", "period": "日期范围", "last_days": "近 {{count}} 天", "fixed_dates": "固定日期", "templates": "选择模板", "new": "新建页面", "save": "保存模板", "save_copy": "另存为新模板", "delete_template": "删除模板", "confirm_delete": "确定删除此模板？", "refresh": "刷新数据", "edit": "编辑", "preview": "预览", "pdf": "导出 PDF", "hint": "在左侧编辑内容与图表，右侧实时预览。模板保存在当前浏览器。", "title": "报表标题", "text": "区块内容", "insert_chart": "插入 / 替换当前图表", "text_only": "改为纯文本", "one_column": "添加单列行", "two_columns": "添加双列行", "up": "上移", "down": "下移", "remove_row": "删除行", "no_data": "当前筛选条件下没有数据", "loading": "加载中…", "needs_refresh": "图表不可用，请刷新重试", "query_error": "部分图表加载失败，请检查权限和查询条件。", "unavailable": "模型不可用", "title_required": "请输入报表标题", "saved": "模板已保存到当前浏览器", "storage_error": "无法读取已保存的模板", "save_error": "模板保存失败，浏览器存储可能已满或被禁用。", "workspace": "报表工作区", "content_layout": "内容与排版", "chart_data": "图表数据", "unsaved": "未保存修改", "up_to_date": "已保存", "focus_preview": "专注预览", "dismiss": "关闭提示", "subtitle": "副标题 / 报表说明", "outline": "页面结构", "undo": "撤销排版", "drag_hint": "拖动手柄调整行顺序，点击区块编辑内容。", "drag_row": "拖动行", "row": "行", "block": "区块", "duplicate": "复制行", "layout_single": "单列", "layout_halves": "双列", "layout_thirds": "三列", "layout_wide-left": "左宽右窄", "layout_wide-right": "左窄右宽", "block_settings": "当前区块", "row_layout": "本行布局", "page_break": "PDF 中另起一页", "insert_below": "下方插入行", "format": "内容格式", "plain_text": "纯文本", "text_placeholder": "输入报表正文…", "html_hint": "支持标题、表格、列表、链接及文字颜色、对齐。不执行脚本或嵌入页面。", "live_hint": "修改会即时显示在右侧预览中。", "swap": "交换区块位置", "choose_position": "选择另一个区块", "chart": "图表", "add_chart_hint": "这个区块也可以插入图表。", "remove_chart": "移除图表", "configure_chart": "配置图表", "select_hint": "先添加行，再选择区块编写内容或插入图表。", "target": "插入位置：", "storage_hint": "模板保存在当前浏览器；打开模板时会重新查询图表数据。", "live_preview": "实时预览", "document": "报表正文预览", "report_label": "数据报告", "report_date": "报告日期", "sections": "个段落", "empty_title": "从一张空白报表开始", "empty_hint": "在左侧添加行，编写正文、表格或插入图表，效果会同步显示在这里。", "first_row": "添加第一行", "page_break_marker": "PDF 分页位置", "empty_block": "点击此区块添加内容", "untitled": "未命名报表", "footer_note": "依据报表查询数据生成", "chart_added": "图表已插入当前区块。", "print_view": "报表打印视图", "pdf_error": "无法打开打印视图，请在浏览器中重试。", "new_sheet": "新页", "canvas_hint": "在页面上添加布局，点击区域编辑内容", "close_chart_panel": "收起图表面板", "chart_title_placeholder": "为数据图表添加标题", "visual_title": "标题（可选）", "visual_title_placeholder": "为图示或图片添加标题", "edit_visual": "编辑图示 / 图片", "insert_visual": "图示 / 图片", "image_url": "图片 URL", "image_alt": "图片说明（替代文字）", "image_error": "图片来源无效或加载失败，请检查 SVG 源码或图片地址。", "data_chart": "数据图表", "edit_text": "编辑文字", "chart_image": "图表图片", "apply_content": "保存内容", "cancel_content": "取消", "mermaid_error": "Mermaid 显示失败，请查看下方错误详情。", "mermaid_not_ready": "Mermaid 正在加载或存在错误，请检查图形后再导出。", "draft_hint": "保存后在当前区域渲染，其他区域保持展示。", "canvas_empty_block": "选择文字、图示 / 图片、数据图表或数据表格填充此区域"},
            "export_csv": "导出 CSV", "filters": "筛选条件", "aggregation": "聚合方式",
            "details": "数据明细",
            "builder_kicker": "报表生成器", "builder_title": "数据报表",
            "builder_description": "自由编排内容与图表，实时预览并导出精美报告",
            "builder_settings": "报表设置", "builder_settings_hint": "可选范围由模型配置控制",
            "model": "模型", "category": "图表大类", "chart": "图表形式", "bin": "分箱方式",
            "x_axis": "X 轴", "y_axis": "Y 轴", "classification": "分类字段", "count": "计数字段",
            "record_count": "记录数", "run_report": "生成报表", "reset_report": "重置",
            "builder_empty_title": "开始创建报表",
            "builder_empty_hint": "选择模型和图表，绑定输入字段后运行查询。",
            "result_summary": "{{model}} · {{count}} 条数据", "truncated_badge": "结果已截断",
            "categories": {
                "cartesian": "趋势与对比", "multi_cartesian": "多系列图表",
                "composition": "占比与构成", "scatter": "相关性分析",
            },
            "charts": {
                "line_basic": "折线图", "line_smooth": "平滑折线图", "line_area": "基础面积图",
                "line_step": "阶梯折线图", "bar_basic": "柱状图", "combo_bar_line": "柱状图 + 折线图",
                "line_multi": "多折线图", "line_multi_smooth": "多平滑折线图",
                "area_multi": "多面积图", "bar_grouped": "多类柱状图", "bar_stacked": "堆叠柱状图",
                "line_multi_step": "多阶梯折线图", "combo_multi_bar_line": "多柱状图 + 折线图",
                "pie_basic": "饼图", "pie_donut": "环形图", "pie_half_donut": "半环形图",
                "pie_rose": "南丁格尔玫瑰图", "scatter_basic": "散点图",
                "scatter_category": "分类散点图",
            },
            "bins": {
                "none": "不分箱", "auto": "自动", "1m": "1 分钟", "5m": "5 分钟",
                "15m": "15 分钟", "hour": "小时", "day": "天", "week": "周", "month": "月",
            },
            "aggregations": {
                "raw": "原始值", "sum": "求和", "avg": "平均值", "min": "最小值", "max": "最大值",
                "median": "中位数", "count": "计数", "distinct_count": "去重计数",
            },
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

    def add_json_model_translations(schema: Any) -> None:
        """Emit labels carried by structured JSON model schemas."""
        if not isinstance(schema, dict):
            return
        for json_field in schema.get("fields", []):
            if not isinstance(json_field, dict):
                continue
            field_name = json_field.get("name")
            label_key = json_field.get("labelKey")
            if isinstance(field_name, str) and isinstance(label_key, str):
                fallback = field_name.replace("_", " ").title()
                translations = json_field.get("translations")
                if not isinstance(translations, dict):
                    translations = {}
                en_label = translations.get("en", fallback)
                zh_label = translations.get("zh", fallback)
                set_by_path(en_translations, label_key, en_label)
                set_by_path(zh_translations, label_key, zh_label)
            add_json_model_translations(json_field.get("model"))
            item = json_field.get("item")
            if isinstance(item, dict):
                add_json_model_translations(item.get("model"))

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

        en_plural = (
            en_pack.get("plural")
            if isinstance(en_pack, dict) and isinstance(en_pack.get("plural"), str)
            else f"{model_name_en}s"
        )
        zh_plural = (
            zh_pack.get("plural")
            if isinstance(zh_pack, dict) and isinstance(zh_pack.get("plural"), str)
            else model_name_zh
        )
        en_model = {"name": model_name_en, "plural": en_plural, "fields": {}}
        zh_model = {"name": model_name_zh, "plural": zh_plural, "fields": {}}

        # Add "my_name" translation for owner-scoped models (e.g., "My Items")
        if model.get("owner_field"):
            en_model["my_name"] = (
                en_pack.get("my_name")
                if isinstance(en_pack, dict) and isinstance(en_pack.get("my_name"), str)
                else f"My {en_plural}"
            )
            zh_model["my_name"] = (
                zh_pack.get("my_name")
                if isinstance(zh_pack, dict) and isinstance(zh_pack.get("my_name"), str)
                else f"我的{model_name_zh}"
            )

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

            add_json_model_translations(field.get("json_model_schema"))
            add_json_model_translations(field.get("json_item_schema"))

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

    for feature in frontend_features or []:
        feature_name = feature["name"]
        en_translations.setdefault("features", {})[feature_name] = feature.get(
            "locales", {}
        ).get("en", {})
        zh_translations.setdefault("features", {})[feature_name] = feature.get(
            "locales", {}
        ).get("zh", {})

    en_translations["agent"] = {
        "title": "Agent", "select": "Select agent", "new": "New conversation",
        "conversations": "Conversations", "start": "Create or select a conversation",
        "tool_result": "Tool result", "tool_calls": "Tool calls", "running": "Working…",
        "stopping": "Stopping…", "message": "Message", "placeholder": "Ask about your data…",
        "send": "Send", "stop": "Stop", "unavailable": "No agents are available for your account.",
        "load_error": "Unable to load conversations", "create_error": "Unable to create conversation",
        "send_error": "Unable to send message", "stop_error": "Unable to stop execution",
    }
    zh_translations["agent"] = {
        "title": "智能助手", "select": "选择助手", "new": "新建对话", "conversations": "历史对话",
        "start": "新建或选择一个对话", "tool_result": "工具结果", "tool_calls": "工具调用",
        "running": "正在处理…", "stopping": "正在停止…", "message": "消息", "placeholder": "询问或操作你的数据…",
        "send": "发送", "stop": "停止", "unavailable": "当前账号没有可用的助手。",
        "load_error": "无法加载对话", "create_error": "无法创建对话", "send_error": "消息发送失败",
        "stop_error": "无法停止执行",
    }
    en_translations["agent"].update({
        "delete": "Delete conversation", "delete_named": "Delete {{title}}",
        "delete_confirm": "Delete “{{title}}” and all its messages? This cannot be undone.",
        "delete_error": "Unable to delete conversation",
        "delete_running": "Stop the conversation before deleting it",
        "interaction_pending": "Waiting for your response", "form_title": "Additional information",
        "form_submit": "Submit and continue", "form_cancel": "Cancel", "form_submitted": "Submitted",
        "form_relation_invalid": "Record unavailable or outside the selected parent. Please select again.", "form_relation_error": "Unable to load options.", "form_relation_empty": "No matching records", "form_relation_retry": "Retry",
        "form_title_create": "Create {{model}}", "form_title_update": "Edit {{model}}", "form_title_list": "Search {{model}}", "form_title_get": "View {{model}}", "form_title_delete": "Delete {{model}}", "form_title_bulk_delete": "Delete {{model}}", "form_title_import": "Import {{model}}",
        "form_yes": "Yes", "form_no": "No", "form_select": "Select…", "form_invalid": "Check the value for {{field}}.",
        "form_hint": "Your answers will be sent to the assistant to continue the task.",
        "confirmation_title": "Operation confirmation", "confirmation_pending": "Waiting for confirmation",
        "confirmation_approved": "Approved", "confirmation_rejected": "Rejected",
        "confirmation_interrupted": "Confirmation expired or stopped",
        "confirmation_approve": "Confirm execution", "confirmation_reject": "Reject",
        "confirmation_hint": "Review the operation and arguments before confirming.",
        "confirmation_error": "Unable to submit confirmation. Check the current status before retrying.",
    })
    zh_translations["agent"].update({
        "delete": "删除对话", "delete_named": "删除 {{title}}",
        "delete_confirm": "删除“{{title}}”及其全部消息？此操作无法撤销。",
        "delete_error": "删除对话失败", "delete_running": "请先停止执行，再删除对话",
        "interaction_pending": "等待你填写或确认", "form_title": "补充信息",
        "form_submit": "提交并继续", "form_cancel": "取消", "form_submitted": "已提交",
        "form_relation_invalid": "记录不可用或不属于所选上级，请重新选择。", "form_relation_error": "选项加载失败。", "form_relation_empty": "没有匹配的记录", "form_relation_retry": "重试",
        "form_title_create": "创建{{model}}", "form_title_update": "编辑{{model}}", "form_title_list": "查询{{model}}", "form_title_get": "查看{{model}}", "form_title_delete": "删除{{model}}", "form_title_bulk_delete": "删除{{model}}", "form_title_import": "导入{{model}}",
        "form_yes": "是", "form_no": "否", "form_select": "请选择…", "form_invalid": "请检查 {{field}} 的填写内容。",
        "form_hint": "提交后，助手将根据填写内容继续处理任务。",
        "confirmation_title": "操作确认", "confirmation_pending": "等待用户确认",
        "confirmation_approved": "已确认", "confirmation_rejected": "已拒绝",
        "confirmation_interrupted": "确认已过期或停止",
        "confirmation_approve": "确认执行", "confirmation_reject": "拒绝",
        "confirmation_hint": "请核对操作及参数后确认。",
        "confirmation_error": "提交确认失败，请检查当前状态后再重试。",
    })
    en_translations["agent"].update(
        {'tool_failed': 'Not completed',
         'tool_done': 'Completed',
         'tool_unknown': 'Interrupted',
         'tool_arguments': 'Arguments',
         'search': 'Search conversations',
         'close_history': 'Close history',
         'collapse_history': 'Collapse conversation history',
         'expand_history': 'Expand conversation history',
         'no_matches': 'No matching conversations',
         'no_history': 'Your conversations will appear here.',
         'history_hint': 'Conversations are saved automatically.',
         'ready': 'Ready',
         'loading': 'Loading conversation…',
         'welcome': 'What would you like to do?',
         'welcome_hint': 'Explore your data, work through a task, or ask what this assistant can '
                         'help with.',
         'suggest_query': 'Help me explore the available data',
         'suggest_help': 'What can you help me do?',
         'copy': 'Copy reply',
         'copy_code': 'Copy code',
         'code_block': 'Code block',
         'table': 'Table',
         'copied': 'Copied',
         'copy_error': 'The browser could not copy the text. Please try again.',
         'sending': 'Sending…',
         'latest': 'Latest messages',
         'reconnecting': 'Connection interrupted. Reconnecting…',
         'retry': 'Retry',
         'dismiss': 'Dismiss',
         'next_message': 'Write your next message…',
         'keyboard_hint': 'Enter to send · Shift + Enter for a new line',
         'composer_hint': 'Tool activity is shown in the conversation.',
         'send_error': 'Unable to confirm delivery. Your draft is saved; check the conversation '
                       'before sending again.'}
    )
    zh_translations["agent"].update(
        {'tool_failed': '未完成',
         'tool_done': '已完成',
         'tool_unknown': '已中断',
         'tool_arguments': '调用参数',
         'search': '搜索历史对话',
         'close_history': '关闭历史对话',
         'collapse_history': '收起历史对话',
         'expand_history': '展开历史对话',
         'no_matches': '没有找到相关对话',
         'no_history': '开始聊天后，对话会保存在这里。',
         'history_hint': '对话自动保存，随时继续。',
         'ready': '就绪',
         'loading': '正在加载对话…',
         'welcome': '今天想做些什么？',
         'welcome_hint': '查询业务数据、处理具体任务，或先了解助手可以为你做什么。',
         'suggest_query': '帮我了解有哪些可用的数据',
         'suggest_help': '你可以帮我完成哪些操作？',
         'copy': '复制回复',
         'copy_code': '复制代码',
         'code_block': '代码块',
         'table': '表格',
         'copied': '已复制',
         'copy_error': '浏览器未能完成复制，请重试。',
         'sending': '发送中…',
         'latest': '回到最新消息',
         'reconnecting': '连接暂时中断，正在重新连接…',
         'retry': '重试',
         'dismiss': '关闭提示',
         'next_message': '可以先写好下一条消息…',
         'keyboard_hint': 'Enter 发送 · Shift + Enter 换行',
         'composer_hint': '工具执行过程会显示在对话中。',
         'send_error': '暂时无法确认是否发送成功。草稿已保留，请检查对话后再发送。'}
    )
    write_file_with_status(locale_dir / "en.json", json.dumps(en_translations, indent=2))
    write_file_with_status(locale_dir / "zh.json", json.dumps(zh_translations, indent=2, ensure_ascii=False))
