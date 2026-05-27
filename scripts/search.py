#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xcgui 源码搜索工具 — 查函数 / 常量 / 事件 / 示例.

用法:
    python scripts/search.py func <keyword>         # 搜索函数定义
    python scripts/search.py const <keyword>        # 搜索常量定义
    python scripts/search.py event <keyword>        # 搜索事件相关
    python scripts/search.py example <keyword>      # 搜索示例代码
    python scripts/search.py list <keyword>         # 列表, 可填: widgets/windows/packages/examples/events/funcs
    python scripts/search.py list events <对象名>   # 列出指定对象的所有事件 (含继承链, 不含 Event 开头函数)
    python scripts/search.py list funcs <对象名>    # 列出指定对象的所有方法 (含继承链, 含事件, 不含 Event 开头函数)

示例:
    python scripts/search.py func Center               # 搜索函数名关键词 (单个关键词)
    python scripts/search.py func button/gettext       # 搜索函数名关键词 (多个关键词用 / 分割)
    python scripts/search.py func 最大化                # 用中文注释搜索函数 (单个关键词)
    python scripts/search.py func 窗口/居中             # 用中文注释搜索函数 (多个关键词用 / 分割)
    python scripts/search.py const Window_Style        # 搜索常量关键词 (单个关键词)
    python scripts/search.py const button/check        # 搜索常量关键词 (多个关键词用 / 分割)
    python scripts/search.py const 阴影窗口             # 用中文注释搜索常量 (单个关键词)
    python scripts/search.py const 窗口/最小化          # 用中文注释搜索常量 (多个关键词用 / 分割)
    python scripts/search.py event BnClick             # 搜索事件函数名关键词 (单个关键词)
    python scripts/search.py event tree/select         # 搜索事件函数名关键词 (多个关键词用 / 分割)
    python scripts/search.py event 窗口消息过程         # 搜索事件函数中文注释关键词 (单个关键词)
    python scripts/search.py event 窗口/鼠标光标        # 搜索事件函数中文注释关键词 (多个关键词用 / 分割)
    python scripts/search.py example TabBar            # 搜索示例关键词 (单个关键词)
    python scripts/search.py example event/TabBar      # 搜索示例关键词 (多个关键词用 / 分割)
    python scripts/search.py example 按钮/选中/事件     # 搜索示例关键词 (多个关键词用 / 分割)
    python scripts/search.py list widgets              # 列出 widget 包所有公开对象
    python scripts/search.py list windows              # 列出 window 包所有公开对象
    python scripts/search.py list packages             # 列出所有源码包
    python scripts/search.py list examples             # 列出所有示例
    python scripts/search.py list events button        # 列出指定对象所有事件函数名
    python scripts/search.py list funcs button         # 列出指定对象所有方法名(含继承链,含事件)
