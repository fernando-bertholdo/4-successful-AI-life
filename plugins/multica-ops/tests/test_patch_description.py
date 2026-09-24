"""patch-description.py against a fake `multica` (tests/fake_multica.py).

Standard library only. Run: bash tests/run-tests.sh
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "skills" / "board" / "scripts" / "patch-description.py"
FAKE = HERE / "fake_multica.py"
NOW = "2026-09-24T20:55:58Z"
TEXT = "## DoD\n\n- [ ] one\n- [ ] two\n"


class Case(unittest.TestCase):
    def run_script(self, *args, hooks=(), description=TEXT, **state):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "state.json")
        st = {"description": description.rstrip("\n"), "revision": 5,
              "updated_at": NOW, "now": NOW, "seq": 0, "events": [],
              "calls": [], "counts": {"get": 0, "timeline": 0, "update": 0},
              "hooks": list(hooks)}
        st.update(state)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f)
        files = []
        for i, a in enumerate(args):
            if isinstance(a, (list, dict)) or (isinstance(a, str) and a.startswith("@")):
                p = os.path.join(tmp.name, f"arg{i}")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(a[1:] if isinstance(a, str) else json.dumps(a))
                files.append(p)
            else:
                files.append(a)
        env = dict(os.environ, MULTICA_BIN=str(FAKE), MULTICA_PROFILE="test",
                   FAKE_MULTICA_STATE=path)
        r = subprocess.run([sys.executable, str(SCRIPT), "--workspace-id", "ws",
                            "--issue", "ISSUE-1", *files],
                           capture_output=True, text=True, env=env)
        with open(path, encoding="utf-8") as f:
            self.state = json.load(f)
        self.updates = [c for c in self.state["calls"] if c[0] == "update"]
        return r


class Baseline(Case):
    def test_clean_write_exits_0_with_one_update(self):
        r = self.run_script("--edits", [["- [ ] one", "- [x] one"]])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.updates), 1)
        self.assertIn("--no-start", self.updates[0])
        self.assertIn("- [x] one", self.state["description"])

    def test_edit_that_changes_nothing_exits_1_without_writing(self):
        r = self.run_script("--edits", [["- [ ] one", "- [ ] one"]])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.updates, [])

    def test_substring_not_found_once_exits_1_without_writing(self):
        r = self.run_script("--edits", [["- [ ] ", "- [x] "]])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.updates, [])

    def test_append_on_empty_description_has_no_leading_blank_lines(self):
        r = self.run_script("--append", "@- [ ] new\n", description="")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.state["description"], "- [ ] new")

    def test_write_after_ours_exits_3(self):
        r = self.run_script("--edits", [["- [ ] one", "- [x] one"]],
                            hooks=[{"when": "after", "call": "update", "nth": 1,
                                    "do": "append", "text": "\n- [ ] theirs"}])
        self.assertEqual(r.returncode, 3)


class Usage(Case):
    """--edits takes only pairs of two strings; an empty append is a usage error."""

    def test_malformed_edits_exit_2_before_touching_the_board(self):
        bad = ["@null", "@12", '@"ab"', {"ab": "zz"}, [[None, "x"]], [[12, 13]],
               [["a", "b", "c"]], [["", "x"]], ["ab"]]
        for payload in bad:
            with self.subTest(payload=payload):
                r = self.run_script("--edits", payload)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("pairs of two strings", r.stderr)
                self.assertEqual(self.state["calls"], [])

    def test_empty_append_block_exits_2(self):
        r = self.run_script("--append", "@  \n\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("empty", r.stderr)
        self.assertEqual(self.state["calls"], [])


EDIT = ("--edits", [["- [ ] one", "- [x] one"]])


def hook(when, call, do, text="", nth=1):
    return {"when": when, "call": call, "nth": nth, "do": do, "text": text}


class Window(Case):
    """The window is decided by counting description_updated, not by revision."""

    def test_counts_events_before_reading_and_never_uses_since(self):
        r = self.run_script(*EDIT)
        self.assertEqual(r.returncode, 0, r.stderr)
        kinds = [c[0] for c in self.state["calls"]]
        self.assertEqual(kinds[:2], ["timeline", "get"])
        self.assertFalse(any("--since" in c for c in self.state["calls"]))

    def test_comment_in_the_window_is_not_a_concurrent_write(self):
        r = self.run_script(*EDIT, hooks=[hook("before", "update", "comment")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("revision 5 -> 7", r.stdout)

    def test_write_before_ours_in_the_updated_at_second_exits_3(self):
        r = self.run_script(*EDIT, hooks=[hook("before", "update", "append",
                                               "\n- [ ] theirs")])
        self.assertEqual(r.returncode, 3)
        self.assertNotIn("theirs", self.state["description"])
        self.assertIn("WINDOW NOT CLEAN:", r.stderr)

    def test_own_event_that_trails_the_write_is_waited_for(self):
        r = self.run_script(*EDIT, own_event_lag=1)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.state["counts"]["timeline"], 3)

    def test_own_event_that_never_shows_exits_3(self):
        r = self.run_script(*EDIT, own_event_lag=10)
        self.assertEqual(r.returncode, 3)
        self.assertIn("WINDOW NOT VERIFIED", r.stderr)


if __name__ == "__main__":
    unittest.main()
