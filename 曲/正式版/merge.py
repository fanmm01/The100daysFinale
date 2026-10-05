from pathlib import Path
from fractions import Fraction
from collections import defaultdict, deque
import sys
import mido

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
LAYERS = ROOT / "迷幻流行_修订版"
OUTPUT = ROOT / "迷幻流行_合轨输出"
SOURCE = ROOT / "如梦人生的X日终焉&最后第零个愿望-2.mid"
TEMPO = 500000  # 120 BPM


def timed(track):
    tick = 0
    for message in track:
        tick += message.time
        yield tick, message


def load(path):
    midi = mido.MidiFile(str(path))
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError(f"不支持此 MIDI 的时间格式：{path.name}")
    return midi


def read_notes(midi):
    """按轨道、通道配对音符；时间以精确的拍数表示。"""
    lanes = defaultdict(list)
    ppq = midi.ticks_per_beat

    for track_index, track in enumerate(midi.tracks):
        active = defaultdict(deque)
        for tick, message in timed(track):
            if message.type not in ("note_on", "note_off"):
                continue
            key = (message.channel, message.note)

            if message.type == "note_on" and message.velocity > 0:
                active[key].append((tick, message.velocity))
            else:
                if not active[key]:
                    raise ValueError(
                        f"轨道 {track_index} 出现未配对的 note_off"
                    )
                start, velocity = active[key].popleft()
                lanes[(track_index, message.channel)].append(
                    (
                        Fraction(start, ppq),
                        Fraction(tick, ppq),
                        message.note,
                        velocity,
                    )
                )

        if any(active.values()):
            raise ValueError(f"轨道 {track_index} 有未结束的音符")

    return lanes


def all_notes(midi):
    return [
        note
        for lane in read_notes(midi).values()
        for note in lane
    ]


def make_track(name, events, end_tick):
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name=name, time=0))
    previous = 0

    # 稳定排序，保留同一时刻原事件的先后顺序。
    for tick, message in sorted(events, key=lambda item: item[0]):
        track.append(message.copy(time=tick - previous))
        previous = tick

    track.append(
        mido.MetaMessage(
            "end_of_track",
            time=max(previous, end_tick) - previous,
        )
    )
    return track


def instrument_track(name, notes, channel, program, volume, ppq):
    events = [
        (0, mido.Message(
            "program_change", channel=channel, program=program
        )),
        (0, mido.Message(
            "control_change", channel=channel,
            control=7, value=volume
        )),
    ]

    for start, end, pitch, velocity in sorted(notes):
        first = round(start * ppq)
        last = round(end * ppq)
        if last <= first:
            raise ValueError(f"{name} 中存在无法保留的音符时值")

        events.append((first, mido.Message(
            "note_on", channel=channel,
            note=pitch, velocity=velocity
        )))
        events.append((last, mido.Message(
            "note_off", channel=channel,
            note=pitch, velocity=0
        )))

    return make_track(name, events, 568 * ppq)


def conductor(ppq, source=None):
    events = []
    if source is not None:
        seen = set()
        for track in source.tracks:
            for tick, message in timed(track):
                if message.type not in (
                    "set_tempo", "time_signature", "key_signature"
                ):
                    continue
                key = (tick, str(message.copy(time=0)))
                if key not in seen:
                    seen.add(key)
                    events.append((tick, message.copy(time=0)))

    if not any(
        tick == 0 and message.type == "set_tempo"
        for tick, message in events
    ):
        events.insert(0, (0, mido.MetaMessage(
            "set_tempo", tempo=TEMPO
        )))

    if not any(
        tick == 0 and message.type == "time_signature"
        for tick, message in events
    ):
        events.append((0, mido.MetaMessage(
            "time_signature", numerator=4, denominator=4
        )))

    return make_track("Conductor", events, 568 * ppq)


def save_checked(midi, filename, expected_count):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / filename
    version = 2
    while target.exists():
        target = OUTPUT / (
            f"{Path(filename).stem}_{version}.mid"
        )
        version += 1

    midi.save(str(target))
    actual_count = len(all_notes(load(target)))
    if actual_count != expected_count:
        raise RuntimeError(
            f"回读数量不一致：{target.name}，"
            f"预期 {expected_count}，实际 {actual_count}"
        )
    print(f"已生成：{target}（{actual_count} 个音符）")


