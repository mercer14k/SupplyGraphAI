import json
import subprocess
import sys


def test_machine_readable_benchmark_outputs(tmp_path):
    subprocess.run(
        [
            sys.executable,
            "-m",
            "supplygraph.evaluation.benchmark",
            "--sizes",
            "1000",
            "--repeats",
            "2",
            "--output",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
    )
    result = json.loads((tmp_path / "results.json").read_text())
    assert result["evaluation"]["impact_precision"] == 1
    assert result["evaluation"]["impact_recall"] == 1
    assert result["evaluation"]["query_accuracy"] == 1
    assert result["performance"][0]["affected"] == 895
    assert result["performance"][0]["impact_p50_ms"] > 0
    assert (tmp_path / "performance.csv").read_text().startswith("nodes,edges,")
    assert "not proof of enterprise accuracy" in (tmp_path / "summary.md").read_text()
