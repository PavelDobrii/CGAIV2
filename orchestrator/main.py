import argparse
import os
import re
from pathlib import Path
import requests

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "story_prompt.txt"

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "output"

def load_template() -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()

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

    template = load_template()
    formatted_prompt = template.format(prompt=args.prompt, language=args.language, style=args.style)

    llm_response = requests.post(f"{args.llm_url.rstrip('/')}/generate_story", json={"prompt": formatted_prompt})
    llm_response.raise_for_status()
    story_text = llm_response.json().get("story") or llm_response.text

    slug = slugify(args.prompt)
    output_dir = Path("outputs") / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "story.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(story_text)

    tts_response = requests.post(f"{args.tts_url.rstrip('/')}/speak", json={"text": story_text, "language": args.language})
    tts_response.raise_for_status()
    audio_path = output_dir / "story.mp3"
    with open(audio_path, "wb") as f:
        f.write(tts_response.content)

    print(f"Markdown saved to {md_path}")
    print(f"Audio saved to {audio_path}")

if __name__ == "__main__":
    main()
