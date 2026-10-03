# Multi-runtime Autopilot (Claude Code + Antigravity) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Autopilot skill run natively in Antigravity (IDE + `agy` CLI, Windows/PowerShell) without changing Claude Code behaviour.

**Architecture:** Shared phases stay untouched except one pointer line each. All host-specific behaviour moves into one file, `phases/runtime.md`, with a section per runtime; the agent selects its section from its own tool list and records it in `state.js` (`init --runtime`). A new `ap.py setup` command replaces the unix-only bootstrap for Antigravity. A small `tools/agy-run.py` launches Autopilot headless through `agy -p`, auto-approving permissions (headless cannot prompt) and re-entering a bare `/autopilot` (the skill's own resume) until `state.js` reports `finishedAt`, because a finished turn ends the `-p` process.

**Tech Stack:** Python 3 stdlib only (`unittest`, `subprocess`, `shutil`), Markdown, PowerShell 7 (`pwsh`).

**Spec:** `docs/superpowers/specs/2026-10-03-multi-runtime-autopilot-design.md`

## Global Constraints

- Python stdlib only; no new dependencies. Must run on Windows, macOS, Linux.
- Claude Code path text must not change, except one pointer line per phase file and the new `runtime.md` row in `SKILL.md`.
- No symlinks anywhere in new code (Windows).
- Code, identifiers, comments, new `.md` skill text: English. User-facing strings that already exist in `ap.py` stay Russian.
- Baseline: `python -m unittest tests.test_ap` = 24 tests OK. Never leave it red between commits.
- Repo root: `d:\ANTIGRAVITY\Autopilot`. Skill dir: `skills/autopilot`. Run all commands from the repo root.
- Commit locally after every task; do **not** push (the fork push is the owner's decision).

## File Structure

| File | Responsibility |
|---|---|
| `skills/autopilot/tools/ap.py` (modify) | add `cmd_setup`, `RUNTIMES`, `runtime` in state, early `setup` dispatch |
| `skills/autopilot/phases/runtime.md` (create) | the runtime contract: detection rule + `claude` / `antigravity` / `codex` sections |
| `skills/autopilot/SKILL.md` (modify) | list `runtime.md` in the phase table |
| `skills/autopilot/phases/{0-instruments,5-subagents,6-review,8-final}.md` (modify) | one pointer line each (+ Antigravity bootstrap/dashboard note in `0-instruments`) |
| `skills/autopilot/tools/agy-run.py` (create) | `find_agy`, `build_args`, `read_state`, `is_finished`, `parse_result`, `run_round` (resume loop), `main` |
| `tests/test_ap.py` (modify) | tests for `setup`, `--runtime`, runtime contract |
| `tests/test_agy_run.py` (create) | tests for `find_agy`, `build_args`, state reading, result parsing |
| `docs/antigravity.md` (create) | install, run, verified facts, known limits |
| `README.md`, `CHANGELOG.md` (modify) | short Antigravity section / entry |

---

### Task 0: Spike — verify the unverified (DONE 2026-10-03)

Results are recorded in `docs/antigravity.md` (created in this task). Summary: agent id `antigravity`; project path `.agents/skills/autopilot`; global path `~/.agents/skills/autopilot` (CLI-reported, not exercised in a live IDE session); `/autopilot` expands under `agy -p` (`init.expanded_commands`); `disable-model-invocation` is honoured; `agy` accepts the prompt via `-p` or stdin; headless without `--dangerously-skip-permissions` auto-denies every `run_command`; a turn that ends (e.g. to wait for a subagent) ends the whole `-p` process; `python3` on the owner's machine is the Store stub, `python`/`py -3` work; pwsh 7.6 supports `&&`, Windows PowerShell 5.1 does not.

- [x] **Step 1: Create `docs/antigravity.md` with the verified facts** (see the file in the repo; Task 5 appends the rest)
- [x] **Step 2: Commit** — `docs: Antigravity verified facts`

---

### Task 0b: Spike — can a headless run survive a wave? (blocks Task 3 wording and Task 4 loop limits)

**Why:** In `agy -p` a baseline `/autopilot semi …` run dispatched executor T01 via `invoke_subagent` and then ended its turn (as `phases/5-subagents.md` instructs). The process exited with `result.status = SUCCESS` and ticket 01 left `in-progress`. We need to know what happens to that subagent and whether a bare `/autopilot` (the skill's own resume, `phases/0-resume.md`) picks the run up.

**Files:**
- Modify: `docs/antigravity.md` (append a "Headless waves" section with the findings)

**Interfaces:**
- Produces: the answers to Q1–Q3 below; Task 3 and Task 4 use them.

- [ ] **Step 1: Re-create the scratch project and run a headless round**

```powershell
$t = Join-Path $env:TEMP "ap-spike0b"; Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue
New-Item -ItemType Directory $t | Out-Null; git -C $t init -q
Push-Location $t
npx -y skills add d:/ANTIGRAVITY/Autopilot --skill autopilot -a antigravity --copy -y | Out-Null
agy -p "/autopilot full A tiny CLI that prints hello" --output-format stream-json --mode accept-edits --dangerously-skip-permissions 2>&1 | Set-Content $env:TEMP\r1.txt
python .autopilot\ap.py --no-serve | Select-String "build|ticket|T0"
git log --oneline
Pop-Location
```
Record **Q1:** at process exit, is the executor's work (`src/hello_cli`, commits) present, partial, or absent? (`git status --short`, `git log`).

- [ ] **Step 2: Resume with a bare `/autopilot` and watch**

```powershell
Push-Location $t
agy -p "/autopilot" --output-format stream-json --mode accept-edits --dangerously-skip-permissions 2>&1 | Set-Content $env:TEMP\r2.txt
Get-Content .autopilot\state.js | Select-String '"finishedAt"|"status"'
Pop-Location
```
Record **Q2:** did the second round finish the ticket (and how many rounds until `finishedAt`)? Repeat Step 2 up to 6 times, counting rounds. Record **Q3:** did a resume ever redo a ticket from scratch, double-commit, or stall without changing `updatedAt`?

- [ ] **Step 3: Decide and record**

Append to `docs/antigravity.md`:
```markdown
## Headless waves (verified <date>)

| Question | Result |
|---|---|
| Executor work at process exit | <Q1> |
| Rounds of bare `/autopilot` to finish the toy run | <Q2> |
| Duplicate/redone work or stalls on resume | <Q3> |
```
Replace each `<…>` with the recorded value. Decision rule:
- Q2 finishes in ≤ 6 rounds with no duplicate work → proceed as planned (Task 4 loop re-enters `/autopilot`; `runtime.md` keeps "end your turn to wait").
- Otherwise → stop and report to the owner; candidate fixes are an in-flight-ticket rule in `runtime.md` (`ticket NN retry` on resume) or a blocking-wait instruction (`wait` / `manage_subagents`), each needing its own spike.

- [ ] **Step 4: Clean up and commit**

```powershell
Remove-Item -Recurse -Force $env:TEMP\ap-spike0b, $env:TEMP\r1.txt, $env:TEMP\r2.txt
git add docs/antigravity.md
git commit -m "docs: headless wave findings"
```

---

### Task 1: `ap.py setup` — cross-platform bootstrap

**Files:**
- Modify: `skills/autopilot/tools/ap.py` (imports near line 40; new function before `def main` at ~line 859; early dispatch at top of `main`; docstring command list)
- Test: `tests/test_ap.py` (new class `Setup`, inserted before `class Pure`)

**Interfaces:**
- Produces: `cmd_setup()`; CLI `python <skillDir>/tools/ap.py setup` → creates `<root>/.autopilot/{dashboard.html,index.html,ap.py}`, prints `skillDir = <abs path with forward slashes>` and `.autopilot = <abs path>`. Exit code 1 (via `die`) when run from a copy that has no `phases/dashboard-template.html` above it.

- [ ] **Step 1: Write the failing tests**

Insert before `class Pure(unittest.TestCase):` in `tests/test_ap.py`:
```python
class Setup(unittest.TestCase):
    """`ap.py setup`: bootstrap from the skill directory, no symlinks, no bash."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ap-setup-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_setup(self, script=AP, cwd=None):
        return subprocess.run([sys.executable, script, "setup"], capture_output=True,
                              text=True, cwd=cwd or self.root)

    def test_setup_in_a_git_repo_creates_the_instruments(self):
        subprocess.run(["git", "-C", self.root, "init", "-q"], check=True)
        sub = os.path.join(self.root, "src")
        os.makedirs(sub)
        r = self.run_setup(cwd=sub)                      # run from a subfolder: root is the toplevel
        self.assertEqual(r.returncode, 0, r.stderr)
        a = os.path.join(os.path.realpath(self.root), ".autopilot")
        for name in ("dashboard.html", "index.html", "ap.py"):
            self.assertTrue(os.path.isfile(os.path.join(a, name)), name)
        self.assertEqual(read(os.path.join(a, "index.html")), read(os.path.join(a, "dashboard.html")))
        self.assertFalse(os.path.islink(os.path.join(a, "index.html")))
        self.assertIn("skillDir = " + SKILL.replace("\\", "/"), r.stdout)

    def test_setup_without_git_uses_the_current_folder(self):
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".autopilot", "ap.py")))

    def test_setup_is_idempotent(self):
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(self.run_setup().returncode, 0)

    def test_setup_refuses_to_run_from_the_project_copy(self):
        self.assertEqual(self.run_setup().returncode, 0)
        copy = os.path.join(self.root, ".autopilot", "ap.py")
        r = self.run_setup(script=copy)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("setup", r.stderr + r.stdout)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_ap.Setup -v`
Expected: 4 failures — `setup` is an unknown command (`state.js ещё нет`).

- [ ] **Step 3: Implement**

First check imports: `Select-String skills\autopilot\tools\ap.py -Pattern "^import shutil"`. If absent, add `import shutil` in alphabetical position in the import block (after `import re`).

Add before `def main():`:
```python
def cmd_setup():
    """Bootstrap .autopilot/ from the skill directory (no bash, no symlinks)."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template = os.path.join(skill, "phases", "dashboard-template.html")
    if not os.path.isfile(template):
        die("setup запускается из каталога навыка: python <skillDir>/tools/ap.py setup")
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = top.stdout.strip() if top.returncode == 0 and top.stdout.strip() else os.getcwd()
    dst = os.path.join(os.path.realpath(root), ".autopilot")
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(template, os.path.join(dst, "dashboard.html"))
    shutil.copyfile(template, os.path.join(dst, "index.html"))
    shutil.copyfile(os.path.abspath(__file__), os.path.join(dst, "ap.py"))
    print("skillDir = %s" % skill.replace("\\", "/"))
    print(".autopilot = %s" % dst)
```
Dispatch: in `main()`, directly after the `--stop-now` block (before `pos, opt, multi = parse_args(argv)`):
```python
    if argv and argv[0] == "setup":
        cmd_setup()
        return
```
Docstring: after the `ap.py init` example block add the line
`    python3 .autopilot/ap.py setup        # из каталога навыка: python <skillDir>/tools/ap.py setup`.

Note: `die()` prints to stderr and exits 1 — confirm with `Select-String skills\autopilot\tools\ap.py -Pattern "def die" -Context 0,4`; the last test accepts stdout or stderr.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest tests.test_ap -v 2>&1 | Select-Object -Last 6`
Expected: `Ran 28 tests ... OK`.

- [ ] **Step 5: Commit**

```powershell
git add skills/autopilot/tools/ap.py tests/test_ap.py
git commit -m "feat(ap): setup command - cross-platform bootstrap without bash or symlinks"
```

---

### Task 2: `--runtime` recorded in `state.js`

**Files:**
- Modify: `skills/autopilot/tools/ap.py` (constants near `ORDER` ~line 67; `fresh_state`; `cmd_init`; docstring `init` example)
- Test: `tests/test_ap.py` (class `Run`, after `test_init_refuses_on_live_run`)

**Interfaces:**
- Consumes: `fresh_state(a)` reads `a["runtime"]`.
- Produces: `RUNTIMES = ("claude", "antigravity", "codex")`; `state["runtime"]` always present, default `"claude"`.

- [ ] **Step 1: Write the failing tests**

Add inside `class Run` after `test_init_refuses_on_live_run`:
```python
    def test_init_records_runtime_default_claude(self):
        self.init()
        self.assertEqual(self.state()["runtime"], "claude")

    def test_init_records_antigravity_runtime(self):
        code, out = self.ap("init", "--slug", "x", "--runtime", "antigravity", "--skill-dir", SKILL)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.state()["runtime"], "antigravity")

    def test_init_rejects_an_unknown_runtime(self):
        code, out = self.ap("init", "--slug", "x", "--runtime", "bogus", "--skill-dir", SKILL)
        self.assertNotEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.a, "state.js")))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_ap.Run.test_init_records_runtime_default_claude tests.test_ap.Run.test_init_records_antigravity_runtime tests.test_ap.Run.test_init_rejects_an_unknown_runtime -v`
Expected: FAIL — `KeyError: 'runtime'`, and the bogus runtime exits 0.

- [ ] **Step 3: Implement**

After the `ORDER = [...]` line add:
```python
RUNTIMES = ("claude", "antigravity", "codex")
```
In `fresh_state`, after the `"skillDir": ...` line add:
```python
        "runtime": a.get("runtime") or "claude",
