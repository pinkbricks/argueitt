import io

from google import genai
from google.genai import types

TRANSCRIBE_MODEL = "gemini-3.5-transcribe"


async def transcribe_words(client: genai.Client, data: bytes, mime_type: str | None) -> tuple[str, list[dict]]:
    """
    Uploads audio bytes and transcribes them with word-level timestamps.
    Returns (transcript_text, words) where words is a list of
    {"text": str, "start_offset": "12.800s", "end_offset": "13.100s"} —
    the shape stats.compute_delivery_metrics expects.
    """
    mime = (mime_type or "audio/wav").split(";")[0]
    uploaded = await client.aio.files.upload(
        file=io.BytesIO(data),
        config=types.UploadFileConfig(mime_type=mime),
    )

    result = await client.aio.interactions.create(
        model=TRANSCRIBE_MODEL,
        input=[{"type": "audio", "uri": uploaded.uri, "mime_type": uploaded.mime_type}],
        generation_config={
            "transcription_config": {
                "mode": {"type": "verbatim", "timestamp_granularities": ["word"]}
            }
        },
    )

    words = []
    for step in result.steps or []:
        for content in step.content or []:
            for w in content.annotations or []:
                if w.type == "word_info" and w.text and w.start_offset:
                    words.append({"text": w.text, "start_offset": w.start_offset, "end_offset": w.end_offset})

    return (result.output_text or "").strip(), words


if __name__ == "__main__":
    # Manual test against a local audio file.
    import asyncio
    import os

    from dotenv import load_dotenv

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    with open("argueitt-should-schools-start-later-in-the-mornin-against-attempt1.wav", "rb") as f:
        data = f.read()

    transcript, words = asyncio.run(transcribe_words(client, data, "audio/wav"))
    print(transcript)
    for w in words:
        print(w["start_offset"], w["text"])
