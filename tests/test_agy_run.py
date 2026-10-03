import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
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

    def test_real_exe_is_preferred_over_a_shell_shim(self):
        got = self.m.find_agy(env={}, which=lambda n: {"agy.exe": "E", "agy": "S.cmd"}.get(n),
                              exists=lambda p: False)
        self.assertEqual(got, "E")

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


class Main(unittest.TestCase):
    """main(): round sequencing, resume protocol, stale finishedAt, guards."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="agy-main-")
        self.calls, self.stops, self.script = [], [], []

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, **state):
        os.makedirs(os.path.join(self.root, ".autopilot"), exist_ok=True)
        with open(os.path.join(self.root, ".autopilot", "state.js"), "w", encoding="utf-8") as f:
            f.write("window.AUTOPILOT = " + json.dumps(state) + ";\n")

    def fake_run(self, exe, args, cwd, show="stream-json"):
        self.calls.append(args)
        step = self.script.pop(0) if self.script else {}
        if "state" in step:
            self.put(**step["state"])
        return step.get("code", 0), step.get("result", {"status": "SUCCESS"})

    def main(self, *argv):
        return self.m.main(list(argv) + ["--project", self.root], run=self.fake_run,
                           find=lambda: "agy", stop=self.stops.append)

    def prompt(self, i):
        return self.calls[i][self.calls[i].index("-p") + 1]

    def test_new_run_finishing_in_round_one(self):
        self.script = [{"state": {"finishedAt": "f1", "updatedAt": "u1"}}]
        self.assertEqual(self.main("--mode", "full", "hello"), 0)
        self.assertEqual(self.prompt(0), "/autopilot full hello")
        self.assertEqual(self.stops, [])

    def test_agy_is_always_asked_for_stream_json(self):
        self.script = [{"state": {"finishedAt": "f1", "updatedAt": "u1"}}]
        self.main("--output-format", "text", "hello")
        self.assertEqual(self.calls[0][self.calls[0].index("--output-format") + 1], "stream-json")

    def test_a_stale_finished_run_is_not_success(self):
        self.put(finishedAt="old", updatedAt="u0")
        self.script = [{}, {}]                              # the agent never touches state
        self.assertEqual(self.main("hello"), 3)

    def test_resume_round_stops_the_server_first_and_is_bare(self):
        self.script = [{"state": {"finishedAt": None, "updatedAt": "u1"}},
                       {"state": {"finishedAt": "f2", "updatedAt": "u2"}}]
        self.assertEqual(self.main("hello"), 0)
        self.assertEqual(self.prompt(1), "/autopilot")
        self.assertEqual(self.stops, [os.path.abspath(self.root)])

    def test_unfinished_run_without_resume_is_refused(self):
        self.put(finishedAt=None, updatedAt="u0")
        self.assertEqual(self.main("hello"), 4)
        self.assertEqual(self.calls, [])

    def test_resume_only_starts_bare_after_stopping_the_server(self):
        self.put(finishedAt=None, updatedAt="u0")
        self.script = [{"state": {"finishedAt": "f1", "updatedAt": "u1"}}]
        self.assertEqual(self.main("--resume"), 0)
        self.assertEqual(self.prompt(0), "/autopilot")
        self.assertEqual(len(self.stops), 1)

    def test_resume_without_a_run_is_refused(self):
        self.assertEqual(self.main("--resume"), 4)
        self.assertEqual(self.calls, [])

    def test_no_brief_and_no_resume_is_refused(self):
        self.assertEqual(self.main(), 4)

    def test_agent_error(self):
        self.script = [{"code": 0, "result": None}]
        self.assertEqual(self.main("hello"), 1)

    def test_conversation_only_in_round_one(self):
        self.script = [{"state": {"finishedAt": None, "updatedAt": "u1"}},
                       {"state": {"finishedAt": "f", "updatedAt": "u2"}}]
        self.main("--conversation", "c1", "hello")
        self.assertIn("--conversation", self.calls[0])
        self.assertNotIn("--conversation", self.calls[1])

    def test_round_cap(self):
        self.script = [{"state": {"finishedAt": None, "updatedAt": "u%d" % i}} for i in range(3)]
        self.assertEqual(self.main("--max-rounds", "2", "hello"), 2)
        self.assertEqual(len(self.calls), 2)

    def test_max_rounds_must_be_positive(self):
        with self.assertRaises(SystemExit):
            self.main("--max-rounds", "0", "hello")

    def test_agy_not_found(self):
        self.assertEqual(self.m.main(["hello", "--project", self.root], run=self.fake_run,
                                     find=lambda: None, stop=self.stops.append), 127)


FAKE_AGY = """import json, os, sys, time
sys.stdout.reconfigure(encoding="utf-8")
pidfile = os.environ.get("FAKE_PIDFILE")
if pidfile:
    open(pidfile, "w").write(str(os.getpid()))
print(json.dumps({"event": "init", "init": {"conversation_id": "c"}}), flush=True)
print("noise ✓ ↑", flush=True)
if os.environ.get("FAKE_SLEEP"):
    time.sleep(float(os.environ["FAKE_SLEEP"]))
print(json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "привет"}}), flush=True)
"""


class RealProcess(unittest.TestCase):
    """run_round / signals against a real child process (a fake agy)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="agy-proc-")
        self.fake = os.path.join(self.root, "fake_agy.py")
        with open(self.fake, "w", encoding="utf-8") as f:
            f.write(FAKE_AGY)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_run_round_reads_the_result_from_a_real_child(self):
        code, result = self.m.run_round(sys.executable, [self.fake], self.root, show="none")
        self.assertEqual(code, 0)
        self.assertEqual(result, {"status": "SUCCESS", "response": "привет"})

    @unittest.skipIf(os.name == "nt", "POSIX signal handling")
    def test_sigterm_to_the_launcher_kills_agy(self):
        agy = os.path.join(self.root, "agy")
        with open(agy, "w", encoding="utf-8") as f:
            f.write("#!%s\n%s" % (sys.executable, FAKE_AGY))
        os.chmod(agy, 0o755)
        pidfile = os.path.join(self.root, "pid")
        env = dict(os.environ, ANTIGRAVITY_BIN_PATH=agy, FAKE_PIDFILE=pidfile, FAKE_SLEEP="60")
        launcher = subprocess.Popen([sys.executable, PATH, "hello", "--project", self.root],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if os.path.exists(pidfile) and open(pidfile).read():
                break
            time.sleep(0.1)
        child = int(open(pidfile).read())
        launcher.send_signal(signal.SIGTERM)
        self.assertEqual(launcher.wait(timeout=10), 130)
        time.sleep(0.5)
        with self.assertRaises(OSError):
            os.kill(child, 0)


if __name__ == "__main__":
    unittest.main()
