import re
from typing import Any, cast

import fitz  # type: ignore
import streamlit as st
import yt_dlp
from openai import OpenAI
from streamlit.runtime.uploaded_file_manager import UploadedFile

# --- CONFIGURATION ---
try:
    client: OpenAI = OpenAI(
        api_key=cast(str, st.secrets["SUMOPOD_API_KEY"]),
        base_url=cast(str, st.secrets["BASE_URL"]),
    )
except KeyError as e:
    _ = st.error(
        f"Secret configuration not found: {e}. Please ensure your .streamlit/secrets.toml file is set up correctly."
    )
    _ = st.stop()


def get_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    pattern = (
        r"(?:v=|\/live\/|\/shorts\/|youtu\.be\/|\/v\/|\/embed\/|^)([0-9A-Za-z_-]{11})"
    )
    match = re.search(pattern, url)
    return str(match.group(1)) if match else ""


def get_video_duration(url: str) -> int:
    """Fetches video duration in seconds."""
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    with yt_dlp.YoutubeDL(cast(Any, ydl_opts)) as ydl:
        info_dict = cast(Any, ydl.extract_info(url, download=False))

        if info_dict is None:
            return 0

        duration = info_dict.get("duration")
        return int(duration) if duration is not None else 0


def get_transcript_text(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(["id"])
        except Exception:
            transcript = transcript_list.find_transcript(["en"])

        data = transcript.fetch()

        return " ".join(
            str(getattr(t, "text", t["text"] if isinstance(t, dict) else ""))
            for t in data
        ).strip()

    except Exception as e:
        raise Exception(f"Failed to fetch transcript: {str(e)}")


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


def display_summary_and_download(content: str, file_prefix: str):
    """Helper function to display the summary and a download button."""
    _ = st.success("Selesai!")
    _ = st.markdown(content)

    _ = st.download_button(
        label="📥 Download Summary (.md)",
        data=content,
        file_name=f"summary_{file_prefix}.md",
        mime="text/markdown",
    )


# --- UI SETUP ---
_ = st.set_page_config(
    page_title="AI Document & Video Summarizer", page_icon="🤖", layout="wide"
)

_ = st.title("🤖 AI Document & Video Summarizer")
_ = st.write("Summarize YouTube videos or PDF documents using AI.")

with st.sidebar:
    _ = st.header("Settings")
    model_choice: str = st.selectbox(
        "Pilih Model", ["deepseek-v3-2-251201", "kimi-k2-250905"]
    )  # type: ignore
    temp: float = st.slider("Temperature", 0.0, 1.0, 0.3)
    max_duration = st.slider("Maximum Duration (in minutes)", 1, 75, 15)
    max_pdf_pages = st.slider("Maximum PDF Pages", 1, 30, 15)

tab1, tab2 = st.tabs(["📺 YouTube Video", "📄 PDF Document"])

# --- TAB 1: YOUTUBE ---

with tab1:
    yt_url = st.text_input("Enter YouTube URL")
    if st.button("Summarize Video", key="btn_yt"):
        if yt_url:
            v_id = get_video_id(yt_url)
            if not v_id:
                _ = st.error("invalid URL")
            else:
                duration_min = 0.0

                with st.spinner("Checking video duration..."):
                    try:
                        duration_sec = get_video_duration(yt_url)
                        duration_min = duration_sec / 60
                    except Exception as e:
                        _ = st.error(f"Failed to check duration: {e}")
                        _ = st.stop()

                if duration_min > max_duration:
                    _ = st.error(
                        f"Video is too long! Maximum {max_duration} minutes allowed. (this video is : {duration_min:.1f} minutes)"
                    )
                else:
                    with st.spinner("Processing transcript & AI Summary..."):
                        try:
                            text = get_transcript_text(v_id)
                            res = client.chat.completions.create(
                                model=model_choice,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": (
                                            "Anda adalah asisten ahli yang meringkas konten secara mendalam. "
                                            "Tugas Anda adalah memberikan ringkasan dalam **Bahasa Indonesia** yang sangat detail, "
                                            "menggunakan poin-poin, menjelaskan konsep utama, dan memberikan kesimpulan akhir yang komprehensif. "
                                            "Apapun bahasa sumber teksnya, hasil akhir HARUS dalam Bahasa Indonesia."
                                        ),
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Tolong buatkan ringkasan mendalam dari teks berikut ke dalam Bahasa Indonesia: {text}",
                                    },
                                ],
                                temperature=temp,
                            )
                            display_summary_and_download(
                                str(res.choices[0].message.content), v_id
                            )
                        except Exception as e:
                            _ = st.error(f"Error: {e}")

# --- TAB 2: PDF ---
with tab2:
    uploaded_file = st.file_uploader("Upload file PDF", type="pdf")

    if uploaded_file:
        with st.spinner("Analyzing document..."):
            try:
                total_pages, full_text, char_count = extract_pdf_info(uploaded_file)

                col1, col2 = st.columns(2)
                _ = col1.metric("Page count", f"{total_pages} / {max_pdf_pages}")
                char_status = "normal" if char_count <= 45000 else "inverse"
                _ = col2.metric(
                    "Character count",
                    f"{char_count:,} / 45.000",
                    delta_color=char_status,
                )

                is_valid, msg, msg_type = validate_pdf(
                    total_pages, char_count, max_pdf_pages, 45000
                )

                if msg_type == "error":
                    _ = st.error(msg)
                elif msg_type == "warning":
                    _ = st.warning(msg)
                else:
                    _ = st.success(msg)

                if st.button("Summarize PDF", key="btn_pdf", disabled=not is_valid):
                    with st.spinner("processing summary..."):
                        try:
                            res = client.chat.completions.create(
                                model=model_choice,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": (
                                            "Anda adalah asisten ahli yang meringkas konten secara mendalam. "
                                            "Tugas Anda adalah memberikan ringkasan dalam **Bahasa Indonesia** yang sangat detail, "
                                            "menggunakan poin-poin, menjelaskan konsep utama, dan memberikan kesimpulan akhir yang komprehensif. "
                                            "Apapun bahasa sumber teksnya, hasil akhir HARUS dalam Bahasa Indonesia."
                                        ),
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Please provide a detailed summary of the following text: {full_text}",
                                    },
                                ],
                                temperature=temp,
                            )
                            display_summary_and_download(
                                str(res.choices[0].message.content), "document"
                            )
                        except Exception as e:
                            _ = st.error(f"PDF Error: {e}")

            except Exception as e:
                _ = st.error(f"Failed to read PDF file : {e}")
