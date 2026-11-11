import csv
import json


def export_results(json_path, csv_path):
    # TODO: read the students from json_path
    # TODO: write name,score,result rows (with a header) to csv_path
    # TODO: return how many students were written
    return 0


if __name__ == "__main__":
    with open("students.json", "w", encoding="utf-8") as f:
        json.dump([{"name": "Ana", "score": 81}, {"name": "Ben", "score": 45}], f)
    print(export_results("students.json", "results.csv"), "written")
    with open("results.csv", encoding="utf-8") as f:
        print(f.read())
