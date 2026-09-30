import importlib

from tools import bili_paths


def reload_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("BILIDIGEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BILIDIGEST_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("BILIDIGEST_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("BILIDIGEST_OUTPUT_DIR", str(tmp_path / "docs"))
    return importlib.reload(bili_paths)


def test_env_overrides_define_runtime_dirs(monkeypatch, tmp_path):
    paths = reload_paths(monkeypatch, tmp_path)

    assert paths.DATA_DIR == tmp_path / "data"
    assert paths.CACHE_DIR == tmp_path / "cache"
    assert paths.LOG_DIR == tmp_path / "logs"
    assert paths.OUTPUT_DIR == tmp_path / "docs"
    assert paths.SESSION_FILE == tmp_path / "data" / "session.json"
    assert paths.QR_IMAGE_PATH == tmp_path / "cache" / "login_qr.png"


def test_dated_output_dir_lives_under_documents_output(monkeypatch, tmp_path):
    paths = reload_paths(monkeypatch, tmp_path)

    out_dir = paths.dated_output_dir("2026-05-28")

    assert out_dir == tmp_path / "docs" / "bilidigest" / "2026-05-28"
    assert out_dir.exists()


def test_app_support_state_and_cache_are_separated(monkeypatch, tmp_path):
    paths = reload_paths(monkeypatch, tmp_path)

    assert paths.batch_state_dir() == tmp_path / "data" / "state"
    assert paths.batch_cache_dir() == tmp_path / "cache" / "bilidigest" / "cache"
    assert paths.batch_snapshot_dir() == tmp_path / "cache" / "bilidigest" / "snapshots"
    assert paths.stable_lock_path() == tmp_path / "data" / "state" / "watch-later.lock"
    assert paths.stable_log_path("run-1.log") == tmp_path / "logs" / "run-1.log"


def test_legacy_download_helpers_use_cache_dir(monkeypatch, tmp_path):
    reload_paths(monkeypatch, tmp_path)
    from tools import download, utils

    importlib.reload(utils)
    importlib.reload(download)

    assert utils.get_output_dir() == tmp_path / "cache" / "downloads"
    cookie_path = download.create_temp_cookie_file({"SESSDATA": "abc"})

    assert cookie_path == tmp_path / "cache" / ".temp_cookies.txt"
    assert cookie_path.read_text(encoding="utf-8").startswith("# Netscape HTTP Cookie File")
