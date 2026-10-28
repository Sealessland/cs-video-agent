"""字幕：把每幕的 beat 时间戳（真实渲染时钟）合成为全局 SRT。"""

from datetime import timedelta

import srt


def build_srt(scene_entries: list[dict]) -> str:
    """scene_entries: [{duration, beats: [{id, narration, start, end}]}]"""
    subs = []
    offset = 0.0
    for s in scene_entries:
        dur = float(s["duration"])
        for b in s["beats"]:
            text = (b.get("narration") or "").strip()
            if not text:
                continue
            start = offset + max(0.0, float(b["start"]))
            end = offset + min(float(b["end"]), dur)
            if end <= start:
                end = start + 0.4
            subs.append(srt.Subtitle(
                index=len(subs) + 1,
                start=timedelta(seconds=start),
                end=timedelta(seconds=end),
                content=text,
            ))
        offset += dur
    return srt.compose(subs)
