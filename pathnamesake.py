"""查找文件夹内同名文件，帮助整理合并文件夹前的命名冲突。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

TOOL_NAME = "PathNamesake"
VERSION = "0.1.1"


def scan_directory(directory, min_copies=2, case_sensitive=False, recursive=True):
    if isinstance(min_copies, bool) or not isinstance(min_copies, int) or min_copies < 2:
        raise ValueError("最少同名文件数必须是大于或等于 2 的整数。")
    root = Path(directory).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError("请选择文件夹。")
    buckets = {}
    pending = [root]
    errors = []
    total_files = 0
    skipped_links = 0
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                        # 不跟随目录连接或符号链接，避免循环与跨目录统计。
                        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & reparse_flag:
                            skipped_links += 1
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            if recursive:
                                pending.append(Path(entry.path))
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        total_files += 1
                        key = entry.name if case_sensitive else entry.name.casefold()
                        buckets.setdefault(key, []).append({
                            "name": entry.name,
                            "path": str(Path(entry.path).relative_to(root)),
                            "bytes": info.st_size,
                        })
                    except OSError as exc:
                        errors.append({"path": entry.path, "message": str(exc)})
        except OSError as exc:
            errors.append({"path": str(current), "message": str(exc)})
    groups = []
    for key, files in sorted(buckets.items()):
        if len(files) >= min_copies:
            files.sort(key=lambda row: (row["path"].casefold(), row["path"]))
            groups.append({"comparison_name": key, "count": len(files), "files": files})
    return {
        "tool": TOOL_NAME, "version": VERSION, "directory": str(root),
        "recursive": recursive, "case_sensitive": case_sensitive, "min_copies": min_copies,
        "total_files": total_files, "matched_groups": len(groups),
        "matched_files": sum(row["count"] for row in groups),
        "skipped_links": skipped_links, "errors": errors, "groups": groups,
    }


def save_new_file(filename, content):
    """仅创建新报告，拒绝覆盖已有文件。"""
    with Path(filename).expanduser().open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def format_report(report):
    lines = [f"{TOOL_NAME} {VERSION}", f"目录：{report['directory']}",
             f"扫描文件：{report['total_files']}；同名组：{report['matched_groups']}；涉及文件：{report['matched_files']}",
             f"最少同名文件数：{report['min_copies']}；区分大小写：{'是' if report['case_sensitive'] else '否'}", "",
             "同名不代表内容相同。以下结果用于检查命名冲突，不能据此直接删除文件。", ""]
    for row in report["groups"]:
        lines.append(f"{row['comparison_name']} —— {row['count']} 个文件")
        lines += [f"  {file['path']}（{file['bytes']} 字节）" for file in row["files"]]
        lines.append("")
    if not report["groups"]:
        lines.append("按当前规则没有符合数量要求的同名组。")
    lines.append(f"跳过链接：{report['skipped_links']}；读取问题：{len(report['errors'])}")
    if report["errors"]:
        lines.append("部分路径无法读取，结果不完整：")
        lines += [f"  {item['path']}：{item['message']}" for item in report["errors"]]
    return "\n".join(lines)


def create_app(root):
    import tkinter as tk
    from tkinter import ttk
    from tool_window import ToolWindow

    app = ToolWindow(root, TOOL_NAME, "找出文件夹中的同名文件", directory=True,
                     description="查看各文件的位置和大小，便于合并文件夹前检查命名冲突；不会移动或删除文件。")
    minimum = tk.StringVar(value="2")
    sensitive = tk.BooleanVar(value=False)
    recursive = tk.BooleanVar(value=True)
    ttk.Label(app.options, text="最少同名文件数：").pack(side="left")
    ttk.Spinbox(app.options, from_=2, to=999999, textvariable=minimum, width=8).pack(side="left", padx=(0, 16))
    ttk.Checkbutton(app.options, text="区分大小写", variable=sensitive).pack(side="left", padx=(0, 16))
    ttk.Checkbutton(app.options, text="包含子目录", variable=recursive).pack(side="left")
    app.prepare = lambda: (app.path.get(), int(minimum.get()), sensitive.get(), recursive.get())
    app.analyze = lambda *args: (scan_directory(*args), None)
    app.render = format_report
    app.save_new = save_new_file
    app.min_copies = minimum
    app.case_sensitive = sensitive
    app.recursive = recursive
    return app


def launch_gui():
    import tkinter as tk
    root = tk.Tk()
    create_app(root)
    root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=f"{TOOL_NAME}：查找同名文件，只检查名称与大小，不比较内容。")
    parser.add_argument("directory", nargs="?", help="要检查的文件夹")
    parser.add_argument("--pathnamesake-min-copies", type=int, default=2, metavar="N", help="只显示至少有 N 个文件的同名组，默认 2，最小 2")
    parser.add_argument("--case-sensitive", action="store_true", help="比较文件名时区分大小写，默认忽略大小写")
    parser.add_argument("--shallow", action="store_true", help="只检查当前目录，默认包含子目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--gui", action="store_true", help="打开窗口")
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {VERSION}")
    args = parser.parse_args(argv)
    if args.gui:
        launch_gui()
        return 0
    if not args.directory:
        parser.error("请提供文件夹路径，或使用 --gui。")
    try:
        report = scan_directory(args.directory, args.pathnamesake_min_copies, args.case_sensitive, not args.shallow)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
