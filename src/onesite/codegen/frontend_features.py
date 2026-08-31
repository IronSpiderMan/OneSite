"""Discovery, validation, and synchronization for frontend features."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from .config import SiteConfigError
from .file_utils import copy_file_with_status, write_file_with_status
from ..frontend import FrontendFeature
from ..project_paths import get_project_paths


_NAME_RE = re.compile(r"[a-z][a-z0-9_]*")
_WIDGET_ID_RE = re.compile(r"[a-z][a-z0-9_.-]*")
_ICON_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ROUTE_TARGET_RE = re.compile(r"[a-z][a-z0-9_.-]*")
_PACKAGE_RE = re.compile(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]+", re.IGNORECASE)
_IGNORED_PARTS = {"__pycache__", "node_modules", ".git", ".DS_Store"}
_SPAN_BREAKPOINTS = ("sm", "md", "lg", "xl", "2xl")


def _load_feature_module(path: Path) -> Any:
    module_name = f"_onesite_frontend_feature_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SiteConfigError(f"Unable to load frontend feature manifest {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise SiteConfigError(f"Unable to import frontend feature manifest {path}: {exc}") from exc
    finally:
        sys.modules.pop(module_name, None)
    return module


def _safe_relative_file(feature_dir: Path, raw: str, field: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise SiteConfigError(f"{field} must be a non-empty relative file path.")
    posix = PurePosixPath(raw)
    if posix.is_absolute() or ".." in posix.parts:
        raise SiteConfigError(f"{field} must stay inside {feature_dir}.")
    resolved = feature_dir.joinpath(*posix.parts)
    if not resolved.is_file():
        raise SiteConfigError(f"{field} references missing file {resolved}.")
    return resolved


def _span_classes(value: int | dict[str, int], field: str) -> str:
    def validate_span(span: Any, item_field: str) -> int:
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 12:
            raise SiteConfigError(f"{item_field} must be an integer from 1 to 12.")
        return span

    classes = ["col-span-12"]
    if isinstance(value, int):
        classes.append(f"xl:col-span-{validate_span(value, field)}")
        return " ".join(classes)
    if not isinstance(value, dict) or not value:
        raise SiteConfigError(f"{field} must be a span integer or breakpoint mapping.")
    for breakpoint in _SPAN_BREAKPOINTS:
        if breakpoint in value:
            classes.append(
                f"{breakpoint}:col-span-{validate_span(value[breakpoint], f'{field}.{breakpoint}')}"
            )
    unexpected = sorted(set(value) - set(_SPAN_BREAKPOINTS))
    if unexpected:
        raise SiteConfigError(f"{field} contains unsupported breakpoints: {', '.join(unexpected)}.")
    return " ".join(classes)


def _load_locales(feature_dir: Path, feature: FrontendFeature) -> dict[str, dict[str, Any]]:
    locale_paths = dict(feature.locales)
    for language in ("en", "zh"):
        conventional = feature_dir / "locales" / f"{language}.json"
        if language not in locale_paths and conventional.is_file():
            locale_paths[language] = f"locales/{language}.json"

    result: dict[str, dict[str, Any]] = {}
    for language, relative in locale_paths.items():
        path = _safe_relative_file(
            feature_dir, relative, f"frontend feature '{feature.name}' locales.{language}"
        )
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SiteConfigError(f"Unable to read frontend locale {path}: {exc}") from exc
        if not isinstance(content, dict):
            raise SiteConfigError(f"Frontend locale {path} must contain a JSON object.")
        result[language] = content
    return result


def _validate_dependencies(
    values: dict[str, str], field: str, aggregate: dict[str, tuple[str, str]]
) -> None:
    for package, version in values.items():
        if not isinstance(package, str) or not _PACKAGE_RE.fullmatch(package):
            raise SiteConfigError(f"{field} contains invalid npm package name {package!r}.")
        if not isinstance(version, str) or not version.strip():
            raise SiteConfigError(f"{field}.{package} must be a non-empty version string.")
        previous = aggregate.get(package)
        if previous and previous[0] != version:
            raise SiteConfigError(
                f"Frontend dependency {package!r} has conflicting versions "
                f"{previous[0]!r} ({previous[1]}) and {version!r} ({field})."
            )
        aggregate[package] = (version, field)


def load_frontend_features(cwd: Path) -> list[dict[str, Any]]:
    """Discover and validate every ``app/frontend/features/*/feature.py``."""

    features_root = get_project_paths(cwd).frontend_source / "features"
    if not features_root.is_dir():
        return []

    missing_manifests = [
        directory
        for directory in sorted(features_root.iterdir())
        if directory.is_dir()
        and not directory.name.startswith(".")
        and not (directory / "feature.py").is_file()
    ]
    if missing_manifests:
        raise SiteConfigError(
            "Every frontend feature directory must contain feature.py; missing: "
            + ", ".join(str(path) for path in missing_manifests)
            + "."
        )

    compiled: list[dict[str, Any]] = []
    seen_widget_ids: set[str] = set()
    seen_route_ids: set[str] = set()
    seen_route_paths: set[str] = set()
    seen_override_targets: set[str] = set()
    dependencies: dict[str, tuple[str, str]] = {}
    dev_dependencies: dict[str, tuple[str, str]] = {}

    for manifest in sorted(features_root.glob("*/feature.py")):
        feature_dir = manifest.parent
        module = _load_feature_module(manifest)
        feature = getattr(module, "feature", None)
        if not isinstance(feature, FrontendFeature):
            raise SiteConfigError(
                f"{manifest} must export `feature = FrontendFeature(...)`."
            )
        if not _NAME_RE.fullmatch(feature.name):
            raise SiteConfigError(
                f"Frontend feature name {feature.name!r} must use lowercase snake_case."
            )
        if feature.name != feature_dir.name:
            raise SiteConfigError(
                f"Frontend feature {manifest} declares name {feature.name!r}; "
                f"it must match directory {feature_dir.name!r}."
            )

        _validate_dependencies(
            feature.dependencies, f"frontend feature '{feature.name}' dependencies", dependencies
        )
        _validate_dependencies(
            feature.dev_dependencies,
            f"frontend feature '{feature.name}' dev_dependencies",
            dev_dependencies,
        )

        widgets: list[dict[str, Any]] = []
        for index, widget in enumerate(feature.dashboard_widgets):
            field = f"frontend feature '{feature.name}' dashboard_widgets[{index}]"
            if not _WIDGET_ID_RE.fullmatch(widget.id):
                raise SiteConfigError(
                    f"{field}.id must start with a lowercase letter and contain only "
                    "lowercase letters, numbers, '.', '_', or '-'."
                )
            full_id = f"{feature.name}.{widget.id}"
            if full_id in seen_widget_ids:
                raise SiteConfigError(f"Duplicate frontend Dashboard widget id {full_id!r}.")
            seen_widget_ids.add(full_id)
            if set(widget.title) != {"en", "zh"} or any(
                not title.strip() for title in widget.title.values()
            ):
                raise SiteConfigError(
                    f"{field}.title must provide non-empty 'zh' and 'en' labels."
                )
            component_path = _safe_relative_file(
                feature_dir, widget.component, f"{field}.component"
            )
            if component_path.suffix not in {".tsx", ".ts", ".jsx", ".js"}:
                raise SiteConfigError(f"{field}.component must be a TypeScript or JavaScript module.")
            if len(set(widget.access)) != len(widget.access):
                raise SiteConfigError(f"{field}.access must not contain duplicate roles.")
            widgets.append(
                {
                    "id": full_id,
                    "local_id": widget.id,
                    "component": widget.component.rsplit(".", 1)[0],
                    "title": dict(widget.title),
                    "title_key": f"features.{feature.name}.widgets.{widget.id}.title",
                    "span_class": _span_classes(widget.span, f"{field}.span"),
                    "order": widget.order,
                    "access": list(widget.access),
                    "frame": widget.frame,
                }
            )

        routes: list[dict[str, Any]] = []
        for index, route in enumerate(feature.routes):
            field = f"frontend feature '{feature.name}' routes[{index}]"
            if not _WIDGET_ID_RE.fullmatch(route.id):
                raise SiteConfigError(
                    f"{field}.id must start with a lowercase letter and contain only "
                    "lowercase letters, numbers, '.', '_', or '-'."
                )
            full_id = f"{feature.name}.{route.id}"
            if full_id in seen_route_ids:
                raise SiteConfigError(f"Duplicate frontend route id {full_id!r}.")
            seen_route_ids.add(full_id)
            if (
                not route.path.startswith("/")
                or route.path == "/"
                or route.path.endswith("/")
                or any(character.isspace() for character in route.path)
                or "?" in route.path
                or "#" in route.path
                or "//" in route.path
            ):
                raise SiteConfigError(
                    f"{field}.path must be an absolute application path without a "
                    "trailing slash, query, fragment, whitespace, or duplicate slash."
                )
            if route.path in seen_route_paths:
                raise SiteConfigError(f"Duplicate frontend route path {route.path!r}.")
            seen_route_paths.add(route.path)
            component_path = _safe_relative_file(
                feature_dir, route.component, f"{field}.component"
            )
            if component_path.suffix not in {".tsx", ".ts", ".jsx", ".js"}:
                raise SiteConfigError(f"{field}.component must be a TypeScript or JavaScript module.")
            if len(set(route.access)) != len(route.access):
                raise SiteConfigError(f"{field}.access must not contain duplicate roles.")
            if route.layout == "public" and route.menu is not None:
                raise SiteConfigError(f"{field}.menu is only supported for app routes.")
            if route.layout == "public" and set(route.access) != {
                "user", "admin", "developer"
            }:
                raise SiteConfigError(
                    f"{field}.access cannot restrict a public route; use layout='app'."
                )
            if route.menu is not None and ":" in route.path:
                raise SiteConfigError(f"{field}.menu cannot point to a parameterized path.")

            menu = None
            if route.menu is not None:
                if set(route.menu.title) != {"en", "zh"} or any(
                    not title.strip() for title in route.menu.title.values()
                ):
                    raise SiteConfigError(
                        f"{field}.menu.title must provide non-empty 'zh' and 'en' labels."
                    )
                if not _ICON_RE.fullmatch(route.menu.icon):
                    raise SiteConfigError(f"{field}.menu.icon must be a valid component name.")
                visible_roles = (
                    route.access if route.menu.visible is None else route.menu.visible
                )
                if len(set(visible_roles)) != len(visible_roles):
                    raise SiteConfigError(f"{field}.menu.visible must not contain duplicate roles.")
                menu = {
                    "title": dict(route.menu.title),
                    "label": f"features.{feature.name}.routes.{route.id}.menu",
                    "icon": route.menu.icon,
                    "visible": {
                        role: role in route.access and role in visible_roles
                        for role in ("user", "admin", "developer")
                    },
                }

            routes.append(
                {
                    "id": full_id,
                    "local_id": route.id,
                    "path": route.path,
                    "component": route.component.rsplit(".", 1)[0],
                    "layout": route.layout,
                    "access": list(route.access),
                    "menu": menu,
                }
            )

        overrides: list[dict[str, Any]] = []
        for index, override in enumerate(feature.overrides):
            field = f"frontend feature '{feature.name}' overrides[{index}]"
            if not _ROUTE_TARGET_RE.fullmatch(override.target):
                raise SiteConfigError(f"{field}.target must be a stable generated route ID.")
            if override.target in seen_override_targets:
                raise SiteConfigError(
                    f"Generated route {override.target!r} is overridden more than once."
                )
            seen_override_targets.add(override.target)
            component_path = _safe_relative_file(
                feature_dir, override.component, f"{field}.component"
            )
            if component_path.suffix not in {".tsx", ".ts", ".jsx", ".js"}:
                raise SiteConfigError(f"{field}.component must be a TypeScript or JavaScript module.")
            if override.access is not None and len(set(override.access)) != len(override.access):
                raise SiteConfigError(f"{field}.access must not contain duplicate roles.")
            overrides.append(
                {
                    "target": override.target,
                    "component": override.component.rsplit(".", 1)[0],
                    "access": list(override.access) if override.access is not None else None,
                }
            )

        locales = _load_locales(feature_dir, feature)
        for language in ("en", "zh"):
            locale = locales.setdefault(language, {})
            widget_translations = locale.setdefault("widgets", {})
            if not isinstance(widget_translations, dict):
                raise SiteConfigError(
                    f"Frontend feature '{feature.name}' {language} locale key 'widgets' "
                    "must be an object."
                )
            for widget in widgets:
                entry = widget_translations.setdefault(widget["local_id"], {})
                if not isinstance(entry, dict):
                    raise SiteConfigError(
                        f"Frontend feature '{feature.name}' {language} locale widget "
                        f"{widget['local_id']!r} must be an object."
                    )
                entry.setdefault("title", widget["title"][language])
            route_translations = locale.setdefault("routes", {})
            if not isinstance(route_translations, dict):
                raise SiteConfigError(
                    f"Frontend feature '{feature.name}' {language} locale key 'routes' "
                    "must be an object."
                )
            for route in routes:
                if route["menu"] is None:
                    continue
                entry = route_translations.setdefault(route["local_id"], {})
                if not isinstance(entry, dict):
                    raise SiteConfigError(
                        f"Frontend feature '{feature.name}' {language} locale route "
                        f"{route['local_id']!r} must be an object."
                    )
                entry.setdefault("menu", route["menu"]["title"][language])

        compiled.append(
            {
                "name": feature.name,
                "source_dir": feature_dir,
                "routes": routes,
                "overrides": overrides,
                "dashboard_widgets": widgets,
                "dependencies": dict(feature.dependencies),
                "dev_dependencies": dict(feature.dev_dependencies),
                "locales": locales,
            }
        )

    return compiled


