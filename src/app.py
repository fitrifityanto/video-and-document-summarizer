from typing import cast

import streamlit as st

from services.ai_engine import generate_summary, get_ai_client
from services.document import extract_pdf_info, validate_pdf
from services.youtube import get_transcript_text, get_video_details, get_video_id
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
        "Pilih Model", ["seed-2-0-mini-free", "seed-1-8-free", "deepseek-v3-2-free"]
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
    yt_url = st.text_input("Enter YouTube URL", key="yt_url_input")

    # Inisialisasi session states
    if "yt_info" not in st.session_state:
        st.session_state.yt_info = None
    if "yt_summary" not in st.session_state:
        st.session_state.yt_summary = None
    if "last_v_id" not in st.session_state:
        st.session_state.last_v_id = None

    v_id = get_video_id(yt_url) if yt_url else None

    if v_id != st.session_state.last_v_id:
        st.session_state.yt_summary = None
        st.session_state.yt_info = None
        st.session_state.last_v_id = v_id
        if v_id:
            with st.spinner("Fetching video details..."):
                try:
                    st.session_state.yt_info = get_video_details(yt_url)
                except Exception as e:
                    _ = st.error(f"Error: {e}")

    info = st.session_state.yt_info

    if v_id and info:
        duration_min = info["length"] / 60

        col_img, col_txt = st.columns([1, 2])
        with col_img:
            _ = st.image(info["thumbnail_url"], width="stretch")
        with col_txt:
            _ = st.subheader(info["title"])
            _ = st.caption(f"📺 Channel: {info['author']}")
            m_col1, m_col2 = st.columns(2)
            duration_status = "normal" if duration_min <= max_duration else "inverse"
            _ = m_col1.metric(
                "Duration",
                f"{duration_min:.1f} / {max_duration} min",
                delta_color=duration_status,
            )
            _ = m_col2.metric("Views", f"{info['views']:,}")

        if not st.session_state.yt_summary:
            if duration_min > max_duration:
                _ = st.error(f"Video is too long! (Max: {max_duration} min)")
            else:
                _ = st.success("Video ready to summarize")

                if st.button("Summarize Video", key="btn_yt", type="primary"):
                    with st.status(
                        "Processing YouTube Content...", expanded=True
                    ) as status:
                        try:
                            status.write("Downloading transcript...")
                            text = get_transcript_text(v_id)

                            status.write("Analyzing with AI...")
                            summary = generate_summary(client, text, model_choice, temp)

                            # Simpan hasil ke session state
                            st.session_state.yt_summary = str(summary)

                            status.update(
                                label="Summarization Complete!",
                                state="complete",
                                expanded=False,
                            )

                            st.rerun()

                        except Exception as e:
                            status.update(label="Failed!", state="error")
                            _ = st.error(f"Error: {e}")

        else:
            display_summary_and_download(st.session_state.yt_summary, v_id)

            _ = st.divider()
            if st.button("🔄 Summarize Another Video / Reset", key="re_summarize"):
                st.session_state.yt_summary = None
                st.rerun()


# --- TAB 2: PDF ---
with tab2:
    uploaded_file = st.file_uploader("Upload file PDF", type="pdf")

    if "pdf_summary" not in st.session_state:
        st.session_state.pdf_summary = None

    if not uploaded_file:
        st.session_state.pdf_data = None
        st.session_state.last_file_id = None
        st.session_state.pdf_summary = None

    else:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"

        if st.session_state.get("last_file_id") != file_id:
            try:
                total_pages, full_text, char_count = extract_pdf_info(uploaded_file)
                st.session_state.pdf_data = {
                    "total_pages": total_pages,
                    "full_text": full_text,
                    "char_count": char_count,
                }
                st.session_state.last_file_id = file_id
                st.session_state.pdf_summary = None
            except Exception as e:
                _ = st.error(f"Failed to read PDF file: {e}")
                st.stop()

        pdf_info = st.session_state.pdf_data

        col1, col2 = st.columns(2)
        _ = col1.metric("Page count", f"{pdf_info['total_pages']} / {max_pdf_pages}")

        char_count = int(pdf_info["char_count"])
        char_status = "normal" if char_count <= 45000 else "inverse"
        _ = col2.metric(
            "Character count", f"{char_count:,} / 45.000", delta_color=char_status
        )

        is_valid, msg, msg_type = validate_pdf(
            int(pdf_info["total_pages"]), char_count, int(max_pdf_pages), 45000
        )

        if st.session_state.pdf_summary is None:
            if msg_type == "error":
                _ = st.error(msg)
            elif msg_type == "warning":
                _ = st.warning(msg)
            else:
                _ = st.success(msg)

            if st.button(
                "Summarize PDF", key="btn_pdf", disabled=not is_valid, type="primary"
            ):
                with st.spinner("Processing summary..."):
                    try:
                        pdf_text = str(pdf_info["full_text"])
                        summary = generate_summary(client, pdf_text, model_choice, temp)
                        st.session_state.pdf_summary = str(summary)
                        st.rerun()
                    except Exception as e:
                        _ = st.error(f"AI Error: {e}")
        else:
            display_summary_and_download(st.session_state.pdf_summary, "document")

            _ = st.divider()
            if st.button("🔄 Summarize Another PDF", key="reset_pdf"):
                st.session_state.pdf_summary = None
                st.rerun()
