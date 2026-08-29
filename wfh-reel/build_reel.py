#!/usr/bin/env python3
"""Build a 60s desi WFH family-drama Instagram Reel for @family_drama_001."""

from __future__ import annotations

import asyncio
import json
import math
import struct
import subprocess
import wave
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
AUDIO = ROOT / "audio"
SFX = ROOT / "sfx"
OUT = ROOT / "out"

W, H, FPS = 1080, 1920, 30
HANDLE = "@family_drama_001"

VOICES = {
    "son": {"voice": "hi-IN-MadhurNeural", "rate": "+26%", "pitch": "+10Hz"},
    "sister": {"voice": "hi-IN-SwaraNeural", "rate": "+28%", "pitch": "+14Hz"},
    "mom": {"voice": "hi-IN-SwaraNeural", "rate": "+16%", "pitch": "-6Hz"},
    "dad": {"voice": "hi-IN-MadhurNeural", "rate": "+14%", "pitch": "-14Hz"},
    "dadi": {"voice": "hi-IN-SwaraNeural", "rate": "+10%", "pitch": "-16Hz"},
    "boss": {"voice": "hi-IN-MadhurNeural", "rate": "+8%", "pitch": "-2Hz"},
}

LINES = [
    {
        "id": "01_son",
        "who": "son",
        "text": "टीम, आज का टारगेट क्लियर है!",
        "caption": "Team, aaj ka target clear hai!",
        "img": "wfh-s01-son-meeting.png",
        "sfx": None,
    },
    {
        "id": "02_mom",
        "who": "mom",
        "text": "ए बेटा, रोटी खा ले, ठंडा हो जाएगा!",
        "caption": "Ae beta, roti kha le, thanda ho jayega!",
        "img": "wfh-s02-mom-thali.png",
        "sfx": "whoosh",
    },
    {
        "id": "03_son",
        "who": "son",
        "text": "मइया, मीटिंग चल रही है!",
        "caption": "Maiya, meeting chal rahi hai!",
        "img": "wfh-s03-son-panic.png",
        "sfx": None,
    },
    {
        "id": "04_mom",
        "who": "mom",
        "text": "मीटिंग-वीटिंग से पेट नहीं भरता!",
        "caption": "Meeting-veeting se pet nahi bharta!",
        "img": "wfh-s10-mom-feed.png",
        "sfx": "rim",
    },
    {
        "id": "05_boss",
        "who": "boss",
        "text": "बेटा... हम सब सुन रहे हैं।",
        "caption": "Beta... hum sab sun rahe hain.",
        "img": "wfh-s06-boss-hear.png",
        "sfx": "shock",
    },
    {
        "id": "06_son",
        "who": "son",
        "text": "सॉरी सर! मुझे लगा म्यूट ऑन है!",
        "caption": "Sorry sir! Mujhe laga mute ON hai!",
        "img": "wfh-s03-son-panic.png",
        "sfx": None,
    },
    {
        "id": "07_sister",
        "who": "sister",
        "text": "भैया, यूपीआई कर दो, पार्सल आ गया!",
        "caption": "Bhaiya, UPI kar do, parcel aa gaya!",
        "img": "wfh-s04-sister-upi.png",
        "sfx": "coin",
    },
    {
        "id": "08_dad",
        "who": "dad",
        "text": "रात को पार्सल? पइसा फूंक दिया का?!",
        "caption": "Raat ko parcel? Paisa phoonk diya ka?!",
        "img": "wfh-s05-dad-salary.png",
        "sfx": None,
    },
    {
        "id": "09_son",
        "who": "son",
        "text": "बाबू, बॉस सुन रहे हैं!",
        "caption": "Babu, boss sun rahe hain!",
        "img": "wfh-s03-son-panic.png",
        "sfx": None,
    },
    {
        "id": "10_dad",
        "who": "dad",
        "text": "बाबू जी, सैलरी मेरे खाते में डाल दीजिए, एफडी कर देंगे!",
        "caption": "Babu ji, salary mere khate mein daal dijiye, FD kar denge!",
        "img": "wfh-s05-dad-salary.png",
        "sfx": "rim",
    },
    {
        "id": "11_boss",
        "who": "boss",
        "text": "अंकल... ये बोर्ड मीटिंग है!",
        "caption": "Uncle... yeh BOARD meeting hai!",
        "img": "wfh-s06-boss-hear.png",
        "sfx": None,
    },
    {
        "id": "12_dadi",
        "who": "dadi",
        "text": "बोर्ड? बेटा बियाह कब होगा?!",
        "caption": "Board? Beta biyah kab hoga?!",
        "img": "wfh-s07-dadi-shaadi.png",
        "sfx": "laugh_hit",
    },
    {
        "id": "13_mom",
        "who": "mom",
        "text": "पहले रोटी, बाद में बियाह!",
        "caption": "Pehle roti, baad mein biyah!",
        "img": "wfh-s10-mom-feed.png",
        "sfx": None,
    },
    {
        "id": "14_boss",
        "who": "boss",
        "text": "मीटिंग कैंसिल! बेटा... रोटी खा लो।",
        "caption": "Meeting cancel! Beta... roti kha lo.",
        "img": "wfh-s08-family-chaos.png",
        "sfx": "sting",
    },
    {
        "id": "15_dadi",
        "who": "dadi",
        "text": "बिहार में डब्ल्यू एफ एच मतलब होल फैमिली हियरिंग!",
        "caption": "Bihar mein WFH = Whole Family Hearing!",
        "img": "wfh-s09-end-laugh.png",
        "sfx": "laugh_hit",
    },
]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


