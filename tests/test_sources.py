import sys
from pathlib import Path
import types

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

requests_stub = types.SimpleNamespace()
def _fake_get(url, headers=None):
    raise AssertionError("should be patched")
requests_stub.get = _fake_get
sys.modules['requests'] = requests_stub

from orchestrator import sources


def test_fetch_wikipedia_extract(monkeypatch):
    captured = {}

    def fake_get(url, headers=None):
        captured['url'] = url
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {'extract': 'Info about place'}
        return Resp()

    monkeypatch.setattr(sources.requests, 'get', fake_get)
    result = sources.fetch_wikipedia_extract('Berlin')
    assert 'Berlin' in captured['url']
    assert result == 'Info about place'


def test_fetch_wikivoyage_extract(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None):
        captured['url'] = url
        captured['params'] = params
        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"query": {"pages": {"1": {"extract": "Travel info"}}}}

        return Resp()

    monkeypatch.setattr(sources.requests, 'get', fake_get)
    result = sources.fetch_wikivoyage_extract('Berlin')
    assert captured['params']['titles'] == 'Berlin'
    assert result == 'Travel info'
