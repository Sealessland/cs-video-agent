"""字幕生成测试：全局时间轴、顺序、跨幕偏移。"""

from cs_video_agent.engine.subtitles import build_srt

ENTRIES = [
    {
        "duration": 10.0,
        "beats": [
            {"id": "a1", "narration": "第一幕开场", "start": 0.0, "end": 4.0},
            {"id": "a2", "narration": None, "start": 4.0, "end": 10.0},
        ],
    },
    {
        "duration": 5.0,
        "beats": [
            {"id": "b1", "narration": "第二幕开场", "start": 0.0, "end": 3.0},
        ],
    },
]


def test_srt_contains_all_narrations_in_order():
    text = build_srt(ENTRIES)
    assert "第一幕开场" in text and "第二幕开场" in text
    assert text.index("第一幕开场") < text.index("第二幕开场")
    assert "None" not in text


def test_srt_second_scene_offset_by_first_duration():
    text = build_srt(ENTRIES)
    # 第二幕解说起始应 ≥ 10s（第一幕总长）
    assert "00:00:10,000" in text


def test_srt_blocks_are_wellformed():
    text = build_srt(ENTRIES)
    blocks = [b for b in text.strip().split("\n\n") if b.strip()]
    assert len(blocks) == 2
    assert blocks[0].splitlines()[0] == "1"
    assert blocks[1].splitlines()[0] == "2"
