import importlib
import json
import os
import sys
import types
from pathlib import Path

import base64

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


class _LLMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"story": "This is a test story."}).encode())

    def log_message(self, *args):
        pass


class _TTSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.end_headers()
        self.wfile.write(b"TESTMP3")

    def log_message(self, *args):
        pass


def _start_server(handler):
    server = HTTPServer(("localhost", 0), handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server, thread, f"http://localhost:{server.server_address[1]}"


def _load_app(tmp_path: Path, llm_url: str, tts_url: str):
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

    # create stub fastapi and pydantic modules
    fastapi_mod = types.ModuleType("fastapi")
    class FastAPI:
        def __init__(self):
            self.endpoint = None
        def post(self, path):
            def decorator(fn):
                self.endpoint = fn
                return fn
            return decorator
    fastapi_mod.FastAPI = FastAPI
    fastapi_mod.HTTPException = Exception

    pyd_mod = types.ModuleType("pydantic")
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
    pyd_mod.BaseModel = BaseModel

    sys.modules.pop("requests", None)
    sys.modules["fastapi"] = fastapi_mod
    sys.modules["pydantic"] = pyd_mod

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(tmp_path))
    try:
        main = importlib.import_module("orchestrator.main")
        importlib.reload(main)
        os.environ["LLM_SERVER_URL"] = llm_url
        os.environ["TTS_SERVER_URL"] = tts_url
        app = main.app
        handler = app.endpoint
        request_obj = main.StoryRequest(prompt="P", language="en", style="fun")
        result = handler(request_obj)
        out_dir = repo_root / "outputs"
        if out_dir.exists():
            import shutil
            shutil.rmtree(out_dir)
    finally:
        sys.path.remove(str(tmp_path))
        sys.path.remove(str(repo_root))
        sys.modules.pop("fastapi", None)
        sys.modules.pop("pydantic", None)
    return result


def test_api_response(tmp_path):
    llm_server, llm_thread, llm_url = _start_server(_LLMHandler)
    tts_server, tts_thread, tts_url = _start_server(_TTSHandler)
    try:
        result = _load_app(tmp_path, llm_url, tts_url)
    finally:
        llm_server.shutdown()
        llm_thread.join()
        tts_server.shutdown()
        tts_thread.join()

    assert result["text"] == "This is a test story."
    assert result["audio_base64"] == base64.b64encode(b"TESTMP3").decode()

