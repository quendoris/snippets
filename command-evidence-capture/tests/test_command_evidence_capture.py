from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"src"/"command_evidence_capture.py"


class CommandEvidenceCaptureTests(unittest.TestCase):
    def invoke(
        self,
        temp:Path,
        *wrapper_args:str,
    )->subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--output-prefix",
                str(temp/"run"),
                *wrapper_args,
            ],
            cwd=temp,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def read_meta(self,temp:Path)->dict[str,object]:
        return json.loads(
            (temp/"run.meta.json").read_text(
                encoding="utf-8"
            )
        )

    def test_success_separates_streams(self)->None:
        with tempfile.TemporaryDirectory() as raw:
            temp=Path(raw)
            result=self.invoke(
                temp,
                "--",
                sys.executable,
                "-c",
                (
                    "import sys;"
                    "print('OUT');"
                    "print('ERR',file=sys.stderr)"
                ),
            )
            self.assertEqual(result.returncode,0)
            self.assertEqual(
                (temp/"run.stdout.log").read_text().strip(),
                "OUT",
            )
            self.assertEqual(
                (temp/"run.stderr.log").read_text().strip(),
                "ERR",
            )
            meta=self.read_meta(temp)
            self.assertEqual(meta["childExitCode"],0)
            self.assertTrue(meta["success"])

    def test_failure_propagates_by_default(self)->None:
        with tempfile.TemporaryDirectory() as raw:
            temp=Path(raw)
            result=self.invoke(
                temp,
                "--",
                sys.executable,
                "-c",
                "import sys;sys.exit(7)",
            )
            self.assertEqual(result.returncode,7)
            meta=self.read_meta(temp)
            self.assertEqual(meta["childExitCode"],7)
            self.assertFalse(meta["success"])
            self.assertEqual(meta["wrapperExitCode"],7)

    def test_keep_shell_records_failure_but_returns_zero(self)->None:
        with tempfile.TemporaryDirectory() as raw:
            temp=Path(raw)
            result=self.invoke(
                temp,
                "--keep-shell",
                "--",
                sys.executable,
                "-c",
                (
                    "import sys;"
                    "print('boom',file=sys.stderr);"
                    "sys.exit(9)"
                ),
            )
            self.assertEqual(result.returncode,0)
            meta=self.read_meta(temp)
            self.assertEqual(meta["childExitCode"],9)
            self.assertFalse(meta["success"])
            self.assertTrue(meta["keepShell"])
            self.assertEqual(meta["wrapperExitCode"],0)
            self.assertEqual(
                (temp/"run.stderr.log").read_text().strip(),
                "boom",
            )


if __name__=="__main__":
    unittest.main()
