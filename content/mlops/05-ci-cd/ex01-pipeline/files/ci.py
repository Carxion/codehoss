"""Run a .gitlab-ci.yml pipeline here, the way GitLab would, minus the servers.

    python ci.py                      # the pipeline for the main branch
    python ci.py --branch feature/x   # another branch: rules decide which jobs run
    python ci.py --plan               # list the jobs and whether each would run
    python ci.py --manual             # also run jobs marked when: manual

Each job starts from a clean copy of the project (paths in .gitignore are left out, as
they would be in git), plus the artifacts of the jobs it depends on: every job in an
earlier stage, or only the jobs listed in its needs:. Supported keys: stages, variables,
script, before_script, after_script, artifacts:paths, needs, rules (if / when),
when: manual. image: is ignored: jobs run in this lab, where the tools are installed.
"""

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

RESERVED = {
    "stages",
    "variables",
    "default",
    "workflow",
    "include",
    "image",
    "services",
    "before_script",
    "after_script",
    "cache",
}
WORK = Path(tempfile.gettempdir()) / "ci"


def load(path):
    config = yaml.safe_load(Path(path).read_text()) or {}
    stages = config.get("stages", ["build", "test", "deploy"])
    jobs = {}
    for name, job in config.items():
        if name in RESERVED or name.startswith(".") or not isinstance(job, dict):
            continue
        if "script" not in job:
            sys.exit(f"job {name} has no script:")
        if job.get("stage", "test") not in stages:
            sys.exit(f"job {name}: stage {job.get('stage')!r} isn't in stages: {stages}")
        jobs[name] = job
    jobs = dict(sorted(jobs.items(), key=lambda kv: stages.index(kv[1].get("stage", "test"))))
    return config, stages, jobs


def expand(text, env):
    return re.sub(r"\$\{?(\w+)\}?", lambda m: env.get(m[1], ""), str(text))


def condition(expr, env):
    """GitLab's rules:if subset: $A == "x", $A != "x", $A =~ /re/, $A, joined by && and ||."""

    def one(part):
        part = part.strip()
        if m := re.fullmatch(r'\$(\w+)\s*(==|!=)\s*["\']?([^"\']*)["\']?', part):
            same = env.get(m[1], "") == m[3]
            return same if m[2] == "==" else not same
        if m := re.fullmatch(r"\$(\w+)\s*=~\s*/(.*)/", part):
            return re.search(m[2], env.get(m[1], "")) is not None
        if m := re.fullmatch(r"\$(\w+)", part):
            return bool(env.get(m[1]))
        sys.exit(f"ci.py doesn't understand the rule: {part}")

    return any(all(one(p) for p in alt.split("&&")) for alt in expr.split("||"))


def decide(job, env, manual):
    """("run" | "skip", reason)"""
    when = job.get("when", "on_success")
    if "rules" in job:
        for rule in job["rules"]:
            if "if" not in rule or condition(rule["if"], env):
                when = rule.get("when", "on_success")
                break
        else:
            return "skip", "no rule matched"
    if when == "never":
        return "skip", "when: never"
    if when == "manual" and not manual:
        return "skip", "manual (run with --manual)"
    return "run", ""


def ignored(rel, patterns):
    parts = rel.split("/")
    for pattern in patterns:
        pattern = pattern.strip().rstrip("/")
        if pattern and any(fnmatch.fnmatch(p, pattern) for p in parts):
            return True
    return False


def checkout(project, target, patterns):
    for path in project.rglob("*"):
        rel = path.relative_to(project).as_posix()
        if path.is_file() and not ignored(rel, patterns + [".git"]):
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def run_job(name, job, config, env, project, patterns, artifacts, done):
    folder = WORK / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    checkout(project, folder, patterns)
    sources = job["needs"] if "needs" in job else [j for j in done]
    for source in sources:
        source = source["job"] if isinstance(source, dict) else source
        if (artifacts / source).is_dir():
            shutil.copytree(artifacts / source, folder, dirs_exist_ok=True)
    lines = [*config.get("before_script", []), *job.get("before_script", []), *job["script"]]
    script = "set -e\n" + "".join(
        f"printf '%s\\n' {shlex.quote('$ ' + str(line))}\n{line}\n" for line in lines
    )
    job_env = {
        **env,
        **{k: expand(v, env) for k, v in job.get("variables", {}).items()},
        "CI_JOB_NAME": name,
        "CI_PROJECT_DIR": str(folder),
    }
    ok = subprocess.run(["bash", "-c", script], cwd=folder, env=job_env).returncode == 0
    for line in job.get("after_script", []):
        subprocess.run(["bash", "-c", str(line)], cwd=folder, env=job_env)
    if ok:
        keep = artifacts / name
        for pattern in job.get("artifacts", {}).get("paths", []):
            for found in folder.glob(expand(pattern, job_env).rstrip("/")):
                dest = keep / found.relative_to(folder)
                if found.is_dir():
                    shutil.copytree(found, dest, dirs_exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(found, dest)
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch", default="main")
    parser.add_argument("--plan", action="store_true", help="show the jobs as JSON, run nothing")
    parser.add_argument("--manual", action="store_true", help="also run when: manual jobs")
    parser.add_argument("--file", default=".gitlab-ci.yml")
    args = parser.parse_args()
    if not Path(args.file).exists():
        sys.exit(f"no {args.file} here")
    config, stages, jobs = load(args.file)
    env = {
        **os.environ,
        "CI": "true",
        "CI_COMMIT_BRANCH": args.branch,
        "CI_DEFAULT_BRANCH": "main",
        "CI_PIPELINE_ID": str(int(time.time()) % 100000),
        "CI_COMMIT_SHORT_SHA": "0000000",
    }
    env.update({k: expand(v, env) for k, v in config.get("variables", {}).items()})
    plan = [
        {
            "job": name,
            "stage": job.get("stage", "test"),
            "decision": decide(job, env, args.manual)[0],
            "reason": decide(job, env, args.manual)[1],
        }
        for name, job in jobs.items()
    ]
    if args.plan:
        print(json.dumps({"stages": stages, "jobs": plan}, indent=2))
        return 0

    project = Path.cwd()
    patterns = Path(".gitignore").read_text().splitlines() if Path(".gitignore").exists() else []
    shutil.rmtree(WORK, ignore_errors=True)
    artifacts = WORK / ".artifacts"
    artifacts.mkdir(parents=True)
    done, results = [], []
    for stage in stages:
        for item in [p for p in plan if p["stage"] == stage]:
            name = item["job"]
            if item["decision"] == "skip":
                print(f"\n--- {name} ({stage}): skipped, {item['reason']}")
                results.append((name, "skipped"))
                continue
            print(f"\n--- {name} ({stage})", flush=True)
            if not run_job(name, jobs[name], config, env, project, patterns, artifacts, done):
                print(f"\nJob {name} failed: the pipeline stops here.")
                results.append((name, "failed"))
                print("\n".join(f"  {n}: {r}" for n, r in results))
                print("Pipeline failed")
                return 1
            print(f"Job {name} passed")
            results.append((name, "passed"))
            done.append(name)
    print("\n" + "\n".join(f"  {n}: {r}" for n, r in results))
    print("Pipeline passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
