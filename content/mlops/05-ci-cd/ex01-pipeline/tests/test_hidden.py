from hoss_checks import lab_dir, sh


def test_feature_pipeline_runs():
    out = sh(f"cd {lab_dir()} && python ci.py --branch feature/x", timeout=180)
    assert out.returncode == 0, f"the feature pipeline failed: {out.stdout[-600:]}"
    assert "metrics OK" in out.stdout, (
        "quality-gate should run check_metrics.py (and get model/ from train)"
    )
    assert "Pipeline passed" in out.stdout
