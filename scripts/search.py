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


def find_go_files(base: Path, subdirs: list[str] | None = None) -> list[Path]:
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
    """提取函数的完整注释和函数体.

    向上查找完整的注释块（连续的 // 行），向下匹配函数体的大括号。
    注意：line_no 是 1-indexed（从 enumerate(..., 1) 传入）。
    """
    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    total_lines = len(lines)
    # 转换为 0-indexed
    func_idx = line_no - 1

    # ── 向上查找注释起始位置 ──────────────────────────
    # 从函数声明行的前一行开始向上查找
    comment_start = func_idx
    if func_idx > 0:
        i = func_idx - 1
        while i >= 0:
            stripped = lines[i].strip()
            # 空行表示注释块结束
            if stripped == "":
                comment_start = i + 1
                break
            # 注释行，继续向上
            if stripped.startswith("//") or stripped.startswith("/*"):
                comment_start = i
                i -= 1
                continue
            # 非注释非空行，注释块结束
            else:
                comment_start = i + 1
                break
        else:
            # 到达文件开头
            comment_start = 0

    # ── 向下查找函数体结束位置 ────────────────────────
    brace_count = 0
    found_open = False
    end = func_idx  # 至少包含函数声明行

    for i in range(func_idx, total_lines):
        line = lines[i]
        for ch in line:
            if ch == '{':
                brace_count += 1
                found_open = True
            elif ch == '}':
                brace_count -= 1

        # 找到匹配的函数体结束
        if found_open and brace_count == 0:
            end = i
            break
    else:
        # 未找到匹配的大括号，使用简单策略：取函数声明后20行
        end = min(total_lines - 1, func_idx + 20)

    return "\n".join(lines[comment_start:end + 1])


def search_func(keyword: str) -> None:
    """搜索函数定义.

    搜索范围:
        - source/xcgui/ 下除 xcc/ 外的所有子目录
    """
    patterns = [
        # 底层 C API: func XBtn_Create(...) int {
        re.compile(rf'^\s*func\s+(\w*{keyword}\w*)\(', re.IGNORECASE),
        # Go 方法: func (b *Button) SetText(...) {
        re.compile(rf'^\s*func\s+\(.*?\)\s+(\w*{keyword}\w*)\(', re.IGNORECASE),
    ]

    # 动态获取所有子目录，排除 xcc
    search_dirs = [
        d.name for d in XCGUI_SRC.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name != "xcc"
    ]

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

    # 编译正则表达式 - 支持精确匹配和前缀匹配
    # 使用 re.escape 处理特殊字符
    pattern_const = re.compile(rf'^\s*(\w*{re.escape(keyword)}\w*)\s', re.IGNORECASE)
    pattern_comment = re.compile(rf'^\s*//.*{re.escape(keyword)}', re.IGNORECASE)
    pattern_exact = re.compile(rf'^\s*{re.escape(keyword)}\b', re.IGNORECASE)

    for go_file in sorted(xcc_dir.rglob("*.go")):
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        in_const_block = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 追踪是否在 const ( ) 块中
            if "const (" in stripped:
                in_const_block = True
            if in_const_block and stripped == ")":
                in_const_block = False
                continue
            
            # 判断是否为常量相关行：
            # 1. 在 const 块中
            # 2. 行以 // 开头（注释）
            # 3. 行包含 = 且不是注释（常量赋值）
            is_const_line = (
                in_const_block or
                stripped.startswith("//") or
                ("=" in stripped and not stripped.startswith("//"))
            )
            
            if not is_const_line:
                continue
            
            # 尝试匹配
            m = pattern_exact.search(line) or pattern_const.search(line) or pattern_comment.search(line)
            if not m:
                continue

            relative = go_file.relative_to(PROJECT_ROOT)
            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")

            # 显示上下文
            start = max(0, i - 1)
            end = min(len(lines), i + 3)
            for j in range(start, end):
                stripped_line = lines[j].strip()
                if stripped_line.startswith("//"):
                    print(f"    {C_GRAY}{stripped_line}{C_RESET}")
                elif j == i:
                    print(f"    {C_BOLD}{C_YELLOW}{stripped_line}{C_RESET}")
                elif stripped_line == "":
                    continue
                else:
                    print(f"    {stripped_line}")
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

    # 智能处理关键词：提取事件名
    # 例如: "AddEvent_BnClick" -> "BnClick", "BNCLICK" -> "BNCLICK"
    event_name = keyword
    if event_name.startswith("AddEvent_"):
        event_name = event_name[len("AddEvent_"):]
    elif event_name.startswith("XE_"):
        event_name = event_name[len("XE_"):]

    # 构建搜索模式
    # 1. 完整匹配: AddEvent_BnClick, XE_BNCLICK
    # 2. 方法名: EventClicks, EventClick
    # 3. 常量: XE_BNCLICK, XE_BnClick
    # 4. 注释: 事件相关
    patterns = [
        re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE),  # 完整匹配关键词
        re.compile(rf'AddEvent_{re.escape(event_name)}', re.IGNORECASE),  # AddEvent_XXX
        re.compile(rf'Event{re.escape(event_name)}', re.IGNORECASE),  # EventXXX 方法
        re.compile(rf'XE_{re.escape(event_name)}', re.IGNORECASE),  # XE_XXX 常量
        re.compile(rf'onEvent{re.escape(event_name)}', re.IGNORECASE),  # onEventXXX
        re.compile(rf'//.*事件.*{re.escape(event_name)}', re.IGNORECASE),  # 注释
    ]

    search_dirs = ["xc", "widget", "window", "xcc"]
    found = 0

    for go_file in find_go_files(XCGUI_SRC, search_dirs):
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines):
            # 跳过测试文件
            if go_file.name.endswith("_test.go"):
                continue

            matched_text = None
            for pat in patterns:
                m = pat.search(line)
                if m:
                    matched_text = m.group(0)
                    break
            if not matched_text:
                continue

            relative = go_file.relative_to(PROJECT_ROOT)
            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")

            # 显示上下文（包含完整函数）
            context = extract_func_block(go_file, i + 1)
            for ctx_line in context.splitlines():
                stripped = ctx_line.strip()
                if stripped.startswith("//"):
                    print(f"    {C_GRAY}{stripped}{C_RESET}")
                elif matched_text in stripped:
                    highlighted = stripped.replace(matched_text, f"{C_BOLD}{C_YELLOW}{matched_text}{C_RESET}")
                    print(f"    {highlighted}")
                elif "func" in stripped:
                    print(f"    {C_BOLD}{stripped}{C_RESET}")
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
        relative = go_file.relative_to(PROJECT_ROOT)
        for i, line in enumerate(lines):
            if pattern.search(line):
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