```
In `cmd_init`, right after the `--slug` check add:
```python
    rt = opt.get("runtime")
    if rt is not None and rt not in RUNTIMES:
        die("--runtime: %s — допустимо: %s" % (rt, ", ".join(RUNTIMES)))
```
Docstring: in the `init` example add `--runtime claude|antigravity` to the flag list line.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest tests.test_ap -v 2>&1 | Select-Object -Last 6`
Expected: `Ran 31 tests ... OK`.

- [ ] **Step 5: Commit**

```powershell
git add skills/autopilot/tools/ap.py tests/test_ap.py
git commit -m "feat(ap): record the host runtime in state.js (init --runtime)"
```

---

### Task 3: Runtime contract `phases/runtime.md` and pointers

**Files:**
- Create: `skills/autopilot/phases/runtime.md`
- Modify: `skills/autopilot/SKILL.md` (phase table, Phase 0 row); `skills/autopilot/phases/0-instruments.md`; `skills/autopilot/phases/5-subagents.md`; `skills/autopilot/phases/6-review.md`; `skills/autopilot/phases/8-final.md`
- Test: `tests/test_ap.py` (class `Pure`)

**Interfaces:**
- Consumes: `init --runtime` (Task 2), `ap.py setup` (Task 1), and the Task 0b findings (they confirm or change the wording of the antigravity **Dispatch** bullet).
- Produces: sections `## claude`, `## antigravity`, `## codex`, each with the bullets **Dispatch**, **Ask**, **Dashboard**, **Model tier**.

