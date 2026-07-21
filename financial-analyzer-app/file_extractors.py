"""
Handles extracting analyzable text from uploaded files.
Supports: .txt (plain text), .pdf (narrative reports), .csv / .xlsx / .xls (tabular financial data).
"""

import io
import pdfplumber
import pandas as pd

ALLOWED_EXTENSIONS = {"txt", "pdf", "csv", "xlsx", "xls"}
MAX_TABLE_ROWS = 200  # cap rows converted to text, per sheet/file, to keep prompts a reasonable size


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _dataframe_to_text(df: pd.DataFrame, max_rows: int = MAX_TABLE_ROWS) -> str:
    """Converts a DataFrame to a plain-text table the LLM can read."""
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_string(index=False)


def extract_text_from_pdf(file_storage) -> str:
    """Extracts all page text from an uploaded PDF (same approach as the notebook 01 pipeline)."""
    file_bytes = io.BytesIO(file_storage.read())
    text_parts = []
    with pdfplumber.open(file_bytes) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_csv(file_storage) -> str:
    """Reads a CSV and converts it to a readable text table."""
    df = pd.read_csv(file_storage)
    return _dataframe_to_text(df)


def extract_text_from_excel(file_storage) -> str:
    """Reads all sheets of an Excel file and converts each to a labeled text table."""
    sheets = pd.read_excel(file_storage, sheet_name=None)  # dict of {sheet_name: DataFrame}
    parts = []
    for sheet_name, df in sheets.items():
        parts.append(f"--- Sheet: {sheet_name} ---")
        parts.append(_dataframe_to_text(df))
    return "\n\n".join(parts)


def extract_text_from_txt(file_storage) -> str:
    return file_storage.read().decode("utf-8", errors="replace")


def extract_text_from_upload(file_storage) -> str:
    """
    Dispatches to the right extractor based on file extension.
    Raises ValueError for unsupported types or extraction failures.
    """
    filename = file_storage.filename
    if not filename or not allowed_file(filename):
        raise ValueError(
            f"Unsupported file type for '{filename}'. Allowed: .txt, .pdf, .csv, .xlsx, .xls"
        )

    ext = filename.rsplit(".", 1)[1].lower()

    try:
        if ext == "txt":
            return extract_text_from_txt(file_storage)
        elif ext == "pdf":
            return extract_text_from_pdf(file_storage)
        elif ext == "csv":
            return extract_text_from_csv(file_storage)
        elif ext in ("xlsx", "xls"):
            return extract_text_from_excel(file_storage)
    except Exception as e:
        raise ValueError(f"Could not read '{filename}': {e}")

    raise ValueError(f"Unhandled extension: .{ext}")
