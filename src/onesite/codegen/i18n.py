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
            "select": "Select",
            "auto_refresh": "Auto Refresh",
            "refresh_interval": "Refresh Interval",
            "local_storage": "Local Storage",
            "back": "Back",
            "back_home": "Back Home",
            "retry": "Retry",
            "profile": "Profile",
            "bulk_delete": "Bulk Delete",
        },
        "menu": {
            "dashboard": "Dashboard",
        },
        "dashboard": {
            "total": "total",
            "no_models": "No models available for dashboard",
            "no_visualizations": "No visualizations configured",
            "no_data": "No data available",
            "period_day": "Daily",
            "period_week": "Weekly",
            "period_month": "Monthly",
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
            "select": "选择",
            "auto_refresh": "自动刷新",
            "refresh_interval": "刷新频率",
            "local_storage": "本地存储",
            "back": "返回",
            "back_home": "返回首页",
            "retry": "重试",
            "profile": "个人信息",
            "bulk_delete": "批量删除",
        },
        "menu": {
            "dashboard": "仪表盘",
        },
        "dashboard": {
            "total": "总计",
            "no_models": "没有可用于仪表盘的模型",
            "no_visualizations": "未配置可视化",
            "no_data": "暂无数据",
            "period_day": "按日",
            "period_week": "按周",
            "period_month": "按月",
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

        en_translations["models"][model_name] = en_model
        zh_translations["models"][model_name] = zh_model

    (locale_dir / "en.json").write_text(json.dumps(en_translations, indent=2))
    (locale_dir / "zh.json").write_text(json.dumps(zh_translations, indent=2, ensure_ascii=False))
    console.print(f"Generated locale files in {locale_dir}")