- [ ] **Step 1: Write the failing tests**

Add inside `class Pure` before `test_skill_declares_a_version`:
```python
    def test_runtime_contract_has_every_section_and_point(self):
        text = read(os.path.join(SKILL, "phases", "runtime.md"))
        for section in ("## claude", "## antigravity", "## codex"):
            self.assertIn(section, text)
        for point in ("**Dispatch:**", "**Ask:**", "**Dashboard:**", "**Model tier:**"):
            self.assertGreaterEqual(text.count(point), 3, point)

    def test_phases_point_at_the_runtime_contract(self):
        for name in ("0-instruments", "5-subagents", "6-review", "8-final"):
            self.assertIn("phases/runtime.md", read(os.path.join(SKILL, "phases", name + ".md")), name)

    def test_skill_table_lists_the_runtime_contract(self):
        self.assertIn("phases/runtime.md", read(os.path.join(SKILL, "SKILL.md")))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_ap.Pure -v 2>&1 | Select-Object -Last 12`
Expected: 3 failures (`runtime.md` missing; pointers absent).

- [ ] **Step 3: Create `skills/autopilot/phases/runtime.md`**

```markdown
# Runtime contract

Phases never branch on the host. Everything host-specific lives here, one section per runtime.
Read this file once in Phase 0, after `0-preflight.md`.

## Which section applies

- You have the `invoke_subagent` tool → **antigravity**.
- You have the `Agent` tool and not `invoke_subagent` → **claude**.
- Neither → ask the user once which host this is. **codex** is a stub (below).

Record it with `init --runtime <id>`. On a resume read `runtime` from `state.js` and do not detect again.

## claude

- **Dispatch:** one `Agent` call per ticket, in the background; a whole wave in one message (`phases/5-subagents.md`).
- **Ask:** plain chat text.
- **Dashboard:** `preview_start`, then `navigate` (`phases/0-instruments.md` §3, Path A).
- **Model tier:** `обычная` → `model: "sonnet"` on the `Agent` call; `сильная` → the session model.
- **Bootstrap:** the bash block in `phases/0-instruments.md` §1, `python3` (on Windows `python` or `py -3`).

## antigravity

- **Dispatch:** `invoke_subagent` per ticket — `TypeName: "self"`, `Role: "Executor T<NN>"`, `Workspace: "inherit"` (one shared checkout, zones and commit-by-zone work exactly as in `phases/5-subagents.md`), `Prompt` = the paths-not-contents contract and the return contract from that file. Launch a whole wave in one tool-call block. Ending your turn is how you wait: the subagent's message wakes you (in a headless `agy -p` run the process ends with the turn and the launcher re-enters `/autopilot`; on that resume a ticket that is `in-progress` without a commit is re-checked before it is launched again). Subagents do not spawn subagents. Do not use `Workspace: "branch"` — it moves commits onto branches, which breaks commit-by-zone.
- **Ask:** plain chat text. `ask_question` is allowed for the forks of `interview` and `manual`, one question per call.
- **Dashboard:** `ap.py` serves it. Open it with `Start-Process "http://localhost:<PORT>/dashboard.html"` through `run_command`, and print the address in the chat. A failure to open is not an error. There is no side pane.
- **Model tier:** `обычная` → `Model: "flash"`; `сильная` and every retried ticket → `Model: "inherit"`.
- **Bootstrap:** `<skillDir>` is the directory that contains the `SKILL.md` you were given. If you were not given its path, look — in this order, stop at the first hit — for `skills/autopilot/SKILL.md` under `.agents/skills/autopilot`, `~/.agents/skills/autopilot`, `~/.gemini/config/skills/autopilot`; do not search the whole disk. Run `python "<skillDir>/tools/ap.py" setup` (it prints `skillDir`), then `python .autopilot/ap.py init … --runtime antigravity --skill-dir "<skillDir>"`. If `python` is not a working interpreter use `py -3`.
- **Shell:** the shell is PowerShell. `&&` chains work in PowerShell 7 (`pwsh`); in Windows PowerShell 5.1 write `a; if ($?) { b }`. Read exit codes from `$LASTEXITCODE`.
- **Memory file:** unchanged — Antigravity reads `AGENTS.md` natively.

## codex

Not implemented. Say so in one line and stop; do not guess a mapping.
```

