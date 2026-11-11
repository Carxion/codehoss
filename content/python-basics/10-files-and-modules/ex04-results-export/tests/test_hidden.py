import csv
import json


def test_boundary_and_names_with_commas(tmp_path):
    from main import export_results

    students = [
        {"name": "Kai", "score": 50},
        {"name": "Lee, Jr.", "score": 49},
        {"name": "Mo", "score": 100},
    ]
    source, target = tmp_path / "s.json", tmp_path / "r.csv"
    source.write_text(json.dumps(students))
    assert export_results(source, target) == 3, "export_results should return 3"
    with open(target, newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [
        ["name", "score", "result"],
        ["Kai", "50", "pass"],
        ["Lee, Jr.", "49", "fail"],
        ["Mo", "100", "pass"],
    ], f"The CSV holds {rows}. Write rows with csv.writer so commas in names are quoted."


def test_empty_class(tmp_path):
    from main import export_results

    source, target = tmp_path / "s.json", tmp_path / "r.csv"
    source.write_text("[]")
    assert export_results(source, target) == 0
    assert target.read_text().splitlines() == ["name,score,result"], "Only the header row"
