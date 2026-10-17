"""Test configuration precedence, scope validation, and path origins."""

import math
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory

from gc_stem.d2l.config import ConfigurationError, Settings, load_settings


MINIMAL_CONFIG = """\
schema_version = 1

[instance]
base_url = "https://Brightspace.Example.ORG/"

[courses]
file = "../data/courses.xlsx"

[search]
terms = [" example.org ", "a.b?"]

[output]
directory = "../reports"
"""


class ConfigurationTests(unittest.TestCase):
    """Verify observable configuration behavior without browser access."""

    def setUp(self) -> None:
        """Create isolated configuration and invocation directories."""
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config_directory = self.root / "settings folder"
        self.config_directory.mkdir()
        self.invocation = self.root / "invocation folder"
        self.invocation.mkdir()
        self.path = self.config_directory / "d2l.toml"
        self.path.write_text(MINIMAL_CONFIG, encoding="utf-8")

    def load(
        self,
        overrides: dict[str, object] | None = None,
        environment: dict[str, str] | None = None,
    ) -> Settings:
        """Load the fixture using explicitly controlled environment values."""
        return load_settings(
            self.path,
            overrides=overrides,
            environment={} if environment is None else environment,
            cwd=self.invocation,
        )

    def test_file_values_and_safe_defaults(self) -> None:
        """Minimal configuration produces the documented first-release mode."""
        settings = self.load()
        self.assertEqual(settings.schema_version, 1)
        self.assertEqual(
            settings.instance.base_url,
            "https://brightspace.example.org/d2l/",
        )
        self.assertEqual(
            settings.instance.tenant_origin,
            "https://brightspace.example.org",
        )
        self.assertEqual(settings.instance.provider, "browser")
        self.assertEqual(settings.instance.auth, "interactive")
        self.assertEqual(settings.search.mode, "all")
        self.assertTrue(settings.search.ignore_case)
        self.assertTrue(settings.crawl.include_hidden)
        self.assertEqual(len(settings.crawl.tools), 7)
        self.assertEqual(settings.crawl.max_retries, 2)
        self.assertEqual(settings.crawl.max_reauthentications, 1)
        self.assertEqual(settings.output.formats, ("csv", "json"))

    def test_file_paths_resolve_from_config_directory(self) -> None:
        """Data paths do not depend on the directory invoking the tool."""
        settings = self.load()
        self.assertEqual(
            settings.courses.file, self.root / "data" / "courses.xlsx"
        )
        self.assertEqual(settings.output.directory, self.root / "reports")

    def test_environment_paths_resolve_from_invocation(self) -> None:
        """Relative environment paths keep their documented origin."""
        settings = self.load(
            environment={
                "D2L_COURSES_FILE": "environment.csv",
                "D2L_OUTPUT_DIRECTORY": "environment reports",
            }
        )
        self.assertEqual(
            settings.courses.file, self.invocation / "environment.csv"
        )
        self.assertEqual(
            settings.output.directory, self.invocation / "environment reports"
        )
        self.assertEqual(settings.courses.format, "csv")

    def test_cli_environment_file_default_precedence(self) -> None:
        """Explicit choices win over environment, file, and defaults."""
        settings = self.load(
            overrides={
                "instance.base_url": "https://command.example.org/d2l/",
                "courses.file": "command.csv",
                "output.directory": Path("command reports"),
                "search.mode": "source",
            },
            environment={
                "D2L_BASE_URL": "https://environment.example.org/",
                "D2L_COURSES_FILE": "environment.csv",
                "D2L_OUTPUT_DIRECTORY": "environment reports",
            },
        )
        self.assertEqual(
            settings.instance.tenant_origin, "https://command.example.org"
        )
        self.assertEqual(
            settings.courses.file, self.invocation / "command.csv"
        )
        self.assertEqual(
            settings.output.directory, self.invocation / "command reports"
        )
        self.assertEqual(settings.search.mode, "source")

    def test_override_lists_replace_instead_of_append(self) -> None:
        """Repeated CLI options replace the configured target/tool lists."""
        settings = self.load(
            overrides={
                "search.terms": ["replacement"],
                "crawl.tools": ["files"],
            }
        )
        self.assertEqual(settings.search.terms, ("replacement",))
        self.assertEqual(settings.crawl.tools, ("files",))

    def test_path_origins_are_tracked_independently(self) -> None:
        """Overriding one path does not move another TOML-relative path."""
        settings = self.load(overrides={"courses.file": "command.csv"})
        self.assertEqual(
            settings.courses.file, self.invocation / "command.csv"
        )
        self.assertEqual(settings.output.directory, self.root / "reports")

    def test_absolute_paths_keep_their_location(self) -> None:
        """Absolute path overrides are not prefixed by either directory."""
        course_path = self.root / "absolute.csv"
        report_path = self.root / "absolute reports"
        settings = self.load(
            overrides={
                "courses.file": course_path,
                "output.directory": report_path,
            }
        )
        self.assertEqual(settings.courses.file, course_path)
        self.assertEqual(settings.output.directory, report_path)

    def test_config_path_can_come_from_environment(self) -> None:
        """D2L_CONFIG selects the file when no explicit path was supplied."""
        settings = load_settings(
            environment={"D2L_CONFIG": str(self.path)},
            cwd=self.invocation,
        )
        self.assertEqual(settings.config_path, self.path)

    def test_relative_config_path_uses_invocation_directory(self) -> None:
        """A relative config argument has the same origin as CLI paths."""
        relative = Path("..") / self.config_directory.name / "d2l.toml"
        settings = load_settings(
            relative, environment={}, cwd=self.invocation
        )
        self.assertEqual(settings.config_path, self.path)

    def test_explicit_config_path_overrides_environment_selection(self) -> None:
        """D2L_CONFIG cannot unexpectedly replace an explicit file argument."""
        settings = self.load(
            environment={"D2L_CONFIG": str(self.root / "does-not-exist.toml")}
        )
        self.assertEqual(settings.config_path, self.path)

    def test_no_implicit_config_search(self) -> None:
        """Calling from a checkout does not trigger brittle root discovery."""
        with self.assertRaises(ConfigurationError):
            load_settings(environment={}, cwd=self.config_directory)

    def test_missing_config_file_has_a_specific_error(self) -> None:
        """A missing explicit file is a configuration failure."""
        with self.assertRaisesRegex(ConfigurationError, "Cannot read"):
            load_settings(
                self.root / "absent.toml",
                environment={},
                cwd=self.invocation,
            )

    def test_loading_does_not_create_output_or_inventory(self) -> None:
        """Configuration parsing has no preflight write side effects."""
        settings = self.load()
        self.assertFalse(settings.courses.file.exists())
        self.assertFalse(settings.output.directory.exists())

    def test_tilde_uses_native_home_directory(self) -> None:
        """Home expansion is explicit and platform-native."""
        settings = self.load(overrides={"courses.file": "~/inventory.csv"})
        self.assertEqual(
            settings.courses.file, (Path.home() / "inventory.csv").resolve()
        )

    def test_path_environment_placeholders_are_not_expanded(self) -> None:
        """TOML values cannot interpolate arbitrary environment variables."""
        settings = self.load(
            overrides={"courses.file": "$PRIVATE_LOCATION.csv"},
            environment={"PRIVATE_LOCATION": "secret location"},
        )
        self.assertEqual(
            settings.courses.file,
            self.invocation / "$PRIVATE_LOCATION.csv",
        )

    def test_schema_version_is_required(self) -> None:
        """The loader does not guess which configuration schema applies."""
        self.path.write_text(
            MINIMAL_CONFIG.replace("schema_version = 1\n", ""),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ConfigurationError, "schema_version"):
            self.load()

    def test_unsupported_and_noninteger_schema_versions_fail(self) -> None:
        """A future or malformed schema cannot be silently reinterpreted."""
        for version in ("2", "true", '"1"', "1.0"):
            with self.subTest(version=version):
                self.path.write_text(
                    MINIMAL_CONFIG.replace(
                        "schema_version = 1", f"schema_version = {version}"
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ConfigurationError):
                    self.load()

    def test_schema_version_cannot_be_overridden(self) -> None:
        """Schema identity is file metadata rather than a runtime setting."""
        with self.assertRaises(ConfigurationError):
            self.load(overrides={"schema_version": 1})

    def test_unknown_root_keys_are_rejected_without_values(self) -> None:
        """Mistyped or credential-bearing settings do not become defaults."""
        secret = "AUTH_SECRET_SENTINEL_654"
        self.path.write_text(
            f'password = "{secret}"\n' + MINIMAL_CONFIG,
            encoding="utf-8",
        )
        with self.assertRaises(ConfigurationError) as caught:
            self.load()
        self.assertIn("password", str(caught.exception))
        self.assertNotIn(secret, str(caught.exception))

    def test_unknown_nested_keys_are_rejected(self) -> None:
        """Nested typos must not quietly disable an intended setting."""
        self.path.write_text(
            MINIMAL_CONFIG + '\n[browser]\nheadles = false\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ConfigurationError, "browser.headles"):
            self.load()

    def test_nontable_section_is_rejected(self) -> None:
        """A scalar cannot stand in for a configuration section."""
        self.path.write_text(
            'crawl = "not a table"\n' + MINIMAL_CONFIG,
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ConfigurationError, "crawl"):
            self.load()

    def test_bad_toml_does_not_echo_contents(self) -> None:
        """Parser diagnostics must not copy secrets from malformed input."""
        secret = "AUTH_SECRET_SENTINEL_987"
        self.path.write_text(
            f'password = "{secret}\n' + MINIMAL_CONFIG,
            encoding="utf-8",
        )
        with self.assertRaises(ConfigurationError) as caught:
            self.load()
        self.assertNotIn(secret, str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_unknown_override_keys_are_rejected(self) -> None:
        """Overrides must use documented dotted keys."""
        for overrides in (
            {"search": {"terms": ["value"]}},
            {"search.unknown": True},
            {"password": "AUTH_SECRET_SENTINEL"},
        ):
            with self.subTest(keys=list(overrides)):
                with self.assertRaises(ConfigurationError) as caught:
                    self.load(overrides=overrides)
                self.assertNotIn(
                    "AUTH_SECRET_SENTINEL", str(caught.exception)
                )

    def test_unknown_d2l_environment_names_are_rejected(self) -> None:
        """Unsupported D2L variables are named without exposing values."""
        secret = "AUTH_SECRET_SENTINEL_123"
        with self.assertRaises(ConfigurationError) as caught:
            self.load(environment={"D2L_PASSWORD": secret})
        self.assertIn("D2L_PASSWORD", str(caught.exception))
        self.assertNotIn(secret, str(caught.exception))

    def test_unrelated_environment_names_are_ignored(self) -> None:
        """Ordinary process environment values do not become settings."""
        settings = self.load(
            environment={"OTHER_APP_SECRET": "AUTH_SECRET_SENTINEL"}
        )
        self.assertEqual(settings.instance.provider, "browser")

    def test_required_values_can_come_from_overrides(self) -> None:
        """A file can leave deployment-specific values to explicit inputs."""
        self.path.write_text("schema_version = 1\n", encoding="utf-8")
        settings = self.load(
            overrides={"search.terms": ["target"]},
            environment={
                "D2L_BASE_URL": "https://environment.example.org/",
                "D2L_COURSES_FILE": "courses.csv",
                "D2L_OUTPUT_DIRECTORY": "reports",
            },
        )
        self.assertEqual(settings.search.terms, ("target",))
        self.assertEqual(settings.courses.format, "csv")

    def test_required_settings_are_not_hardcoded(self) -> None:
        """Tenant, course path, terms, and output require explicit input."""
        self.path.write_text("schema_version = 1\n", encoding="utf-8")
        with self.assertRaisesRegex(
            ConfigurationError, "instance.base_url"
        ):
            self.load()

    def test_valid_tenant_url_normalization(self) -> None:
        """Canonical origins handle root paths, ports, IDNA, and IPv6."""
        cases = (
            ("https://EXAMPLE.org", "https://example.org/d2l/"),
            ("https://example.org:443/d2l", "https://example.org/d2l/"),
            ("https://example.org:8443/", "https://example.org:8443/d2l/"),
            ("https://bücher.example/", "https://xn--bcher-kva.example/d2l/"),
            ("https://[2001:db8::1]/", "https://[2001:db8::1]/d2l/"),
        )
        for original, expected in cases:
            with self.subTest(original=original):
                settings = self.load(
                    overrides={"instance.base_url": original}
                )
                self.assertEqual(settings.instance.base_url, expected)

    def test_invalid_tenant_urls_are_rejected_without_echo(self) -> None:
        """Base URLs cannot carry credentials, unsafe syntax, or deep paths."""
        cases = (
            "http://example.org/",
            "example.org",
            "https://user:AUTH_SECRET_SENTINEL@example.org/",
            "https://example.org/?token=AUTH_SECRET_SENTINEL",
            "https://example.org/#AUTH_SECRET_SENTINEL",
            "https://example.org/?",
            "https://example.org/#",
            "https://example.org/d2l/home/123",
            "https://example.org:99999/",
            "https://example.org:0/",
            "https://exa mple.org/",
            "https://example.org\n.evil/",
            "https://example.org\\evil/",
            "https://*.example.org/",
            "https://[bad-ipv6/",
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError) as caught:
                    self.load(overrides={"instance.base_url": value})
                self.assertNotIn(
                    "AUTH_SECRET_SENTINEL", str(caught.exception)
                )

    def test_api_and_noninteractive_auth_are_rejected(self) -> None:
        """Unimplemented access modes cannot be selected accidentally."""
        for key, value in (
            ("instance.provider", "api"),
            ("instance.auth", "password"),
        ):
            with self.subTest(key=key):
                with self.assertRaises(ConfigurationError):
                    self.load(overrides={key: value})

    def test_case_sensitive_and_text_modes_are_supported(self) -> None:
        """Documented safe search overrides remain available."""
        settings = self.load(
            overrides={"search.mode": "text", "search.ignore_case": False}
        )
        self.assertEqual(settings.search.mode, "text")
        self.assertFalse(settings.search.ignore_case)

    def test_target_characters_are_preserved(self) -> None:
        """Spaces and regex metacharacters remain part of literal targets."""
        settings = self.load()
        self.assertEqual(
            settings.search.terms, (" example.org ", "a.b?")
        )

    def test_empty_or_malformed_target_lists_are_rejected(self) -> None:
        """An empty target cannot match the entire inventory."""
        for value in ([], "", "target", [" "], [1], [True]):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError):
                    self.load(overrides={"search.terms": value})

    def test_invalid_search_modes_are_rejected(self) -> None:
        """Unknown representation modes do not fall back silently."""
        with self.assertRaises(ConfigurationError):
            self.load(overrides={"search.mode": "anything"})

    def test_unsupported_features_are_rejected(self) -> None:
        """Regex, external crawling, headless auth, and parallelism fail."""
        cases = (
            ("search.regex", True),
            ("crawl.follow_external_links", True),
            ("browser.headless", True),
            ("crawl.concurrency", 2),
        )
        for key, value in cases:
            with self.subTest(key=key):
                with self.assertRaises(ConfigurationError):
                    self.load(overrides={key: value})

    def test_boolean_settings_do_not_accept_truthy_strings(self) -> None:
        """A string 'false' cannot act as a boolean setting."""
        for key in (
            "search.ignore_case",
            "search.regex",
            "crawl.include_hidden",
            "crawl.follow_external_links",
            "browser.headless",
        ):
            with self.subTest(key=key):
                with self.assertRaises(ConfigurationError):
                    self.load(overrides={key: "false"})

    def test_repeated_tools_are_scanned_once_in_input_order(self) -> None:
        """Duplicate tool keys cannot inflate scope or work counts."""
        settings = self.load(
            overrides={"crawl.tools": ["quizzes", "files", "quizzes"]}
        )
        self.assertEqual(settings.crawl.tools, ("quizzes", "files"))

    def test_empty_or_unsupported_tool_lists_are_rejected(self) -> None:
        """Unknown adapters cannot appear as supported scope."""
        for value in ([], ["rubrics"], ["Content"], "content"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError):
                    self.load(overrides={"crawl.tools": value})

    def test_durations_are_finite_with_correct_boundaries(self) -> None:
        """No negative, infinite, boolean, or zero read timeout is accepted."""
        for value in (-1, math.inf, -math.inf, math.nan, True, "30", 0):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError):
                    self.load(
                        overrides={"crawl.read_timeout_seconds": value}
                    )

    def test_zero_delay_and_retry_budget_are_explicit_choices(self) -> None:
        """Nonnegative controls permit intentional zero values."""
        settings = self.load(
            overrides={
                "crawl.delay_seconds": 0,
                "crawl.max_retries": 0,
                "crawl.max_reauthentications": 0,
                "crawl.max_retry_wait_seconds": 0,
            }
        )
        self.assertEqual(settings.crawl.delay_seconds, 0)
        self.assertEqual(settings.crawl.max_retries, 0)
        self.assertEqual(settings.crawl.max_reauthentications, 0)
        self.assertEqual(settings.crawl.max_retry_wait_seconds, 0)

    def test_item_limits_require_positive_integers(self) -> None:
        """Counts cannot be booleans, fractions, zero, or negatives."""
        for key in (
            "crawl.max_pages_per_course",
            "crawl.max_objects_per_tool",
            "crawl.max_field_characters",
        ):
            for value in (0, -1, True, 1.5):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ConfigurationError):
                        self.load(overrides={key: value})

    def test_csv_defaults_use_normalized_headers(self) -> None:
        """Format selects the correct inventory column contract."""
        settings = self.load(overrides={"courses.file": "courses.CSV"})
        self.assertEqual(settings.courses.format, "csv")
        self.assertEqual(settings.courses.id_column, "org_unit_id")
        self.assertEqual(settings.courses.name_column, "course_name")
        self.assertEqual(settings.courses.url_column, "course_url")

    def test_excel_defaults_and_optional_id_column(self) -> None:
        """The existing Excel workflow needs no invented ID header."""
        settings = self.load()
        self.assertEqual(settings.courses.format, "xlsx")
        self.assertEqual(settings.courses.sheet, "D2L")
        self.assertEqual(settings.courses.name_column, "CourseName")
        self.assertEqual(settings.courses.url_column, "CourseURL")
        self.assertIsNone(settings.courses.id_column)
        explicit = self.load(overrides={"courses.id_column": " OrgUnitID "})
        self.assertEqual(explicit.courses.id_column, "OrgUnitID")

    def test_explicit_format_supports_other_extensions(self) -> None:
        """A configured format avoids unnecessary filename brittleness."""
        settings = self.load(
            overrides={
                "courses.file": "inventory.data",
                "courses.format": "csv",
            }
        )
        self.assertEqual(settings.courses.format, "csv")

    def test_unknown_inferred_inventory_format_is_rejected(self) -> None:
        """Unrecognized file types need an explicit supported format."""
        with self.assertRaises(ConfigurationError):
            self.load(overrides={"courses.file": "inventory.data"})

    def test_csv_requires_an_id_column(self) -> None:
        """The normalized CSV identity contract cannot be disabled."""
        with self.assertRaises(ConfigurationError):
            self.load(
                overrides={
                    "courses.file": "inventory.csv",
                    "courses.id_column": None,
                }
            )

    def test_output_requires_both_csv_and_json(self) -> None:
        """The first release has review rows and a final manifest."""
        for formats in ([], ["csv"], ["json"], ["csv", "xml"], "csv"):
            with self.subTest(formats=formats):
                with self.assertRaises(ConfigurationError):
                    self.load(overrides={"output.formats": formats})

    def test_output_formats_have_stable_order(self) -> None:
        """Equivalent format lists produce a deterministic contract."""
        settings = self.load(
            overrides={"output.formats": ["json", "csv", "csv"]}
        )
        self.assertEqual(settings.output.formats, ("csv", "json"))

    def test_asset_hosts_are_exact_normalized_names(self) -> None:
        """Host configuration is explicit and case-normalized."""
        settings = self.load(
            overrides={
                "browser.trusted_asset_hosts": [
                    "Assets.Example.ORG",
                    "assets.example.org",
                    "2001:db8::1",
                ]
            }
        )
        self.assertEqual(
            settings.browser.trusted_asset_hosts,
            ("assets.example.org", "2001:db8::1"),
        )

    def test_asset_host_urls_and_wildcards_are_rejected(self) -> None:
        """Trusted-host settings cannot become a broad URL allowlist."""
        for value in (
            "https://assets.example.org",
            "*.example.org",
            "assets.example.org/path",
            "user@assets.example.org",
            "assets.example.org:443",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError):
                    self.load(
                        overrides={"browser.trusted_asset_hosts": [value]}
                    )

    def test_empty_paths_are_rejected(self) -> None:
        """Empty strings must not resolve silently to a directory."""
        for key in ("courses.file", "output.directory"):
            for value in ("", " ", "\x00"):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ConfigurationError):
                        self.load(overrides={key: value})

    def test_settings_are_immutable_and_loads_independent(self) -> None:
        """One run's overrides cannot mutate another run's defaults."""
        changed = self.load(overrides={"search.terms": ["replacement"]})
        untouched = self.load()
        self.assertEqual(changed.search.terms, ("replacement",))
        self.assertEqual(untouched.search.terms, (" example.org ", "a.b?"))
        with self.assertRaises(FrozenInstanceError):
            untouched.search.mode = "text"

    def test_shipped_example_resolves_repository_inventory(self) -> None:
        """The example points outside config/ to the processed inventory."""
        package_root = Path(__file__).resolve().parents[2]
        example = package_root / "config" / "d2l.toml"
        settings = load_settings(example, environment={}, cwd=self.invocation)
        self.assertEqual(
            settings.courses.file,
            package_root / "data/processed/d2l_courses.xlsx",
        )
        self.assertEqual(settings.search.mode, "all")


if __name__ == "__main__":
    unittest.main()
