#!/usr/bin/env python3
"""Run Autopilot headless through the Antigravity CLI (agy).

    python agy-run.py [--mode full|semi|interview|manual] [--depth strict|normal|deep]
                      [--project DIR] [--model M] [--effort low|medium|high|max]
                      [--conversation ID] [--output-format text|json|stream-json]
                      [--max-rounds N] [--ask-permissions] BRIEF...

A finished turn is a finished `agy -p` process, and Autopilot ends its turn to wait for
subagents, so this launcher re-enters a bare `/autopilot` (the skill's own resume, driven by
.autopilot/state.js) until the run reports finishedAt. Headless runs cannot answer permission
prompts, so tool permissions are auto-approved unless --ask-permissions is given.
`full` is the only mode that does not stop to ask the user; the others stall without a human.

Exit codes: 0 finished, 1 agent error, 2 round cap, 3 no progress, 127 agy not found, 130 interrupted.
Binary lookup: ANTIGRAVITY_BIN_PATH, PATH, %LOCALAPPDATA%\\agy\\bin\\agy.exe, ~/.local/bin/agy.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys

MODES = ("full", "semi", "interview", "manual")
DEPTHS = ("strict", "normal", "deep")
EFFORTS = ("low", "medium", "high", "max")
FORMATS = ("text", "json", "stream-json")


def find_agy(env=None, which=shutil.which, exists=os.path.isfile, home=None):
    env = os.environ if env is None else env
    explicit = env.get("ANTIGRAVITY_BIN_PATH")
    if explicit and exists(explicit):
        return explicit
    found = which("agy")
    if found:
        return found
    candidates = []
    if env.get("LOCALAPPDATA"):
        candidates.append(os.path.join(env["LOCALAPPDATA"], "agy", "bin", "agy.exe"))
    candidates.append(os.path.join(home or os.path.expanduser("~"), ".local", "bin", "agy"))
    for path in candidates:
        if exists(path):
            return path
    return None


def build_args(brief=None, mode="semi", depth="normal", project=None, model=None, effort="high",
               conversation=None, output_format="stream-json", skip_permissions=True):
    for value, allowed, name in ((mode, MODES, "mode"), (depth, DEPTHS, "depth"),
                                 (effort, EFFORTS, "effort"), (output_format, FORMATS, "output-format")):
        if value not in allowed:
            raise ValueError("%s: %s — expected one of %s" % (name, value, ", ".join(allowed)))
    if brief is None:
        prompt = "/autopilot"
    else:
        prompt = " ".join(["/autopilot", mode] + ([depth] if depth != "normal" else []) + [brief])
    argv = ["-p", prompt, "--output-format", output_format, "--mode", "accept-edits", "--effort", effort]
    if model:
        argv += ["--model", model]
    if conversation:
        argv += ["--conversation", conversation]
    if project:
        argv += ["--add-dir", project]
    if skip_permissions:
        argv.append("--dangerously-skip-permissions")
    return argv


def read_state(project):
    path = os.path.join(project, ".autopilot", "state.js")
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        return json.loads(raw.split("=", 1)[1].strip().rstrip(";"))
    except (OSError, ValueError, IndexError):
        return None


def is_finished(project):
    state = read_state(project)
    return bool(state and state.get("finishedAt"))


def progress_stamp(project):
    state = read_state(project)
    return state.get("updatedAt") if state else None


def parse_result(lines):
    result = None
    for line in lines:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if isinstance(message, dict) and message.get("event") == "result":
            result = message.get("result")
    return result


def kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except OSError:
        proc.kill()


def run_round(exe, args, cwd):
    kw = {} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen([exe] + args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
    lines = []
    try:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lines.append(line)
        proc.wait()
    except KeyboardInterrupt:
        kill_tree(proc)
        raise
    return proc.returncode, parse_result(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="Run Autopilot headless through agy")
    p.add_argument("brief", nargs="+", help="what to build, or a path to brief.md")
    p.add_argument("--mode", default="semi", choices=MODES)
    p.add_argument("--depth", default="normal", choices=DEPTHS)
    p.add_argument("--project", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--effort", default="high", choices=EFFORTS)
    p.add_argument("--conversation", default=None)
    p.add_argument("--output-format", default="stream-json", choices=FORMATS)
    p.add_argument("--max-rounds", type=int, default=12)
    p.add_argument("--ask-permissions", action="store_true",
                   help="do not auto-approve tool permissions (headless will then deny every command)")
    a = p.parse_args(argv)
    exe = find_agy()
    if not exe:
        print("agy not found: set ANTIGRAVITY_BIN_PATH or put agy on PATH", file=sys.stderr)
        return 127
    project = os.path.abspath(a.project or os.getcwd())
    brief = " ".join(a.brief)
    try:
        for rnd in range(1, a.max_rounds + 1):
            before = progress_stamp(project)
            args = build_args(brief if rnd == 1 else None, a.mode, a.depth, project, a.model, a.effort,
                              a.conversation if rnd == 1 else None, a.output_format,
                              skip_permissions=not a.ask_permissions)
            code, result = run_round(exe, args, project)
            if is_finished(project):
                return 0
            if result is None or result.get("status") != "SUCCESS":
                print("round %d: agent error (exit %s)" % (rnd, code), file=sys.stderr)
                return code or 1
            if rnd > 1 and progress_stamp(project) == before:
                print("round %d: no progress — the agent is probably waiting for an answer" % rnd,
                      file=sys.stderr)
                return 3
        print("round cap (%d) reached, run not finished" % a.max_rounds, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
