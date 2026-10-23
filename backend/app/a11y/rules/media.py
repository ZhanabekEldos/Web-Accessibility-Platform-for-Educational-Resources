"""Аудио и видео: субтитры, расшифровки, автовоспроизведение (WCAG 1.2.x, 1.4.2)."""
from __future__ import annotations

import re

from ..document import Document
from ..registry import RuleReport, rule

_VIDEO_HOSTS = re.compile(
    r"(youtube(-nocookie)?\.com|youtu\.be|vimeo\.com|rutube\.ru|dailymotion\.com|vk\.com/video|vkvideo\.ru|"
    r"ok\.ru/videoembed|kinescope\.io|loom\.com|wistia\.(com|net)|facebook\.com/plugins/video|player\.twitch\.tv)",
    re.I,
)


@rule(
    id="video-captions", wcag=["1.2.2"], level="A", impact="critical", principle="perceivable", tags=["media", "education"],
    bad='<video src="lecture.mp4" controls></video>',
    good='<video src="lecture.mp4" controls>\n  <track kind="captions" src="lecture.vtt" srclang="ru" label="Русский">\n</video>',
)
def video_captions(doc: Document, report: RuleReport) -> None:
    for video in doc.find_all("video"):
        if not doc.is_exposed(video):
            continue
        # Беззвучный «фоновый» ролик без элементов управления в субтитрах не нуждается.
        if video.has_attr("muted") and not video.has_attr("controls"):
            continue
        report.checked()
        tracks = video.find_all("track", kind=lambda k: (k or "").lower() in ("captions", "subtitles"))
        if not tracks:
            report.fail(video)


@rule(
    id="audio-transcript", wcag=["1.2.1"], level="A", impact="serious", principle="perceivable", tags=["media", "education"],
    manual=True, bad='<audio src="podcast.mp3" controls></audio>',
    good='<audio src="podcast.mp3" controls></audio>\n<a href="podcast-transcript.html">Transcript</a>',
)
def audio_transcript(doc: Document, report: RuleReport) -> None:
    for audio in doc.find_all("audio"):
        if not doc.is_exposed(audio):
            continue
        report.checked()
        report.review(audio)


@rule(
    id="embedded-video-review", wcag=["1.2.2"], level="A", impact="serious", principle="perceivable", tags=["media", "education"],
    manual=True, bad='<iframe src="https://www.youtube.com/embed/ID"></iframe>',
    good='<iframe title="Lecture 3: Limits" src="https://www.youtube.com/embed/ID?cc_load_policy=1"></iframe>',
)
def embedded_video_review(doc: Document, report: RuleReport) -> None:
    for frame in doc.find_all("iframe"):
        src = frame.get("src") or frame.get("data-src") or ""
        if not _VIDEO_HOSTS.search(src) or not doc.is_exposed(frame):
            continue
        report.checked()
        report.review(frame, data={"host": re.sub(r"^https?://([^/]+).*$", r"\1", src)[:60]})


@rule(
    id="media-autoplay", wcag=["1.4.2", "2.2.2"], level="A", impact="serious", principle="perceivable", tags=["media"],
    bad='<video src="intro.mp4" autoplay></video>', good='<video src="intro.mp4" controls></video>',
)
def media_autoplay(doc: Document, report: RuleReport) -> None:
    for media in doc.find_all("video", "audio"):
        if not media.has_attr("autoplay") or not doc.is_exposed(media):
            continue
        report.checked()
        # Автовоспроизведение допустимо, если звука нет и пользователь может остановить ролик.
        if not media.has_attr("muted") or not media.has_attr("controls"):
            report.fail(media)
