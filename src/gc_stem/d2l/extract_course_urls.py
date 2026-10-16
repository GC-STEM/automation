"""Extract D2L course hyperlinks into a CourseURL worksheet column."""

from pathlib import Path
from openpyxl import load_workbook


def find_project_root() -> Path:
    """Locate the repository root using pyproject.toml."""
    for directory in Path(__file__).resolve().parents:
        if (directory / "pyproject.toml").is_file():
            return directory

    raise FileNotFoundError(
        "Could not locate the project root (pyproject.toml)."
    )


PROJECT_ROOT = find_project_root()
SOURCE_FILE = (
    PROJECT_ROOT / "data" / "raw" / "gc-stem_d2l_courses.xlsx"
)
OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "gc-stem_d2l_courses.xlsx"
)
SHEET_NAME = "D2L"


def extract_course_urls(source: Path, destination: Path) -> int:
    """Copy CourseName hyperlink targets into the CourseURL column.

    Create the CourseURL column at the end of the header row if it does
    not already exist. Leave cells unchanged when no hyperlink exists.

    Args:
        source: Path to the source Excel workbook.
        destination: Path for the updated Excel workbook.

    Returns:
        Number of course URLs copied.

    Raises:
        ValueError: If the CourseName column is missing.
    """
    workbook = load_workbook(source)
    worksheet = workbook[SHEET_NAME]

    columns = {
        str(cell.value).strip(): cell.column
        for cell in worksheet[1]
        if cell.value is not None
    }

    if "CourseName" not in columns:
        raise ValueError("Missing required column: CourseName")

    course_url_column = columns.get("CourseURL")
    if course_url_column is None:
        course_url_column = worksheet.max_column + 1
        worksheet.cell(row=1, column=course_url_column, value="CourseURL")

    updated_count = 0

    for row_number in range(2, worksheet.max_row + 1):
        course_name = worksheet.cell(row_number, columns["CourseName"])
        hyperlink = course_name.hyperlink

        if hyperlink is not None and hyperlink.target:
            worksheet.cell(
                row=row_number,
                column=course_url_column,
                value=hyperlink.target,
            )
            updated_count += 1

    workbook.save(destination)
    return updated_count


def main() -> None:
    """Extract course URLs and report the number copied."""
    count = extract_course_urls(SOURCE_FILE, OUTPUT_FILE)
    print(f"Saved {count} course URLs to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
