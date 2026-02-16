from typing import cast

import streamlit as st

from services.ai_engine import generate_summary, get_ai_client
from services.document import extract_pdf_info, validate_pdf
from services.youtube import get_transcript_text, get_video_duration, get_video_id
from utils.helpers import display_summary_and_download

# --- CONFIGURATION ---
client = get_ai_client()


# --- UI SETUP ---
_ = st.set_page_config(
    page_title="AI Document & Video Summarizer", page_icon="🤖", layout="wide"
)

_ = st.title("🤖 AI Document & Video Summarizer")
_ = st.write("Summarize YouTube videos or PDF documents using AI.")

with st.sidebar:
    _ = st.header("Settings")

    _ = st.subheader("🤖 AI Configuration")
    model_choice: str = st.selectbox(
        "Pilih Model", ["deepseek-v3-2-251201", "kimi-k2-250905"]
    )  # type: ignore
    temp: float = st.slider("Temperature", 0.0, 1.0, 0.3)

    _ = st.divider()

    _ = st.subheader("🎥 Video Settings")
    max_duration = st.slider("Maximum Duration (in minutes)", 1, 75, 15)

    _ = st.divider()

    _ = st.subheader("📄 Document Settings")
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
                            summary = generate_summary(client, text, model_choice, temp)
                            display_summary_and_download(str(summary), v_id)
                        except Exception as e:
                            _ = st.error(f"Error: {e}")

# --- TAB 2: PDF ---
with tab2:
    uploaded_file = st.file_uploader("Upload file PDF", type="pdf")

    if not uploaded_file:
        st.session_state.pop("pdf_data", None)
        st.session_state.pop("last_file_id", None)

    if uploaded_file:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if (
            "pdf_data" not in st.session_state
            or st.session_state.get("last_file_id") != file_id
        ):
            try:
                total_pages, full_text, char_count = extract_pdf_info(uploaded_file)

                st.session_state.pdf_data = {
                    "total_pages": total_pages,
                    "full_text": full_text,
                    "char_count": char_count,
                }
                st.session_state.last_file_id = file_id
            except Exception as e:
                _ = st.error(f"Failed to read PDF file: {e}")
                _ = st.stop()

        pdf_info = st.session_state.pdf_data
        total_pages = pdf_info["total_pages"]
        full_text = cast(str, pdf_info["full_text"])
        char_count = pdf_info["char_count"]

        col1, col2 = st.columns(2)
        _ = col1.metric("Page count", f"{total_pages} / {max_pdf_pages}")

        char_count_int = int(pdf_info.get("char_count", 0))

        char_status = "normal" if char_count_int <= 45000 else "inverse"

        _ = col2.metric(
            "Character count",
            f"{char_count_int:,} / 45.000",
            delta_color=char_status,
        )

        # Validasi
        is_valid, msg, msg_type = validate_pdf(
            int(total_pages), int(char_count), int(max_pdf_pages), 45000
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
                    summary = generate_summary(client, full_text, model_choice, temp)
                    display_summary_and_download(str(summary), "document")
                except Exception as e:
                    _ = st.error(f"PDF Error: {e}")
