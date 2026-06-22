import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

console = Console()


def generate_locale_files(models: List[Dict[str, Any]], locale_dir: Path):
    locale_dir.mkdir(parents=True, exist_ok=True)

    zh_field_defaults: Dict[str, str] = {
        "language": "语言",
        "timezone": "时区",
        "theme": "主题",
        "theme_style": "主题样式",
        "theme_mode": "主题模式",
        "site_name": "站点名称",
        "allow_registration": "允许注册",
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
            "no result": "No result",
            "previous": "Previous",
            "next": "Next",
            "first": "First",
            "last": "Last",
            "page_info": "Page",
            "of_page": "of",
            "page_size": "Page size",
            "select": "Select",
            "auto_refresh": "Auto Refresh",
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
        },
        "menu": {
            "dashboard": "Dashboard",
        },
        "dashboard": {
            "total": "total",
            "no_models": "No models available for dashboard",
            "no_visualizations": "No visualizations or tasks configured",
            "no_data": "No data available",
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
            "no result": "结果为空",
            "previous": "前一页",
            "next": "后一页",
            "first": "首页",
            "last": "末页",
            "page_info": "第",
            "of_page": "页，共",
            "page_size": "每页条数",
            "select": "选择",
            "auto_refresh": "自动刷新",
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
        },
        "menu": {
            "dashboard": "仪表盘",
        },
        "dashboard": {
            "total": "总计",
            "no_models": "没有可用于仪表盘的模型",
            "no_visualizations": "未配置可视化或定时任务",
            "no_data": "暂无数据",
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

    for model in models:
        model_name = model["module_name"]
        model_name_en = model["name"]
        model_name_zh = model["name"]

        model_translations = model.get("translations", {})
        en_pack = model_translations.get("en")
        zh_pack = model_translations.get("zh")
        model_name_en = pick_model_name(en_pack, model_name_en)
        model_name_zh = pick_model_name(zh_pack, model_name_zh)

        en_model = {"name": model_name_en, "fields": {}}
        zh_model = {"name": model_name_zh, "fields": {}}

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

        for field in model["fields"]:
            field_name = field["name"]
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
                else:
                    if field_name in zh_field_defaults:
                        label_zh = zh_field_defaults[field_name]

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

        en_translations["models"][model_name] = en_model
        zh_translations["models"][model_name] = zh_model

    (locale_dir / "en.json").write_text(json.dumps(en_translations, indent=2))
    (locale_dir / "zh.json").write_text(json.dumps(zh_translations, indent=2, ensure_ascii=False))
    console.print(f"Generated locale files in {locale_dir}")
