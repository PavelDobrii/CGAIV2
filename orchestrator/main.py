import argparse
import os
import re
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "story_prompt.txt"

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "output"

def load_template() -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def run_story(prompt: str, language: str, style: str, llm_url: str, tts_url: str):
    template = load_template()
    formatted_prompt = template.format(prompt=prompt, language=language, style=style)

    llm_response = requests.post(f"{llm_url.rstrip('/')}/generate_story", json={"prompt": formatted_prompt})
    llm_response.raise_for_status()
    story_text = llm_response.json().get("story") or llm_response.text

    slug = slugify(prompt)
    output_dir = Path(__file__).resolve().parent / "outputs" / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "story.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(story_text)

    tts_response = requests.post(
        f"{tts_url.rstrip('/')}/speak", json={"text": story_text, "language": language}
    )
    tts_response.raise_for_status()
    audio_path = output_dir / "story.mp3"
    with open(audio_path, "wb") as f:
        f.write(tts_response.content)

    return md_path, audio_path

def main():
    parser = argparse.ArgumentParser(description="Generate a story and TTS audio")
    parser.add_argument("prompt", help="Prompt for the story")
    parser.add_argument("language", help="Language for the story")
    parser.add_argument("style", help="Story style")
    parser.add_argument(
        "--llm-url",
        default=os.environ.get("LLM_SERVER_URL", "http://localhost:8080"),
        help="Base URL of LLM server",
    )
    parser.add_argument(
        "--tts-url",
        default=os.environ.get("TTS_SERVER_URL", "http://localhost:5500"),
        help="Base URL of TTS server",
    )
    args = parser.parse_args()

    md_path, audio_path = run_story(
        prompt=args.prompt,
        language=args.language,
        style=args.style,
        llm_url=args.llm_url,
        tts_url=args.tts_url,
    )

    print(f"Markdown saved to {md_path}")
    print(f"Audio saved to {audio_path}")


class StoryRequest(BaseModel):
    prompt: str
    language: str
    style: str


app = FastAPI()


@app.post("/story")
def create_story(request: StoryRequest):
    llm_url = os.environ.get("LLM_SERVER_URL", "http://localhost:8080")
    tts_url = os.environ.get("TTS_SERVER_URL", "http://localhost:5500")
    try:
        md_path, audio_path = run_story(
            prompt=request.prompt,
            language=request.language,
            style=request.style,
            llm_url=llm_url,
            tts_url=tts_url,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"markdown": str(md_path), "audio": str(audio_path)}

if __name__ == "__main__":
    main()
