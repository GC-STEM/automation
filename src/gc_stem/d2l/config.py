"""Load validated, nonsecret configuration for the D2L tools.

Precedence is explicit overrides, supported environment variables, TOML,
then defaults. Overrides use dotted names such as "search.terms".

Paths from TOML resolve relative to the configuration file. Paths from
overrides or environment variables resolve relative to the invocation
directory. Loading settings never opens a browser or creates output files.
"""

from __future__ import annotations

import ipaddress
import math
import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast, get_args
from urllib.parse import urlsplit, urlunsplit

from .models import SearchMode, ToolKey


SCHEMA_VERSION = 1
CourseFormat = Literal["csv", "xlsx"]
OutputFormat = Literal["csv", "json"]

_SECTIONS = {
    "instance": frozenset({"base_url", "provider", "auth"}),
    "courses": frozenset(
        {"file", "format", "sheet", "name_column", "url_column", "id_column"}
    ),
    "search": frozenset({"terms", "mode", "ignore_case", "regex"}),
    "crawl": frozenset(
        {
            "tools",
            "include_hidden",
            "follow_external_links",
            "delay_seconds",
            "read_timeout_seconds",
            "auth_timeout_seconds",
            "max_retries",
            "max_reauthentications",
            "max_retry_wait_seconds",
            "max_pages_per_course",
            "max_objects_per_tool",
            "max_field_characters",
            "concurrency",
        }
    ),
    "browser": frozenset({"headless", "trusted_asset_hosts"}),
    "output": frozenset({"directory", "formats"}),
}
_KEYS = frozenset(
    f"{section}.{key}"
    for section, keys in _SECTIONS.items()
    for key in keys
)
_ENVIRONMENT_KEYS = {
    "D2L_BASE_URL": "instance.base_url",
    "D2L_COURSES_FILE": "courses.file",
    "D2L_OUTPUT_DIRECTORY": "output.directory",
}
_DEFAULTS: dict[str, object] = {
    "instance.provider": "browser",
    "instance.auth": "interactive",
    "courses.sheet": "D2L",
    "search.mode": "all",
    "search.ignore_case": True,
    "search.regex": False,
    "crawl.tools": get_args(ToolKey),
    "crawl.include_hidden": True,
    "crawl.follow_external_links": False,
    "crawl.delay_seconds": 1.0,
    "crawl.read_timeout_seconds": 30,
    "crawl.auth_timeout_seconds": 300,
    "crawl.max_retries": 2,
    "crawl.max_reauthentications": 1,
    "crawl.max_retry_wait_seconds": 60,
    "crawl.max_pages_per_course": 300,
    "crawl.max_objects_per_tool": 1000,
    "crawl.max_field_characters": 2_000_000,
    "crawl.concurrency": 1,
    "browser.headless": False,
    "browser.trusted_asset_hosts": (),
    "output.formats": ("csv", "json"),
}


class ConfigurationError(ValueError):
    """Indicate invalid, unsupported, or unreadable configuration."""


@dataclass(frozen=True, slots=True)
class InstanceSettings:
    """Store the normalized instance URL and supported access methods."""

    base_url: str
    provider: Literal["browser"]
    auth: Literal["interactive"]

    @property
    def tenant_origin(self) -> str:
        """Return the configured HTTPS origin without the /d2l/ path."""
        parts = urlsplit(self.base_url)
        return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


@dataclass(frozen=True, slots=True)
class CourseSettings:
    """Store a resolved inventory path, format, and column mappings.

    sheet applies to Excel. CSV defaults use org_unit_id, course_name, and
    course_url. Excel defaults use D2l_course_name/CourseURL and no ID column.
    An explicit format takes precedence over the filename extension.
    """

    file: Path
    format: CourseFormat
    sheet: str
    name_column: str
    url_column: str
    id_column: str | None


@dataclass(frozen=True, slots=True)
class SearchSettings:
    """Store original literal targets and the selected matching mode."""

    terms: tuple[str, ...]
    mode: SearchMode
    ignore_case: bool
    regex: Literal[False]


@dataclass(frozen=True, slots=True)
class CrawlSettings:
    """Store selected tools, visibility, pacing, and finite work limits."""

    tools: tuple[ToolKey, ...]
    include_hidden: bool
    follow_external_links: Literal[False]
    delay_seconds: float
    read_timeout_seconds: float
    auth_timeout_seconds: float
    max_retries: int
    max_reauthentications: int
    max_retry_wait_seconds: float
    max_pages_per_course: int
    max_objects_per_tool: int
    max_field_characters: int
    concurrency: Literal[1]


@dataclass(frozen=True, slots=True)
class BrowserSettings:
    """Store headed-browser settings and explicit trusted asset hosts."""

    headless: Literal[False]
    trusted_asset_hosts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OutputSettings:
    """Store the resolved destination and required output formats."""

    directory: Path
    formats: tuple[OutputFormat, ...]


