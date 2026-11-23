import asyncio
import os
import sys
from pathlib import Path

import pytest

from agno.context.wiki import git_ops


@pytest.mark.skipif(sys.platform == "win32", reason="fake git is a POSIX script")
async def test_run_cancelled_stops_git(monkeypatch, tmp_path: Path):
    """Cancelling a wiki sync must not leave git running in the background."""
    pid_file = tmp_path / "git.pid"
    fake_git = tmp_path / "bin" / "git"
    fake_git.parent.mkdir()
    fake_git.write_text(
        f"#!{sys.executable}\nimport os, time\nopen({str(pid_file)!r}, 'w').write(str(os.getpid()))\ntime.sleep(30)\n"
    )
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_git.parent}{os.pathsep}{os.environ['PATH']}")

    task = asyncio.ensure_future(git_ops.run(["fetch"], cwd=tmp_path))
    for _ in range(100):
        if pid_file.exists() and pid_file.read_text():
            break
        await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)
