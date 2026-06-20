import os
import subprocess
import sys
from pathlib import Path


def test_auto_response_test_mode_completes_quickly(tmp_path):
    root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env.update({"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"})
    result = subprocess.run(
        [
            sys.executable, str(root / "code" / "main.py"), "--test", "--windowed",
            "--subject", "AUTO", "--session", "1", "--run", "1", "--seed", "99",
            "--auto-respond", "--skip-instructions", "--data-dir", str(tmp_path),
        ],
        cwd=root, env=env, timeout=20, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    events = list(tmp_path.glob("sub-AUTO/*_events.csv"))
    assert len(events) == 1
    assert len(events[0].read_text(encoding="utf-8").splitlines()) == 9