- [ ] **Step 4: Add the pointers**

`skills/autopilot/SKILL.md` — in the phase table change the Phase 0 row's Read cell from
``| 0 Preflight | `phases/0-modes.md`, `phases/0-preflight.md`, then `0-memory.md`, `0-instruments.md` |``
to
``| 0 Preflight | `phases/0-modes.md`, `phases/0-preflight.md`, then `0-memory.md`, `phases/runtime.md`, `0-instruments.md` |``.

`skills/autopilot/phases/0-instruments.md` — insert after the first paragraph (line 3, before `## 1. Copy the template and the tool`):
```markdown
> **Host:** this phase describes the Claude Code way. On any other host read the **Bootstrap** and **Dashboard** bullets of your section in `phases/runtime.md` instead of §1 and §3.
```

`skills/autopilot/phases/5-subagents.md` — append to the end of the `**The model.**` paragraph (line 27):
```markdown
 The dispatch call and the model names of other hosts are in `phases/runtime.md`.
```

`skills/autopilot/phases/6-review.md` and `skills/autopilot/phases/8-final.md` — view the first 3 lines of each (`Get-Content <file> -TotalCount 3`), then insert directly after the first `# ` heading line, with one blank line around:
```markdown
> Subagent dispatch and model names depend on the host — `phases/runtime.md`.
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m unittest tests.test_ap -v 2>&1 | Select-Object -Last 6`
Expected: `Ran 34 tests ... OK`.
Also: `git diff --stat skills/autopilot/phases` — expect only the five files above, each with a few added lines and no deletions except the two `SKILL.md`/`5-subagents.md` line edits.

