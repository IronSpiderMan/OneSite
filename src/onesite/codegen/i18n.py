import json
from pathlib import Path
from typing import Any, Dict, List

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

    for model in models:
        model_name = model["module_name"]
        model_name_en = model["name"]
        model_name_zh = model["name"]

        model_translations = model.get("translations", {})
        if "en" in model_translations:
            model_name_en = model_translations["en"]
        if "zh" in model_translations:
            model_name_zh = model_translations["zh"]

        en_model = {"name": model_name_en, "fields": {}}
        zh_model = {"name": model_name_zh, "fields": {}}

        for field in model["fields"]:
            field_name = field["name"]
            label_en = field_name.replace("_", " ").title()
            label_zh = label_en

            translations = field.get("translations", {})
            if "en" in translations:
                label_en = translations["en"]
            if "zh" in translations:
                label_zh = translations["zh"]
            elif field_name in zh_field_defaults:
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
