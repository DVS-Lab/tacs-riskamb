from config import load_config
from triggers import MarkerLogger


def test_task_marker_logger_works_without_pylsl(tmp_path, monkeypatch):
    import triggers

    monkeypatch.setattr(triggers, "pylsl", None)
    config = load_config()["triggers"]
    config["lsl_enabled"] = True
    logger = MarkerLogger(tmp_path / "markers.csv", config)
    assert logger.lsl_active is False
    logger.send("run_start")
    logger.close()
    assert "run_start" in (tmp_path / "markers.csv").read_text(encoding="utf-8")

