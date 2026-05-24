#!/usr/bin/env python3
"""xcgui 源码搜索工具 — 查函数 / 常量 / 事件 / 示例.

用法:
    python scripts/search.py func <keyword>      # 搜索函数定义
    python scripts/search.py const <keyword>     # 搜索常量定义
    python scripts/search.py event <keyword>     # 搜索事件相关
    python scripts/search.py example <keyword>   # 搜索示例代码

    python scripts/search.py func Button         # 搜索 Button 相关函数
    python scripts/search.py const Window_Style  # 搜索窗口样式常量
    python scripts/search.py event AddEvent_BnClick  # 搜索点击事件
    python scripts/search.py example TabBar      # 搜索 TabBar 示例
"""

import argparse
import os
import re
import sys
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "source"
XCGUI_SRC = SOURCE_DIR / "xcgui"
EXAMPLE_SRC = SOURCE_DIR / "xcgui-example"

# ── ANSI 颜色 ─────────────────────────────────────────────
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_MAGENTA = "\033[35m"
C_RED = "\033[31m"
C_GRAY = "\033[90m"


def color_print(text: str, color: str = "", bold: bool = False):
    """带颜色的打印，Windows 兼容性处理."""
    if not sys.stdout.isatty():
        print(text)
        return
    prefix = C_BOLD if bold else ""
    suffix = C_RESET
    print(f"{prefix}{color}{text}{suffix}")


def find_go_files(base: Path, subdirs: list[str] = None) -> list[Path]:
    """查找指定子目录下的所有 .go 文件."""
    files = []
    if subdirs:
        for d in subdirs:
            p = base / d
            if p.exists():
                files.extend(sorted(p.rglob("*.go")))
    else:
        files = sorted(base.rglob("*.go"))
    return files


def extract_func_block(file_path: Path, line_no: int) -> str:
    """提取函数的完整签名（多行函数声明）."""
    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    # 从当前行向上找注释，向下找函数体开始
    start = max(0, line_no - 5)
    # 从函数声明行向下找到 { 或下一个 func
    end = min(len(lines), line_no + 1)
    # 尝试多行函数签名：检查后续行是否有未闭合的括号
    for i in range(line_no, min(len(lines), line_no + 10)):
        if "{" in lines[i]:
            end = i
            break
        if i + 1 < len(lines) and re.match(r'^\s*func\b', lines[i + 1]):
            end = i
            break
        if ")" in lines[i] and "(" not in lines[i]:
            end = i
            break
    return "\n".join(lines[start:end + 1])


def search_func(keyword: str) -> None:
    """搜索函数定义.

    搜索范围:
        - source/xcgui/xc/     底层 C API (X* 函数)
        - source/xcgui/widget/ 控件方法
        - source/xcgui/window/ 窗口方法
        - source/xcgui/ani/    动画方法
    """
    patterns = [
        # 底层 C API: func XBtn_Create(...) int {
        re.compile(rf'^\s*func\s+(\w*{keyword}\w*)\(', re.IGNORECASE),
        # Go 方法: func (b *Button) SetText(...) {
        re.compile(rf'^\s*func\s+\(.*?\)\s+(\w*{keyword}\w*)\(', re.IGNORECASE),
    ]

    search_dirs = ["xc", "widget", "window", "ani", "app", "adapter",
                   "bkmanager", "bkobj", "svg", "drawx", "font",
                   "imagex", "res", "tf", "common", "objectbase"]

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索函数: \"{keyword}\"", C_CYAN, bold=True)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0
    for go_file in find_go_files(XCGUI_SRC, search_dirs):
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            matched = False
            for pat in patterns:
                m = pat.search(line)
                if m:
                    matched = True
                    break
            if not matched:
                continue

            # 提取上下文
            context = extract_func_block(go_file, i)
            relative = go_file.relative_to(PROJECT_ROOT)

            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i}{C_RESET}")
            for ctx_line in context.splitlines():
                stripped = ctx_line.strip()
                if stripped.startswith("//"):
                    print(f"    {C_GRAY}{stripped}{C_RESET}")
                elif "func" in stripped:
                    print(f"    {C_BOLD}{stripped}{C_RESET}")
                else:
                    print(f"    {stripped}")
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的函数定义", C_RED)


