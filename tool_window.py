"""小工具共用的本地窗口，无网络访问。"""

import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


class ToolWindow:
    def __init__(self, root, name, title, directory, description):
        self.root = root
        self.name = name
        self.directory = directory
        self.report = None
        self.cleaned = None
        self.busy = False
        self.results = queue.Queue()
        self.clean_button = None
        root.title(f"{name} · {title}")
        root.geometry("960x640")
        root.minsize(800, 500)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        main = ttk.Frame(root, padding=18)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)
        ttk.Label(main, text=title, font=("Microsoft YaHei UI", 15, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(main, text=description, wraplength=880).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 16))
        self.path = tk.StringVar()
        ttk.Entry(main, textvariable=self.path).grid(row=2, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(main, text="选择文件夹" if directory else "选择文本文件", command=self.choose).grid(row=2, column=1)
        self.options = ttk.Frame(main)
        self.options.grid(row=3, column=0, columnspan=2, sticky="w", pady=14)
        self.actions = ttk.Frame(main)
        self.actions.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self.run_button = ttk.Button(self.actions, text="开始检查", command=self.start)
        self.run_button.pack(side="left")
        self.save_button = ttk.Button(self.actions, text="另存报告（JSON）", command=self.save_report, state="disabled")
        self.save_button.pack(side="left", padx=10)
        self.output = scrolledtext.ScrolledText(main, wrap="none", font=("Microsoft YaHei UI", 10), state="disabled")
        self.output.grid(row=5, column=0, columnspan=2, sticky="nsew")
        horizontal = ttk.Scrollbar(main, orient="horizontal", command=self.output.xview)
        horizontal.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.output.configure(xscrollcommand=horizontal.set)
        self.status = tk.StringVar(value="选择路径，设置检查方式，然后点击“开始检查”。")
        ttk.Label(main, textvariable=self.status, wraplength=880).grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def enable_cleaned(self):
        self.clean_button = ttk.Button(self.actions, text="另存去重文本", command=self.save_cleaned, state="disabled")
        self.clean_button.pack(side="left")

    def choose(self):
        path = filedialog.askdirectory(title="选择要检查的文件夹") if self.directory else filedialog.askopenfilename(title="选择文本文件", filetypes=[("文本文件", "*.txt *.md *.log"), ("所有文件", "*.*")])
        if path:
            self.path.set(path)

    def start(self):
        if self.busy:
            return
        if not self.path.get():
            messagebox.showerror("缺少路径", "请先选择要检查的文件或文件夹。")
            return
        try:
            args = self.prepare()
        except (ValueError, TypeError) as exc:
            messagebox.showerror("设置不合适", f"请检查输入的设置。\n{exc}")
            return
        self.busy = True
        self.report = None
        self.cleaned = None
        self.run_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        if self.clean_button:
            self.clean_button.configure(state="disabled")
        self.status.set("正在检查，请稍候……")
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

        def worker():
            try:
                self.results.put((True, self.analyze(*args)))
            except Exception as exc:
                self.results.put((False, str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(60, self.poll)

    def poll(self):
        try:
            ok, result = self.results.get_nowait()
        except queue.Empty:
            self.root.after(60, self.poll)
            return
        self.busy = False
        self.run_button.configure(state="normal")
        if not ok:
            self.status.set("检查没有完成，请核对路径、编码或选项。")
            messagebox.showerror("无法完成检查", result)
            return
        self.report, self.cleaned = result
        self.output.configure(state="normal")
        self.output.insert("1.0", self.render(self.report))
        self.output.configure(state="disabled")
        self.save_button.configure(state="normal")
        if self.clean_button:
            self.clean_button.configure(state="normal")
        self.status.set("检查完成；报告包含部分读取问题，请查看末尾。" if self.report.get("errors") else "检查完成。结果对应本次运行时的路径与选项。")

    def save_text(self, content, suffix, name):
        path = filedialog.asksaveasfilename(title="选择一个尚不存在的新文件名", defaultextension=suffix, initialfile=name,
                                          filetypes=[("文本报告", f"*{suffix}")])
        if path:
            try:
                self.save_new(path, content)
            except FileExistsError:
                messagebox.showerror("文件已经存在", "为了保留已有文件，请换一个新的文件名。")
            except (OSError, ValueError) as exc:
                messagebox.showerror("保存失败", str(exc))
            else:
                self.status.set(f"已保存：{path}")

    def save_report(self):
        if self.report is not None:
            self.save_text(json.dumps(self.report, ensure_ascii=False, indent=2) + "\n", ".json", self.name + "-report.json")

    def save_cleaned(self):
        if self.cleaned is not None:
            self.save_text(self.cleaned, ".txt", self.name + "-cleaned.txt")
