import csv
import json


def export_results(json_path, csv_path):
    with open(json_path, encoding="utf-8") as f:
        students = json.load(f)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "score", "result"])
        for student in students:
            result = "pass" if student["score"] >= 50 else "fail"
            writer.writerow([student["name"], student["score"], result])
    return len(students)


if __name__ == "__main__":
    with open("students.json", "w", encoding="utf-8") as f:
        json.dump([{"name": "Ana", "score": 81}, {"name": "Ben", "score": 45}], f)
    print(export_results("students.json", "results.csv"), "written")
    with open("results.csv", encoding="utf-8") as f:
        print(f.read())
