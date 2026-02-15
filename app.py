import re
from collections.abc import Iterable
from typing import Any, cast

import fitz  # type: ignore
import streamlit as st
import yt_dlp
from openai import OpenAI

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
    """mengambil durasi video dalam detik"""
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
        raise Exception(f"Gagal mengambil transkrip: {str(e)}")


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
    max_duration = st.slider("Maksimal Durasi (Menit)", 1, 75, 15)

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
                        st.error(f"Gagal mengecek durasi: {e}")
                        st.stop()

                if duration_min > max_duration:
                    st.error(
                        f"Video terlalu panjang! Maksimal {max_duration} menit. (Video ini: {duration_min:.1f} menit)"
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
                            st.error(f"Error: {e}")

# --- TAB 2: PDF ---
with tab2:
    uploaded_file = st.file_uploader("Upload file PDF", type="pdf")
    if st.button("Summarize PDF", key="btn_pdf"):
        if uploaded_file:
            with st.spinner("Reading PDF..."):
                try:
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

                    text_gen: Iterable[str] = (
                        str(doc[i].get_text()) for i in range(len(doc))
                    )
                    full_text = "".join(text_gen)

                    res = client.chat.completions.create(
                        model=model_choice,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert assistant that summarizes content deeply. Provide detailed bullet points, explain key concepts, and provide a comprehensive final conclusion.",
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
