from google import genai
import os

from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(api_key)

client = genai.Client(api_key=api_key)

audio = client.files.upload(file="argueitt-should-schools-start-later-in-the-mornin-against-attempt1.wav")

result = client.interactions.create(
    model="gemini-3.5-transcribe",
    input=[{"type": "audio", "uri": audio.uri, "mime_type": audio.mime_type}],
    generation_config={
        "transcription_config": {
            "mode": {"type": "verbatim", "timestamp_granularities": ["word"]}
        }
    },
)

print(result.output_text)

for step in result.steps or []:
    for content in step.content or []:
        for w in content.annotations or []:
            if w.type == "word_info":
                print(w.start_offset, w.text)


