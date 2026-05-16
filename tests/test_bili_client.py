import pytest

from tools.bili_client import BiliClient, LoginRequired, RiskControl, load_cookies


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {"code": 0, "data": {}}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}
        self.cookies = {}

    def get(self, *args, **kwargs):
        return self.response


def test_request_json_stops_on_http_412():
    client = BiliClient(cookies={"SESSDATA": "x"}, delay=0)
    client.session = FakeSession(FakeResponse(status_code=412))

    with pytest.raises(RiskControl):
        client.request_json("https://example.test")


def test_request_json_stops_on_login_required():
    client = BiliClient(cookies={"SESSDATA": "x"}, delay=0)
    client.session = FakeSession(FakeResponse(body={"code": -101, "message": "账号未登录"}))

    with pytest.raises(LoginRequired):
        client.request_json("https://example.test")


def test_request_json_stops_on_bilibili_risk_code():
    client = BiliClient(cookies={"SESSDATA": "x"}, delay=0)
    client.session = FakeSession(FakeResponse(body={"code": -352, "message": "风控"}))

    with pytest.raises(RiskControl):
        client.request_json("https://example.test")


def test_load_cookies_reads_explicit_session_file(tmp_path):
    session = tmp_path / "session.json"
    session.write_text('{"SESSDATA": "abc", "empty": null}', encoding="utf-8")

    assert load_cookies(session) == {"SESSDATA": "abc"}