@dataclass(frozen=True, slots=True)
class Settings:
    """Store validated configuration returned by load_settings.

    These records are immutable containers. Validation and normalization
    are performed by the loader, not by directly calling their constructors.
    Inventory contents are validated separately by the course loader.
    """

    config_path: Path
    instance: InstanceSettings
    courses: CourseSettings
    search: SearchSettings
    crawl: CrawlSettings
    browser: BrowserSettings
    output: OutputSettings
    schema_version: int = SCHEMA_VERSION


def _text(value: object, key: str) -> str:
    """Require a nonblank string without altering its characters."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{key} must be a nonblank string.")
    return value


def _boolean(value: object, key: str) -> bool:
    """Require a real boolean rather than a truthy string or number."""
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _integer(value: object, key: str, minimum: int = 0) -> int:
    """Require an integer at or above the supplied boundary."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    if value < minimum:
        raise ConfigurationError(f"{key} must be at least {minimum}.")
    return value


def _seconds(value: object, key: str, *, positive: bool = False) -> float:
    """Require a finite, nonnegative or positive numeric duration."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{key} must be a numeric duration.")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ConfigurationError(f"{key} must be finite.") from None
    if not math.isfinite(result):
        raise ConfigurationError(f"{key} must be finite.")
    if result < 0 or (positive and result == 0):
        boundary = "positive" if positive else "nonnegative"
        raise ConfigurationError(f"{key} must be {boundary}.")
    return result


def _choice(value: object, key: str, choices: tuple[str, ...]) -> str:
    """Require a documented choice without echoing rejected values."""
    result = _text(value, key)
    if result not in choices:
        allowed = ", ".join(choices)
        raise ConfigurationError(f"{key} must be one of: {allowed}.")
    return result


def _strings(
    value: object, key: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    """Read a list or tuple of nonblank strings."""
    if not isinstance(value, (list, tuple)):
        raise ConfigurationError(f"{key} must be a list of strings.")
    result = tuple(_text(item, key) for item in value)
    if not result and not allow_empty:
        raise ConfigurationError(f"{key} must not be empty.")
    return result


def _required(values: Mapping[str, object], key: str) -> object:
    """Return an explicitly supplied required setting."""
    if key not in values:
        raise ConfigurationError(f"Missing required setting: {key}.")
    return values[key]


def _resolve_path(value: object, origin: Path, key: str) -> Path:
    """Resolve one path using its source's directory and native home rules."""
    if not isinstance(value, (str, os.PathLike)):
        raise ConfigurationError(f"{key} must be a filesystem path.")
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            raise ValueError
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = origin / path
        return path.resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        raise ConfigurationError(f"{key} is not a usable path.") from None


def _hostname(value: object, key: str) -> str:
    """Normalize an exact DNS name or IP address without URL syntax."""
    host = _text(value, key).strip()
    if any(character.isspace() for character in host):
        raise ConfigurationError(f"{key} must contain exact hostnames.")
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        pass
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        message = f"{key} contains an invalid hostname."
        raise ConfigurationError(message) from None
    labels = ascii_host.split(".")
    valid_label = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
    if len(ascii_host) > 253 or any(
        valid_label.fullmatch(label) is None for label in labels
    ):
        raise ConfigurationError(f"{key} contains an invalid hostname.")
    return ascii_host


def _base_url(value: object) -> str:
    """Normalize an HTTPS tenant root to an explicit /d2l/ base URL."""
    key = "instance.base_url"
    raw = _text(value, key).strip()
    if (
        any(character.isspace() or ord(character) < 32 for character in raw)
        or any(character in raw for character in "\\?#")
        or "\x7f" in raw
    ):
        raise ConfigurationError(
            f"{key} must not contain whitespace, queries, or fragments."
        )
    try:
        parts = urlsplit(raw)
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        raise ConfigurationError(f"{key} is not a valid tenant URL.") from None
    if (
        parts.scheme != "https"
        or not hostname
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("", "/", "/d2l", "/d2l/")
        or port == 0
    ):
        raise ConfigurationError(
            f"{key} must be an HTTPS tenant root or /d2l/ URL "
            "without credentials."
        )
    host = _hostname(hostname, key)
    if ":" in host:
        host = f"[{host}]"
    authority = host if port in (None, 443) else f"{host}:{port}"
    return urlunsplit(("https", authority, "/d2l/", "", ""))


def _read_toml(path: Path) -> dict[str, object]:
    """Read TOML without leaking its contents through parser exceptions."""
    try:
        with path.open("rb") as source:
            return tomllib.load(source)
    except tomllib.TOMLDecodeError:
        raise ConfigurationError(
            f"Invalid TOML syntax in configuration file: {path}"
        ) from None
    except UnicodeError:
        raise ConfigurationError(
            f"Configuration file must use UTF-8: {path}"
        ) from None
    except OSError:
        raise ConfigurationError(
            f"Cannot read configuration file: {path}"
        ) from None


