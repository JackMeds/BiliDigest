import json

from tools import bili_auth


class FakeResponse:
    def __init__(self, body, cookies=None):
        self._body = body
        self.cookies = FakeCookies(cookies or {})

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class FakeCookies:
    def __init__(self, cookies):
        self._cookies = cookies

    def get_dict(self):
        return dict(self._cookies)


def test_create_login_request_writes_agent_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(bili_auth, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        bili_auth.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            {"data": {"url": "https://passport.example/qr", "qrcode_key": "qr-key"}}
        ),
    )

    payload = bili_auth.create_login_request()

    assert payload["status"] == "login_required"
    assert payload["login_url"] == "https://passport.example/qr"
    assert payload["qrcode_key"] == "qr-key"
    assert payload["qr_image"] == str(tmp_path / "login_qr.png")
    assert (tmp_path / "login_qr.png").exists()
    assert "auth poll qr-key" in payload["poll_command"]


def test_poll_once_saves_cookies_on_success(monkeypatch):
    saved = {}
    login_url = "https://example/?" + "refresh_token" + "=refresh-test"
    monkeypatch.setattr(bili_auth, "save_cookies", lambda cookies: saved.update(cookies))
    monkeypatch.setattr(
        bili_auth.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            {"data": {"code": 0, "url": login_url}},
            {"SESSDATA": "session123"},
        ),
    )

    payload = bili_auth.poll_once("qr-key")

    assert payload["status"] == "logged_in"
    assert saved == {"SESSDATA": "session123", "refresh_token": "refresh-test"}


def test_poll_once_reports_scanned(monkeypatch):
    monkeypatch.setattr(
        bili_auth.requests,
        "get",
        lambda *args, **kwargs: FakeResponse({"data": {"code": 86090}}),
    )

    payload = bili_auth.poll_once("qr-key")

    assert payload["status"] == "scanned"


def test_json_login_no_wait_prints_payload(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(bili_auth, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        bili_auth.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            {"data": {"url": "https://passport.example/qr", "qrcode_key": "qr-key"}}
        ),
    )

    code = bili_auth.login(as_json=True, no_wait=True)
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert output["status"] == "login_required"
    assert output["qrcode_key"] == "qr-key"
