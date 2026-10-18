"""ci_paths.affected: a job is true exactly when a changed path is under
one of its prefixes; no diff and workflow changes run everything."""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import ci_paths  # noqa: E402


class Affected(unittest.TestCase):
    def test_docs_only_runs_nothing(self):
        # PR #746's diff: template + CONTRIBUTING.md. Only `docs` runs,
        # and it is not in the map because it always runs.
        a = ci_paths.affected([".github/pull_request_template.md", "CONTRIBUTING.md"])
        self.assertFalse(any(a.values()))

    def test_no_diff_runs_everything(self):
        for paths in (None, []):
            self.assertTrue(all(ci_paths.affected(paths).values()))

    def test_workflow_change_runs_everything(self):
        a = ci_paths.affected([".github/workflows/ci.yml"])
        self.assertTrue(all(a.values()))

    def test_emu_change_reaches_coldfire_and_tool_jobs(self):
        # tools/** is a family of acceptance, reach and site: over-run,
        # never under-run.
        a = ci_paths.affected(["tools/emu/ot_emu.c"])
        self.assertTrue(a["coldfire"])
        self.assertTrue(a["acceptance"])
        self.assertTrue(a["reach"])
        self.assertTrue(a["site"])
        self.assertFalse(a["dsp"])

    def test_harness_change_reaches_dsp(self):
        a = ci_paths.affected(["tools/harness/dsp_host/dsp_host.cpp"])
        self.assertTrue(a["dsp"])

    def test_manifest_change_reaches_registry_jobs(self):
        a = ci_paths.affected(["modules/stems/manifest.py"])
        self.assertTrue(a["acceptance"])
        self.assertTrue(a["reach"])
        self.assertTrue(a["site"])
        self.assertFalse(a["coldfire"])
        self.assertFalse(a["dsp"])

    def test_makefile_runs_everything(self):
        a = ci_paths.affected(["Makefile"])
        self.assertTrue(all(a.values()))

    def test_scripts_run_everything(self):
        a = ci_paths.affected(["scripts/vendor.sh"])
        self.assertTrue(all(a.values()))


if __name__ == "__main__":
    unittest.main()