def search_const(keyword: str) -> None:
    """搜索常量定义.

    搜索范围:
        - source/xcgui/xcc/  所有常量文件
    """
    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索常量: \"{keyword}\"", C_CYAN, bold=True)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0
    xcc_dir = XCGUI_SRC / "xcc"
    if not xcc_dir.exists():
        color_print(f"  错误: xcc 目录不存在: {xcc_dir}", C_RED)
        return

    patterns = [
        re.compile(rf'^\s*({keyword}\w*)\s', re.IGNORECASE),
        re.compile(rf'^\s*//.*({keyword})', re.IGNORECASE),
    ]

    for go_file in sorted(xcc_dir.rglob("*.go")):
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines):
            # 检查是否为常量定义
            is_const = ("const (" in line or
                        line.strip().startswith("//") or
                        any(kw in line for kw in ["_Flag_", "_Style_", "_State_", "_Event_",
                                                   "_Type_", "_Align_", "_Transparent_",
                                                   "_Button_", "_Window_", "_Element_",
                                                   "_Layout_", "_Scroll_", "_List_",
                                                   "_Edit_", "_Menu_", "_Tool_", "_Image_",
                                                   "_Font_", "_Color_", "_Text_", "_Draw_",
                                                   "_Rect_", "_GroupBox_", "_Shape_",
                                                   "_Tree_", "_Table_", "_Tab_", "_Pane_",
                                                   "_CombinedState_", "_Common_"]))

            if not is_const:
                continue

            m = patterns[0].search(line)
            if not m:
                m = patterns[1].search(line)
            if not m:
                continue

            relative = go_file.relative_to(PROJECT_ROOT)
            # 如果匹配的是注释行，也显示下一条常量定义行
            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")

            # 显示上下文
            start = max(0, i - 1)
            end = min(len(lines), i + 3)
            for j in range(start, end):
                stripped = lines[j].strip()
                if stripped.startswith("//"):
                    print(f"    {C_GRAY}{stripped}{C_RESET}")
                elif j == i:
                    print(f"    {C_BOLD}{C_YELLOW}{stripped}{C_RESET}")
                elif stripped == "":
                    continue
                else:
                    print(f"    {stripped}")
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的常量", C_RED)


def search_event(keyword: str) -> None:
    """搜索事件相关代码.

    搜索范围:
        - source/xcgui/xc/     底层事件绑定函数
        - source/xcgui/widget/  控件事件方法
        - source/xcgui/window/  窗口事件方法
        - source/xcgui/xcc/    事件常量
    """
    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索事件: \"{keyword}\"", C_CYAN, bold=True)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0
    patterns = [
        re.compile(rf'(\w*AddEvent\w*{keyword}\w*)', re.IGNORECASE),
        re.compile(rf'(\w*_{keyword}\w*)', re.IGNORECASE),  # 常量匹配
        re.compile(rf'(\w*{keyword}Event\w*)', re.IGNORECASE),
        re.compile(rf'(\w*onEvent\w*{keyword}\w*)', re.IGNORECASE),
        re.compile(rf'//.*事件.*{keyword}', re.IGNORECASE),  # 注释中的事件说明
    ]

    search_dirs = ["xc", "widget", "window", "xcc"]

    for go_file in find_go_files(XCGUI_SRC, search_dirs):
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines):
            matched = None
            for pat in patterns:
                m = pat.search(line)
                if m:
                    matched = m.group(1)
                    break
            if not matched:
                continue

            relative = go_file.relative_to(PROJECT_ROOT)
            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")

            # 显示上下文
            start = max(0, i - 2)
            end = min(len(lines), i + 2)
            for j in range(start, end):
                stripped = lines[j].strip()
                if stripped.startswith("//"):
                    print(f"    {C_GRAY}{stripped}{C_RESET}")
                elif j == i:
                    # 高亮匹配的关键词
                    highlighted = stripped.replace(matched, f"{C_BOLD}{C_YELLOW}{matched}{C_RESET}")
                    print(f"    {highlighted}")
                elif stripped == "":
                    continue
                else:
                    print(f"    {stripped}")
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的事件", C_RED)


def search_example(keyword: str) -> None:
    """搜索示例代码.

    搜索范围:
        - source/xcgui-example/  全部示例 .go 文件
    """
    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索示例: \"{keyword}\"", C_CYAN, bold=True)
    color_print(f"{'='*60}\n", C_CYAN)

    if not EXAMPLE_SRC.exists():
        color_print(f"  错误: 示例目录不存在: {EXAMPLE_SRC}", C_RED)
        return

    found = 0
    pattern = re.compile(rf'({keyword})', re.IGNORECASE)

    for go_file in sorted(EXAMPLE_SRC.rglob("*.go")):
        # 跳过非 main 包的辅助文件
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 快速检查
        if keyword.lower() not in text.lower():
            continue

        lines = text.splitlines()
        matched_lines = []
        for i, line in enumerate(lines):
            if pattern.search(line):
                relative = go_file.relative_to(PROJECT_ROOT)
                matched_lines.append((i + 1, line))

        if matched_lines:
            found += len(matched_lines)
            color_print(f"  {C_BOLD}{C_MAGENTA}{relative}{C_RESET} ({len(matched_lines)} 处匹配)")
            for line_no, line_text in matched_lines[:8]:  # 每个文件最多显示 8 行
                stripped = line_text.strip()
                # 高亮关键词
                highlighted = pattern.sub(f"{C_BOLD}{C_YELLOW}\\1{C_RESET}", stripped)
                print(f"    {C_GREEN}{line_no:>4}{C_RESET}: {highlighted}")
            if len(matched_lines) > 8:
                print(f"    {C_GRAY}... 还有 {len(matched_lines) - 8} 处匹配{C_RESET}")
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的示例", C_RED)


