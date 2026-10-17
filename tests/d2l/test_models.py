"""Test D2L model contracts with unittest or pytest."""

import unittest
from dataclasses import replace

from gc_stem.d2l.models import (
    MAX_CONTEXT_CHARACTERS,
    AuthoredField,
    CourseRef,
    DiscoveryEnd,
    FieldGap,
    Match,
    ObjectRef,
    ReadResult,
    RepresentationOutcome,
    Target,
)


class ModelContractTests(unittest.TestCase):
    """Verify identities, coverage evidence, and bounded match records."""

    def setUp(self) -> None:
        """Create synthetic records without files or browser access."""
        self.course = CourseRef(
            tenant_origin="https://brightspace.example.org",
            org_unit_id="123",
            name="Synthetic course",
            course_url="https://brightspace.example.org/d2l/home/123",
            source_rows=(2,),
        )
        self.owner = ObjectRef(
            course=self.course,
            tool="quizzes",
            object_key="question-456",
            object_type="quiz_question",
            title="Synthetic question",
            paths=("Quiz A / Section 1 / Question 1",),
            page_url=(
                "https://brightspace.example.org"
                "/d2l/quizzes/quizzes.d2l?ou=123"
            ),
            location_kind="container",
            identity_provenance="platform",
        )
        self.field = AuthoredField(
            owner=self.owner,
            field_path="question_text",
            field_type="html",
            outcomes=(
                RepresentationOutcome("source", "AVAILABLE", value=""),
                RepresentationOutcome(
                    "text", "UNAVAILABLE", reason="Rendered view unavailable"
                ),
            ),
            extraction_method="stored_authored_field",
        )
        self.match = Match(
            owner=self.owner,
            field_path="question_text",
            representation="source",
            target=Target("T001", "example.org"),
            occurrence_count=2,
            first_offset=17,
            context='<a href="https://example.org">Read</a>',
            extraction_method="stored_authored_field",
        )

    def test_course_requires_canonical_ascii_identity(self) -> None:
        """Prevent ambiguous IDs from splitting course identities."""
        identifiers = (
            "", "0", "-1", "01", "1.0", "1e3", " 123 ", "١٢٣", "abc"
        )
        for identifier in identifiers:
            with self.subTest(identifier=identifier):
                with self.assertRaises(ValueError):
                    replace(self.course, org_unit_id=identifier)

    def test_course_allows_missing_display_name(self) -> None:
        """Course identity must not depend on optional display metadata."""
        self.assertEqual(replace(self.course, name="").org_unit_id, "123")

    def test_course_requires_data_row_references(self) -> None:
        """Source rows refer to data rather than the inventory header."""
        with self.assertRaises(ValueError):
            replace(self.course, source_rows=(1,))

    def test_object_identity_ignores_display_changes(self) -> None:
        """Alternate titles and paths must not duplicate object scans."""
        alternate = replace(
            self.owner, title="Renamed", paths=("Another location",)
        )
        self.assertEqual(alternate.identity, self.owner.identity)

    def test_object_identity_separates_courses(self) -> None:
        """Identical object IDs in different courses remain distinct."""
        other_course = replace(
            self.course,
            org_unit_id="124",
            course_url="https://brightspace.example.org/d2l/home/124",
        )
        self.assertNotEqual(
            replace(self.owner, course=other_course).identity,
            self.owner.identity,
        )

    def test_object_identity_separates_tenants(self) -> None:
        """Identical IDs on different tenants remain distinct."""
        other_course = replace(
            self.course,
            tenant_origin="https://another.example.org",
            course_url="https://another.example.org/d2l/home/123",
        )
        self.assertNotEqual(
            replace(self.owner, course=other_course).identity,
            self.owner.identity,
        )

    def test_object_identity_separates_tools(self) -> None:
        """A quiz copy and a library object remain distinct."""
        self.assertNotEqual(
            replace(self.owner, tool="question_library").identity,
            self.owner.identity,
        )

    def test_object_requires_supported_tool(self) -> None:
        """Unknown tools must not be silently treated as supported."""
        with self.assertRaises(ValueError):
            replace(self.owner, tool="unknown_tool")

    def test_available_empty_string_is_successful_extraction(self) -> None:
        """A genuine empty field differs from unavailable content."""
        result = RepresentationOutcome("source", "AVAILABLE", value="")
        self.assertEqual(result.value, "")
        self.assertEqual(result.state, "AVAILABLE")

    def test_representation_rejects_ambiguous_outcomes(self) -> None:
        """Missing data must not look like a successful empty read."""
        cases = (
            ("AVAILABLE", None, None),
            ("AVAILABLE", "", "hidden gap"),
            ("UNAVAILABLE", "", "failed"),
            ("UNAVAILABLE", None, None),
            ("UNAVAILABLE", None, " "),
            ("NOT_APPLICABLE", "", "not HTML"),
            ("NOT_APPLICABLE", None, None),
            ("UNKNOWN", None, "unknown state"),
        )
        for state, value, reason in cases:
            with self.subTest(state=state, value=value, reason=reason):
                with self.assertRaises(ValueError):
                    RepresentationOutcome("source", state, value, reason)

    def test_not_applicable_has_an_explicit_reason(self) -> None:
        """Applicability is recorded instead of inferred from emptiness."""
        result = RepresentationOutcome(
            "dom", "NOT_APPLICABLE", reason="Plain text field"
        )
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "Plain text field")

    def test_field_rejects_duplicate_representations(self) -> None:
        """Prevent duplicate representation rows and match counts."""
        with self.assertRaises(ValueError):
            replace(
                self.field,
                outcomes=(self.field.outcomes[0], self.field.outcomes[0]),
            )

    def test_field_requires_explicit_outcomes(self) -> None:
        """A field without evidence cannot be reported as scanned."""
        with self.assertRaises(ValueError):
            replace(self.field, outcomes=())

    def test_read_preserves_partial_field_evidence(self) -> None:
        """Successful data and a missing field can coexist."""
        result = ReadResult(
            owner=self.owner,
            fields=(self.field,),
            missing_fields=(FieldGap("feedback", "Access denied"),),
        )
        self.assertEqual(result.fields[0].outcomes[0].value, "")
        self.assertEqual(result.missing_fields[0].field_path, "feedback")

    def test_read_cannot_be_ambiguously_empty(self) -> None:
        """An empty collection must not create false completeness."""
        with self.assertRaises(ValueError):
            ReadResult(self.owner)

    def test_read_allows_explicit_total_field_failure(self) -> None:
        """An unreadable field retains an identifiable outcome."""
        result = ReadResult(
            owner=self.owner,
            missing_fields=(FieldGap("question_text", "Unsupported view"),),
        )
        self.assertEqual(result.fields, ())
        self.assertEqual(
            result.missing_fields[0].reason, "Unsupported view"
        )

    def test_read_accepts_updated_metadata_for_same_identity(self) -> None:
        """A display-name or path update does not change object ownership."""
        refreshed_owner = replace(
            self.owner, title="Updated title", paths=("Updated path",)
        )
        result = ReadResult(refreshed_owner, fields=(self.field,))
        self.assertEqual(result.fields[0].owner.identity, result.owner.identity)

    def test_read_rejects_wrong_object_attribution(self) -> None:
        """Do not attach a field to another object."""
        with self.assertRaises(ValueError):
            ReadResult(
                replace(self.owner, object_key="question-999"),
                (self.field,),
            )

    def test_read_rejects_wrong_course_attribution(self) -> None:
        """Do not attach a field to a matching object in another course."""
        other_course = replace(
            self.course,
            org_unit_id="124",
            course_url="https://brightspace.example.org/d2l/home/124",
        )
        with self.assertRaises(ValueError):
            ReadResult(
                replace(self.owner, course=other_course), (self.field,)
            )

    def test_read_rejects_conflicting_field_outcomes(self) -> None:
        """A field cannot be both returned and missing in one read."""
        with self.assertRaises(ValueError):
            ReadResult(
                self.owner,
                fields=(self.field,),
                missing_fields=(
                    FieldGap(self.field.field_path, "missing"),
                ),
            )

    def test_read_rejects_duplicate_field_paths(self) -> None:
        """A field is matched once per object read."""
        with self.assertRaises(ValueError):
            ReadResult(self.owner, fields=(self.field, self.field))

    def test_discovery_distinguishes_unknown_from_empty(self) -> None:
        """An unknown total does not prove an empty tool."""
        unknown = DiscoveryEnd(
            False, reason_codes=("ENUMERATION_INCOMPLETE",)
        )
        empty = DiscoveryEnd(True, known_total=0)
        self.assertIsNone(unknown.known_total)
        self.assertFalse(unknown.enumeration_complete)
        self.assertTrue(empty.enumeration_complete)
        self.assertEqual(empty.known_total, 0)

    def test_incomplete_discovery_requires_a_reason(self) -> None:
        """Incomplete coverage needs an explicit explanation."""
        with self.assertRaises(ValueError):
            DiscoveryEnd(False)

    def test_discovery_rejects_invalid_totals(self) -> None:
        """Totals are nonnegative counts, not flags or estimates."""
        for total in (-1, True, 1.5):
            with self.subTest(total=total):
                with self.assertRaises((TypeError, ValueError)):
                    DiscoveryEnd(True, known_total=total)

    def test_target_rejects_blank_strings(self) -> None:
        """An empty target must not match every location."""
        for text in ("", " ", "\t\n"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    Target("T001", text)

    def test_target_preserves_literal_characters(self) -> None:
        """Do not trim significant spaces or interpret regex syntax."""
        target = Target("T001", " a.b? ", ignore_case=False)
        self.assertEqual(target.text, " a.b? ")
        self.assertFalse(target.ignore_case)

    def test_target_requires_a_real_boolean_case_rule(self) -> None:
        """Strings such as 'false' are not a false case-sensitivity flag."""
        with self.assertRaises(TypeError):
            Target("T001", "example.org", ignore_case="false")

    def test_match_requires_a_positive_integer_count(self) -> None:
        """A finding represents at least one actual occurrence."""
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count):
                with self.assertRaises((TypeError, ValueError)):
                    replace(self.match, occurrence_count=count)

    def test_match_accepts_one_occurrence_at_first_character(self) -> None:
        """The minimum valid count and zero-based offset are accepted."""
        result = replace(self.match, occurrence_count=1, first_offset=0)
        self.assertEqual(result.occurrence_count, 1)
        self.assertEqual(result.first_offset, 0)

    def test_match_rejects_negative_offset(self) -> None:
        """Offsets identify positions in the searched representation."""
        with self.assertRaises(ValueError):
            replace(self.match, first_offset=-1)

    def test_match_context_bound_counts_unicode_characters(self) -> None:
        """Bound excerpts by characters rather than encoded byte length."""
        excerpt = "é" * MAX_CONTEXT_CHARACTERS
        self.assertEqual(
            replace(self.match, context=excerpt).context, excerpt
        )
        with self.assertRaises(ValueError):
            replace(self.match, context=excerpt + "é")


if __name__ == "__main__":
    unittest.main()
