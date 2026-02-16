import fitz  # type: ignore
from streamlit.runtime.uploaded_file_manager import UploadedFile


def extract_pdf_info(uploaded_file: UploadedFile) -> tuple[int, str, int]:
    """Extracts page count, full text, and character count."""
    _ = uploaded_file.seek(0)
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(doc)

    text_gen = (str(doc[i].get_text()) for i in range(total_pages))
    full_text = "".join(text_gen).strip()

    return total_pages, full_text, len(full_text)


def validate_pdf(
    pages: int, chars: int, max_pages: int, max_chars: int
) -> tuple[bool, str, str]:
    """Validates document and returns status and message."""
    if pages > max_pages:
        return (
            False,
            f"❌ Document too long. Maximum {max_pages} pages.",
            "error",
        )
    if chars > max_chars:
        return (
            False,
            f"❌ Text too dense ({chars:,} characters). Maximum {max_chars} characters.",
            "error",
        )
    if chars == 0:
        return (
            False,
            "⚠️ No text detected. PDF may be empty or a scanned image.",
            "warning",
        )

    return True, "✅ Document ready for summarization", "success"
