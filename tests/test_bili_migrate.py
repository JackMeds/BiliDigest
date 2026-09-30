from pathlib import Path

from tools.bili_migrate import migrate_output_tree


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_migration_copies_legacy_outputs_then_renames_source(tmp_path):
    root = tmp_path / "repo"
    old_output = root / "output"
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "docs"

    write(old_output / "bilidigest" / "2026-05-18" / "a.md", "transcript")
    write(old_output / "bilidigest" / "reports" / "watch-later" / "r.md", "report")
    write(old_output / "bilidigest" / "site" / "index.html", "site")
    write(old_output / "bilidigest" / "cache" / "watch-later.jsonl", "{}\n")
    write(old_output / "bilidigest" / "snapshots" / "watch-later.json", "{}")
    write(old_output / "bilidigest" / "state" / "watch-later.json", "{}")
    write(old_output / "feishu-wiki-run-20260519" / "manifest.json", "{}")

    result = migrate_output_tree(
        root=root,
        data_dir=data_dir,
        cache_dir=cache_dir,
        output_dir=output_dir,
        stamp="20260528-120000",
    )

    assert result["status"] == "migrated"
    assert (output_dir / "legacy-output" / "bilidigest" / "2026-05-18" / "a.md").read_text() == "transcript"
    assert (output_dir / "legacy-output" / "bilidigest" / "reports" / "watch-later" / "r.md").exists()
    assert (output_dir / "legacy-output" / "bilidigest" / "site" / "index.html").exists()
    assert (output_dir / "legacy-output" / "feishu-wiki-run-20260519" / "manifest.json").exists()
    assert (cache_dir / "bilidigest" / "cache" / "watch-later.jsonl").exists()
    assert (cache_dir / "bilidigest" / "snapshots" / "watch-later.json").exists()
    assert (data_dir / "state" / "watch-later.json").exists()
    assert not old_output.exists()
    assert (root / "output.migrated-20260528-120000").exists()


def test_migration_is_noop_when_legacy_output_missing(tmp_path):
    result = migrate_output_tree(
        root=tmp_path / "repo",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "docs",
        stamp="20260528-120000",
    )

    assert result["status"] == "missing"


def test_migration_ignores_missing_source_sections_when_destination_has_files(tmp_path):
    root = tmp_path / "repo"
    old_output = root / "output"
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "docs"

    write(old_output / "bilidigest" / "cache" / "watch-later.jsonl", "{}\n")
    write(output_dir / "legacy-output" / "bilidigest" / "reports" / "old.md", "existing")

    result = migrate_output_tree(
        root=root,
        data_dir=data_dir,
        cache_dir=cache_dir,
        output_dir=output_dir,
        stamp="20260528-120000",
    )

    assert result["status"] == "migrated"
    assert (output_dir / "legacy-output" / "bilidigest" / "reports" / "old.md").read_text() == "existing"
    assert (cache_dir / "bilidigest" / "cache" / "watch-later.jsonl").exists()
    assert (root / "output.migrated-20260528-120000").exists()