def main():
    harmony_files = [
        f"{index:02d}_和声贝斯_{letter}.mid"
        for index, letter in enumerate("ABCD", start=1)
    ]
    drum_files = [
        "05_鼓组_A.mid",
        "06_鼓组_B.mid",
        "07_鼓组_C.mid",
        "08_鼓组_D1.mid",
        "09_鼓组_D2.mid",
    ]

    def collect(names):
        notes = []
        for name in names:
            notes.extend(all_notes(load(LAYERS / name)))
        return notes

    combined = collect(harmony_files)
    # 本组文件中贝斯最高为 F2，和声最低为 B2。
    bass = [note for note in combined if note[2] < 45]
    harmony = [note for note in combined if note[2] >= 45]
    drums = collect(drum_files)
    pad = collect(["10_氛围铺底.mid"])
    response = collect(["11_呼应拨弦.mid"])

    drum_keys = {36, 37, 38, 41, 42, 45, 46, 49, 50}
    if any(note[2] not in drum_keys for note in drums):
        raise ValueError("鼓键位与本编曲预期不符，请检查八度映射")

    # Mido 的通道及音色编号从 0 开始。
    # GM 音色仅用于预览，可在 DAW 中替换。
    parts = [
        ("Bass", bass, 1, 33, 100),
        ("Harmony", harmony, 2, 4, 85),
        ("Atmosphere", pad, 3, 89, 70),
        ("Response", response, 4, 10, 80),
        ("Drums", drums, 9, 0, 100),
    ]
    total = sum(len(part[1]) for part in parts)

    def arrangement(ppq, source=None):
        result = mido.MidiFile(type=1, ticks_per_beat=ppq)
        result.tracks.append(conductor(ppq, source))
        for name, notes, channel, program, volume in parts:
            result.tracks.append(instrument_track(
                name, notes, channel, program, volume, ppq
            ))
        return result

    save_checked(
        arrangement(480), "伴奏_120.mid", total
    )

    if not SOURCE.exists():
        print("未找到原始 MIDI；伴奏已完成，未生成含旋律合轨。")
        return

    source = load(SOURCE)
    tempo_events = [
        (tick, message.tempo)
        for track in source.tracks
        for tick, message in timed(track)
        if message.type == "set_tempo"
    ]
    if any(tempo != TEMPO for _, tempo in tempo_events):
        values = sorted({
            round(mido.tempo2bpm(tempo), 6)
            for _, tempo in tempo_events
        })
        print(f"原文件包含这些 BPM：{values}")
        print(
            "为保留原速，未生成 120 BPM 的含旋律合轨。"
            "可在原工程按拍导入伴奏，并保留原工程速度。"
        )
        return

    lanes = read_notes(source)
    tolerance = Fraction(1, source.ticks_per_beat)

    # 来自已核对原谱的主旋律定位点，不按“最高音”猜旋律。
    anchors = [
        (Fraction(7, 2), 67),  # 3.5 拍 G4
        (Fraction(16), 66),    # 16 拍 F#4
        (Fraction(224), 60),   # 224 拍 C4
        (Fraction(424), 85),   # 424 拍 C#6
        (Fraction(564), 57),   # 564 拍 A3
    ]
    candidates = []

    for key, notes in lanes.items():
        if key[1] == 9:
            continue
        matches = all(
            any(
                abs(note[0] - beat) <= tolerance
                and note[2] == pitch
                for note in notes
            )
            for beat, pitch in anchors
        )
        sounding = sorted(
            note for note in notes if note[1] > note[0]
        )
        monophonic = all(
            left[1] <= right[0] + tolerance
            for left, right in zip(sounding, sounding[1:])
        )
        if matches and monophonic:
            candidates.append(key)

    if len(candidates) != 1:
        print(
            "未能唯一识别独立主旋律；"
            "伴奏已完成，含旋律合轨未生成。"
        )
        print("原文件声部清单（轨道编号从 0 开始）：")
        for (track_index, channel), notes in sorted(lanes.items()):
            print(
                f"  轨道 {track_index}，"
                f"MIDI 通道 {channel + 1}，"
                f"{len(notes)} 个音符"
            )
        print("请在 DAW 中将主旋律单独保留，再加入新伴奏。")
        return

    track_index, channel = candidates[0]
    melody_events = []
    for tick, message in timed(source.tracks[track_index]):
        if getattr(message, "channel", None) == channel:
            melody_events.append((
                tick, message.copy(channel=0, time=0)
            ))
        elif message.is_meta and message.type in (
            "lyrics", "text", "marker", "cue_marker"
        ):
            melody_events.append((tick, message.copy(time=0)))

    # 使用原文件的 PPQ，原旋律事件位置保持原始 tick。
    ppq = source.ticks_per_beat
    complete = arrangement(ppq, source)
    complete.tracks.insert(
        1, make_track(
            "Original Melody", melody_events, 568 * ppq
        )
    )
    save_checked(
        complete,
        "含原旋律_120.mid",
        total + len(lanes[(track_index, channel)]),
    )
    print("完成。所有输入 MIDI 均未改写。")


if __name__ == "__main__":
    main()