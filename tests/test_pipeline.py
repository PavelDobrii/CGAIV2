import json
import os
import re
import subprocess
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
            requests.append(data)
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


def _run_pipeline(tmp_path: Path, prompt: str, language: str, llm_url: str, tts_url: str) -> Path:
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

    cmd = [
        sys.executable,
        "-m",
        "orchestrator.main",
        prompt,
        language,
        "fun",
        "--llm-url",
        llm_url,
        "--tts-url",
        tts_url,
    ]
    env = {**os.environ, "PYTHONPATH": f"{repo_root}:{tmp_path}"}
    subprocess.run(cmd, check=True, cwd=tmp_path, env=env)
    return tmp_path / "outputs" / _slugify(prompt)


def test_pipeline(tmp_path, llm_server, tts_server):
    tts_url, requests_data = tts_server
    languages = ["English", "Spanish", "French"]
    output_dirs = []

    for lang in languages:
        out_dir = _run_pipeline(tmp_path, f"Prompt {lang}", lang, llm_server, tts_url)
        output_dirs.append(out_dir)

    assert [r["speaker"] for r in requests_data] == languages

    for dir_ in output_dirs:
        md = dir_ / "story.md"
        mp3 = dir_ / "story.mp3"
        assert md.exists()
        assert mp3.exists()
        assert md.read_text(encoding="utf-8") == "This is a test story."
        assert mp3.read_bytes() == b"TESTMP3"