async def synth_line(line: dict) -> Path:
    dest = AUDIO / f"{line['id']}.mp3"
    cfg = VOICES[line["who"]]
    comm = edge_tts.Communicate(
        line["text"],
        cfg["voice"],
        rate=cfg["rate"],
        pitch=cfg["pitch"],
    )
    await comm.save(str(dest))
    return dest


async def synth_all() -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    for line in LINES:
        print(f"TTS {line['id']} ({line['who']})")
        await synth_line(line)


def write_wav(path: Path, samples: list[float], sr: int = 44100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples
        )
        w.writeframes(frames)


def tone(freq: float, dur: float, sr: int, vol: float = 0.35, decay: bool = True) -> list[float]:
    n = int(sr * dur)
    out = []
    for i in range(n):
        t = i / sr
        env = (1 - t / dur) if decay else 1.0
        env *= min(1.0, i / (0.008 * sr))
        out.append(math.sin(2 * math.pi * freq * t) * vol * env)
    return out


def noise(dur: float, sr: int, vol: float = 0.2) -> list[float]:
    n = int(sr * dur)
    out = []
    x = 1234567
    for i in range(n):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        t = i / sr
        env = math.sin(math.pi * t / dur) if dur else 0
        out.append(((x / 0x7FFFFFFF) * 2 - 1) * vol * env)
    return out


def mix_samples(*tracks: list[float]) -> list[float]:
    n = max((len(t) for t in tracks), default=0)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return [max(-1.0, min(1.0, s)) for s in out]


