"""
Computes delivery metrics from Gemini 3.5 Transcribe word-level output.

Input shape expected: a list of dicts like
    {"text": "Um", "start_offset": "12.800s", "end_offset": "13.100s"}
i.e. what you get by collecting the word_info annotations from the
transcription response. If you're working straight from print-style
output, use parse_raw_lines() first to build this list.
"""

import re
import statistics
from dataclasses import dataclass, asdict

FILLER_WORDS = {
    "um", "uh", "uhh", "umm", "erm", "er",
    "like", "you know", "i mean", "sort of", "kind of", "basically",
}

# Single-word fillers checked per-token; multi-word ones checked via regex on the joined transcript.
SINGLE_WORD_FILLERS = {"um", "uh", "uhh", "umm", "erm", "er", "like", "basically"}
MULTI_WORD_FILLERS = ["you know", "i mean", "sort of", "kind of"]

LONG_PAUSE_THRESHOLD_SEC = 1.5  # gap between words longer than this counts as a "long pause"


@dataclass
class DeliveryMetrics:
    word_count: int
    duration_sec: float
    words_per_minute: float
    filler_word_count: int
    filler_words_found: list
    long_pause_count: int
    longest_pause_sec: float
    pause_details: list  # [{"after_word": str, "gap_sec": float, "at_sec": float}, ...]
    time_to_first_content_word_sec: float  # first word that isn't a filler/pure warm-up


def _to_seconds(offset: str) -> float:
    """'12.800s' -> 12.8"""
    return float(offset.rstrip("s"))


def parse_raw_lines(raw_text: str) -> list:
    """
    Parses lines like:
        12.800s Um
        14s and
        14.100s an
    into [{"text": "Um", "start_offset": "12.800s"}, ...]
    Use this only if you're working from copy-pasted print output rather
    than the structured API response.
    """
    words = []
    pattern = re.compile(r"^([\d.]+)s\s+(.+)$")
    for line in raw_text.strip().splitlines():
        line = line.strip()
        m = pattern.match(line)
        if m:
            offset, text = m.groups()
            words.append({"text": text.rstrip(","), "start_offset": f"{offset}s"})
    return words


def compute_delivery_metrics(words: list) -> DeliveryMetrics:
    """
    words: list of {"text": str, "start_offset": "12.800s", "end_offset": "13.100s"}
    end_offset is optional; if missing, duration/WPM fall back to using
    the last word's start time as the end of the clip.
    """
    if not words:
        raise ValueError("No words provided")

    timestamps = [_to_seconds(w["start_offset"]) for w in words]
    texts = [w["text"] for w in words]

    # --- word count & pace ---
    word_count = len(words)
    start_time = timestamps[0]
    if "end_offset" in words[-1] and words[-1]["end_offset"]:
        end_time = _to_seconds(words[-1]["end_offset"])
    else:
        end_time = timestamps[-1]
    duration_sec = max(end_time - start_time, 0.01)
    words_per_minute = round((word_count / duration_sec) * 60, 1)

    # --- filler words ---
    filler_found = []
    for w in texts:
        clean = w.strip(".,!?").lower()
        if clean in SINGLE_WORD_FILLERS:
            filler_found.append(clean)

    full_lower = " ".join(t.strip(".,!?").lower() for t in texts)
    for phrase in MULTI_WORD_FILLERS:
        filler_found.extend([phrase] * full_lower.count(phrase))

    # --- pauses (gaps between consecutive words) ---
    pause_details = []
    for i in range(1, len(words)):
        prev_end = (
            _to_seconds(words[i - 1]["end_offset"])
            if words[i - 1].get("end_offset")
            else timestamps[i - 1]
        )
        gap = timestamps[i] - prev_end
        if gap >= LONG_PAUSE_THRESHOLD_SEC:
            pause_details.append({
                "after_word": texts[i - 1],
                "gap_sec": round(gap, 2),
                "at_sec": round(timestamps[i - 1], 2),
            })

    longest_pause = max((p["gap_sec"] for p in pause_details), default=0.0)

    # --- time to first real content word (skips leading fillers) ---
    time_to_first_content = start_time
    for w, ts in zip(texts, timestamps):
        clean = w.strip(".,!?").lower()
        if clean not in SINGLE_WORD_FILLERS and clean not in ("", "so", "and", "well"):
            time_to_first_content = ts
            break

    return DeliveryMetrics(
        word_count=word_count,
        duration_sec=round(duration_sec, 2),
        words_per_minute=words_per_minute,
        filler_word_count=len(filler_found),
        filler_words_found=filler_found,
        long_pause_count=len(pause_details),
        longest_pause_sec=round(longest_pause, 2),
        pause_details=pause_details,
        time_to_first_content_word_sec=round(time_to_first_content - start_time, 2),
    )

"""That's when your mind is at rest. That's why I think um content you can grasp content easily and you know it as a thing in your mind. So and it should start early correctly. Technical work. Because when you you get structure of from morning until So that's why That's good I think.
"""
if __name__ == "__main__":
    # Quick manual test using your pasted transcript output
    sample = """
  6.700s That's
7s when
7.700s your
7.800s mind
8.200s is
8.500s at
8.600s rest.
9.800s That's
9.900s why
10.100s I
10.200s think
11s um
13s content
14.400s you
14.500s can
14.700s grasp
15.400s content
16.100s easily
17.300s and
17.500s you
17.700s know
18s it
18.900s as
20s a
20.400s thing
20.500s in
20.600s your
20.700s mind.
22.500s So
24.800s and
28.700s it
28.800s should
29s start
29.600s early
30.600s correctly.
37.600s Technical
37.900s work.
44.700s Because
45s when
45.200s you
45.600s you
45.700s get
46s structure
47.700s of
49.200s from
49.400s morning
50.200s until
52.800s So
52.900s that's
53.100s why
55.300s That's
55.600s good
56s I
56.100s think.
    
    """
    words = parse_raw_lines(sample)
    metrics = compute_delivery_metrics(words)
    import json
    print(json.dumps(asdict(metrics), indent=2))