def _desired_source_files(source: Path, *, exclude_manifest: bool = False) -> dict[Path, Path]:
    if not source.is_dir():
        return {}
    desired: dict[Path, Path] = {}
    for path in source.rglob("*"):
        if not path.is_file() or any(part in _IGNORED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(source)
        if path.suffix in {".py", ".pyc"} or (exclude_manifest and relative.name == "feature.py"):
            continue
        desired[relative] = path
    return desired


def _mirror_files(desired: dict[Path, Path], destination: Path, label: str) -> None:
    if destination.exists():
        for existing in sorted((p for p in destination.rglob("*") if p.is_file()), reverse=True):
            if existing.relative_to(destination) not in desired:
                existing.unlink()
        for directory in sorted((p for p in destination.rglob("*") if p.is_dir()), reverse=True):
            if not any(directory.iterdir()):
                directory.rmdir()
    for relative, source in sorted(desired.items()):
        copy_file_with_status(source, destination / relative)


def sync_frontend_features(
    cwd: Path, frontend_path: Path, features: list[dict[str, Any]]
) -> None:
    """Mirror feature sources and merge their declared npm dependencies."""

    source_root = get_project_paths(cwd).frontend_source
    custom_root = frontend_path / "src" / "custom"
    package_path = frontend_path / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    for manifest_key, feature_key in (
        ("dependencies", "dependencies"),
        ("devDependencies", "dev_dependencies"),
    ):
        target = package.setdefault(manifest_key, {})
        for feature in features:
            for name, version in feature[feature_key].items():
                existing = target.get(name)
                if existing is not None and existing != version:
                    raise SiteConfigError(
                        f"Frontend feature '{feature['name']}' requires {name} {version}, "
                        f"but the generated frontend requires {existing}."
                    )
                target[name] = version
        package[manifest_key] = dict(sorted(target.items()))

    features_destination = custom_root / "features"
    desired_features: dict[Path, Path] = {}
    for feature in features:
        for relative, source in _desired_source_files(
            feature["source_dir"], exclude_manifest=True
        ).items():
            desired_features[Path(feature["name"]) / relative] = source
    _mirror_files(desired_features, features_destination, "frontend feature")
    _mirror_files(
        _desired_source_files(source_root / "shared"),
        custom_root / "shared",
        "shared frontend",
    )
    write_file_with_status(
        package_path, json.dumps(package, ensure_ascii=False, indent=2) + "\n"
    )
