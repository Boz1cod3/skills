#!/usr/bin/env python3
"""Run Autopilot headless through the Antigravity CLI (agy).

    python agy-run.py [--mode full|semi|interview|manual] [--depth strict|normal|deep]
                      [--project DIR] [--model M] [--effort low|medium|high|max]
                      [--conversation ID] [--output-format stream-json|text]
                      [--max-rounds N] [--ask-permissions] BRIEF...
    python agy-run.py --resume [--project DIR] ...       # continue a cut-off run

A finished turn is a finished `agy -p` process. agy keeps the process alive while background
subagents run (a ~30 min cap was observed), but a longer wave or a mode that ends its turn early
ends it before the run is done. The launcher then re-enters a bare `/autopilot` (the skill's own
resume, driven by .autopilot/state.js) until the run reports a new finishedAt. Before every resume
round it stops the run's dashboard server, otherwise preflight would take the live server for
"the run is going on in another window" and stop to ask.

Headless runs cannot answer permission prompts, so tool permissions are auto-approved unless
--ask-permissions is given. agy is always asked for stream-json; --output-format only chooses
what is printed (raw events, or the final response). `full` is the only mode designed to run
without a human; the others may stop to ask.

Exit codes: 0 finished, 1 agent error, 2 round cap, 3 no progress, 4 refused (unfinished run
without --resume, or --resume with nothing to resume), 127 agy not found, 130 interrupted.
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
    if explicit:
        print("ANTIGRAVITY_BIN_PATH=%s does not exist — looking elsewhere" % explicit, file=sys.stderr)
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


def run_round(exe, args, cwd, show="stream-json"):
    kw = {} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen([exe] + args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
    lines = []
    try:
        for line in proc.stdout:
            if show == "stream-json":
                sys.stdout.write(line)
                sys.stdout.flush()
            lines.append(line)
        proc.wait()
    except BaseException:
        kill_tree(proc)
        raise
    result = parse_result(lines)
    if show == "text" and result:
        print(result.get("response") or "")
    return proc.returncode, result


def stop_server(project):
    """Stop the run's dashboard server synchronously (ap.py --stop-now waits ~12 s first)."""
    ap = os.path.join(project, ".autopilot", "ap.py")
    if os.path.isfile(ap):
        try:
            subprocess.run([sys.executable, ap, "--stop-now"], cwd=project, capture_output=True,
                           timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _positive(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return n


def main(argv=None, run=run_round, find=find_agy, stop=stop_server):
    p = argparse.ArgumentParser(description="Run Autopilot headless through agy")
    p.add_argument("brief", nargs="*", help="what to build, or a path to brief.md")
    p.add_argument("--resume", action="store_true", help="continue the unfinished run in --project")
    p.add_argument("--mode", default="semi", choices=MODES)
    p.add_argument("--depth", default="normal", choices=DEPTHS)
    p.add_argument("--project", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--effort", default="high", choices=EFFORTS)
    p.add_argument("--conversation", default=None)
    p.add_argument("--output-format", default="stream-json", choices=("stream-json", "text"),
                   help="what to print; agy itself always streams json")
    p.add_argument("--max-rounds", type=_positive, default=12)
    p.add_argument("--ask-permissions", action="store_true",
                   help="do not auto-approve tool permissions (headless will then deny every command)")
    a = p.parse_args(argv)
    project = os.path.abspath(a.project or os.getcwd())
    brief = " ".join(a.brief) or None
    first = read_state(project)
    unfinished = bool(first) and not first.get("finishedAt")
    if a.resume and not unfinished:
        print("--resume: no unfinished run in %s" % project, file=sys.stderr)
        return 4
    if not a.resume and not brief:
        print("give a brief, or --resume to continue an unfinished run", file=sys.stderr)
        return 4
    if not a.resume and unfinished:
        print("an unfinished run is in %s — continue it with --resume" % project, file=sys.stderr)
        return 4
    exe = find()
    if not exe:
        print("agy not found: set ANTIGRAVITY_BIN_PATH or put agy on PATH", file=sys.stderr)
        return 127
    old_finish = first.get("finishedAt") if first else None
    try:
        for rnd in range(1, a.max_rounds + 1):
            bare = a.resume or rnd > 1
            if bare:
                stop(project)
            before = progress_stamp(project)
            args = build_args(None if bare else brief, a.mode, a.depth, project, a.model, a.effort,
                              a.conversation if rnd == 1 else None, "stream-json",
                              skip_permissions=not a.ask_permissions)
            code, result = run(exe, args, project, a.output_format)
            state = read_state(project)
            finish = state.get("finishedAt") if state else None
            if finish and finish != old_finish:
                return 0
            if result is None or result.get("status") != "SUCCESS":
                print("round %d: agent error (exit %s)" % (rnd, code), file=sys.stderr)
                return code or 1
            if bare and progress_stamp(project) == before:
                print("round %d: no progress — the agent is probably waiting for an answer" % rnd,
                      file=sys.stderr)
                return 3
        print("round cap (%d) reached, run not finished" % a.max_rounds, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
