"""检查窗口的实际筛选、报告显示和保存过程。"""

import json
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pathnamesake


class WindowTest(unittest.TestCase):
    def test_scan_change_threshold_and_save(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name in ('A/report.txt', 'B/report.txt', 'C/report.txt', 'A/todo.txt', 'B/todo.txt'):
                path = folder / name
                path.parent.mkdir(exist_ok=True)
                path.write_text('example', encoding='utf-8')
            root = tk.Tk()
            root.withdraw()
            try:
                app = pathnamesake.create_app(root)
                app.path.set(str(folder))
                for minimum, expected in [('2', 2), ('3', 1)]:
                    app.min_copies.set(minimum)
                    with patch('tool_window.messagebox.showerror', side_effect=AssertionError):
                        app.run_button.invoke()
                        deadline = time.monotonic() + 5
                        while app.busy and time.monotonic() < deadline:
                            root.update()
                            time.sleep(0.01)
                    self.assertFalse(app.busy)
                    self.assertEqual(app.report['matched_groups'], expected)
                    self.assertIn('PathNamesake', app.output.get('1.0', 'end'))
                target = folder / 'result.json'
                with patch('tool_window.filedialog.asksaveasfilename', return_value=str(target)):
                    app.save_button.invoke()
                self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['min_copies'], 3)
            finally:
                root.destroy()


if __name__ == '__main__':
    unittest.main()
