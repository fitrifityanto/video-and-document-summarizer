import re

# from collections.abc import Mapping
from typing import TypedDict

from yt_dlp import YoutubeDL


class VideoDetails(TypedDict):
    title: str
    author: str
    length: int
    thumbnail_url: str
    views: int


def get_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    pattern = (
        r"(?:v=|\/live\/|\/shorts\/|youtu\.be\/|\/v\/|\/embed\/|^)([0-9A-Za-z_-]{11})"
    )
    match = re.search(pattern, url)
    return str(match.group(1)) if match else ""


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


def get_video_details(url: str) -> VideoDetails:
    """
    Extract video metadata using yt-dlp without downloading the file.
    """

    try:
        with YoutubeDL(
            {"quiet": True, "no_warnings": True, "extract_flat": True}
        ) as ydl:
            info = ydl.extract_info(url, download=False)

            return {
                "title": str(info.get("title") or "Unknown Title"),
                "author": str(info.get("uploader") or "Unknown Channel"),
                "length": int(info.get("duration") or 0),
                "thumbnail_url": str(info.get("thumbnail") or ""),
                "views": int(info.get("view_count") or 0),
            }
    except Exception as e:
        raise Exception(f"yt-dlp error: {str(e)}")


def get_video_duration(url: str) -> int:
    """
    Fetches only the duration of the video.
    """
    details = get_video_details(url)
    return details["length"]
