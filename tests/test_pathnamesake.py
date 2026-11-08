"""用独立临时目录检查同名分组、数量筛选和读取异常。"""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pathnamesake


class PathNamesakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "中文 空格"
        self.root.mkdir()
        for name, content in [("甲/report.txt", "a"), ("乙/report.txt", "different"),
                              ("丙/REPORT.TXT", "abc"), ("甲/photo.jpg", "not an image"),
                              ("乙/photo.jpg", "other"), ("only.txt", "one")]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_default_case_and_different_contents(self):
        originals = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        report = pathnamesake.scan_directory(self.root)
        self.assertEqual((report["total_files"], report["matched_groups"], report["matched_files"]), (6, 2, 5))
        rows = {r["comparison_name"]: r for r in report["groups"]}
        self.assertEqual(rows["report.txt"]["count"], 3)
        self.assertEqual(sorted(f["bytes"] for f in rows["report.txt"]["files"]), [1, 3, 9])
        for p, (content, modified) in originals.items():
            self.assertEqual(p.read_bytes(), content)
            self.assertEqual(p.stat().st_mtime_ns, modified)

    def test_threshold_and_case_sensitive_and_shallow(self):
        report = pathnamesake.scan_directory(self.root, min_copies=3)
        self.assertEqual([r["comparison_name"] for r in report["groups"]], ["report.txt"])
        report = pathnamesake.scan_directory(self.root, case_sensitive=True)
        self.assertEqual([r["count"] for r in report["groups"]], [2, 2])
        self.assertEqual(pathnamesake.scan_directory(self.root, min_copies=4)["matched_groups"], 0)
        report = pathnamesake.scan_directory(self.root, recursive=False)
        self.assertEqual((report["total_files"], report["matched_groups"]), (1, 0))

    def test_invalid_inputs_and_empty(self):
        for minimum in (0, 1, -1, 2.5, True):
            with self.subTest(minimum=minimum), self.assertRaises(ValueError):
                pathnamesake.scan_directory(self.root, min_copies=minimum)
        with self.assertRaises(FileNotFoundError):
            pathnamesake.scan_directory(self.root / "missing")
        with self.assertRaises(NotADirectoryError):
            pathnamesake.scan_directory(self.root / "only.txt")
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(pathnamesake.scan_directory(empty)["total_files"], 0)

    def test_permission_problem_is_recorded_with_partial_results(self):
        original_scandir = os.scandir
        denied = self.root / "乙"
        def controlled_scandir(path):
            if Path(path) == denied:
                raise PermissionError("模拟目录不可读")
            return original_scandir(path)
        with patch.object(pathnamesake.os, "scandir", side_effect=controlled_scandir):
            report = pathnamesake.scan_directory(self.root)
            self.assertEqual(report["total_files"], 4)
            self.assertEqual(len(report["errors"]), 1)
            self.assertEqual(report["errors"][0]["path"], str(denied))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pathnamesake.main([str(self.root)]), 1)

    def test_cli_marker_and_invalid_threshold(self):
        result = subprocess.run([sys.executable, str(Path(pathnamesake.__file__)), str(self.root),
                                 "--pathnamesake-min-copies", "3", "--json"],
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["min_copies"], report["matched_groups"]), (3, 1))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            pathnamesake.main([str(self.root), "--pathnamesake-min-copies", "1"])
        self.assertEqual(caught.exception.code, 2)

    def test_saves_report_without_overwriting(self):
        path = self.root / "report.json"
        pathnamesake.save_new_file(path, "报告\n")
        with self.assertRaises(FileExistsError):
            pathnamesake.save_new_file(path, "changed")
        self.assertEqual(path.read_text(encoding="utf-8"), "报告\n")

    @unittest.skipUnless(sys.platform == "win32", "仅 Windows 检查目录连接")
    def test_windows_directory_junction_loop_is_skipped(self):
        junction = self.root / "loop"
        self.assertEqual(junction.parent.resolve(), self.root.resolve())
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "New-Item -ItemType Junction -Path $env:MU_TEST_LINK -Target $env:MU_TEST_ROOT -ErrorAction Stop | Out-Null"],
            env={**os.environ, "MU_TEST_LINK": str(junction), "MU_TEST_ROOT": str(self.root)},
            capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            report = pathnamesake.scan_directory(self.root)
            self.assertEqual(report["total_files"], 6)
            self.assertEqual(report["skipped_links"], 1)
        finally:
            # rmdir 只移除连接本身，不递归删除连接指向的目录。
            junction.rmdir()


if __name__ == "__main__":
    unittest.main()
