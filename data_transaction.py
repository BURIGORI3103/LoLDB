"""チャンピオン更新の中断を記録し、旧ファイルをまとめて復元する。"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

from tqdm import tqdm


JOURNAL_NAME = ".loldb-update"
LOCK_NAME = ".loldb-update.lock"


def json_bytes(value, *, trailing_newline=False):
    result = json.dumps(value, ensure_ascii=False, indent=2)
    return (result + ("\n" if trailing_newline else "")).encode("utf-8")


def revision(path):
    """ファイルの存在と内容を比較できる値にする。"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


@contextmanager
def update_lock(root):
    """同じチェックアウトで参加する処理を直列化する。"""
    lock_path = root / LOCK_NAME
    with lock_path.open("a+b") as lock:
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def require_recovered(root):
    if (root / JOURNAL_NAME / "pending.json").exists():
        raise RuntimeError("中断したデータ更新があります。先に python merge_data.py --recover を実行してください。")


def _atomic_write(path, data):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temp_path = Path(output.name)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _target(root, name):
    relative = PurePosixPath(name)
    if (relative.is_absolute() or len(relative.parts) != 2
            or relative.parts[0] not in {"champions_data", "strategy_data", "merged_data", "data", "docs"}
            or re.fullmatch(r"[A-Za-z0-9_.-]+\.json", relative.name) is None):
        raise ValueError("更新対象のJSONパスが不正です")
    target = root.joinpath(*relative.parts)
    if target.parent.resolve() != target.parent or target.is_symlink():
        raise ValueError("リンクをデータ更新に使用できません")
    return target


def _restore(root, journal):
    marker = journal / "pending.json"
    entries = json.loads(marker.read_text(encoding="utf-8"))
    files = []
    seen = set()
    for index, entry in enumerate(entries):
        name, old_hash, new_hash = entry
        target = _target(root, name)
        if target in seen:
            raise ValueError("復旧記録のパスが重複しています")
        seen.add(target)
        current = revision(target)
        if current not in (old_hash, new_hash):
            raise RuntimeError(f"更新中に別の変更を検出しました: {name}")
        backup = journal / f"{index}.old"
        if old_hash is not None and revision(backup) != old_hash:
            raise RuntimeError(f"復旧用のデータが欠損または破損しています: {name}")
        files.append((target, current, old_hash, backup))
    for target, current, old_hash, backup in tqdm(reversed(files), total=len(files), desc="旧データを復元"):
        if current == old_hash:
            continue
        if revision(target) != current:
            raise RuntimeError(f"復旧中に別の変更を検出しました: {target.name}")
        if old_hash is None:
            target.unlink()
        else:
            _atomic_write(target, backup.read_bytes())
    marker.unlink()


def _recover_locked(root):
    journal = root / JOURNAL_NAME
    if journal.is_symlink() or journal.resolve() != journal:
        raise ValueError("復旧ディレクトリがリンクです")
    if not journal.exists():
        return False
    marker = journal / "pending.json"
    pending = marker.exists()
    if pending:
        _restore(root, journal)
    shutil.rmtree(journal)
    return pending


def recover(root):
    with update_lock(root):
        return _recover_locked(root)


def publish(root, data, *, expected=None):
    """全出力を準備してから置換し、完了前の中断では旧版へ戻す。"""
    root = root.resolve()
    with update_lock(root):
        _recover_locked(root)
        if expected is not None:
            path, before = expected
            if revision(path) != before:
                raise RuntimeError("処理開始後にマスターが更新されました。最初から実行してください。")
        journal = root / JOURNAL_NAME
        journal.mkdir()
        marker = journal / "pending.json"
        entries = []
        seen = set()
        for index, (path, content) in enumerate(tqdm(data, total=len(data), desc="更新を準備")):
            name = path.relative_to(root).as_posix()
            target = _target(root, name)
            if target in seen:
                raise ValueError(f"更新対象のパスが重複しています: {name}")
            seen.add(target)
            old_hash = revision(target)
            if old_hash is not None:
                backup = journal / f"{index}.old"
                _atomic_write(backup, target.read_bytes())
                if revision(backup) != old_hash:
                    raise RuntimeError(f"バックアップ中に別の変更を検出しました: {name}")
            _atomic_write(journal / f"{index}.new", content)
            entries.append((name, old_hash, hashlib.sha256(content).hexdigest()))
        _atomic_write(marker, json.dumps(entries, ensure_ascii=False).encode("utf-8"))
        try:
            for index, (name, old_hash, _) in enumerate(tqdm(entries, desc="検証済みJSON保存")):
                target = _target(root, name)
                if revision(target) != old_hash:
                    raise RuntimeError(f"置換前に別の変更を検出しました: {name}")
                os.replace(journal / f"{index}.new", target)
            marker.unlink()
        except BaseException:
            _restore(root, journal)
            raise
        finally:
            if not marker.exists():
                shutil.rmtree(journal)
