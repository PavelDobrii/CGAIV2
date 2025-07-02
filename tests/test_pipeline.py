import json
import importlib
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest


class _LLMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"story": "This is a test story."}).encode())

    def log_message(self, *args):  # pragma: no cover
        pass


def _start_server(handler):
    server = HTTPServer(("localhost", 0), handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    url = f"http://localhost:{server.server_address[1]}"
    return server, thread, url


@pytest.fixture
def llm_server():
    server, thread, url = _start_server(_LLMHandler)
    yield url
    server.shutdown()
    thread.join()


@pytest.fixture
def tts_server():
    requests = []

    class _TTSHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            requests.append({"path": self.path, "body": data})
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            self.wfile.write(b"TESTMP3")

        def log_message(self, *args):  # pragma: no cover
            pass

    server, thread, url = _start_server(_TTSHandler)
    yield url, requests
    server.shutdown()
    thread.join()


def _slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "output"


def _run_pipeline(
    tmp_path: Path,
    prompt: str,
    language: str,
    llm_url: str,
    tts_url: str,
    tts_engine: str = "opentts",
    location: str | None = None,
) -> tuple[Path, tuple[Path, Path, str, bytes]]:
    requests_stub = '''\
import json as _json
from urllib import request as _request

class Response:
    def __init__(self, resp):
        self.content = resp.read()
        self.status_code = resp.getcode()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(self.status_code)

    def json(self):
        try:
            return _json.loads(self.content.decode())
        except Exception:
            return {}

    @property
    def text(self):
        return self.content.decode()

def post(url, json=None):
    data = None
    if json is not None:
        data = _json.dumps(json).encode()
    req = _request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    resp = _request.urlopen(req)
    return Response(resp)
'''

    (tmp_path / "requests.py").write_text(requests_stub)

    repo_root = Path(__file__).resolve().parents[1]
    sys.modules.pop("requests", None)
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(tmp_path))
    try:
        main = importlib.import_module("orchestrator.main")
        importlib.reload(main)
        final_prompt = prompt
        if location is not None:
            wiki = main.fetch_wikipedia_extract(location)
            voyage = main.fetch_wikivoyage_extract(location)
            info_parts = [wiki, voyage]
            info = "\n\n".join(p for p in info_parts if p)
            if info:
                final_prompt = f"{prompt}\n\n{info}"

        result = main.run_story(
            prompt=prompt,
            language=language,
            style="fun",
            llm_url=llm_url,
            tts_url=tts_url,
            tts_engine=tts_engine,
            location=location,
            output_base_dir=tmp_path,
        )
        md_path, audio_path, text, audio_bytes = result
    finally:
        sys.path.remove(str(tmp_path))
        sys.path.remove(str(repo_root))

    return tmp_path / "outputs" / _slugify(final_prompt), result


def test_pipeline(tmp_path, llm_server, tts_server):
    tts_url, requests_data = tts_server
    languages = ["English", "Spanish", "French"]
    outputs = []

    for lang in languages:
        out_dir, result = _run_pipeline(tmp_path, f"Prompt {lang}", lang, llm_server, tts_url)
        outputs.append((out_dir, result))

    assert [r["body"]["speaker"] for r in requests_data] == languages
    assert all(r["path"] == "/api/tts" for r in requests_data)

    for dir_, result in outputs:
        md = dir_ / "story.md"
        mp3 = dir_ / "story.mp3"
        assert md.exists()
        assert mp3.exists()
        md_path, audio_path, text, audio_bytes = result
        assert md_path == md
        assert audio_path == mp3
        assert text == "This is a test story."
        assert audio_bytes == b"TESTMP3"


def test_pipeline_kokoro(tmp_path, llm_server, tts_server):
    tts_url, requests_data = tts_server
    out_dir, result = _run_pipeline(
        tmp_path,
        "Prompt Kokoro",
        "Japanese",
        llm_server,
        tts_url,
        tts_engine="kokoro",
    )

    md = out_dir / "story.md"
    mp3 = out_dir / "story.mp3"
    assert md.exists()
    assert mp3.exists()
    md_path, audio_path, text, audio_bytes = result
    assert md_path == md
    assert audio_path == mp3
    assert text == "This is a test story."
    assert audio_bytes == b"TESTMP3"
    assert requests_data[0]["path"] == "/api/kokoro"


def test_pipeline_location_context(tmp_path, tts_server, monkeypatch):
    wiki_text = "Wiki info"
    voyage_text = "Voyage info"

    monkeypatch.setattr(
        "orchestrator.sources.fetch_wikipedia_extract", lambda loc: wiki_text
    )
    monkeypatch.setattr(
        "orchestrator.sources.fetch_wikivoyage_extract", lambda loc: voyage_text
    )

    class _EchoHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"story": data["inputs"]}).encode())

        def log_message(self, *args):  # pragma: no cover
            pass

    server, thread, llm_url = _start_server(_EchoHandler)
    tts_url, _ = tts_server
    try:
        out_dir, result = _run_pipeline(
            tmp_path,
            "Base prompt",
            "English",
            llm_url,
            tts_url,
            tts_engine="opentts",
            location="Berlin",
        )
    finally:
        server.shutdown()
        thread.join()

    md_text = (out_dir / "story.md").read_text(encoding="utf-8")
    md_path, audio_path, text, audio_bytes = result
    assert audio_bytes == b"TESTMP3"
    assert text == md_text
    assert "Base prompt" in md_text
    assert wiki_text in md_text
    assert voyage_text in md_text
    assert md_text.index("Base prompt") < md_text.index(wiki_text) < md_text.index(
        voyage_text
    )
