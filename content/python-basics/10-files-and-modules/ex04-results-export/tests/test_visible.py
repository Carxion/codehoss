import json


def test_example(tmp_path):
    from main import export_results

    source, target = tmp_path / "s.json", tmp_path / "r.csv"
    source.write_text(json.dumps([{"name": "Ana", "score": 81}, {"name": "Ben", "score": 45}]))
    assert export_results(source, target) == 2
    rows = target.read_text().splitlines()
    assert rows == ["name,score,result", "Ana,81,pass", "Ben,45,fail"], f"The CSV holds {rows}"
