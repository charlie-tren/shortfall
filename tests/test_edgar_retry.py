import http.client
import io
import urllib.error

import pytest

import edgar


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen(outcomes):
    calls = []

    def fake(req, timeout):
        calls.append(req.full_url)
        out = outcomes[len(calls) - 1]
        if isinstance(out, Exception):
            raise out
        return _Resp(out)
    return fake, calls


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(edgar.time, "sleep", lambda s: None)


def test_truncated_response_is_retried(monkeypatch):
    fake, calls = _urlopen([http.client.IncompleteRead(b""), b'{"data": []}'])
    monkeypatch.setattr(edgar.urllib.request, "urlopen", fake)
    assert edgar._get("https://x") == {"data": []}
    assert len(calls) == 2


def test_server_error_is_retried(monkeypatch):
    err = urllib.error.HTTPError("https://x", 503, "busy", {}, None)
    fake, calls = _urlopen([err, b"{}"])
    monkeypatch.setattr(edgar.urllib.request, "urlopen", fake)
    assert edgar._get("https://x") == {}


def test_404_is_not_retried(monkeypatch):
    err = urllib.error.HTTPError("https://x", 404, "absent", {}, None)
    fake, calls = _urlopen([err, b"{}"])
    monkeypatch.setattr(edgar.urllib.request, "urlopen", fake)
    with pytest.raises(urllib.error.HTTPError):
        edgar._get("https://x")
    assert len(calls) == 1


def test_gives_up_after_the_last_attempt(monkeypatch):
    fake, calls = _urlopen([ConnectionResetError()] * edgar.RETRIES)
    monkeypatch.setattr(edgar.urllib.request, "urlopen", fake)
    with pytest.raises(ConnectionResetError):
        edgar._get("https://x")
    assert len(calls) == edgar.RETRIES