def search_list(subcommand: str) -> None:
    """列出指定子命令下的所有文件/内容."""
    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  列出: {subcommand}", C_CYAN, bold=True)
    color_print(f"{'='*60}\n", C_CYAN)

    if subcommand == "widgets":
        widget_dir = XCGUI_SRC / "widget"
        if widget_dir.exists():
            for f in sorted(widget_dir.glob("*.go")):
                if f.name.endswith("_test.go") or f.name == "doc.go" or f.name == "deprecated.go":
                    continue
                name = f.stem
                # 读取结构体注释
                text = f.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'//\s*(\w+)\s+([^.\n]+)\.', text)
                if m:
                    desc = m.group(2).strip()
                    color_print(f"  {C_BOLD}{C_GREEN}{name:20}{C_RESET} {C_GRAY}{desc}{C_RESET}")
                else:
                    color_print(f"  {C_BOLD}{C_GREEN}{name:20}{C_RESET}")

    elif subcommand == "examples":
        if EXAMPLE_SRC.exists():
            for cat_dir in sorted(EXAMPLE_SRC.iterdir()):
                if not cat_dir.is_dir():
                    continue
                color_print(f"\n  [{cat_dir.name}]", C_CYAN, bold=True)
                for ex_dir in sorted(cat_dir.iterdir()):
                    if ex_dir.is_dir():
                        go_files = list(ex_dir.glob("*.go"))
                        count = len(go_files)
                        desc = ""
                        if go_files:
                            text = go_files[0].read_text(encoding="utf-8", errors="replace")
                            m = re.search(r'//\s*(.+?)\.', text)
                            if m:
                                desc = m.group(1).strip()
                        color_print(f"    {ex_dir.name:35} {C_GRAY}{desc} ({count} 文件){C_RESET}")

    elif subcommand == "packages":
        for d in sorted(XCGUI_SRC.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                go_count = len(list(d.rglob("*.go")))
                # 读取 doc.go 注释
                doc_file = d / "doc.go"
                desc = ""
                if doc_file.exists():
                    text = doc_file.read_text(encoding="utf-8", errors="replace")
                    m = re.search(r'// Package \w+\s+(.+?)\.', text, re.DOTALL)
                    if m:
                        desc = m.group(1).replace("\n", " ").strip()
                color_print(f"  {C_BOLD}{C_GREEN}{d.name:20}{C_RESET} {C_GRAY}{go_count:>4} 文件  {desc}{C_RESET}")

    elif subcommand == "events":
        # 列出所有可用事件类型
        search_dirs = ["xc", "widget", "window"]
        events = set()
        pattern = re.compile(r'AddEvent_(\w+)', re.IGNORECASE)
        for go_file in find_go_files(XCGUI_SRC, search_dirs):
            try:
                text = go_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in pattern.finditer(text):
                events.add(m.group(1))
        color_print(f"  共 {len(events)} 种事件类型:\n", C_YELLOW)
        for ev in sorted(events):
            color_print(f"    AddEvent_{ev}", C_GREEN)


def main():
    parser = argparse.ArgumentParser(
        description="xcgui 源码搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  func <keyword>    搜索函数定义 (xc/widget/window/ani 等)
  const <keyword>   搜索常量定义 (xcc)
  event <keyword>   搜索事件相关代码 (AddEvent / 事件常量)
  example <keyword> 搜索示例代码 (xcgui-example)

列表子命令:
  list widgets      列出所有可用控件
  list packages     列出所有源码包
  list examples     列出所有示例
  list events       列出所有事件类型

示例:
  python scripts/search.py func XBtn_Create
  python scripts/search.py const Window_Style_
  python scripts/search.py event BnClick
  python scripts/search.py example TabBar
  python scripts/search.py list widgets
        """,
    )
    parser.add_argument(
        "command",
        choices=["func", "const", "event", "example", "list"],
        help="搜索命令",
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        default="",
        help="搜索关键词",
    )

    args = parser.parse_args()

    # 验证路径
    if not SOURCE_DIR.exists():
        color_print(f"错误: source 目录不存在: {SOURCE_DIR}", C_RED)
        color_print("请确保在项目根目录 (go-xcgui-dev) 下运行此脚本", C_RED)
        sys.exit(1)

    if args.command == "func":
        if not args.keyword:
            color_print("错误: func 命令需要关键词参数", C_RED)
            sys.exit(1)
        search_func(args.keyword)

    elif args.command == "const":
        if not args.keyword:
            color_print("错误: const 命令需要关键词参数", C_RED)
            sys.exit(1)
        search_const(args.keyword)

    elif args.command == "event":
        if not args.keyword:
            color_print("错误: event 命令需要关键词参数", C_RED)
            sys.exit(1)
        search_event(args.keyword)

    elif args.command == "example":
        if not args.keyword:
            color_print("错误: example 命令需要关键词参数", C_RED)
            sys.exit(1)
        search_example(args.keyword)

    elif args.command == "list":
        if not args.keyword:
            color_print("错误: list 命令需要子类型 (widgets/packages/examples/events)", C_RED)
            sys.exit(1)
        search_list(args.keyword)


if __name__ == "__main__":
    main()