def generate_sfx() -> None:
    sr = 44100
    SFX.mkdir(parents=True, exist_ok=True)

    whoosh = []
    for i in range(int(sr * 0.35)):
        t = i / sr
        f = 220 + 1400 * (t / 0.35)
        env = math.sin(math.pi * t / 0.35) * 0.28
        whoosh.append(math.sin(2 * math.pi * f * t) * env)
    write_wav(SFX / "whoosh.wav", whoosh, sr)

    shock = mix_samples(
        tone(880, 0.12, sr, 0.32),
        tone(1320, 0.10, sr, 0.18),
        noise(0.18, sr, 0.12),
    )
    write_wav(SFX / "shock.wav", shock, sr)

    rim = mix_samples(tone(196, 0.08, sr, 0.4), noise(0.07, sr, 0.22))
    write_wav(SFX / "rim.wav", rim, sr)

    coin = mix_samples(tone(1200, 0.12, sr, 0.28), tone(1800, 0.18, sr, 0.16))
    write_wav(SFX / "coin.wav", coin, sr)

    laugh_hit = mix_samples(
        tone(392, 0.16, sr, 0.22),
        tone(523, 0.18, sr, 0.16),
        tone(659, 0.14, sr, 0.12),
    )
    write_wav(SFX / "laugh_hit.wav", laugh_hit, sr)

    sting = mix_samples(
        tone(523, 0.18, sr, 0.22),
        [0.0] * int(sr * 0.06) + tone(659, 0.18, sr, 0.2),
        [0.0] * int(sr * 0.12) + tone(784, 0.28, sr, 0.24),
    )
    write_wav(SFX / "sting.wav", sting, sr)

    notes = [392, 494, 523, 587, 523, 494, 440, 392, 523, 587, 659, 587, 523, 494, 440, 392]
    music: list[float] = []
    beat = 0.20
    for bar in range(10):
        for i, n in enumerate(notes):
            note = tone(n, beat * 0.85, sr, 0.09, decay=True)
            thump = tone(98, 0.06, sr, 0.05 if i % 2 == 0 else 0.02)
            pad = [0.0] * int(sr * beat)
            for j, s in enumerate(note):
                if j < len(pad):
                    pad[j] += s
            for j, s in enumerate(thump):
                if j < len(pad):
                    pad[j] += s
            music.extend(pad)
    write_wav(SFX / "music.wav", music, sr)


def build_timeline() -> list[dict]:
    tl: list[dict] = []

    def add(img: str, dur: float, caption: str = "", sfx: str | None = None, voice: str | None = None):
        tl.append(
            {
                "img": img,
                "dur": round(dur, 3),
                "caption": caption,
                "sfx": sfx,
                "voice": voice,
            }
        )

    add("wfh-s03-son-panic.png", 0.72, "MUTE OFF tha 😭")
    for line in LINES:
        mp3 = AUDIO / f"{line['id']}.mp3"
        dur = probe_duration(mp3)
        speak = max(0.38, dur / 1.18 + 0.01)
        add(line["img"], speak, line["caption"], line.get("sfx"), str(mp3))
        if line["id"] == "04_mom":
            add("wfh-s06-boss-hear.png", 0.22, "")
        elif line["id"] == "10_dad":
            add("wfh-s06-boss-hear.png", 0.20, "")
        elif line["id"] == "12_dadi":
            add("wfh-s08-family-chaos.png", 0.20, "")
        elif line["id"] == "14_boss":
            add("wfh-s10-mom-feed.png", 0.22, "")
        elif line["id"] == "15_dadi":
            add("wfh-s09-end-laugh.png", 1.35, HANDLE)
    return tl


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Kohinoor.ttc",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def caption_image(src: Path, caption: str, title: bool = False) -> Path:
    dest = OUT / "captioned" / f"{src.stem}__{abs(hash(caption + HANDLE)) % 10_000_000}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return dest
    im = Image.open(src).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    handle_font = load_font(34)
    hw = draw.textlength(HANDLE, font=handle_font)
    draw.rounded_rectangle((W - hw - 56, 36, W - 28, 92), radius=18, fill=(12, 8, 4, 150))
    draw.text((W - hw - 42, 46), HANDLE, font=handle_font, fill=(255, 230, 120, 255))

    if caption:
        font = load_font(58 if title else 44)
        words = caption.split()
        lines: list[str] = []
        cur = ""
        max_w = W - 120
        for word in words:
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        pad = 28
        line_h = 58 if title else 48
        box_h = pad * 2 + line_h * len(lines)
        box_y = H - box_h - (80 if title else 100)
        draw.rounded_rectangle((40, box_y, W - 40, box_y + box_h), radius=28, fill=(12, 8, 4, 155))
        y = box_y + pad
        for line in lines:
            tw = draw.textlength(line, font=font)
            draw.text(((W - tw) / 2, y), line, font=font, fill=(255, 248, 230, 255))
            y += line_h
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    im.save(dest, "PNG", optimize=True)
    return dest


