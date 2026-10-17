"""Test inventory formats, tenant scope, identity, and source preservation."""

import csv
import hashlib
import unittest
from dataclasses import FrozenInstanceError
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook

from gc_stem.d2l.config import Settings, load_settings
from gc_stem.d2l.courses import Inventory, InventoryError, load_courses


TENANT = "https://brightspace.example.org"
CONFIGURATION = """\
schema_version = 1
[instance]
base_url = "https://brightspace.example.org/d2l/"
[courses]
file = "courses.xlsx"
[search]
terms = ["example target"]
[output]
directory = "reports"
"""


class CourseInventoryTests(unittest.TestCase):
    """Exercise the public loader using real temporary Excel/CSV files."""

    def setUp(self) -> None:
        """Create an isolated inventory and configuration directory."""
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config = self.root / "d2l.toml"
        self.config.write_text(CONFIGURATION, encoding="utf-8")

    def settings(
        self, path: Path, overrides: dict[str, object] | None = None
    ) -> Settings:
        """Load validated settings for one synthetic inventory."""
        explicit = {"courses.file": path}
        explicit.update({} if overrides is None else overrides)
        return load_settings(
            self.config, overrides=explicit, environment={}, cwd=self.root
        )

    def excel(
        self,
        rows: list[tuple[object, ...]],
        headers: tuple[object, ...] = ("CourseName", "CourseURL"),
        sheet: str = "D2L",
    ) -> Path:
        """Write a minimal workbook with explicit stored cell values."""
        path = self.root / "courses.xlsx"
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet
        worksheet.append(headers)
        for values in rows:
            worksheet.append(values)
        workbook.save(path)
        workbook.close()
        return path

    def csv(
        self,
        rows: list[tuple[object, ...]],
        headers: tuple[str, ...] = (
            "org_unit_id", "course_name", "course_url"
        ),
        *,
        bom: bool = False,
    ) -> Path:
        """Write CSV with correct quoting and optional UTF-8 BOM."""
        path = self.root / "courses.csv"
        with StringIO(newline="") as text:
            writer = csv.writer(text, lineterminator="\r\n")
            writer.writerow(headers)
            writer.writerows(rows)
            encoding = "utf-8-sig" if bom else "utf-8"
            path.write_bytes(text.getvalue().encode(encoding))
        return path

    def load(
        self, path: Path, overrides: dict[str, object] | None = None
    ) -> Inventory:
        """Read a synthetic inventory through the public API."""
        return load_courses(self.settings(path, overrides))

    def test_excel_accepts_both_home_routes(self) -> None:
        """Existing /p/home links and ordinary /home links retain routes."""
        path = self.excel(
            [
                (" First course ", f"{TENANT}/d2l/p/home/00123/"),
                ("Second course", f"{TENANT}/d2l/home/456"),
            ]
        )
        inventory = self.load(path)
        first, second = inventory.courses
        self.assertEqual(first.org_unit_id, "123")
        self.assertEqual(first.course_url, f"{TENANT}/d2l/p/home/123")
        self.assertEqual(first.name, "First course")
        self.assertEqual(first.source_rows, (2,))
        self.assertEqual(second.course_url, f"{TENANT}/d2l/home/456")
        self.assertEqual(second.source_rows, (3,))

    def test_equivalent_csv_and_excel_produce_same_courses(self) -> None:
        """Format adapters agree on the normalized identity contract."""
        excel = self.excel([("Course one", f"{TENANT}/d2l/home/123")])
        csv_path = self.csv([("00123", "Course one", "")])
        self.assertEqual(self.load(excel).courses, self.load(csv_path).courses)

    def test_csv_can_contain_only_ids(self) -> None:
        """Optional name and URL headers are not required in CSV."""
        path = self.csv([(" 00123 ",)], headers=("org_unit_id",))
        course = self.load(path).courses[0]
        self.assertEqual(course.org_unit_id, "123")
        self.assertEqual(course.name, "")
        self.assertEqual(course.course_url, f"{TENANT}/d2l/home/123")

    def test_csv_url_can_supply_a_missing_row_id(self) -> None:
        """A recognized URL can supply identity when the ID cell is blank."""
        path = self.csv([("", "Course", f"{TENANT}/d2l/p/home/123")])
        self.assertEqual(self.load(path).courses[0].org_unit_id, "123")

    def test_excel_allows_blank_display_names(self) -> None:
        """Names are optional metadata rather than identity."""
        path = self.excel([(None, f"{TENANT}/d2l/home/123")])
        self.assertEqual(self.load(path).courses[0].name, "")

    def test_excel_id_only_row_keeps_processed_header_contract(self) -> None:
        """An explicit ID can fill a blank URL cell after preparation."""
        path = self.excel(
            [("Course", None, 123.0)],
            headers=("CourseName", "CourseURL", "OrgUnitID"),
        )
        course = self.load(path, {"courses.id_column": "OrgUnitID"}).courses[0]
        self.assertEqual(course.org_unit_id, "123")
        self.assertEqual(course.course_url, f"{TENANT}/d2l/home/123")

    def test_id_and_url_agreement_uses_normalized_decimal_ids(self) -> None:
        """Leading zeros do not create conflicting identities."""
        path = self.csv([("00123", "Course", f"{TENANT}/d2l/home/0123")])
        self.assertEqual(self.load(path).courses[0].org_unit_id, "123")

    def test_conflicting_ids_fail_the_entire_inventory(self) -> None:
        """A valid first row cannot hide an unsafe later identity conflict."""
        path = self.csv(
            [
                ("123", "Valid", ""),
                ("456", "Conflict", f"{TENANT}/d2l/home/789"),
            ]
        )
        with self.assertRaises(InventoryError) as caught:
            self.load(path)
        self.assertEqual(caught.exception.diagnostics[0].row, 3)
        self.assertIn("conflicts", str(caught.exception))

    def test_ambiguous_string_ids_are_rejected(self) -> None:
        """Only ASCII decimal strings may represent string IDs."""
        for value in (
            "0", "000", "-1", "+123", "123.0", "1e3", "1,234",
            "１２３", "true", "=123", "course-123",
        ):
            with self.subTest(value=value):
                path = self.csv([(value, "Course", "")])
                with self.assertRaises(InventoryError) as caught:
                    self.load(path)
                self.assertEqual(caught.exception.diagnostics[0].row, 2)

    def test_excel_rejects_boolean_fractional_and_imprecise_ids(self) -> None:
        """Numeric Excel cells must provide an unambiguous whole ID."""
        for value in (True, False, -1, 0, 1.5, 10**15, 9007199254740994.0):
            with self.subTest(value=value):
                path = self.excel(
                    [("Course", None, value)],
                    headers=("CourseName", "CourseURL", "OrgUnitID"),
                )
                with self.assertRaises(InventoryError):
                    self.load(path, {"courses.id_column": "OrgUnitID"})

    def test_excel_precision_boundary_and_long_text_ids(self) -> None:
        """Fifteen-digit numbers and larger text IDs remain usable."""
        path = self.excel(
            [("Numeric", None, 10**15 - 1), ("Text", None, "1" * 16)],
            headers=("CourseName", "CourseURL", "OrgUnitID"),
        )
        inventory = self.load(path, {"courses.id_column": "OrgUnitID"})
        self.assertEqual(
            tuple(course.org_unit_id for course in inventory.courses),
            (str(10**15 - 1), "1" * 16),
        )

    def test_long_ids_do_not_require_integer_conversion(self) -> None:
        """String normalization is not limited by Python's int parser."""
        identifier = "9" * 5000
        path = self.csv([("00" + identifier, "Course", "")])
        self.assertEqual(self.load(path).courses[0].org_unit_id, identifier)

    def test_duplicates_merge_rows_in_first_input_order(self) -> None:
        """Both routes describe one course and retain all source references."""
        path = self.csv(
            [
                ("456", "First", f"{TENANT}/d2l/p/home/456"),
                ("123", "Second", ""),
                ("00456", "First", f"{TENANT}/d2l/home/456"),
                ("456", "First", ""),
            ]
        )
        inventory = self.load(path)
        self.assertEqual(
            tuple(course.org_unit_id for course in inventory.courses),
            ("456", "123"),
        )
        self.assertEqual(inventory.courses[0].source_rows, (2, 4, 5))
        self.assertEqual(
            inventory.courses[0].course_url, f"{TENANT}/d2l/p/home/456"
        )
        self.assertEqual(inventory.row_count, 4)
        self.assertEqual(inventory.duplicate_count, 2)
        self.assertEqual(
            tuple(item.code for item in inventory.diagnostics),
            ("DUPLICATE_COURSE", "DUPLICATE_COURSE"),
        )
        self.assertEqual(inventory.diagnostics[0].related_row, 2)

    def test_duplicate_name_differences_are_nonfatal(self) -> None:
        """The first display name is retained and the difference is visible."""
        path = self.csv([("123", "Original", ""), ("123", "Updated", "")])
        inventory = self.load(path)
        self.assertEqual(inventory.courses[0].name, "Original")
        self.assertEqual(
            tuple(item.code for item in inventory.diagnostics),
            ("DUPLICATE_COURSE", "NAME_DIFFERENCE"),
        )
        self.assertEqual(inventory.diagnostics[1].org_unit_id, "123")

    def test_url_scope_and_route_rejections_do_not_echo_values(self) -> None:
        """Credentials, foreign origins, unsafe syntax, and deep routes fail."""
        cases = (
            "http://brightspace.example.org/d2l/home/123",
            "https://other.example.org/d2l/home/123",
            "https://brightspace.example.org.evil/d2l/home/123",
            "https://user:AUTH_SECRET@brightspace.example.org/d2l/home/123",
            f"{TENANT}/d2l/home/123?token=AUTH_SECRET",
            f"{TENANT}/d2l/home/123#AUTH_SECRET",
            f"{TENANT}/d2l/home/123?",
            f"{TENANT}/d2l/home/123#",
            f"{TENANT}/d2l/home/123/extra",
            f"{TENANT}/d2l/home/0",
            f"{TENANT}/d2l/home/1e3",
            f"{TENANT}/d2l/home/%31%32%33",
            f"{TENANT}/d2l/content/123/Home",
            f"{TENANT}/d2l//home/123",
            "/d2l/home/123",
            "//brightspace.example.org/d2l/home/123",
            "https://brightspace.example.org:8443/d2l/home/123",
            "https://brightspace.example.org:99999/d2l/home/123",
            "https://brightspace.example.org:0/d2l/home/123",
            "https://[bad-ipv6/d2l/home/123",
            "https://brightspace.example.org\\evil/d2l/home/123",
            "https://brightspace.example.org\n.evil/d2l/home/123",
            f"{TENANT}/d2l/home/12\x003",
        )
        for value in cases:
            with self.subTest(value=value):
                path = self.csv([("123", "Course", value)])
                with self.assertRaises(InventoryError) as caught:
                    self.load(path)
                self.assertNotIn("AUTH_SECRET", str(caught.exception))
                self.assertNotIn(
                    "AUTH_SECRET", repr(caught.exception.diagnostics)
                )

    def test_url_normalizes_case_default_port_and_outer_spaces(self) -> None:
        """Equivalent origins normalize to the configured tenant origin."""
        path = self.csv(
            [
                (
                    "123", "Course",
                    " https://BRIGHTSPACE.example.org:443/d2l/home/123/ ",
                )
            ]
        )
        course = self.load(path).courses[0]
        self.assertEqual(course.tenant_origin, TENANT)
        self.assertEqual(course.course_url, f"{TENANT}/d2l/home/123")

    def test_configured_nondefault_port_is_part_of_scope(self) -> None:
        """Only the configured HTTPS origin is accepted, including port."""
        origin = "https://brightspace.example.org:8443"
        path = self.csv([("123", "Course", f"{origin}/d2l/home/123")])
        course = self.load(path, {"instance.base_url": origin}).courses[0]
        self.assertEqual(course.tenant_origin, origin)

    def test_idna_and_ipv6_origins_match_normalized_configuration(self) -> None:
        """URL scope agrees with the configuration loader's host rules."""
        cases = (
            ("https://bücher.example", "https://xn--bcher-kva.example"),
            ("https://[2001:0db8:0:0:0:0:0:1]", "https://[2001:db8::1]"),
        )
        for original, normalized in cases:
            with self.subTest(origin=original):
                path = self.csv([("123", "Course", f"{original}/d2l/home/123")])
                course = self.load(
                    path, {"instance.base_url": original}
                ).courses[0]
                self.assertEqual(course.tenant_origin, normalized)

    def test_header_case_and_outer_whitespace_are_normalized(self) -> None:
        """Configured mappings do not depend on cosmetic header changes."""
        path = self.excel(
            [("Course", f"{TENANT}/d2l/home/123")],
            headers=(" coursename ", " COURSEURL "),
        )
        self.assertEqual(self.load(path).courses[0].org_unit_id, "123")

    def test_duplicate_normalized_headers_are_rejected(self) -> None:
        """Duplicate headers cannot silently select a different identity."""
        for kind in ("csv", "xlsx"):
            with self.subTest(kind=kind):
                if kind == "csv":
                    path = self.csv(
                        [("123", "456")],
                        headers=("org_unit_id", " ORG_UNIT_ID "),
                    )
                else:
                    path = self.excel(
                        [("First", "Second", f"{TENANT}/d2l/home/123")],
                        headers=("CourseName", " coursename ", "CourseURL"),
                    )
                with self.assertRaisesRegex(InventoryError, "Duplicate"):
                    self.load(path)

    def test_missing_url_header_gives_preparation_instruction(self) -> None:
        """The loader does not extract links or modify an unprepared file."""
        path = self.excel([("Course",)], headers=("CourseName",))
        original = path.read_bytes()
        with self.assertRaisesRegex(InventoryError, "extract_course_urls"):
            self.load(path)
        self.assertEqual(path.read_bytes(), original)

    def test_missing_excel_name_header_is_reported(self) -> None:
        """Excel requires the configured name column even for blank names."""
        path = self.excel(
            [(f"{TENANT}/d2l/home/123",)], headers=("CourseURL",)
        )
        with self.assertRaisesRegex(InventoryError, "name_column"):
            self.load(path)

    def test_missing_csv_id_header_is_reported(self) -> None:
        """CSV retains its required normalized ID header contract."""
        path = self.csv(
            [("Course", f"{TENANT}/d2l/home/123")],
            headers=("course_name", "course_url"),
        )
        with self.assertRaisesRegex(InventoryError, "id_column"):
            self.load(path)

    def test_missing_explicit_excel_id_header_is_reported(self) -> None:
        """An explicit mapping cannot be silently ignored."""
        path = self.excel([("Course", f"{TENANT}/d2l/home/123")])
        with self.assertRaisesRegex(InventoryError, "id_column"):
            self.load(path, {"courses.id_column": "OrgUnitID"})

    def test_custom_sheet_and_column_mappings_are_supported(self) -> None:
        """Configuration selects the inventory layout."""
        path = self.excel(
            [(123, f"{TENANT}/d2l/home/123", "Course")],
            headers=("Identifier", "Link", "Title"),
            sheet="Master shells",
        )
        inventory = self.load(
            path,
            {
                "courses.sheet": "Master shells",
                "courses.id_column": "Identifier",
                "courses.url_column": "Link",
                "courses.name_column": "Title",
            },
        )
        self.assertEqual(inventory.sheet_name, "Master shells")
        self.assertEqual(inventory.courses[0].name, "Course")

    def test_missing_sheet_is_reported_without_guessing(self) -> None:
        """A different worksheet is not silently selected."""
        path = self.excel([], sheet="Different sheet")
        with self.assertRaisesRegex(InventoryError, "courses.sheet"):
            self.load(path)

    def test_nontext_headers_are_rejected(self) -> None:
        """Invalid header values do not become invented column names."""
        path = self.excel([], headers=(123, "CourseURL"))
        with self.assertRaisesRegex(InventoryError, "headers must contain"):
            self.load(path)

    def test_configured_column_roles_must_be_distinct(self) -> None:
        """Name and identity fields cannot accidentally share a column."""
        path = self.excel([("Course", f"{TENANT}/d2l/home/123")])
        with self.assertRaisesRegex(InventoryError, "distinct"):
            self.load(path, {"courses.name_column": "CourseURL"})

    def test_blank_rows_preserve_source_row_numbers(self) -> None:
        """Row references retain blank gaps in both formats."""
        excel = self.excel(
            [
                (None, None),
                ("Course", f"{TENANT}/d2l/home/123"),
                (" ", " "),
            ]
        )
        csv_path = self.csv(
            [("", "", ""), ("123", "Course", ""), (" ", " ", " ")]
        )
        for path in (excel, csv_path):
            with self.subTest(format=path.suffix):
                inventory = self.load(path)
                self.assertEqual(inventory.row_count, 1)
                self.assertEqual(inventory.courses[0].source_rows, (3,))

    def test_metadata_only_row_is_invalid(self) -> None:
        """A nonempty course row must provide an ID or a supported URL."""
        path = self.csv([("", "Course without identity", "")])
        with self.assertRaisesRegex(InventoryError, "neither an ID nor a URL"):
            self.load(path)

    def test_empty_and_header_only_csv_are_rejected(self) -> None:
        """An empty scope cannot look like a successful validation."""
        for text in ("", "org_unit_id\n", "org_unit_id\n\n \n"):
            with self.subTest(text=text):
                path = self.root / "empty.csv"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(InventoryError):
                    self.load(path)

    def test_header_only_excel_is_rejected(self) -> None:
        """A structurally valid workbook still needs at least one course."""
        path = self.excel([])
        with self.assertRaisesRegex(InventoryError, "no course rows"):
            self.load(path)

    def test_missing_inventory_file_is_reported(self) -> None:
        """Input existence is checked locally before any browser work."""
        with self.assertRaisesRegex(InventoryError, "does not exist"):
            self.load(self.root / "missing.xlsx")

    def test_directory_is_not_an_inventory_file(self) -> None:
        """Filesystem errors are converted to the inventory error contract."""
        path = self.root / "directory.xlsx"
        path.mkdir()
        with self.assertRaisesRegex(InventoryError, "Cannot read"):
            self.load(path)

    def test_corrupt_excel_does_not_echo_file_contents(self) -> None:
        """Archive/parser errors do not leak rejected input into diagnostics."""
        path = self.root / "broken.xlsx"
        path.write_bytes(b"AUTH_SECRET: not an Excel workbook")
        with self.assertRaises(InventoryError) as caught:
            self.load(path)
        self.assertNotIn("AUTH_SECRET", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_csv_requires_utf8(self) -> None:
        """Legacy encodings are not guessed or silently replaced."""
        path = self.root / "legacy.csv"
        path.write_bytes(b"org_unit_id,course_name\n123,caf\xe9\n")
        with self.assertRaisesRegex(InventoryError, "UTF-8"):
            self.load(path)

    def test_malformed_csv_is_rejected_without_echo(self) -> None:
        """A broken quoted record cannot return a partial valid inventory."""
        path = self.root / "broken.csv"
        path.write_text(
            'org_unit_id,course_name\n123,Valid\n456,"AUTH_SECRET\n',
            encoding="utf-8",
        )
        with self.assertRaises(InventoryError) as caught:
            self.load(path)
        self.assertNotIn("AUTH_SECRET", str(caught.exception))

    def test_utf8_bom_and_unicode_names_are_supported(self) -> None:
        """A BOM does not become part of the required ID header."""
        path = self.csv([("123", "Café — 编程", "")], bom=True)
        self.assertEqual(self.load(path).courses[0].name, "Café — 编程")

    def test_multiline_csv_records_keep_starting_line_numbers(self) -> None:
        """Diagnostics identify physical source lines after quoted newlines."""
        path = self.csv(
            [("123", "Course\nname", ""), ("123", "Course\nname", "")]
        )
        inventory = self.load(path)
        self.assertEqual(inventory.courses[0].source_rows, (2, 4))
        self.assertEqual(inventory.diagnostics[0].row, 4)
        self.assertEqual(inventory.diagnostics[0].related_row, 2)

    def test_csv_extra_cells_are_rejected(self) -> None:
        """Unmapped data cannot hide a shifted identity field."""
        path = self.csv([("123", "Unexpected")], headers=("org_unit_id",))
        with self.assertRaisesRegex(InventoryError, "more cells than headers"):
            self.load(path)

    def test_csv_missing_trailing_optional_values_are_blank(self) -> None:
        """Omitted optional cells have the same meaning as explicit blanks."""
        path = self.csv([("123",)])
        course = self.load(path).courses[0]
        self.assertEqual(course.org_unit_id, "123")
        self.assertEqual(course.name, "")

    def test_formula_identity_cells_are_not_evaluated(self) -> None:
        """Excel formulas cannot supply cached or computed course identities."""
        for identifier, url in (
            ("=123", None),
            (None, '=HYPERLINK("https://example.org", "Course")'),
        ):
            with self.subTest(identifier=identifier, url=url):
                path = self.excel(
                    [("Course", url, identifier)],
                    headers=("CourseName", "CourseURL", "OrgUnitID"),
                )
                with self.assertRaises(InventoryError):
                    self.load(path, {"courses.id_column": "OrgUnitID"})

    def test_formula_like_csv_names_remain_plain_metadata(self) -> None:
        """The loader preserves names; report export owns formula escaping."""
        path = self.csv([("123", "=1+1", "")])
        self.assertEqual(self.load(path).courses[0].name, "=1+1")

    def test_input_bytes_are_preserved_and_digest_matches(self) -> None:
        """Inventory loading changes neither the workbook nor its timestamp."""
        path = self.excel([("Course", f"{TENANT}/d2l/home/123")])
        original = path.read_bytes()
        modified = path.stat().st_mtime_ns
        inventory = self.load(path)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(path.stat().st_mtime_ns, modified)
        self.assertEqual(inventory.sha256, hashlib.sha256(original).hexdigest())
        self.assertEqual(inventory.source_path, path)
        self.assertEqual(inventory.source_format, "xlsx")
        self.assertEqual(inventory.sheet_name, "D2L")

    def test_csv_digest_includes_original_bom_and_newlines(self) -> None:
        """Reproducibility uses source bytes rather than reconstructed rows."""
        path = self.csv([("123", "Course", "")], bom=True)
        inventory = self.load(path)
        self.assertEqual(
            inventory.sha256, hashlib.sha256(path.read_bytes()).hexdigest()
        )
        self.assertEqual(inventory.source_format, "csv")
        self.assertIsNone(inventory.sheet_name)

    def test_each_load_reads_current_file_contents(self) -> None:
        """A later run cannot silently reuse an earlier course list."""
        path = self.csv([("123", "Before", "")])
        settings = self.settings(path)
        before = load_courses(settings)
        self.csv([("456", "After", "")])
        after = load_courses(settings)
        self.assertEqual(before.courses[0].org_unit_id, "123")
        self.assertEqual(after.courses[0].org_unit_id, "456")
        self.assertNotEqual(before.sha256, after.sha256)

    def test_all_invalid_rows_have_structured_diagnostics(self) -> None:
        """A concise error preview still retains every row failure."""
        path = self.csv(
            [(f"invalid-{number}", "Course", "") for number in range(7)]
        )
        with self.assertRaises(InventoryError) as caught:
            self.load(path)
        error = caught.exception
        self.assertEqual(len(error.diagnostics), 7)
        self.assertEqual(
            tuple(item.row for item in error.diagnostics), tuple(range(2, 9))
        )
        self.assertTrue(
            all(item.code == "INVALID_ROW" for item in error.diagnostics)
        )
        self.assertIn("7 invalid", str(error))
        self.assertIn("row 6:", str(error))
        self.assertNotIn("row 7:", str(error))

    def test_inventory_and_course_results_are_immutable(self) -> None:
        """Consumers cannot accidentally change scope after validation."""
        path = self.csv([("123", "Course", ""), ("123", "Updated", "")])
        inventory = self.load(path)
        with self.assertRaises(FrozenInstanceError):
            inventory.row_count = 99
        with self.assertRaises(FrozenInstanceError):
            inventory.courses[0].org_unit_id = "456"
        with self.assertRaises(FrozenInstanceError):
            inventory.diagnostics[0].row = 99


if __name__ == "__main__":
    unittest.main()