"""

import argparse
import re
import sys
from pathlib import Path

# 解决 Windows cmd 中文输出乱码：重新配置 stdout/stderr 使用 UTF-8
# 使用 getattr + try 避免 basedpyright 类型检查报错
_reconfigure = getattr(sys.stdout, 'reconfigure', None)
if _reconfigure is not None:
    try:
        _reconfigure(encoding='utf-8')
    except Exception:
        pass
_reconfigure = getattr(sys.stderr, 'reconfigure', None)
if _reconfigure is not None:
    try:
        _reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── 路径配置 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "source"
XCGUI_SRC = SOURCE_DIR / "xcgui"
EXAMPLE_SRC = SOURCE_DIR / "xcgui-example"

# ── ANSI 颜色 ─────────────────────────────────────────────
ENABLE_COLOR = False  # 默认关闭颜色输出（避免增加 token 消耗）

# 颜色常量（会根据 ENABLE_COLOR 动态设置）
C_RESET = ""
C_BOLD = ""
C_CYAN = ""
C_GREEN = ""
C_YELLOW = ""
C_MAGENTA = ""
C_RED = ""
C_GRAY = ""


def _enable_color(enable: bool = True):
    """启用或禁用颜色输出."""
    global ENABLE_COLOR, C_RESET, C_BOLD, C_CYAN, C_GREEN, C_YELLOW, C_MAGENTA, C_RED, C_GRAY
    ENABLE_COLOR = enable
    if enable:
        C_RESET = "\033[0m"
        C_BOLD = "\033[1m"
        C_CYAN = "\033[36m"
        C_GREEN = "\033[32m"
        C_YELLOW = "\033[33m"
        C_MAGENTA = "\033[35m"
        C_RED = "\033[31m"
        C_GRAY = "\033[90m"
    else:
        C_RESET = ""
        C_BOLD = ""
        C_CYAN = ""
        C_GREEN = ""
        C_YELLOW = ""
        C_MAGENTA = ""
        C_RED = ""
        C_GRAY = ""


def color_print(text: str, color: str = "", bold: bool = False):
    """带颜色的打印."""
    if not ENABLE_COLOR:
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
    # 跳过 deprecated.go、doc.go 和 _test.go 文件
    skip_files = {"deprecated.go", "doc.go"}
    files = [f for f in files if f.name not in skip_files and not f.name.endswith("_test.go")]
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

    # ── 判断是否为类型定义（非函数定义）──────────────────
    func_line = lines[func_idx].strip()
    is_type_def = func_line.startswith("type ") and "func(" not in func_line.split("//")[0]
    is_event_type = func_line.startswith("type ") and "func(" in func_line

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

    # ── 向下查找结束位置 ──────────────────────────────
    if is_type_def and not is_event_type:
        # 普通类型定义：只取当前行
        end = func_idx
    elif is_event_type:
        # 事件类型定义（type XE_XXX func(...)）：只取当前行
        end = func_idx
    else:
        # 函数定义：匹配大括号
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
            # 未找到匹配的大括号，使用简单策略：取函数声明后10行
            end = min(total_lines - 1, func_idx + 10)

    return "\n".join(lines[comment_start:end + 1])


def _get_func_comment(lines: list[str], func_line_idx: int) -> str:
    """获取函数定义行上方的注释块内容.

    Args:
        lines: 文件行列表 (0-indexed)
        func_line_idx: 函数声明行的索引 (0-indexed)

    Returns:
        注释文本（合并多行注释，过滤掉参数说明）
    """
    # 收集函数行上方的所有注释行
    comment_lines = []
    i = func_line_idx - 1
    
    # 向上查找，收集所有注释行
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped.startswith("//"):
            break
        
        line_content = stripped.lstrip("/").strip()
        comment_lines.insert(0, line_content)
        i -= 1
    
    if not comment_lines:
        return ""
    
    # 只取第一行非空的注释作为简短描述
    # Go 注释约定：第一行是简短描述，后面是详细说明
    comment = ""
    for line in comment_lines:
        # 跳过空行
        if not line:
            continue
        # 跳过参数说明行
        if _is_param_description(line):
            continue
        # 找到第一行有效注释，作为描述
        comment = line
        break
    
    if not comment:
        return ""
    
    # 获取函数名
    func_line = lines[func_line_idx]
    m = re.search(r'func\s+\(\w+\s+\*(\w+)\)\s+(\w+)', func_line)
    if m:
        func_name = m.group(2)
        
        # 只有注释中包含函数名时，才去掉函数名
        if func_name in comment:
            comment = comment.replace(func_name, "").strip()
    
    # 去掉开头可能的函数名（中文格式：Button 按钮控件.）
    # 格式：中文名 + 空格 + 描述
    for sep in [" ", "\t"]:
        parts = comment.split(sep, 1)
        if len(parts) > 1 and parts[0] and not parts[0][0].islower():
            # 检查是否是函数名（英文）
            if parts[0][0].isupper():
                # 是英文函数名，去掉它
                comment = parts[1]
                break
            # 如果不是英文（如中文），保留整个注释
    
    return comment.strip()


def _is_param_description(line: str) -> bool:
    """判断一行注释是否是参数说明.
    
    Args:
        line: 注释内容（已去掉 // 前缀）
        
    Returns:
        是否是参数说明
    """
    # 格式1: fn: 回调函数.
    if line.startswith("fn:") or line.startswith("参数:"):
        return True
    
    # 格式2: allowAddingMultiple: 允许添加多个回调函数
    if re.match(r'^\w+:', line):
        return True
    
    return False


def _get_package_comment(file_path: Path) -> str:
    """提取文件中的包注释（package 语句上方的多行注释），合并为一行.

    查找 package main 或 package xxx 语句上方的所有连续 // 注释行，
    将多行注释合并为一行（用空格连接，清理多余空白）。

    Args:
        file_path: Go 文件路径

    Returns:
        合并后的包注释字符串，如果没有找到则返回空字符串
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    lines = text.split('\n')

    # 找到 package 语句的行号
    pkg_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('package '):
            pkg_idx = i
            break

    if pkg_idx is None or pkg_idx == 0:
        return ""

    # 向上查找所有连续的 // 注释行
    comment_lines = []
    i = pkg_idx - 1
    while i >= 0:
        stripped = lines[i].strip()
        if stripped.startswith('//'):
            # 去掉 // 前缀，保留注释内容
            content = stripped[2:].strip()
            if content:
                comment_lines.insert(0, content)
            i -= 1
        else:
            # 非注释行（包括空行），停止
            break

    if not comment_lines:
        return ""

    # 合并多行注释，用空格连接，并清理多余空白
    return re.sub(r'\s+', ' ', ' '.join(comment_lines)).strip()


def _extract_func_name(line: str) -> str | None:
    """从函数定义行提取函数名.

    Args:
        line: 函数定义行

    Returns:
        函数名，如果不是函数定义行则返回 None
    """
    # 普通函数: func XBtn_Create(...)
    m = re.match(r'^\s*func\s+(\w+)\s*\(', line)
    if m:
        return m.group(1)

    # 方法: func (b *Button) SetText(...)
    m = re.match(r'^\s*func\s+\(.*?\)\s+(\w+)\s*\(', line)
    if m:
        return m.group(1)

    return None


