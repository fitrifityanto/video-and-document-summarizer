import re
from collections.abc import Mapping
from typing import cast

from yt_dlp import YoutubeDL


def get_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    pattern = (
        r"(?:v=|\/live\/|\/shorts\/|youtu\.be\/|\/v\/|\/embed\/|^)([0-9A-Za-z_-]{11})"
    )
    match = re.search(pattern, url)
    return str(match.group(1)) if match else ""


def get_video_duration(url: str) -> int:
    """Fetches video duration in seconds."""
    with YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as ydl:
        info = cast(Mapping[str, object] | None, ydl.extract_info(url, download=False))

        if not info:
            return 0

        duration = info.get("duration")

        if isinstance(duration, (int, float)):
            return int(duration)

        return 0


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