def _flatten(document: Mapping[str, object]) -> dict[str, object]:
    """Validate schema and setting names before applying overrides."""
    version = _required(document, "schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ConfigurationError(
            f"schema_version must be {SCHEMA_VERSION}."
        )
    unknown = set(document) - {"schema_version", *_SECTIONS}
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigurationError(f"Unknown configuration keys: {names}.")

    flattened: dict[str, object] = {}
    for section, allowed in _SECTIONS.items():
        table = document.get(section, {})
        if not isinstance(table, Mapping):
            raise ConfigurationError(f"{section} must be a TOML table.")
        for key, value in table.items():
            if key not in allowed:
                raise ConfigurationError(
                    f"Unknown configuration setting: {section}.{key}."
                )
            flattened[f"{section}.{key}"] = value
    return flattened


def _course_settings(
    values: Mapping[str, object], origins: Mapping[str, Path]
) -> CourseSettings:
    """Build normalized inventory settings with format-aware defaults."""
    key = "courses.file"
    file = _resolve_path(_required(values, key), origins[key], key)
    format_value = values.get("courses.format", file.suffix.lower()[1:])
    format_name = cast(
        CourseFormat,
        _choice(format_value, "courses.format", get_args(CourseFormat)),
    )
    excel = format_name == "xlsx"
    name_default = "D2l_course_name" if excel else "course_name"
    url_default = "CourseURL" if excel else "course_url"
    id_default = None if excel else "org_unit_id"
    id_value = values.get("courses.id_column", id_default)
    id_column = None
    if id_value is not None:
        id_column = _text(id_value, "courses.id_column").strip()
    if not excel and id_column is None:
        raise ConfigurationError("CSV inventories require courses.id_column.")
    return CourseSettings(
        file=file,
        format=format_name,
        sheet=_text(values["courses.sheet"], "courses.sheet"),
        name_column=_text(
            values.get("courses.name_column", name_default),
            "courses.name_column",
        ).strip(),
        url_column=_text(
            values.get("courses.url_column", url_default),
            "courses.url_column",
        ).strip(),
        id_column=id_column,
    )


def _search_settings(values: Mapping[str, object]) -> SearchSettings:
    """Require literal targets and reject the unimplemented regex mode."""
    terms = _strings(_required(values, "search.terms"), "search.terms")
    regex = _boolean(values["search.regex"], "search.regex")
    if regex:
        raise ConfigurationError("Regular-expression search is not supported.")
    return SearchSettings(
        terms=terms,
        mode=cast(
            SearchMode,
            _choice(values["search.mode"], "search.mode", get_args(SearchMode)),
        ),
        ignore_case=_boolean(
            values["search.ignore_case"], "search.ignore_case"
        ),
        regex=False,
    )


def _crawl_settings(values: Mapping[str, object]) -> CrawlSettings:
    """Validate selected tools and bounded sequential crawl settings."""
    selected = _strings(values["crawl.tools"], "crawl.tools")
    tools = tuple(
        dict.fromkeys(
            cast(ToolKey, _choice(tool, "crawl.tools", get_args(ToolKey)))
            for tool in selected
        )
    )
    external = _boolean(
        values["crawl.follow_external_links"], "crawl.follow_external_links"
    )
    if external:
        raise ConfigurationError("External-link crawling is not supported.")
    concurrency = _integer(values["crawl.concurrency"], "crawl.concurrency", 1)
    if concurrency != 1:
        raise ConfigurationError("crawl.concurrency must be 1.")
    return CrawlSettings(
        tools=tools,
        include_hidden=_boolean(
            values["crawl.include_hidden"], "crawl.include_hidden"
        ),
        follow_external_links=False,
        delay_seconds=_seconds(
            values["crawl.delay_seconds"], "crawl.delay_seconds"
        ),
        read_timeout_seconds=_seconds(
            values["crawl.read_timeout_seconds"],
            "crawl.read_timeout_seconds",
            positive=True,
        ),
        auth_timeout_seconds=_seconds(
            values["crawl.auth_timeout_seconds"],
            "crawl.auth_timeout_seconds",
            positive=True,
        ),
        max_retries=_integer(
            values["crawl.max_retries"], "crawl.max_retries"
        ),
        max_reauthentications=_integer(
            values["crawl.max_reauthentications"],
            "crawl.max_reauthentications",
        ),
        max_retry_wait_seconds=_seconds(
            values["crawl.max_retry_wait_seconds"],
            "crawl.max_retry_wait_seconds",
        ),
        max_pages_per_course=_integer(
            values["crawl.max_pages_per_course"],
            "crawl.max_pages_per_course",
            1,
        ),
        max_objects_per_tool=_integer(
            values["crawl.max_objects_per_tool"],
            "crawl.max_objects_per_tool",
            1,
        ),
        max_field_characters=_integer(
            values["crawl.max_field_characters"],
            "crawl.max_field_characters",
            1,
        ),
        concurrency=1,
    )


