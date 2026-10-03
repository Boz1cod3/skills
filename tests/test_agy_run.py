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
