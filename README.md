# PathNamesake

查找文件夹及子目录中的同名文件，列出相对路径和文件大小，帮助在合并多个资料目录前检查命名冲突。

版本：0.1.1。需要 Python 3.10 或以上；仅使用标准库，窗口需要 Tkinter。程序只读取文件名称和元信息，不读取文件内容、不访问网络、不移动或删除文件。

## 双击使用

Windows 下双击 `打开工具.cmd`，选择本工具的 `demo` 文件夹，再点“开始检查”。本机已有运行环境。其他电脑需要先安装包含 Tkinter 的 Python，并使 `python` 命令可用。

- 默认包含子目录、忽略大小写：扫描 6 个文件，找到 2 组同名文件，共涉及 5 个文件。
- 把“最少同名文件数”从 2 改为 3：只剩 `report.txt` 这一组，涉及 3 个文件。
- 最少数量为 2 且勾选“区分大小写”：`REPORT.TXT` 与 `report.txt` 分开；仍有 2 组，但共涉及 4 个文件。
- 不包含子目录：只扫描根目录的 `unique.txt`，没有同名组。

可以将报告另存为 JSON；必须选择尚不存在的新文件名。

## 命令行

在本工具目录中运行；路径含空格时加双引号。

```powershell
python pathnamesake.py demo
python pathnamesake.py demo --pathnamesake-min-copies 3
python pathnamesake.py demo --case-sensitive
python pathnamesake.py demo --shallow
python pathnamesake.py demo --json
python pathnamesake.py --gui
```

| 参数 | 作用 |
| --- | --- |
| `directory` | 要检查的文件夹 |
| `--pathnamesake-min-copies N` | 只显示至少含 N 个文件的同名组，默认 2，最小值为 2 |
| `--case-sensitive` | 区分文件名大小写，默认不区分 |
| `--shallow` | 只检查当前目录，默认包括子目录 |
| `--json` | 输出 JSON 报告 |
| `--gui` | 打开窗口 |
| `--version` | 显示版本 |

`--pathnamesake-min-copies` 用于筛选组内文件数量，不控制文件大小或扫描深度。例如同名组有 2、3、5 个文件，设置为 3 时只显示后两组。

## 结果怎样理解

- 比较的是完整文件名（含扩展名），不是路径、文件内容或相似程度。
- 默认使用 Unicode casefold 忽略大小写；这是一条比较规则，可能与特定文件系统自身的大小写规则不同。
- 同名文件可能内容不同；大小相同也不能证明内容相同。本工具不能用来判断哪些文件可以安全删除。
- 报告包含相对于所选根目录的路径、原始名称和逻辑字节数，便于人工定位。
- 硬链接按路径分别计数；符号链接、Windows 目录连接及其他重解析点会跳过，云盘占位项也可能因此跳过。
- 读取失败会记录具体路径；存在读取问题时报告不完整。扫描过程中目录变化也可能影响结果。
- 选项变化不会自动重算，需要重新点击“开始检查”。报告对应本次运行时的路径和选项。
- 报告中的名称和路径可能包含私人信息，分享前请检查。
- 成功且没有读取问题时退出码为 0；存在读取问题时为 1；输入或参数错误时为 2。

## 检查程序

```powershell
python -m unittest discover -s tests -v
```

测试使用临时目录，覆盖不同内容的同名文件、大小写、数量筛选、子目录、原文件不变、输入错误与部分路径无法读取。