def render_picture(timeline: list[dict]) -> Path:
    lst = OUT / "concat.txt"
    last_captioned = None
    with lst.open("w") as f:
        f.write("ffconcat version 1.0\n")
        for seg in timeline:
            src = FRAMES / seg["img"]
            titled = seg.get("caption") in {"MUTE OFF tha 😭", HANDLE}
            cap = caption_image(src, seg.get("caption") or "", title=titled)
            last_captioned = cap
            f.write(f"file '{cap}'\n")
            f.write(f"duration {seg['dur']:.3f}\n")
        if last_captioned:
            f.write(f"file '{last_captioned}'\n")
    dest = OUT / "picture.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-vf",
            f"scale={W}:{H},fps={FPS},eq=contrast=1.05:saturation=1.14",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
    )
    return dest


def mix_audio(timeline: list[dict], total: float) -> Path:
    dest = OUT / "mix.wav"
    inputs = ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
    inputs += ["-i", str(SFX / "music.wav")]
    next_idx = 2
    voice_filters = []
    sfx_filters = []
    t = 0.0
    for seg in timeline:
        if seg.get("voice"):
            inputs += ["-i", seg["voice"]]
            delay_ms = int(t * 1000)
            voice_filters.append(
                f"[{next_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                f"volume=2.85,atempo=1.18,adelay={delay_ms}|{delay_ms}[v{next_idx}]"
            )
            next_idx += 1
        if seg.get("sfx"):
            sfx_path = SFX / f"{seg['sfx']}.wav"
            if sfx_path.exists():
                inputs += ["-i", str(sfx_path)]
                delay_ms = int(t * 1000)
                sfx_filters.append(
                    f"[{next_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                    f"volume=0.62,adelay={delay_ms}|{delay_ms}[s{next_idx}]"
                )
                next_idx += 1
        t += seg["dur"]

    parts = [f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{total:.3f},atempo=1.15,volume=0.10[music]"]
    mix_labels = ["[0:a]", "[music]"]
    for vf in voice_filters:
        parts.append(vf)
        mix_labels.append(vf[vf.rfind("[") :])
    for sf in sfx_filters:
        parts.append(sf)
        mix_labels.append(sf[sf.rfind("[") :])
    n = len(mix_labels)
    parts.append(f"{''.join(mix_labels)}amix=inputs={n}:normalize=0:duration=longest,volume=1.0[aout]")
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[aout]",
            "-t",
            f"{total:.3f}",
            str(dest),
        ]
    )
    return dest


def mux(picture: Path, audio: Path) -> Path:
    dest = OUT / "WFH_Maa_Meeting_Reel_60s.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(picture),
            "-i",
            str(audio),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )
    return dest


def main() -> None:
    for d in (AUDIO, SFX, OUT, FRAMES):
        d.mkdir(parents=True, exist_ok=True)
    print("== generating SFX / music ==")
    generate_sfx()
    print("== generating voices ==")
    asyncio.run(synth_all())
    print("== building timeline ==")
    timeline = build_timeline()
    total = sum(s["dur"] for s in timeline)
    (OUT / "timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False))
    print(f"total duration: {total:.2f}s  clips: {len(timeline)}")
    print("== rendering picture ==")
    picture = render_picture(timeline)
    print("== mix audio ==")
    audio = mix_audio(timeline, total)
    print("== mux ==")
    final = mux(picture, audio)
    print(f"DONE: {final}  ({probe_duration(final):.2f}s)")


if __name__ == "__main__":
    main()