def _browser_settings(values: Mapping[str, object]) -> BrowserSettings:
    """Require a visible browser and exact asset-host names."""
    headless = _boolean(values["browser.headless"], "browser.headless")
    if headless:
        raise ConfigurationError(
            "browser.headless must be false for interactive authentication."
        )
    key = "browser.trusted_asset_hosts"
    hosts = _strings(values[key], key, allow_empty=True)
    normalized = tuple(dict.fromkeys(_hostname(host, key) for host in hosts))
    return BrowserSettings(headless=False, trusted_asset_hosts=normalized)


def _output_settings(
    values: Mapping[str, object], origins: Mapping[str, Path]
) -> OutputSettings:
    """Require the report pair and resolve its output directory."""
    formats = _strings(values["output.formats"], "output.formats")
    if set(formats) != {"csv", "json"}:
        raise ConfigurationError(
            "output.formats must include exactly csv and json."
        )
    key = "output.directory"
    directory = _resolve_path(_required(values, key), origins[key], key)
    return OutputSettings(directory=directory, formats=("csv", "json"))


def load_settings(
    config_path: str | os.PathLike[str] | None = None,
    overrides: Mapping[str, object] | None = None,
    environment: Mapping[str, str] | None = None,
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> Settings:
    """Load, merge, normalize, and validate D2L configuration.

    Args:
        config_path: Explicit TOML path, otherwise D2L_CONFIG is required.
        overrides: Highest-priority values keyed by dotted setting name.
            Lists replace configured lists. schema_version is file-only.
        environment: Environment mapping; defaults to os.environ. Supported
            names are D2L_CONFIG, D2L_BASE_URL, D2L_COURSES_FILE, and
            D2L_OUTPUT_DIRECTORY. Other D2L_ names are rejected without
            displaying their values. Unrelated names are ignored.
        cwd: Optional invocation directory for explicit/environment paths.
            Defaults to the working directory when called.

    Returns:
        Immutable settings with absolute paths and normalized tenant URL.

    Raises:
        ConfigurationError: If the file, schema, options, or values are
            invalid. Inventory contents and output writability are checked
            by later preflight/application services.

    The loader performs no browser activity, creates no directories, and
    does not expand environment placeholders inside configured paths.
    """
    invocation = _resolve_path(
        Path.cwd() if cwd is None else cwd, Path.cwd(), "cwd"
    )
    env = os.environ if environment is None else environment
    if not isinstance(env, Mapping):
        raise ConfigurationError("environment must be a mapping.")
    for name in env:
        if not isinstance(name, str):
            raise ConfigurationError("Environment names must be strings.")
        if (
            name.startswith("D2L_")
            and name != "D2L_CONFIG"
            and name not in _ENVIRONMENT_KEYS
        ):
            raise ConfigurationError(
                f"Unsupported D2L environment variable: {name}."
            )
    selected_path = config_path
    if selected_path is None:
        selected_path = env.get("D2L_CONFIG")
    if selected_path is None:
        raise ConfigurationError("Supply config_path or D2L_CONFIG.")
    path = _resolve_path(selected_path, invocation, "config_path")
    document = _flatten(_read_toml(path))
    values = dict(_DEFAULTS)
    values.update(document)
    origins = {
        "courses.file": path.parent,
        "output.directory": path.parent,
    }

    for variable, key in _ENVIRONMENT_KEYS.items():
        if variable in env:
            values[key] = env[variable]
            if key in origins:
                origins[key] = invocation

    if overrides is not None:
        if not isinstance(overrides, Mapping):
            raise ConfigurationError("overrides must be a mapping.")
        for key, value in overrides.items():
            if key not in _KEYS:
                raise ConfigurationError(
                    "Overrides must use supported dotted setting names."
                )
            values[key] = value
            if key in origins:
                origins[key] = invocation

    instance = InstanceSettings(
        base_url=_base_url(_required(values, "instance.base_url")),
        provider=cast(
            Literal["browser"],
            _choice(
                values["instance.provider"], "instance.provider", ("browser",)
            ),
        ),
        auth=cast(
            Literal["interactive"],
            _choice(
                values["instance.auth"], "instance.auth", ("interactive",)
            ),
        ),
    )
    return Settings(
        config_path=path,
        instance=instance,
        courses=_course_settings(values, origins),
        search=_search_settings(values),
        crawl=_crawl_settings(values),
        browser=_browser_settings(values),
        output=_output_settings(values, origins),
    )