def search_func(keyword: str) -> None:
    """搜索函数定义.

    搜索范围:
        - source/xcgui/ 下除 xcc/ 外的所有子目录

    关键词规则:
        - 用 / 分割多个关键词，函数必须同时匹配所有关键词
        - 中文关键词：搜索函数注释
        - 英文关键词：搜索函数名
    """
    # ── 判断是否为中文搜索 ──────────────────────────
    is_chinese = bool(re.search(r'[\u4e00-\u9fff]', keyword))

    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    # 动态获取所有子目录，排除 xcc
    search_dirs = [
        d.name for d in XCGUI_SRC.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name != "xcc"
    ]

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索函数: \"{keyword}\"", C_CYAN, bold=True)
    if len(keywords) > 1:
        color_print(f"  (关键词: {', '.join(keywords)})", C_GRAY)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0
    for go_file in find_go_files(XCGUI_SRC, search_dirs):
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            # 函数声明行索引 (0-indexed)
            func_idx = i - 1

            # 提取函数名
            func_name = _extract_func_name(line)
            if func_name is None:
                continue

            # 跳过未导出的函数（小写字母开头）
            if not func_name[0].isupper():
                continue

            if is_chinese:
                # ── 中文搜索：通过注释过滤 ──
                comment = _get_func_comment(lines, func_idx)
                # 检查所有关键词是否都在注释中（不区分大小写）
                if not all(kw in comment for kw in keywords):
                    continue
            else:
                # ── 英文搜索：在函数定义行中搜索（含接收者类型），不区分大小写 ──
                # 例如 "func (b *Button) SetText(...)" 可匹配 Button 和 Text
                line_lower = line.lower()
                if not all(kw.lower() in line_lower for kw in keywords):
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
        - source/xcgui/edge/consts.go
        - source/xcgui/edge/IStream.go
        - source/xcgui/edge/webview2_iids.go

    关键词规则:
        - 用 / 分割多个关键词，常量必须同时匹配所有关键词
        - 支持在常量名和注释中搜索
    """
    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索常量: \"{keyword}\"", C_CYAN, bold=True)
    if len(keywords) > 1:
        color_print(f"  (关键词: {', '.join(keywords)})", C_GRAY)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0

    # ── 搜索 xcc 目录 ──────────────────────────────
    xcc_dir = XCGUI_SRC / "xcc"
    go_files = []

    if xcc_dir.exists():
        for go_file in sorted(xcc_dir.rglob("*.go")):
            # 跳过 deprecated.go、doc.go 和 _test.go 文件
            if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
                continue
            go_files.append(go_file)

    # ── 搜索 edge 目录下的指定文件 ──────────────────
    edge_dir = XCGUI_SRC / "edge"
    edge_const_files = [
        edge_dir / "consts.go",
        edge_dir / "IStream.go",
        edge_dir / "webview2_iids.go",
    ]

    for edge_file in edge_const_files:
        if edge_file.exists():
            go_files.append(edge_file)

    # ── 搜索所有收集到的文件 ────────────────────────
    for go_file in go_files:
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        in_const_block = False

        # 判断是否为中文搜索
        is_chinese = any(re.search(r'[\u4e00-\u9fff]', kw) for kw in keywords)

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 追踪是否在 const ( ) 块中
            if "const (" in stripped:
                in_const_block = True
            if in_const_block and stripped == ")":
                in_const_block = False
                continue

            # 判断是否为注释行
            is_comment_line = stripped.startswith("//")

            # 判断是否为常量定义行（非注释，有 = 或在 const 块中且非注释）
            is_const_def = (
                (in_const_block and not is_comment_line) or
                ("=" in stripped and not is_comment_line)
            )

            # 根据搜索类型决定是否处理此行
            if is_chinese:
                # 中文搜索：处理常量定义行和注释行
                if not is_const_def and not is_comment_line:
                    continue
            else:
                # 英文搜索：只处理常量定义行（不匹配纯注释行）
                if not is_const_def:
                    continue

            # 检查所有关键词是否都匹配（在常量名或注释中）
            line_lower = line.lower()
            if not all(kw.lower() in line_lower for kw in keywords):
                continue

            relative = go_file.relative_to(PROJECT_ROOT)
            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")

            # 显示上下文：完整注释块 + 匹配的行
            # 1. 向上查找注释块起始位置
            comment_start = i
            if i > 0:
                j = i - 1
                while j >= 0:
                    stripped_line = lines[j].strip()
                    if stripped_line.startswith("//"):
                        comment_start = j
                        j -= 1
                    elif stripped_line == "":
                        # 空行：如果上面有注释，注释块结束
                        if comment_start == i:
                            # 还没有找到注释，继续向上
                            j -= 1
                            continue
                        else:
                            # 已经找到注释块，空行表示注释块结束
                            break
                    else:
                        # 非注释非空行，注释块结束
                        break

            # 2. 显示注释块和匹配的行
            # 收集要显示的行
            display_lines = []
            # 添加注释块
            for j in range(comment_start, i):
                display_lines.append((j, lines[j].rstrip(), "comment"))

            # 添加匹配的行
            display_lines.append((i, lines[i].rstrip(), "match"))

            # 3. 显示行
            for _, line_content, line_type in display_lines:
                stripped_line = line_content.strip()
                if line_type == "comment":
                    print(f"    {C_GRAY}{stripped_line}{C_RESET}")
                elif line_type == "match":
                    print(f"    {stripped_line}")
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的常量", C_RED)


def _find_type_definitions(type_names: set[str]) -> list[tuple[Path, int, str]]:
    """查找类型定义.

    Args:
        type_names: 类型名称集合（如 {"XWM_WINDPROC", "XWM_WINDPROC1"}）

    Returns:
        [(文件路径, 行号, 类型定义内容), ...]
    """
    results = []
    xc_dir = XCGUI_SRC / "xc"

    if not xc_dir.exists():
        return results

    # 搜索 xc 目录下的所有 Go 文件
    for go_file in sorted(xc_dir.rglob("*.go")):
        if go_file.name in {"deprecated.go", "doc.go"}:
            continue

        try:
            lines = go_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            # 检查是否为类型定义行
            if not line.strip().startswith("type "):
                continue

            # 检查是否匹配任何类型名称
            for type_name in type_names:
                if f"type {type_name} " in line or f"type {type_name}(" in line:
                    # 提取完整的类型定义（可能包括多行）
                    context = extract_func_block(go_file, i + 1)
                    results.append((go_file, i + 1, context))
                    break

    return results


def search_event(keyword: str) -> None:
    """搜索事件相关代码.

    搜索策略:
        - 在 AddEvent_ 和 Event_ 开头的函数定义及其注释中搜索
        - 支持中英文关键词搜索
        - 自动显示函数中引用的类型定义

    关键词规则:
        - 用 / 分割多个关键词，必须同时匹配所有关键词
        - 中文关键词：搜索函数注释
        - 英文关键词：搜索函数名
    """
    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索事件: \"{keyword}\"", C_CYAN, bold=True)
    if len(keywords) > 1:
        color_print(f"  (关键词: {', '.join(keywords)})", C_GRAY)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0
    # 收集所有找到的函数中引用的类型名称
    referenced_types = set()

    # ── 判断是否为中文搜索 ──────────────────────────
    is_chinese = any(re.search(r'[\u4e00-\u9fff]', kw) for kw in keywords)

    # 搜索目录
    search_dirs = ["widget", "window", "edge"]

    for go_file in find_go_files(XCGUI_SRC, search_dirs):
        if go_file.name.endswith("_test.go"):
            continue

        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines):
            # 只处理 AddEvent_ 或 Event_ 开头的函数定义行
            if not ("AddEvent_" in line or "Event_" in line):
                continue

            # 检查是否为函数定义行
            func_name = _extract_func_name(line)
            if func_name is None:
                continue

            if is_chinese:
                # ── 中文搜索：通过注释过滤 ──
                comment = _get_func_comment(lines, i)
                # 检查所有关键词是否都在注释中
                if not all(kw in comment for kw in keywords):
                    continue
            else:
                # ── 英文搜索：在函数定义行中搜索，不区分大小写 ──
                line_lower = line.lower()
                if not all(kw.lower() in line_lower for kw in keywords):
                    continue

            # 提取上下文
            context = extract_func_block(go_file, i + 1)
            relative = go_file.relative_to(PROJECT_ROOT)

            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")
            for ctx_line in context.splitlines():
                stripped = ctx_line.strip()
                if stripped.startswith("//"):
                    print(f"    {C_GRAY}{stripped}{C_RESET}")
                elif "func" in stripped:
                    print(f"    {C_BOLD}{stripped}{C_RESET}")
                else:
                    print(f"    {stripped}")
            print()

            # 提取函数中引用的类型名称（如 xc.XWM_WINDPROC1）
            type_pattern = re.compile(r'xc\.([A-Z_][A-Z0-9_]*)')
            for m in type_pattern.finditer(line):
                type_name = m.group(1)
                referenced_types.add(type_name)

    # 显示引用的类型定义
    if referenced_types:
        color_print(f"\n  {'─'*50}", C_CYAN)
        color_print(f"  相关类型定义:", C_CYAN, bold=True)
        color_print(f"  {'─'*50}\n", C_CYAN)

        type_defs = _find_type_definitions(referenced_types)
        if type_defs:
            for type_file, type_line, type_context in type_defs:
                relative = type_file.relative_to(PROJECT_ROOT)
                color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{type_line}{C_RESET}")
                for ctx_line in type_context.splitlines():
                    stripped = ctx_line.strip()
                    if stripped.startswith("//"):
                        print(f"    {C_GRAY}{stripped}{C_RESET}")
                    elif "type" in stripped:
                        print(f"    {C_BOLD}{stripped}{C_RESET}")
                    else:
                        print(f"    {stripped}")
                print()
        else:
            color_print(f"  {C_GRAY}未找到相关类型定义{C_RESET}", C_GRAY)

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的事件", C_RED)


def search_example(keyword: str) -> None:
    """搜索示例代码.

    搜索范围:
        - source/xcgui-example/  全部示例 .go 文件

    关键词规则:
        - 用 / 分割多个关键词，示例必须同时匹配所有关键词
        - 支持在示例代码的任何位置搜索（函数名、注释、代码逻辑等）
    """
    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索示例: \"{keyword}\"", C_CYAN, bold=True)
    if len(keywords) > 1:
        color_print(f"  (关键词: {', '.join(keywords)})", C_GRAY)
    color_print(f"{'='*60}\n", C_CYAN)

    if not EXAMPLE_SRC.exists():
        color_print(f"  错误: 示例目录不存在: {EXAMPLE_SRC}", C_RED)
        return

    found = 0

    for go_file in sorted(EXAMPLE_SRC.rglob("*.go")):
        # 跳过 deprecated.go、doc.go 和 _test.go 文件
        if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
            continue

        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 快速检查：所有关键词都必须出现在文件中（不区分大小写）
        text_lower = text.lower()
        if not all(kw.lower() in text_lower for kw in keywords):
            continue

        # 构建多个关键词的正则模式（用于高亮）
        # 用 | 连接多个关键词，匹配任意一个
        pattern_str = '|'.join(re.escape(kw) for kw in keywords)
        pattern = re.compile(rf'({pattern_str})', re.IGNORECASE)

        lines = text.splitlines()
        matched_lines = []
        relative = go_file.relative_to(PROJECT_ROOT)

        for i, line in enumerate(lines):
            # 检查当前行是否包含所有关键词（不区分大小写）
            line_lower = line.lower()
            if all(kw.lower() in line_lower for kw in keywords):
                matched_lines.append((i + 1, line))

        if matched_lines:
            found += len(matched_lines)
            color_print(f"  {C_BOLD}{C_MAGENTA}{relative}{C_RESET} ({len(matched_lines)} 处匹配)")
            for line_no, line_text in matched_lines[:8]:  # 每个文件最多显示 8 行
                stripped = line_text.strip()
                # 高亮所有关键词
                highlighted = pattern.sub(f"{C_BOLD}{C_YELLOW}\\1{C_RESET}", stripped)
                print(f"    {C_GREEN}{line_no:>4}{C_RESET}: {highlighted}")
            if len(matched_lines) > 8:
                print(f"    {C_GRAY}... 还有 {len(matched_lines) - 8} 处匹配{C_RESET}")
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的示例", C_RED)


def _parse_struct_inheritance(go_file: Path) -> dict[str, str]:
    """解析 Go 文件中的结构体嵌入关系.

    从 Go 文件中提取所有结构体定义及其嵌入的父结构体。
    只处理当前 package 中的类型定义。

    Args:
        go_file: Go 文件路径

    Returns:
        字典 {子结构体名: 父结构体名}
        例如: {"Button": "Element", "Element": "Widget"}
    """
    inheritance = {}
    try:
        text = go_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return inheritance

    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配: type Button struct {
        m = re.match(r'^type\s+(\w+)\s+struct\s*\{', stripped)
        if not m:
            continue

        child = m.group(1)
        # 向后查找嵌入的父结构体
        # 查找范围: 从当前行到匹配的结束大括号
        brace_count = 0
        found_open = False
        for j in range(i, min(i + 50, len(lines))):  # 最多查找50行
            for ch in lines[j]:
                if ch == '{':
                    brace_count += 1
                    found_open = True
                elif ch == '}':
                    brace_count -= 1

            # 在结构体定义范围内查找嵌入字段
            if found_open and brace_count == 0:
                # 已到达结构体结束
                break

            # 检查当前行是否是嵌入字段 (大写字母开头, 后面是空格或换行)
            if j > i:  # 不是 type 定义行
                embed_line = lines[j].strip()
                # 嵌入字段格式: Element 或 Element `json:"-"`
                # 嵌入字段特点: 只有类型名, 没有字段名
                # 匹配带包名前缀的嵌入: objectbase.Widget
                # 匹配不带包名前缀的嵌入: Element
                embed_m = re.match(r'^([\w.]+)(?:\s+`.+`)?\s*$', embed_line)
                if embed_m:
                    full_name = embed_m.group(1)
                    # 提取结构体名 (去掉包名前缀)
                    parent = full_name.split('.')[-1]
                    # 排除基本类型、空结构体和内置类型
                    basic_types = ["int", "string", "bool", "byte", "rune", "float32", "float64", "int32", "int64", "uint32", "uint64", "uintptr"]
                    if parent and parent not in basic_types:
                        inheritance[child] = parent
                        break  # 找到直接父类就停止

    return inheritance


def _build_inheritance_map() -> tuple[dict[str, list[str]], dict[str, str]]:
    """构建完整的继承关系映射.

    Returns:
        (inheritance_map, file_map):
        - inheritance_map: {结构体名: [继承链]}
        - file_map: {结构体名: 所在文件路径}
    """
    inheritance_map = {}  # {结构体名: [直接父类]}
    file_map = {}  # {结构体名: 文件路径}

    # 扫描 widget、window、objectbase 和 edge 目录
    search_dirs = ["widget", "window", "objectbase", "edge"]
    for subdir in search_dirs:
        dir_path = XCGUI_SRC / subdir
        if not dir_path.exists():
            continue

        for go_file in sorted(dir_path.rglob("*.go")):
            if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
                continue

            # 记录结构体到文件的映射
            try:
                text = go_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # 提取所有结构体名
            for m in re.finditer(r'^type\s+(\w+)\s+struct\s*\{', text, re.MULTILINE):
                struct_name = m.group(1)
                file_map[struct_name] = str(go_file)

            # 解析继承关系
            inherits = _parse_struct_inheritance(go_file)
            inheritance_map.update(inherits)

    # 构建完整继承链
    def _get_chain(name: str, visited: set[str] | None = None) -> list[str]:
        """获取完整的继承链."""
        if visited is None:
            visited = set()
        if name in visited:
            return []
        visited.add(name)

        if name not in inheritance_map:
            return []

        parent = inheritance_map[name]
        chain = [parent]
        chain.extend(_get_chain(parent, visited))
        return chain

    # 为每个结构体计算完整继承链
    full_chains = {}
    for struct_name in set(list(inheritance_map.keys()) + list(file_map.keys())):
        chain = _get_chain(struct_name)
        if chain:
            full_chains[struct_name] = chain

    return full_chains, file_map


def _find_event_functions(go_file: Path) -> list[tuple[int, str, str]]:
    """在 Go 文件中查找所有事件函数 (AddEvent_ 或 Event_ 开头).

    Args:
        go_file: Go 文件路径

    Returns:
        [(行号, 函数名, 注释), ...]
    """
    results = []
    try:
        lines = go_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return results

    for i, line in enumerate(lines):
        # 匹配 AddEvent_ 或 Event_ 开头的函数定义
        # func (b *Button) AddEvent_BnClick(...)
        # func (w *WebView) Event_NavigationCompleted(...)
        m = re.search(r'func\s+\(\w+\s+\*\w+\)\s+((?:AddEvent_|Event_)\w+)\s*\(', line)
        if m:
            func_name = m.group(1)
            # 获取函数上方的注释
            comment = _get_func_comment(lines, i)
            results.append((i + 1, func_name, comment))

    return results


def _find_event_functions_in_dir(dir_path: Path, target_structs: list[str], include_event_prefix: bool = False) -> list[tuple[str, int, str, str]]:
    """在指定目录下搜索事件函数，且接收者是目标结构体之一.

    Args:
        dir_path: 目录路径
        target_structs: 目标结构体名列表
        include_event_prefix: 是否包含 Event_ 开头的函数

    Returns:
        [(结构体名, 行号, 函数名, 注释), ...]
    """
    results = []
    
    if not dir_path.exists():
        return results
    
    # 遍历目录下所有 Go 文件
    for go_file in sorted(dir_path.rglob("*.go")):
        if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
            continue
        
        try:
            lines = go_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        
        for i, line in enumerate(lines):
            # 匹配 AddEvent_ 或 Event_ 开头的函数定义
            # func (w *WebViewEventImpl) Event_NavigationCompleted(...)
            m = re.search(r'func\s+\(\w+\s+\*(\w+)\)\s+((?:AddEvent_|Event_)\w+)\s*\(', line)
            if m:
                receiver_type = m.group(1)  # 接收者类型名
                func_name = m.group(2)
                
                # 如果不包含 Event_ 开头的函数，跳过
                if not include_event_prefix and func_name.startswith("Event_"):
                    continue
                
                # 检查接收者类型是否在目标结构体列表中
                if receiver_type in target_structs:
                    # 获取函数上方的注释
                    comment = _get_func_comment(lines, i)
                    results.append((receiver_type, i + 1, func_name, comment))
    
    return results


def _find_all_functions_in_dir(dir_path: Path, target_structs: list[str], include_event_prefix: bool = False) -> list[tuple[str, int, str, str]]:
    """在指定目录下搜索所有方法函数，且接收者是目标结构体之一.

    Args:
        dir_path: 目录路径
        target_structs: 目标结构体名列表
        include_event_prefix: 是否包含 Event_ 开头的函数

    Returns:
        [(结构体名, 行号, 函数名, 注释), ...]
    """
    results = []
    
    if not dir_path.exists():
        return results
    
    # 遍历目录下所有 Go 文件
    for go_file in sorted(dir_path.rglob("*.go")):
        if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
            continue
        
        try:
            lines = go_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        
        for i, line in enumerate(lines):
            # 匹配所有方法定义
            # func (b *Button) MethodName(...)
            m = re.search(r'func\s+\(\w+\s+\*(\w+)\)\s+(\w+)\s*\(', line)
            if m:
                receiver_type = m.group(1)
                func_name = m.group(2)
                
                # 检查接收者类型是否在目标结构体列表中
                if receiver_type in target_structs:
                    # 只显示公开方法（首字母大写）
                    if func_name[0].isupper():
                        # 如果不包含 Event_ 开头的函数，跳过
                        if not include_event_prefix and func_name.startswith("Event_"):
                            continue
                        
                        # 获取函数上方的注释
                        comment = _get_func_comment(lines, i)
                        results.append((receiver_type, i + 1, func_name, comment))
    
    return results


def _list_object_funcs(obj_name: str, include_event_prefix: bool = False) -> None:
    """列出指定对象及其继承链上的所有公开方法.

    Args:
        obj_name: 对象名 (不区分大小写)
        include_event_prefix: 是否包含 Event_ 开头的函数
    """
    # 构建继承关系映射
    inheritance_chain, file_map = _build_inheritance_map()

    # 不区分大小写查找对象
    target_struct = None
    for name in file_map.keys():
        if name.lower() == obj_name.lower():
            target_struct = name
            break

    if not target_struct:
        color_print(f"  错误: 未找到对象 '{obj_name}'", C_RED)
        color_print(f"  提示: 可用对象请运行: python scripts/search.py list widgets", C_GRAY)
        return

    # 获取继承链
    chain = inheritance_chain.get(target_struct, [])
    all_structs = [target_struct] + chain

    color_print(f"  继承链: {' -> '.join(all_structs)}", C_CYAN)
    if include_event_prefix:
        color_print(f"  {C_GRAY}(包含 Event_ 开头的函数){C_RESET}")
    print()

    # 收集所有方法
    all_funcs = []  # [(结构体名, 行号, 函数名, 注释)]

    # 按目录分组处理（避免重复搜索）
    processed_dirs = set()
    
    for struct_name in all_structs:
        if struct_name not in file_map:
            continue

        go_file = Path(file_map[struct_name])
        if not go_file.exists():
            continue
        
        # 获取文件所在目录
        dir_path = go_file.parent
        
        # 如果已经处理过这个目录，跳过
        if str(dir_path) in processed_dirs:
            continue
        processed_dirs.add(str(dir_path))
        
        # 在当前目录及其子目录中搜索所有方法
        funcs = _find_all_functions_in_dir(dir_path, all_structs, include_event_prefix)
        all_funcs.extend(funcs)

    if not all_funcs:
        color_print(f"  未找到 {target_struct} 及其父类的方法", C_YELLOW)
        return

    # 计算最大函数名长度（用于对齐注释）
    max_func_len = max(len(func_name) for _, _, func_name, _ in all_funcs)

    # 按结构体分组显示
    current_struct = None
    for struct_name, line_no, func_name, comment in all_funcs:
        if struct_name != current_struct:
            current_struct = struct_name
            color_print(f"  {C_BOLD}{C_CYAN}【{struct_name}】{C_RESET}")

        # 显示方法名和注释（两列格式，注释对齐）
        padding = " " * (max_func_len - len(func_name))
        if comment:
            print(f"    {C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}{comment}{C_RESET}")
        else:
            rel_path = Path(file_map[struct_name]).relative_to(PROJECT_ROOT)
            print(f"    {C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}({rel_path}:{line_no}){C_RESET}")

    color_print(f"  共找到 {len(all_funcs)} 个方法", C_YELLOW)


def _list_object_events(obj_name: str, include_event_prefix: bool = False) -> None:
    """列出指定对象及其继承链上的所有事件函数 (AddEvent_ 或 Event_ 开头).

    Args:
        obj_name: 对象名 (不区分大小写)
        include_event_prefix: 是否包含 Event_ 开头的函数
    """
    # 构建继承关系映射
    inheritance_chain, file_map = _build_inheritance_map()

    # 不区分大小写查找对象
    target_struct = None
    for name in file_map.keys():
        if name.lower() == obj_name.lower():
            target_struct = name
            break

    if not target_struct:
        color_print(f"  错误: 未找到对象 '{obj_name}'", C_RED)
        color_print(f"  提示: 可用对象请运行: python scripts/search.py list widgets", C_GRAY)
        return

    # 获取继承链
    chain = inheritance_chain.get(target_struct, [])
    all_structs = [target_struct] + chain

    color_print(f"  继承链: {' -> '.join(all_structs)}", C_CYAN)
    if include_event_prefix:
        color_print(f"  {C_GRAY}(包含 Event_ 开头的函数){C_RESET}")
    print()

    # 收集所有事件
    all_events = []  # [(结构体名, 行号, 函数名, 注释)]

    # 按目录分组处理（避免重复搜索）
    processed_dirs = set()
    
    for struct_name in all_structs:
        if struct_name not in file_map:
            continue

        go_file = Path(file_map[struct_name])
        if not go_file.exists():
            continue
        
        # 获取文件所在目录
        dir_path = go_file.parent
        
        # 如果已经处理过这个目录，跳过
        if str(dir_path) in processed_dirs:
            continue
        processed_dirs.add(str(dir_path))
        
        # 在当前目录及其子目录中搜索事件函数
        events = _find_event_functions_in_dir(dir_path, all_structs, include_event_prefix)
        all_events.extend(events)

    if not all_events:
        color_print(f"  未找到 {target_struct} 及其父类的事件函数", C_YELLOW)
        return

    # 计算最大函数名长度（用于对齐注释）
    max_func_len = max(len(func_name) for _, _, func_name, _ in all_events)

    # 按结构体分组显示
    current_struct = None
    for struct_name, line_no, func_name, comment in all_events:
        if struct_name != current_struct:
            current_struct = struct_name
            color_print(f"  {C_BOLD}{C_CYAN}【{struct_name}】{C_RESET}")

        # 显示事件名和注释（两列格式，注释对齐）
        padding = " " * (max_func_len - len(func_name))
        if comment:
            print(f"    {C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}{comment}{C_RESET}")
        else:
            rel_path = Path(file_map[struct_name]).relative_to(PROJECT_ROOT)
            print(f"    {C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}({rel_path}:{line_no}){C_RESET}")

    color_print(f"  共找到 {len(all_events)} 个事件", C_YELLOW)


def search_list(subcommand: str, extra_arg: str = "", include_event_prefix: bool = False) -> None:
    """列出指定子命令下的所有文件/内容.

    Args:
        subcommand: 子命令 (widgets/packages/examples/events)
        extra_arg: 额外参数 (如对象名)
        include_event_prefix: 是否包含 Event_ 开头的函数
    """
    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  列出: {subcommand}", C_CYAN, bold=True)
    if extra_arg:
        color_print(f"  对象: {extra_arg}", C_CYAN)
    if include_event_prefix:
        color_print(f"  {C_GRAY}(包含 Event_ 开头的函数){C_RESET}")
    color_print(f"{'='*60}\n", C_CYAN)

    if subcommand == "widgets":
        widget_dir = XCGUI_SRC / "widget"
        found = 0
        if widget_dir.exists():
            for f in sorted(widget_dir.glob("*.go")):
                if f.name.endswith("_test.go") or f.name == "doc.go" or f.name == "deprecated.go":
                    continue
                # 读取文件提取类型名和注释
                text = f.read_text(encoding="utf-8", errors="replace")
                # 提取类型名: type Xxx struct {
                type_m = re.search(r'^type\s+(\w+)\s+struct\s*\{', text, re.MULTILINE)
                if not type_m:
                    continue
                type_name = type_m.group(1)
                found += 1
                # 匹配注释: // 描述文字. 或 // Button 按钮控件.
                comment_m = re.search(r'//\s*(?:[A-Za-z]+\s+)?([^.\n]+?)\.', text)
                if comment_m:
                    desc = comment_m.group(1).strip()
                    color_print(f"  {C_BOLD}{C_GREEN}{type_name:20}{C_RESET} {C_GRAY}{desc}{C_RESET}")
                else:
                    color_print(f"  {C_BOLD}{C_GREEN}{type_name:20}{C_RESET}")
        color_print(f"\n  {C_YELLOW}共 {found} 个控件{C_RESET}")

    elif subcommand == "examples":
        if EXAMPLE_SRC.exists():
            for cat_dir in sorted(EXAMPLE_SRC.iterdir()):
                if not cat_dir.is_dir():
                    continue
                color_print(f"\n  [{cat_dir.name}]", C_CYAN, bold=True)
                for ex_dir in sorted(cat_dir.iterdir()):
                    if ex_dir.is_dir():
                        # 跳过 deprecated.go、doc.go 和 _test.go 文件
                        go_files = [f for f in ex_dir.glob("*.go")
                                    if f.name not in {"deprecated.go", "doc.go"}
                                    and not f.name.endswith("_test.go")]
                        count = len(go_files)
                        desc = ""
                        if go_files:
                            # 使用辅助函数获取合并后的包注释
                            desc = _get_package_comment(go_files[0])
                        color_print(f"    {ex_dir.name:35} {C_GRAY}{desc} ({count} 文件){C_RESET}")

    elif subcommand == "packages":
        # 递归查找所有包含 .go 文件的目录（排除测试文件和废弃文件）
        pkg_dirs = set()
        for go_file in XCGUI_SRC.rglob("*.go"):
            if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
                continue
            # 排除 main 包
            try:
                content = go_file.read_text(encoding="utf-8", errors="replace")
                if re.search(r'^package\s+main\s*$', content, re.MULTILINE):
                    continue
            except Exception:
                pass
            pkg_dirs.add(go_file.parent)

        found = 0
        for d in sorted(pkg_dirs):
            rel_path = d.relative_to(XCGUI_SRC)
            # 计数该目录下符合条件的 .go 文件
            go_count = len([f for f in d.glob("*.go")
                            if f.name not in {"deprecated.go", "doc.go"}
                            and not f.name.endswith("_test.go")])
            found += 1
            # 读取 doc.go 注释 (支持多行注释)
            desc = ""
            doc_file = d / "doc.go"
            if doc_file.exists():
                text = doc_file.read_text(encoding="utf-8", errors="replace")
                # 提取 Package 注释块 (多行)
                lines = text.split('\n')
                in_pkg_comment = False
                comment_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('// Package'):
                        in_pkg_comment = True
                        # 提取 Package 后面的描述
                        m = re.search(r'//\s*Package\s+\w+\s+(.*)', line)
                        if m and m.group(1).strip():
                            comment_lines.append(m.group(1).strip())
                    elif in_pkg_comment:
                        if stripped.startswith('//'):
                            content = stripped[2:].strip()
                            if content:
                                comment_lines.append(content)
                        else:
                            # 非注释行，结束
                            break
                if comment_lines:
                    # 合并多行，去除多余空白
                    desc = re.sub(r'\s+', ' ', ' '.join(comment_lines)).strip()
            color_print(f"  {C_BOLD}{C_GREEN}{str(rel_path):30}{C_RESET} {C_GRAY}{go_count:>4} 文件  {desc}{C_RESET}")

        color_print(f"\n  {C_YELLOW}共 {found} 个包{C_RESET}")

    elif subcommand == "windows":
        # 列出 window 包的所有公开对象
        window_dir = XCGUI_SRC / "window"
        found = 0
        if window_dir.exists():
            for f in sorted(window_dir.glob("*.go")):
                if f.name.endswith("_test.go") or f.name == "doc.go" or f.name == "deprecated.go":
                    continue
                # 读取文件提取类型名和注释
                text = f.read_text(encoding="utf-8", errors="replace")
                # 提取类型名: type Xxx struct { 或 type Xxx = ...
                # 只匹配大写字母开头的公开类型
                type_patterns = [
                    re.search(r'^type\s+([A-Z]\w*)\s+struct\s*\{', text, re.MULTILINE),
                    re.search(r'^type\s+([A-Z]\w*)\s*=\s*\w+', text, re.MULTILINE),
                ]
                type_name = None
                for m in type_patterns:
                    if m:
                        type_name = m.group(1)
                        break
                
                if not type_name:
                    continue
                
                found += 1
                # 尝试从 package 注释或文件头部注释获取描述
                desc = _get_package_comment(f)
                if not desc:
                    # 尝试从文件中的第一个类型注释获取
                    comment_m = re.search(r'//\s*(?:[A-Za-z]+\s+)?([^.\n]+?)\.', text)
                    if comment_m:
                        desc = comment_m.group(1).strip()
                
                if desc:
                    color_print(f"  {C_BOLD}{C_GREEN}{type_name:20}{C_RESET} {C_GRAY}{desc}{C_RESET}")
                else:
                    color_print(f"  {C_BOLD}{C_GREEN}{type_name:20}{C_RESET}")
        color_print(f"\n  {C_YELLOW}共 {found} 个窗口对象{C_RESET}")

    elif subcommand == "events":
        if not extra_arg:
            color_print(f"  错误: events 命令需要指定对象名", C_RED)
            color_print(f"  用法: python scripts/search.py list events <对象名>", C_GRAY)
            return
        # 列出指定对象的所有事件 (含继承)
        _list_object_events(extra_arg, include_event_prefix)

    elif subcommand == "funcs":
        if not extra_arg:
            color_print(f"  错误: funcs 命令需要指定对象名", C_RED)
            color_print(f"  用法: python scripts/search.py list funcs <对象名>", C_GRAY)
            return
        # 列出指定对象的所有方法 (含继承)
        _list_object_funcs(extra_arg, include_event_prefix)


def main():
    parser = argparse.ArgumentParser(
        description="xcgui 源码搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  func <keyword>       搜索函数定义 (支持中英文, 多关键词用 / 分割)
  const <keyword>      搜索常量定义 (支持中英文, 多关键词用 / 分割)
  event <keyword>      搜索事件相关代码 (支持中英文, 多关键词用 / 分割)
  example <keyword>    搜索示例代码 (在 xcgui-example 中搜索, 支持中英文, 多关键词用 / 分割)

列表子命令:
  list widgets       列出 widget 包所有公开对象
  list windows       列出 window 包所有公开对象
  list packages      列出所有源码包
  list examples      列出所有示例
  list events <对象名>       列出指定对象的所有事件 (含继承链, 不含 Event 开头函数)
  list funcs <对象名>        列出指定对象的所有方法 (含继承链, 含事件, 不含 Event 开头函数)

关键词规则:
  - 用 / 分割多个关键词，会同时匹配所有关键词, 支持中英文, 不区分大小写
  - 关键词除了可以搜索函数/常量/事件定义外, 还可以搜索它们的注释, 在关键词含中文时触发
  - `list funcs <对象名>` 和 `list events <对象名>` 命令默认是不会列出以 `Event` 开头的函数的, 除非在最后面再加个 `all` 参数, 一般不需要 `Event` 开头的函数, 这两个命令都会列出 `AddEvent` 开头的函数, 这种事件添加方式更常用

示例:
  python scripts/search.py func Center               # 搜索函数名关键词 (单个)
  python scripts/search.py func button/gettext       # 搜索函数名关键词 (多个用 / 分割)
  python scripts/search.py func 最大化                # 用中文注释搜索函数
  python scripts/search.py func 窗口/居中             # 用中文注释搜索函数 (多个关键词)
  python scripts/search.py const Window_Style        # 搜索常量关键词
  python scripts/search.py const button/check        # 搜索常量关键词 (多个)
  python scripts/search.py const 阴影窗口             # 用中文注释搜索常量
  python scripts/search.py event BnClick             # 搜索事件函数名关键词
  python scripts/search.py event tree/select         # 搜索事件函数名关键词 (多个)
  python scripts/search.py event 窗口消息过程         # 搜索事件函数中文注释
  python scripts/search.py example TabBar            # 搜索示例关键词
  python scripts/search.py example event/TabBar      # 搜索示例关键词 (多个)
  python scripts/search.py list widgets              # 列出所有控件
  python scripts/search.py list events button        # 列出 button 的所有事件 (不含 Event 开头函数)
  python scripts/search.py list funcs button         # 列出 button 的所有方法 (不含 Event 开头函数)
        """,
    )
    parser.add_argument(
        "command",
        choices=["func", "const", "event", "example", "list"],
        help="搜索命令",
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="命令参数 (keyword 或多个参数)",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="启用彩色输出",
    )

    args = parser.parse_args()

    # 如果指定了 --color，启用颜色输出
    if args.color:
        _enable_color(True)

    # 验证路径
    if not SOURCE_DIR.exists():
        color_print(f"错误: source 目录不存在: {SOURCE_DIR}", C_RED)
        color_print("请确保在项目根目录 (go-xcgui-dev) 下运行此脚本", C_RED)
        sys.exit(1)

    # 处理参数
    if args.command == "list":
        # list 命令: list <subcommand> [extra_arg] [all]
        if len(args.args) == 0:
            color_print("错误: list 命令需要子类型 (widgets/windows/packages/examples/events/funcs)", C_RED)
            sys.exit(1)
        subcommand = args.args[0].lower()
        
        # 解析 extra_arg 和 all 参数
        include_event_prefix = False
        if len(args.args) > 1:
            # 检查最后一个参数是否为 "all"
            if args.args[-1].lower() == "all":
                include_event_prefix = True
                # extra_arg 是除去 subcommand 和 "all" 之后的部分
                extra_arg = " ".join(args.args[1:-1]) if len(args.args) > 2 else ""
            else:
                # 没有 "all" 参数
                extra_arg = " ".join(args.args[1:])
        else:
            extra_arg = ""
        
        search_list(subcommand, extra_arg, include_event_prefix)
    else:
        # 其他命令: <command> <keyword>
        if len(args.args) == 0:
            color_print(f"错误: {args.command} 命令需要关键词参数", C_RED)
            sys.exit(1)
        keyword = " ".join(args.args)

        if args.command == "func":
            search_func(keyword)
        elif args.command == "const":
            search_const(keyword)
        elif args.command == "event":
            search_event(keyword)
        elif args.command == "example":
            search_example(keyword)


if __name__ == "__main__":
    main()
