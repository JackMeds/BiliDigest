import filecmp
import shutil
from pathlib import Path
from typing import Any

from . import bili_paths


def _copytree_merge(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    for path in src.rglob("*"):
        if path.is_dir():
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _file_count_and_size(root: Path) -> tuple[int, int]:
    if not root.exists():
        return (0, 0)
    if root.is_file():
        return (1, root.stat().st_size)
    count = 0
    size = 0
    for path in root.rglob("*"):
        if path.is_file():
            count += 1
            size += path.stat().st_size
    return count, size


def _verify_copy(src: Path, dst: Path) -> None:
    src_count, src_size = _file_count_and_size(src)
    dst_count, dst_size = _file_count_and_size(dst)
    if src_count != dst_count or src_size != dst_size:
        raise RuntimeError(f"Copy verification failed: {src} -> {dst}")
    if src.is_file() and dst.exists() and not filecmp.cmp(src, dst, shallow=False):
        raise RuntimeError(f"File verification failed: {src} -> {dst}")


def _copy_and_verify(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    _copytree_merge(src, dst)
    _verify_copy(src, dst)
    return True


def _rename_without_overwrite(path: Path, target: Path) -> Path:
    if not target.exists():
        path.rename(target)
        return target
    index = 1
    while True:
        candidate = target.with_name(f"{target.name}-{index}")
        if not candidate.exists():
            path.rename(candidate)
            return candidate
        index += 1


def migrate_output_tree(
    *,
    root: Path = bili_paths.ROOT_DIR,
    data_dir: Path = bili_paths.DATA_DIR,
    cache_dir: Path = bili_paths.CACHE_DIR,
    output_dir: Path = bili_paths.OUTPUT_DIR,
    stamp: str,
) -> dict[str, Any]:
    old_output = root / "output"
    if not old_output.exists():
        return {"status": "missing", "old_output": str(old_output)}

    moved: list[dict[str, str]] = []

    legacy_root = output_dir / "legacy-output"
    old_bilidigest = old_output / "bilidigest"
    for name in ("reports", "site"):
        src = old_bilidigest / name
        dst = legacy_root / "bilidigest" / name
        if _copy_and_verify(src, dst):
            moved.append({"from": str(src), "to": str(dst)})
    if old_bilidigest.exists():
        for src in sorted(old_bilidigest.glob("2026-*")):
            dst = legacy_root / "bilidigest" / src.name
            _copy_and_verify(src, dst)
            moved.append({"from": str(src), "to": str(dst)})

    for src in sorted(old_output.glob("feishu-*")):
        dst = legacy_root / src.name
        _copy_and_verify(src, dst)
        moved.append({"from": str(src), "to": str(dst)})

    cache_src = old_bilidigest / "cache"
    cache_dst = cache_dir / "bilidigest" / "cache"
    if _copy_and_verify(cache_src, cache_dst):
        moved.append({"from": str(cache_src), "to": str(cache_dst)})

    snapshots_src = old_bilidigest / "snapshots"
    snapshots_dst = cache_dir / "bilidigest" / "snapshots"
    if _copy_and_verify(snapshots_src, snapshots_dst):
        moved.append({"from": str(snapshots_src), "to": str(snapshots_dst)})

    state_src = old_bilidigest / "state"
    state_dst = data_dir / "state"
    if _copy_and_verify(state_src, state_dst):
        moved.append({"from": str(state_src), "to": str(state_dst)})

    renamed_to = _rename_without_overwrite(old_output, root / f"output.migrated-{stamp}")
    return {"status": "migrated", "renamed_to": str(renamed_to), "moved": moved}