- [ ] **Step 6: Commit**

```powershell
git add skills/autopilot tests/test_ap.py
git commit -m "feat(skill): runtime contract for Claude Code and Antigravity"
```

---

### Task 4: `tools/agy-run.py` — headless launcher with resume loop

**Why the loop:** in `agy -p` a finished turn is a finished process, and Autopilot ends its turn to wait for subagents (Task 0b). The launcher therefore re-enters a bare `/autopilot` — the skill's own resume, driven by `state.js` — until the run reports `finishedAt`, with a round cap and a no-progress guard. Headless cannot prompt for permissions (every `run_command` is auto-denied), so permissions are auto-approved by default for **all** modes; `--ask-permissions` opts out.

**Files:**
- Create: `skills/autopilot/tools/agy-run.py`
- Test: `tests/test_agy_run.py` (create)

**Interfaces:**
- Produces:
  - `find_agy(env=None, which=shutil.which, exists=os.path.isfile, home=None) -> str | None`
  - `build_args(brief=None, mode="semi", depth="normal", project=None, model=None, effort="high", conversation=None, output_format="stream-json", skip_permissions=True) -> list[str]` — `brief=None` builds the bare resume prompt `/autopilot`; raises `ValueError` on bad `mode`/`depth`/`effort`/`output_format`
  - `read_state(project) -> dict | None` (parses `<project>/.autopilot/state.js`)
  - `is_finished(project) -> bool`, `progress_stamp(project) -> str | None` (the state's `updatedAt`)
  - `parse_result(lines) -> dict | None` (the last `{"event":"result"}` object's `result`)
  - `kill_tree(proc) -> None`, `run_round(exe, args, cwd) -> (int, dict | None)`, `main(argv=None) -> int`
  - exit codes: 0 finished, 1 agent error, 2 round cap reached, 3 no progress, 127 `agy` not found, 130 interrupted

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agy_run.py`:
```python
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(os.path.dirname(HERE), "skills", "autopilot", "tools", "agy-run.py")


def load():
    spec = importlib.util.spec_from_file_location("agy_run", PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FindAgy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_env_override_wins(self):
        got = self.m.find_agy(env={"ANTIGRAVITY_BIN_PATH": "X"}, which=lambda n: "Y", exists=lambda p: p == "X")
        self.assertEqual(got, "X")

    def test_path_lookup_next(self):
        got = self.m.find_agy(env={}, which=lambda n: "Y", exists=lambda p: False)
        self.assertEqual(got, "Y")

    def test_localappdata_fallback(self):
        want = os.path.join("L", "agy", "bin", "agy.exe")
        got = self.m.find_agy(env={"LOCALAPPDATA": "L"}, which=lambda n: None, exists=lambda p: p == want)
        self.assertEqual(got, want)

    def test_unix_fallback(self):
        want = os.path.join("H", ".local", "bin", "agy")
        got = self.m.find_agy(env={}, which=lambda n: None, exists=lambda p: p == want, home="H")
        self.assertEqual(got, want)

    def test_nothing_found(self):
        self.assertIsNone(self.m.find_agy(env={}, which=lambda n: None, exists=lambda p: False, home="H"))


class BuildArgs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_defaults_skip_permissions_because_headless_cannot_prompt(self):
        a = self.m.build_args("Telegram bot")
        self.assertEqual(a[:2], ["-p", "/autopilot semi Telegram bot"])
        self.assertEqual(a[a.index("--mode") + 1], "accept-edits")
        self.assertEqual(a[a.index("--effort") + 1], "high")
        self.assertIn("--dangerously-skip-permissions", a)
        self.assertNotIn("--print-timeout", a)

    def test_ask_permissions_opt_out(self):
        self.assertNotIn("--dangerously-skip-permissions", self.m.build_args("x", skip_permissions=False))

    def test_bare_resume_prompt(self):
        self.assertEqual(self.m.build_args(None, mode="full", depth="deep")[:2], ["-p", "/autopilot"])

    def test_depth_only_when_not_normal(self):
        self.assertEqual(self.m.build_args("x", depth="deep")[1], "/autopilot semi deep x")
        self.assertEqual(self.m.build_args("x", depth="normal")[1], "/autopilot semi x")

    def test_optional_flags(self):
        a = self.m.build_args("x", project="D:/p", model="m1", conversation="c1")
        self.assertEqual(a[a.index("--add-dir") + 1], "D:/p")
        self.assertEqual(a[a.index("--model") + 1], "m1")
        self.assertEqual(a[a.index("--conversation") + 1], "c1")

    def test_invalid_values_raise(self):
        for kw in ({"mode": "x"}, {"depth": "x"}, {"effort": "x"}, {"output_format": "x"}):
            with self.assertRaises(ValueError):
                self.m.build_args("x", **kw)


class RunState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="agy-run-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, state):
        os.makedirs(os.path.join(self.root, ".autopilot"), exist_ok=True)
        with open(os.path.join(self.root, ".autopilot", "state.js"), "w", encoding="utf-8") as f:
            f.write("window.AUTOPILOT = " + json.dumps(state) + ";\n")

    def test_missing_state(self):
        self.assertIsNone(self.m.read_state(self.root))
        self.assertFalse(self.m.is_finished(self.root))
        self.assertIsNone(self.m.progress_stamp(self.root))

    def test_unfinished_run(self):
        self.put({"finishedAt": None, "updatedAt": "t1"})
        self.assertFalse(self.m.is_finished(self.root))
        self.assertEqual(self.m.progress_stamp(self.root), "t1")

    def test_finished_run(self):
        self.put({"finishedAt": "2026-10-03T11:00:00+03:00", "updatedAt": "t2"})
        self.assertTrue(self.m.is_finished(self.root))

    def test_corrupt_state_is_not_finished(self):
        os.makedirs(os.path.join(self.root, ".autopilot"))
        with open(os.path.join(self.root, ".autopilot", "state.js"), "w", encoding="utf-8") as f:
            f.write("window.AUTOPILOT = {broken")
        self.assertFalse(self.m.is_finished(self.root))


class ParseResult(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_returns_the_last_result_and_skips_noise(self):
        lines = ['{"event":"init"}\n', "not json\n",
                 '{"event":"result","result":{"status":"ERROR"}}\n',
                 '{"event":"result","result":{"status":"SUCCESS","conversation_id":"c"}}\n']
        self.assertEqual(self.m.parse_result(lines), {"status": "SUCCESS", "conversation_id": "c"})

    def test_no_result(self):
        self.assertIsNone(self.m.parse_result(['{"event":"init"}\n', "x\n"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_agy_run -v 2>&1 | Select-Object -Last 8`
Expected: ERROR — `FileNotFoundError` for `agy-run.py`.

- [ ] **Step 3: Implement `skills/autopilot/tools/agy-run.py`**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest tests.test_agy_run tests.test_ap 2>&1 | Select-Object -Last 5`
Expected: `Ran 51 tests ... OK`.
Then: `python -c "import runpy;m=runpy.run_path('skills/autopilot/tools/agy-run.py');print(m['find_agy']())"` — expect `C:\Users\wait\AppData\Local\agy\bin\agy.exe`. A real `agy` session is not started here (Task 6).

- [ ] **Step 5: Commit**

```powershell
git add skills/autopilot/tools/agy-run.py tests/test_agy_run.py
git commit -m "feat: agy-run - headless Autopilot launcher with resume loop"
```

---

### Task 5: Documentation

**Files:**
- Modify: `docs/antigravity.md` (add everything below the facts table); `README.md` (short section after the install section); `CHANGELOG.md` (new top entry)

**Interfaces:**
- Consumes: the verified facts from Task 0 (substitute them into the commands below), `agy-run.py` flags (Task 4).

- [ ] **Step 1: Complete `docs/antigravity.md`**

Append after the facts table (replace `<project-path>`/`<global-path>`/`<id>` with Task 0 values):
````markdown
## Install

```powershell
npx skills add Boz1cod3/skills --skill autopilot -a <id> --copy -y      # project: <project-path>
npx skills add Boz1cod3/skills --skill autopilot -a <id> -g --copy -y   # global:  <global-path>
```

`--copy` avoids symlinks, which are unreliable on Windows.

## Run

Interactive (Antigravity IDE or `agy`): type `/autopilot [full|semi|interview|manual] [strict|deep] <what to build>`.

Headless:

```powershell
python <skillDir>/tools/agy-run.py --mode full --project D:\work\my-app "Telegram bot for repair requests"
```

Headless cannot answer permission prompts, so tool permissions are auto-approved (`--ask-permissions` turns that off and every command is then denied). A finished turn ends the `agy -p` process, so the launcher re-enters a bare `/autopilot` (the skill's own resume) until `finishedAt`; `--max-rounds` (default 12) caps it and a round with no change in `updatedAt` stops it. Only `full` runs without a human — the other modes stop to ask questions.

## How it adapts

Phases are shared with Claude Code. Host-specific behaviour (dispatch, questions, dashboard, model tier, bootstrap) lives in `phases/runtime.md`; the agent picks the `antigravity` section because it has the `invoke_subagent` tool and records it as `runtime` in `.autopilot/state.js`.

## Known limits

- Executors share one checkout (`Workspace: "inherit"`); `branch` worktrees are not used because Autopilot commits by zone.
- No side pane: the dashboard opens in the browser via `Start-Process`.
- `.agents/skills` is shared with the Codex app (slash vs `$` commands); installing both into one project is not handled.
- Codex runtime is a stub.
````

- [ ] **Step 2: README section and CHANGELOG**

In `README.md`, after the install section (the one containing `npx skills add nick-vels/skills`), add:
```markdown
### Antigravity (fork)

This fork also runs in Google Antigravity and the `agy` CLI — see [docs/antigravity.md](docs/antigravity.md).
```
In `CHANGELOG.md`, add at the top (match the file's existing heading style — view the first 10 lines first):
```markdown
## Unreleased

- Antigravity runtime: `phases/runtime.md` contract, `ap.py setup`, `init --runtime`, `tools/agy-run.py`.
```

- [ ] **Step 3: Verify and commit**

Run: `Select-String docs\antigravity.md -Pattern "<id>|<project-path>|<global-path>|<yes/no"` — expect no matches (all placeholders substituted).
```powershell
git add docs README.md CHANGELOG.md
git commit -m "docs: Antigravity install, run and limits"
```

---

### Task 6: End-to-end verification

**Files:** none modified (fix-forward in the owning task if anything fails).

- [ ] **Step 1: Full suite**

Run: `python -m unittest discover -s tests -v 2>&1 | Select-Object -Last 6`
Expected: `Ran 51 tests ... OK`.

- [ ] **Step 2: Real bootstrap in a scratch project, exactly as the agent will do it**

```powershell
$t = Join-Path $env:TEMP "ap-e2e"; Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue
New-Item -ItemType Directory $t | Out-Null; git -C $t init -q
Push-Location $t
python D:\ANTIGRAVITY\Autopilot\skills\autopilot\tools\ap.py setup
python .autopilot\ap.py init --slug e2e --title "E2E" --runtime antigravity --skill-dir "D:/ANTIGRAVITY/Autopilot/skills/autopilot" --no-serve
python .autopilot\ap.py stage manifest --no-serve
Get-Content .autopilot\state.js | Select-String '"runtime"'
Pop-Location
```
Expected: `skillDir = D:/ANTIGRAVITY/Autopilot/skills/autopilot`, init/stage print no errors, and the last command prints `"runtime": "antigravity"`.

- [ ] **Step 3: Serve and dashboard**

```powershell
Push-Location $env:TEMP\ap-e2e; python .autopilot\ap.py; Pop-Location
```
Expected: a line `сервер поднят: http://localhost:<PORT>/dashboard.html`. Open it with `Start-Process` and confirm the page renders the run `e2e`. Then `python .autopilot\ap.py --stop-now` in that folder and `Remove-Item -Recurse -Force $env:TEMP\ap-e2e`.

- [ ] **Step 4: Live agent smoke (manual, owner present)**

In an Antigravity session inside a scratch project with the skill installed (docs/antigravity.md): run `/autopilot semi A tiny CLI that prints hello`. Pass criteria: the agent reads `phases/runtime.md`, selects `antigravity`, runs `setup` then `init --runtime antigravity`, dispatches at least one executor via `invoke_subagent`, and the dashboard shows progress. Record any deviation in `docs/antigravity.md` → Known limits.

Then the same toy run headless: `python <skillDir>/tools/agy-run.py --mode full --project <scratch-project> "A tiny CLI that prints hello"`. Pass criteria: exit code 0, `.autopilot/state.js` has `finishedAt`, and the number of rounds is printed in the transcript (one `agy` invocation per round). Record the round count in `docs/antigravity.md`.

- [ ] **Step 5: Final state**

`git status -sb` must be clean; `git log --oneline -7` shows the six commits of this plan. Do not push.
