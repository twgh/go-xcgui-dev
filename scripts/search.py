#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xcgui 源码搜索工具 — 查函数 / 常量 / 事件 / 类型 / 结构体 / 示例.

用法:
    python scripts/search.py func <keyword>         # 搜索函数定义
    python scripts/search.py const <keyword>        # 搜索常量定义
    python scripts/search.py event <keyword>        # 搜索事件相关
    python scripts/search.py type <keyword>         # 搜索类型定义 (struct/interface/等)
    python scripts/search.py example <keyword>      # 搜索示例代码
    python scripts/search.py example_name <keyword> # 搜索示例名或包注释
    python scripts/search.py list <keyword>         # 列表, 可填: widgets/windows/packages/examples/events/funcs/objects/pkg_funcs/pkg_doc
    python scripts/search.py list events <对象名>   # 列出指定对象的所有事件 (含继承链, 不含 Event 开头函数, edge目录自动包含 Event 开头函数)
    python scripts/search.py list funcs <对象名>    # 列出指定对象的所有方法 (含继承链, 含事件, 不含 Event 开头函数, edge目录自动包含 Event 开头函数)
    python scripts/search.py list objects <包名>    # 列出指定包的所有公开对象 (含描述)
    python scripts/search.py list pkg_funcs <包名>  # 列出指定包的所有公开非对象函数 (包级函数, 无接收者)
    python scripts/search.py list pkg_doc <包名>    # 输出指定包 doc.go 的完整包文档 (保留 Markdown 结构)

说明:
    list funcs / list events 适用于 source/xcgui 下全部包的对象; 同名对象可用
    "包名.对象名" 精确指定, 例如: python scripts/search.py list funcs app.App
    const 覆盖 source/xcgui 下全部包 (xcc / wapi / edge / xc 等); 英文匹配常量定义行,
    含中文时额外匹配常量分组/条目注释.
    list packages 只显示每个包注释的首段摘要; 需要全文时用 list pkg_doc <包名>,
    如: python scripts/search.py list pkg_doc wapi/d2d

示例:
    python scripts/search.py func button/gettext       # 搜索函数名关键词 (多个关键词用 / 分割)
    python scripts/search.py func 窗口/居中             # 用中文搜索函数注释 (多个关键词用 / 分割)
    python scripts/search.py const button/check        # 搜索常量关键词 (多个关键词用 / 分割)
    python scripts/search.py const 窗口/最小化          # 用中文搜索常量注释 (多个关键词用 / 分割)
    python scripts/search.py event tree/select         # 搜索事件函数名关键词 (多个关键词用 / 分割)
    python scripts/search.py event 窗口/鼠标光标        # 搜索事件函数中文注释关键词 (多个关键词用 / 分割)
    python scripts/search.py type WebViewOptions       # 搜索type名关键词 (多个关键词用 / 分割)
    python scripts/search.py type webview/选项         # 用中文搜索type注释
    python scripts/search.py example event/TabBar      # 搜索示例内容关键词 (多个关键词用 / 分割)
    python scripts/search.py example 按钮/选中/事件     # 搜索示例内容关键词 (多个关键词用 / 分割)
    python scripts/search.py list widgets              # 列出 widget 包所有公开对象
    python scripts/search.py list windows              # 列出 window 包所有公开对象
    python scripts/search.py list packages             # 列出所有源码包
    python scripts/search.py list examples             # 列出所有示例
    python scripts/search.py list events button        # 列出 Button 的所有事件函数名
    python scripts/search.py list funcs button         # 列出 Button 的所有方法名(含继承链,含事件)
    python scripts/search.py list objects window       # 列出 window 包所有公开对象 (含描述)
    python scripts/search.py list pkg_funcs svg        # 列出 svg 包所有公开非对象函数 (包级函数)
    python scripts/search.py list funcs app.App        # 查看非 widget/window 包对象的方法
    python scripts/search.py list funcs xc.POINT       # 用包名区分跨包同名对象
    python scripts/search.py list pkg_doc wapi/d2d     # 查看 wapi/d2d 的完整包文档
    python scripts/search.py example_name 美化/编辑框   # 搜索示例包注释
    python scripts/search.py example_name draw/button  # 搜索示例名
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
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


def _has_go_files(base: Path) -> bool:
    """目录是否含至少一个 .go 文件 (源码完整性的最低校验).

    目录存在不代表源码完整: 下载中断会留下空目录, 此时应提示重新下载,
    而不是让各个命令静默返回 "查无结果" 或抛出 FileNotFoundError.
    """
    if not base.is_dir():
        return False
    try:
        return next(base.rglob("*.go"), None) is not None
    except OSError:
        return False


def _source_subdirs(exclude: set[str] | None = None) -> list[str]:
    """列出 source/xcgui 下的包目录名; 目录缺失时返回空列表而不是抛异常."""
    if not XCGUI_SRC.is_dir():
        return []
    return [
        d.name for d in XCGUI_SRC.iterdir()
        if d.is_dir() and not d.name.startswith(".")
        and not (exclude and d.name in exclude)
    ]


def find_go_files(base: Path, subdirs: list[str] | None = None) -> list[Path]:
    """查找指定子目录下的所有 .go 文件."""
    files = []
    if not base.is_dir():
        return files
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
    m = re.search(r'func\s+\((?:\w+\s+)?\*?(\w+)\)\s+(\w+)', func_line)
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


def _iter_pkg_dirs() -> list[Path]:
    """列出 source/xcgui 下所有含有效 .go 文件的包目录 (排除 main 包)."""
    pkg_dirs: set[Path] = set()
    if not XCGUI_SRC.exists():
        return []
    for go_file in XCGUI_SRC.rglob("*.go"):
        if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
            continue
        try:
            content = go_file.read_text(encoding="utf-8", errors="replace")
            if re.search(r'^package\s+main\s*$', content, re.MULTILINE):
                continue
        except Exception:
            pass
        pkg_dirs.add(go_file.parent)
    return sorted(pkg_dirs)


def _get_package_doc_lines(doc_file: Path) -> list[str]:
    """提取 doc.go 中 // Package 注释块的原始行.

    去掉 "// " 前缀但保留空行、Markdown 标题与代码缩进, 供摘要和全文两种输出共用.
    """
    try:
        text = doc_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines: list[str] = []
    in_pkg_comment = False
    for line in text.splitlines():
        stripped = line.strip()
        pkg_m = re.match(r'//\s*[Pp]ackage\s+\w+\s*(.*)', stripped)
        if pkg_m and not in_pkg_comment:
            in_pkg_comment = True
            lines.append(pkg_m.group(1).strip())
            continue
        if not in_pkg_comment:
            continue
        if not stripped.startswith("//"):
            break
        content = stripped[2:]
        # 去掉一个分隔空格, 保留更深缩进 (代码块靠它表达)
        lines.append(content[1:] if content.startswith(" ") else content)

    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _package_doc_summary(lines: list[str], limit: int = 110) -> tuple[str, bool]:
    """把包注释压成一句摘要, 返回 (摘要, 是否有更多内容).

    只取第一个 Markdown 标题 / 空行之前的第一段; 过长时优先在句号处断开.
    """
    para: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("# "):
            if para:
                break
            continue
        para.append(stripped)

    summary = re.sub(r'\s+', ' ', ' '.join(para)).strip()
    full = re.sub(r'\s+', ' ', ' '.join(x.strip() for x in lines if x.strip())).strip()
    if not summary:
        return full[:limit], len(full) > limit

    if len(summary) > limit:
        cut = summary[:limit]
        for sep in ("。", "；", ". ", "; "):
            pos = cut.rfind(sep)
            if pos >= limit * 0.5:
                summary = cut[:pos + len(sep)].rstrip()
                break
        else:
            summary = cut.rstrip()
        return summary, True
    return summary, len(full) > len(summary)


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
    search_dirs = _source_subdirs({"xcc"})

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
                # ── 中文搜索：注释 + 函数定义行 (中英关键词均不区分大小写) ──
                comment = _get_func_comment(lines, func_idx).lower()
                line_lower = line.lower()
                if not all(kw.lower() in comment or kw.lower() in line_lower for kw in keywords):
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


def search_type(keyword: str) -> None:
    """搜索类型定义 (struct/interface/等).

    搜索范围:
        - source/xcgui/ 下的所有子目录, 不含.开头的

    关键词规则:
        - 用 / 分割多个关键词，类型必须同时匹配所有关键词
        - 中文关键词：搜索类型名上方的注释
        - 英文关键词：搜索类型名 (type Xxx ...)
    """
    # 判断是否为中文搜索
    is_chinese = bool(re.search(r'[\u4e00-\u9fff]', keyword))

    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    # 动态获取所有子目录
    search_dirs = _source_subdirs()

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索类型: \"{keyword}\"", C_CYAN, bold=True)
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
        for i, line in enumerate(lines):
            # 匹配类型定义行: type Xxx struct { / type Xxx interface { / type Xxx = ...
            m = re.match(r'^\s*type\s+(\w+)\s+', line)
            if not m:
                continue
            type_name = m.group(1)

            # 跳过未导出的类型（小写字母开头）
            if not type_name[0].isupper():
                continue

            if is_chinese:
                # 中文搜索：注释 + 类型定义行 (中英关键词均不区分大小写)
                comment = _get_func_comment(lines, i).lower()
                line_lower = line.lower()
                if not all(kw.lower() in comment or kw.lower() in line_lower for kw in keywords):
                    continue
            else:
                # 英文搜索：在类型定义行中搜索（含类型名），不区分大小写
                line_lower = line.lower()
                if not all(kw.lower() in line_lower for kw in keywords):
                    continue

            relative = go_file.relative_to(PROJECT_ROOT)
            found += 1
            color_print(f"  {C_MAGENTA}{relative}{C_RESET}:{C_GREEN}{i+1}{C_RESET}")

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
                        if comment_start == i:
                            j -= 1
                            continue
                        else:
                            break
                    else:
                        break

            # 2. 显示注释块
            for j in range(comment_start, i):
                print(f"    {C_GRAY}{lines[j].rstrip()}{C_RESET}")

            # 3. 显示类型定义行
            print(f"    {C_BOLD}{lines[i].rstrip()}{C_RESET}")

            # 4. 显示字段块 (struct/interface 用 {} 包裹)
            if '{' in lines[i]:
                depth = lines[i].count('{') - lines[i].count('}')
                k = i + 1
                while k < len(lines) and depth > 0:
                    ln = lines[k]
                    print(f"    {ln.rstrip()}")
                    depth += ln.count('{') - ln.count('}')
                    k += 1
            print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的类型定义", C_RED)


# ── 常量索引 ──────────────────────────────────────────────
_CONST_BLOCK_RE = re.compile(r"^const\s*\(")
_CONST_SINGLE_RE = re.compile(r"^const\s+[A-Za-z_]\w*")
_CONST_ENTRY_RE = re.compile(r"^[A-Za-z_]\w*")
_CONST_SKIP_FILES = {"deprecated.go", "doc.go"}


@lru_cache(maxsize=None)
def _const_file_context(go_file: Path):
    """解析单个 go 文件的常量上下文, 结果按文件缓存.

    返回 (所有行, 常量定义行索引集合, 常量注释行索引集合).
    只把 const (...) 块内条目与单行 const X = ... 视为常量定义, 因此不会把
    函数体里的赋值语句误判为常量; 中文检索只覆盖 const 块内及紧邻声明的注释.
    """
    try:
        lines = go_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return (), frozenset(), frozenset()

    def_lines = set()
    comment_lines = set()
    pending = []            # 连续注释行 (允许与声明之间夹空行)
    type_doc = []           # 常量类型声明上方的分组说明 (type Xxx uint32 紧接着 const 块)
    in_block = False
    in_raw_string = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # const 块内的多行原始字符串, 内容行不属于常量声明
        if in_block and in_raw_string:
            if "`" in line:
                in_raw_string = False
            continue

        if _CONST_BLOCK_RE.match(stripped):
            in_block = True
            comment_lines.update(pending)   # const ( 上方的分组说明
            comment_lines.update(type_doc)  # type Xxx uint32 上方的分组说明
            type_doc = []
            pending = []
            continue

        if in_block and stripped.startswith(")"):
            in_block = False
            in_raw_string = False
            pending = []
            continue

        if stripped.startswith("//"):
            pending.append(i)
            if in_block:
                comment_lines.add(i)
            continue

        if not stripped:
            continue

        is_def = (
            bool(_CONST_ENTRY_RE.match(stripped)) if in_block
            else bool(_CONST_SINGLE_RE.match(stripped))
        )
        if is_def:
            def_lines.add(i)
            comment_lines.update(pending)
            # 只看代码部分: 注释里出现反引号 (如 "// `键") 不应被当成原始字符串起始
            code_part = stripped.split("//", 1)[0]
            if in_block and code_part.count("`") % 2:
                in_raw_string = True
        # 常量往往按类型分组: "// 窗口样式" + type WS_ uint32 + const (...)
        type_doc = list(pending) if stripped.startswith("type ") else []
        pending = []

    return tuple(lines), frozenset(def_lines), frozenset(comment_lines)


def search_const(keyword: str) -> None:
    """搜索常量定义.

    搜索范围: source/xcgui 下全部包的全部 go 文件 (排除 deprecated.go / doc.go / _test.go),
    自动识别 const (...) 块与单行 const 声明.

    关键词规则:
        - 用 / 分割多个关键词，常量必须同时匹配所有关键词
        - 英文只匹配常量定义行; 含中文时同时匹配常量定义行及其相邻注释
    """
    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索常量: \"{keyword}\"", C_CYAN, bold=True)
    if len(keywords) > 1:
        color_print(f"  (关键词: {', '.join(keywords)})", C_GRAY)
    color_print(f"{'='*60}\n", C_CYAN)

    found = 0
    is_chinese = any(re.search(r'[\u4e00-\u9fff]', kw) for kw in keywords)

    # 全库枚举: xcc / wapi / edge / xc 等所有含 const 声明的包
    go_files = []
    if XCGUI_SRC.exists():
        for go_file in sorted(XCGUI_SRC.rglob("*.go")):
            if go_file.name in _CONST_SKIP_FILES or go_file.name.endswith("_test.go"):
                continue
            go_files.append(go_file)

    for go_file in go_files:
        lines, def_lines, comment_lines = _const_file_context(go_file)
        if not lines:
            continue

        for i, line in enumerate(lines):
            is_const_def = i in def_lines
            is_comment_line = line.strip().startswith("//")

            # 英文只匹配常量定义行; 中文额外匹配与常量声明相邻的注释行
            if is_chinese:
                if not is_const_def and not (is_comment_line and i in comment_lines):
                    continue
            elif not is_const_def:
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

    # 动态枚举全部源码包: 事件函数目前集中在 widget / window / edge,
    # 但不写死目录, 以便上游源码新增事件时自动纳入检索
    search_dirs = _source_subdirs()

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
                # ── 中文搜索：注释 + 函数定义行 (中英关键词均不区分大小写) ──
                comment = _get_func_comment(lines, i).lower()
                line_lower = line.lower()
                if not all(kw.lower() in comment or kw.lower() in line_lower for kw in keywords):
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


def search_example_name(keyword: str) -> None:
    """搜索示例名或包注释.

    搜索策略:
        - 关键词不含中文: 搜索示例目录名 (example_name <keyword>)
        - 关键词含中文: 搜索示例的包注释 (package 上方的注释)

    关键词规则:
        - 用 / 分割多个关键词，示例必须同时匹配所有关键词
        - 不区分大小写
    """
    # 分割关键词
    keywords = [k.strip() for k in keyword.split('/') if k.strip()]

    # 判断是否为中文搜索
    is_chinese = any(re.search(r'[\u4e00-\u9fff]', kw) for kw in keywords)

    color_print(f"\n{'='*60}", C_CYAN)
    color_print(f"  搜索示例{'注释' if is_chinese else '名'}: \"{keyword}\"", C_CYAN, bold=True)
    if len(keywords) > 1:
        color_print(f"  (关键词: {', '.join(keywords)})", C_GRAY)
    color_print(f"{'='*60}\n", C_CYAN)

    if not EXAMPLE_SRC.exists():
        color_print(f"  错误: 示例目录不存在: {EXAMPLE_SRC}", C_RED)
        return

    found = 0

    # 递归收集所有包含 main 包的示例目录
    example_dirs: list[Path] = []

    def _is_main_example(d: Path) -> bool:
        """目录是否包含 main 包 (以 package main 声明)."""
        for f in d.glob("*.go"):
            if f.name in {"deprecated.go", "doc.go"} or f.name.endswith("_test.go"):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if re.search(r"^package\s+main\b", text, re.MULTILINE):
                return True
        return False

    def _walk(d: Path) -> None:
        for sub in sorted(d.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            if _is_main_example(sub):
                example_dirs.append(sub)
            else:
                # 中间分组目录, 继续向下寻找示例
                _walk(sub)

    _walk(EXAMPLE_SRC)

    for ex_dir in example_dirs:
        # 示例名 (目录名)
        example_name = ex_dir.name

        # 获取示例的包注释
        go_files = [f for f in ex_dir.glob("*.go")
                    if f.name not in {"deprecated.go", "doc.go"}
                    and not f.name.endswith("_test.go")]
        package_comment = _get_package_comment(go_files[0]) if go_files else ""

        # 根据搜索类型进行匹配
        if is_chinese:
            # 中文搜索: 在包注释中搜索
            if not package_comment:
                continue
            # 检查所有关键词是否都在包注释中 (不区分大小写)
            if not all(kw.lower() in package_comment.lower() for kw in keywords):
                continue
        else:
            # 英文搜索: 在示例名 (目录名) 中搜索
            if not all(kw.lower() in example_name.lower() for kw in keywords):
                continue

        # 找到匹配
        found += 1
        relative = ex_dir.relative_to(PROJECT_ROOT)

        # 显示结果
        color_print(f"  {C_BOLD}{C_MAGENTA}{relative}{C_RESET}")
        if package_comment:
            print(f"    {C_GRAY}包注释: {package_comment}{C_RESET}")
        print()

    if found:
        color_print(f"  共找到 {found} 个匹配", C_YELLOW)
    else:
        color_print(f"  未找到匹配 \"{keyword}\" 的示例", C_RED)


# ── 对象索引 (list funcs / list events) ───────────────────────────
# 索引动态覆盖 source/xcgui 下全部包, 主键为 (包名, 类型名), 避免跨包同名对象互相覆盖.
# 对象包含 struct / interface / 别名 / 具名基础类型; 方法同时支持指针与值接收者.


@dataclass(frozen=True)
class ObjectEntry:
    """索引中的一个类型对象."""

    name: str
    pkg: str
    file: Path
    kind: str
    is_public: bool

    @property
    def key(self) -> tuple[str, str]:
        return (self.pkg, self.name)

    @property
    def label(self) -> str:
        return f"{self.pkg}.{self.name}" if self.pkg else self.name


@dataclass
class ObjectIndex:
    """全库对象索引: 类型、继承链与方法."""

    entries: dict[tuple[str, str], ObjectEntry]
    by_name: dict[str, list[ObjectEntry]]
    parents: dict[tuple[str, str], tuple[str, str]]
    chains: dict[tuple[str, str], list[tuple[str, str]]]
    funcs: dict[tuple[str, str], list[tuple[int, str, str, Path]]]


_TYPE_DEF_RE = re.compile(r"^type\s+(\w+)\s+(.*)$", re.M)
# 允许省略接收者名、允许值接收者 (如 func (c ComProc) AddRef())
_METHOD_LINE_RE = re.compile(r"^func\s+\(\s*(?:\w+\s+)?\*?(\w+)\s*\)\s+([A-Z]\w*)\s*\(")
_EMBED_RE = re.compile(r"^([\w.]+)(?:\s+`[^`]*`)?\s*$")
_PREFERRED_PKGS = ("widget", "window", "objectbase", "edge")
_BASIC_TYPES = {
    "int", "int8", "int16", "int32", "int64", "uint", "uint8", "uint16",
    "uint32", "uint64", "uintptr", "string", "bool", "byte", "rune",
    "float32", "float64", "complex64", "complex128", "any", "error",
}
_SKIP_GO_FILES = {"deprecated.go", "doc.go"}


def _is_source_go(go_file: Path) -> bool:
    """是否为参与索引的源码文件 (排除废弃/文档/测试文件)."""
    return go_file.name not in _SKIP_GO_FILES and not go_file.name.endswith("_test.go")


def _iter_source_files():
    """遍历 source/xcgui 下全部 Go 文件, 产出 (包名, 文件路径).

    包名为顶层目录名; 根目录下的 .go 文件包名记为空字符串.
    """
    if not XCGUI_SRC.is_dir():
        return
    for go_file in sorted(XCGUI_SRC.glob("*.go")):
        if _is_source_go(go_file):
            yield "", go_file
    for pkg_dir in sorted(p for p in XCGUI_SRC.iterdir()
                          if p.is_dir() and not p.name.startswith(".")):
        for go_file in sorted(pkg_dir.rglob("*.go")):
            if _is_source_go(go_file):
                yield pkg_dir.name, go_file


def _type_kind(rest: str) -> str:
    """根据类型定义行的剩余部分判断类型种类."""
    if rest.startswith("struct"):
        return "struct"
    if rest.startswith("interface"):
        return "interface"
    if rest.startswith("func"):
        return "func"
    if rest.startswith("="):
        return "alias"
    return "named"


def _parse_embeddings(text: str) -> list[tuple[str, str]]:
    """提取 [(子类型名, 嵌入父类型全名)].

    与原逻辑一致只取第一个嵌入字段 (xcgui 采用单一继承链模型);
    父类型可能带包名前缀, 如 objectbase.Widget.
    """
    lines = text.splitlines()
    results = []
    for i, line in enumerate(lines):
        m = re.match(r"^type\s+(\w+)\s+struct\s*\{", line.strip())
        if not m:
            continue
        child = m.group(1)
        brace = 0
        opened = False
        for j in range(i, min(i + 50, len(lines))):
            brace += lines[j].count("{") - lines[j].count("}")
            if "{" in lines[j]:
                opened = True
            if opened and brace == 0:
                break
            if j == i:
                continue
            em = _EMBED_RE.match(lines[j].strip())
            if not em:
                continue
            parent = em.group(1).split(".")[-1]
            if parent and parent not in _BASIC_TYPES:
                results.append((child, em.group(1)))
                break
    return results


def _resolve_parent_key(
    pkg: str,
    parent_full: str,
    entries: dict[tuple[str, str], ObjectEntry],
    by_name: dict[str, list[ObjectEntry]],
    pkg_aliases: dict[str, str],
) -> tuple[str, str] | None:
    """把嵌入字段解析为 (包名, 类型名), 优先同包/带包名前缀的精确匹配."""
    if "." in parent_full:
        prefix, pname = parent_full.rsplit(".", 1)
        target_pkg = pkg_aliases.get(prefix)
        if target_pkg and (target_pkg, pname) in entries:
            return (target_pkg, pname)
        if (prefix, pname) in entries:
            return (prefix, pname)
        candidates = by_name.get(pname.lower(), [])
    else:
        pname = parent_full
        if (pkg, pname) in entries:
            return (pkg, pname)
        candidates = by_name.get(pname.lower(), [])

    if len(candidates) == 1:
        return candidates[0].key
    if candidates:
        same = [e for e in candidates if e.pkg == pkg]
        if len(same) == 1:
            return same[0].key
        return min(candidates, key=lambda e: (
            _PREFERRED_PKGS.index(e.pkg)
            if e.pkg in _PREFERRED_PKGS else len(_PREFERRED_PKGS),
            e.pkg,
        )).key
    return None


@lru_cache(maxsize=1)
def build_object_index() -> ObjectIndex:
    """扫描全库构建对象索引 (一次命令内只扫描一次, 结果缓存)."""
    entries: dict[tuple[str, str], ObjectEntry] = {}
    by_name: dict[str, list[ObjectEntry]] = defaultdict(list)
    funcs: dict[tuple[str, str], list[tuple[int, str, str, Path]]] = defaultdict(list)
    raw_parents: list[tuple[str, str, str]] = []  # (包名, 子类型名, 父类型全名)
    pkg_aliases: dict[str, str] = {}  # Go package 名 -> 顶层目录名

    for pkg, go_file in _iter_source_files():
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()

        package_m = re.search(r"^package\s+(\w+)", text, re.M)
        if package_m and pkg:
            pkg_aliases.setdefault(package_m.group(1), pkg)

        for m in _TYPE_DEF_RE.finditer(text):
            name, rest = m.group(1), m.group(2).strip()
            entry = ObjectEntry(name, pkg, go_file, _type_kind(rest), name[0].isupper())
            if entry.key not in entries:
                by_name[name.lower()].append(entry)
            entries[entry.key] = entry

        for child, parent_full in _parse_embeddings(text):
            raw_parents.append((pkg, child, parent_full))

        for line_no, line in enumerate(lines, 1):
            fm = _METHOD_LINE_RE.match(line)
            if not fm:
                continue
            recv, func_name = fm.group(1), fm.group(2)
            comment = _get_func_comment(lines, line_no - 1)
            funcs[(pkg, recv)].append((line_no, func_name, comment, go_file))

    parents: dict[tuple[str, str], tuple[str, str]] = {}
    for pkg, child, parent_full in raw_parents:
        child_key = (pkg, child)
        if child_key not in entries:
            continue
        parent_key = _resolve_parent_key(pkg, parent_full, entries, by_name, pkg_aliases)
        if parent_key and parent_key != child_key:
            parents[child_key] = parent_key

    chains: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for key in entries:
        chain = []
        seen = {key}
        current = parents.get(key)
        while current and current not in seen:
            chain.append(current)
            seen.add(current)
            current = parents.get(current)
        if chain:
            chains[key] = chain

    return ObjectIndex(
        entries=dict(entries),
        by_name=dict(by_name),
        parents=parents,
        chains=chains,
        funcs=dict(funcs),
    )


def resolve_object(index: ObjectIndex, query: str) -> tuple[ObjectEntry | None, list[ObjectEntry]]:
    """解析对象名, 支持 "对象名" 与 "包名.对象名".

    返回 (最匹配项, 全部同名候选). 同名时优先公开类型、方法数多者,
    再按 widget/window/objectbase/edge 的常用顺序选择.
    """
    pkg_filter = None
    name = query.strip()
    if "." in name:
        pkg_filter, name = name.rsplit(".", 1)
    candidates = list(index.by_name.get(name.lower(), []))
    if pkg_filter:
        candidates = [e for e in candidates if e.pkg.lower() == pkg_filter.lower()]
    if not candidates:
        return None, []

    exact = [e for e in candidates if e.name == name]
    if exact:
        candidates = exact
    public = [e for e in candidates if e.is_public]
    if public:
        candidates = public

    def score(entry: ObjectEntry):
        method_count = len(index.funcs.get(entry.key, ()))
        order = (_PREFERRED_PKGS.index(entry.pkg)
                 if entry.pkg in _PREFERRED_PKGS else len(_PREFERRED_PKGS))
        return (method_count, -order, entry.pkg)

    return max(candidates, key=score), candidates


def _is_object_in_edge(obj_name: str) -> bool:
    """对象是否属于 edge 包 (edge 事件以 Event_ 开头, 需默认包含)."""
    entry, _ = resolve_object(build_object_index(), obj_name)
    return bool(entry and entry.pkg == "edge")


def _chain_label(keys: list[tuple[str, str]]) -> str:
    """继承链文字: 跨包时带包名前缀, 便于区分同名对象."""
    if len({k[0] for k in keys}) <= 1:
        return " -> ".join(k[1] for k in keys)
    return " -> ".join(f"{k[0]}.{k[1]}" if k[0] else k[1] for k in keys)


def _print_object_members(obj_name: str, only_events: bool, include_event_prefix: bool) -> None:
    """列出对象及继承链上的方法/事件, 基于全库索引."""
    index = build_object_index()
    entry, candidates = resolve_object(index, obj_name)
    noun = "事件" if only_events else "方法"

    if entry is None:
        color_print(f"  错误: 未找到对象 '{obj_name}'", C_RED)
        color_print("  提示: 用 list objects <包名> 查看包内对象, list packages 查看全部包", C_GRAY)
        color_print("  提示: 同名对象可用 '包名.对象名' 精确指定 (如 widget.Button)", C_GRAY)
        return

    if len(candidates) > 1:
        others = [e.label for e in candidates if e.key != entry.key]
        hint = f"; 同名对象还有 {', '.join(others)}, 可用 '包名.对象名' 精确指定" if others else ""
        color_print(f"  提示: 已选择 {entry.label}{hint}", C_GRAY)

    keys = [entry.key] + index.chains.get(entry.key, [])
    color_print(f"  继承链: {_chain_label(keys)}", C_CYAN)
    if include_event_prefix:
        color_print(f"  {C_GRAY}(包含 Event_ 开头的函数){C_RESET}")
    print()

    groups: list[tuple[str, list[tuple[int, str, str, Path]]]] = []
    for key in keys:
        methods = list(index.funcs.get(key, ()))
        if only_events:
            methods = [m for m in methods if m[1].startswith(("AddEvent_", "Event_"))]
        if not include_event_prefix:
            methods = [m for m in methods if not m[1].startswith("Event_")]
        if methods:
            groups.append((key[1], methods))

    if not groups:
        color_print(f"  未找到 {entry.label} 及其父类的{noun}", C_YELLOW)
        return

    max_func_len = max(len(m[1]) for _, methods in groups for m in methods)
    total = 0
    for label, methods in groups:
        color_print(f"  {C_BOLD}{C_CYAN}【{label}】{C_RESET}")
        total += len(methods)
        for line_no, func_name, comment, go_file in methods:
            padding = " " * (max_func_len - len(func_name))
            if comment:
                print(f"    {C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}{comment}{C_RESET}")
            else:
                try:
                    rel_path = go_file.relative_to(PROJECT_ROOT)
                except ValueError:
                    rel_path = go_file
                print(f"    {C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}({rel_path}:{line_no}){C_RESET}")

    color_print(f"  共找到 {total} 个{noun}", C_YELLOW)


def _list_object_funcs(obj_name: str, include_event_prefix: bool = False) -> None:
    """列出指定对象及继承链上的所有公开方法 (全库索引)."""
    _print_object_members(obj_name, False, include_event_prefix)


def _list_object_events(obj_name: str, include_event_prefix: bool = False) -> None:
    """列出指定对象及继承链上的所有事件函数 (全库索引)."""
    _print_object_members(obj_name, True, include_event_prefix)



def _get_type_comment(file_path: Path, type_name: str) -> str:
    """获取类型定义上方的注释.

    从 Go 文件中提取指定类型定义上方的注释块，作为类型的描述。

    Args:
        file_path: Go 文件路径
        type_name: 类型名称

    Returns:
        注释文本（合并多行注释），如果没有找到则返回空字符串
    """
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return ""

    # 查找类型定义行
    type_pattern = re.compile(rf'^type\s+{re.escape(type_name)}\s+')
    type_line_idx = None
    for i, line in enumerate(lines):
        if type_pattern.match(line.strip()):
            type_line_idx = i
            break

    if type_line_idx is None or type_line_idx == 0:
        return ""

    # 向上查找注释块
    comment_lines = []
    i = type_line_idx - 1
    while i >= 0:
        stripped = lines[i].strip()
        if stripped.startswith("//"):
            # 去掉 // 前缀，保留注释内容
            content = stripped[2:].strip()
            if content:
                comment_lines.insert(0, content)
            i -= 1
        elif stripped == "":
            # 空行：如果上面有注释，注释块结束
            if comment_lines:
                break
            i -= 1
        else:
            # 非注释非空行，注释块结束
            break

    if not comment_lines:
        return ""

    # 合并多行注释，用空格连接，并清理多余空白
    return re.sub(r'\s+', ' ', ' '.join(comment_lines)).strip()


def _list_package_objects(pkg_name: str, label: str = "公开对象") -> None:
    """列出指定包的所有公开对象.

    在 XCGUI_SRC / <pkg_name> 目录下查找所有 .go 文件，
    提取公开的类型定义及其注释描述。
    list widgets / list windows 复用此实现, 只换计数文案, 避免两套清单口径不一致.

    Args:
        pkg_name: 包名（如 widget, window, app, font 等）
        label: 结尾计数用的名称（控件 / 窗口对象 / 公开对象）
    """
    pkg_dir = XCGUI_SRC / pkg_name
    if not pkg_dir.exists():
        color_print(f"  错误: 包目录不存在: {pkg_dir.relative_to(PROJECT_ROOT)}", C_RED)
        color_print(f"  提示: 可用包请运行: python scripts/search.py list packages", C_GRAY)
        return

    found = 0
    objects = []  # [(type_name, desc, file_path)]

    for go_file in sorted(pkg_dir.glob("*.go")):
        if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
            continue

        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 提取所有公开类型定义
        # 匹配: type Xxx struct { 或 type Xxx = ...
        # 只匹配大写字母开头的公开类型
        type_patterns = [
            r'^type\s+([A-Z]\w*)\s+struct\s*\{',
            r'^type\s+([A-Z]\w*)\s*=\s*\w+',
            r'^type\s+([A-Z]\w*)\s+interface\s*\{',
            r'^type\s+([A-Z]\w*)\s+func\(',
        ]

        for pattern in type_patterns:
            for m in re.finditer(pattern, text, re.MULTILINE):
                type_name = m.group(1)
                # 获取类型注释
                desc = _get_type_comment(go_file, type_name)
                objects.append((type_name, desc, go_file))
                found += 1

    if not objects:
        color_print(f"  未找到 {pkg_name} 包的公开对象", C_YELLOW)
        return

    # 按类型名排序
    objects.sort(key=lambda x: x[0])

    # 显示结果
    for type_name, desc, file_path in objects:
        rel_path = file_path.relative_to(PROJECT_ROOT)
        if desc:
            color_print(f"  {C_BOLD}{C_GREEN}{type_name:25}{C_RESET} {C_GRAY}{desc}{C_RESET}")
        else:
            color_print(f"  {C_BOLD}{C_GREEN}{type_name:25}{C_RESET} {C_GRAY}({rel_path.name}){C_RESET}")

    color_print(f"\n  {C_YELLOW}共 {found} 个{label}{C_RESET}")


def _list_package_funcs(pkg_name: str) -> None:
    """列出指定包的所有公开非对象函数 (包级函数, 无接收者).

    在 XCGUI_SRC / <pkg_name> 目录下查找所有 .go 文件，
    提取大写的包级函数定义 (func Xxx(...), 无接收者) 及注释描述。

    Args:
        pkg_name: 包名（如 widget, window, app, font 等）
    """
    pkg_dir = XCGUI_SRC / pkg_name
    if not pkg_dir.exists():
        color_print(f"  错误: 包目录不存在: {pkg_dir.relative_to(PROJECT_ROOT)}", C_RED)
        color_print(f"  提示: 可用包请运行: python scripts/search.py list packages", C_GRAY)
        return

    found = 0
    funcs = []  # [(func_name, desc, file_path, line_no)]

    for go_file in sorted(pkg_dir.glob("*.go")):
        if go_file.name in {"deprecated.go", "doc.go"} or go_file.name.endswith("_test.go"):
            continue

        try:
            lines = go_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            # 只匹配包级函数 (无接收者): func Xxx(...)
            # 形如 func (b *Button) SetText(...) 的方法不会匹配 (func 后紧跟 '(')
            m = re.match(r'^\s*func\s+([A-Z]\w*)\s*\(', line)
            if not m:
                continue
            func_name = m.group(1)
            # 获取函数注释
            comment = _get_func_comment(lines, i)
            funcs.append((func_name, comment, go_file, i + 1))
            found += 1

    if not funcs:
        color_print(f"  未找到 {pkg_name} 包的公开非对象函数", C_YELLOW)
        return

    # 按函数名排序
    funcs.sort(key=lambda x: x[0])

    # 计算最大函数名长度用于对齐
    max_func_len = max(len(fn) for fn, _, _, _ in funcs)

    # 显示结果
    for func_name, comment, file_path, line_no in funcs:
        rel_path = file_path.relative_to(PROJECT_ROOT)
        if comment:
            padding = " " * (max_func_len - len(func_name))
            color_print(f"  {C_BOLD}{C_GREEN}{func_name}{C_RESET}{padding}  {C_GRAY}{comment}{C_RESET}")
        else:
            color_print(f"  {C_BOLD}{C_GREEN}{func_name:40}{C_RESET} {C_GRAY}({rel_path.name}:{line_no}){C_RESET}")

    color_print(f"\n  {C_YELLOW}共 {found} 个公开非对象函数{C_RESET}")


def _list_package_doc(pkg_name: str) -> None:
    """输出指定包 doc.go 的完整 // Package 注释 (保留 Markdown 结构与代码块缩进)."""
    if not pkg_name:
        color_print("  错误: pkg_doc 命令需要指定包名", C_RED)
        color_print("  用法: python scripts/search.py list pkg_doc <包名>", C_GRAY)
        color_print("  提示: 可用包请运行: python scripts/search.py list packages", C_GRAY)
        return

    dirs = _iter_pkg_dirs()
    # 允许 wapi/com、wapi\com 以及末段包名 com 三种写法
    key = pkg_name.strip().replace("\\", "/").strip("/")
    matches = [d for d in dirs if d.relative_to(XCGUI_SRC).as_posix() == key]
    if not matches:
        matches = [d for d in dirs
                   if d.relative_to(XCGUI_SRC).as_posix().endswith("/" + key)]

    if len(matches) != 1:
        if not matches:
            color_print(f"  错误: 未找到包 '{pkg_name}'", C_RED)
        else:
            color_print(f"  包名 '{pkg_name}' 匹配到多个包, 请用完整路径指定:", C_RED)
            for d in matches:
                color_print(f"    {d.relative_to(XCGUI_SRC).as_posix()}", C_GRAY)
        color_print("  提示: 可用包请运行: python scripts/search.py list packages", C_GRAY)
        return

    d = matches[0]
    rel = d.relative_to(XCGUI_SRC).as_posix()
    doc_file = d / "doc.go"
    lines = _get_package_doc_lines(doc_file)
    if not lines:
        color_print(f"  {rel} 没有 // Package 注释 (doc.go 不存在或格式不同)", C_YELLOW)
        return

    color_print(f"  包: {rel}    文档: {doc_file.relative_to(PROJECT_ROOT).as_posix()}", C_CYAN)
    print()
    for line in lines:
        print(f"    {line}")
    print()
    color_print(f"  共 {len(lines)} 行", C_YELLOW)


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
        # pkg_funcs / pkg_doc 的参数为包名, 其余 (events/funcs/objects) 为对象名
        arg_label = "包名" if subcommand in ("pkg_funcs", "pkg_doc", "pkgdoc", "package") else "对象"
        color_print(f"  {arg_label}: {extra_arg}", C_CYAN)
    if include_event_prefix:
        color_print(f"  {C_GRAY}(包含 Event_ 开头的函数){C_RESET}")
    color_print(f"{'='*60}\n", C_CYAN)

    if subcommand in ("widgets", "windows"):
        # 与 list objects 共用同一套对象清单, 避免漏掉同文件内的第二个类型
        if subcommand == "widgets":
            _list_package_objects("widget", "控件")
        else:
            _list_package_objects("window", "窗口对象")

    elif subcommand == "examples":
        if EXAMPLE_SRC.exists():
            # 递归收集所有包含 main 包的目录, 每个 main 包目录即为一个独立示例
            example_dirs: list[tuple[str, str]] = []  # [(分类相对路径, 示例名)]

            def _is_main_example(d: Path) -> bool:
                """目录是否包含 main 包 (以 package main 声明)."""
                for f in d.glob("*.go"):
                    if f.name in {"deprecated.go", "doc.go"} or f.name.endswith("_test.go"):
                        continue
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    if re.search(r"^package\s+main\b", text, re.MULTILINE):
                        return True
                return False

            def _walk(d: Path) -> None:
                for sub in sorted(d.iterdir()):
                    if not sub.is_dir() or sub.name.startswith("."):
                        continue
                    if _is_main_example(sub):
                        header = sub.parent.relative_to(EXAMPLE_SRC).as_posix()
                        example_dirs.append((header, sub.name))
                    else:
                        # 中间分组目录, 继续向下寻找示例
                        _walk(sub)

            _walk(EXAMPLE_SRC)

            # 按分类相对路径分组输出
            grouped: dict[str, list[str]] = {}
            for header, name in example_dirs:
                grouped.setdefault(header, []).append(name)

            for header in sorted(grouped):
                color_print(f"\n  [{header}]", C_CYAN, bold=True)
                for name in sorted(grouped[header]):
                    ex_dir = EXAMPLE_SRC / header / name
                    go_files = [f for f in ex_dir.glob("*.go")
                                if f.name not in {"deprecated.go", "doc.go"}
                                and not f.name.endswith("_test.go")]
                    desc = ""
                    if go_files:
                        desc = _get_package_comment(go_files[0])
                    color_print(f"    {name:35} {C_GRAY}{desc}{C_RESET}")

    elif subcommand == "packages":
        # 递归查找所有包含 .go 文件的目录 (排除测试文件、废弃文件与 main 包)
        found = 0
        truncated: list[str] = []
        for d in _iter_pkg_dirs():
            rel_path = d.relative_to(XCGUI_SRC)
            go_count = len([f for f in d.glob("*.go")
                            if f.name not in {"deprecated.go", "doc.go"}
                            and not f.name.endswith("_test.go")])
            found += 1
            # 只显示包注释首段: 部分包 (svgp / wapi/com / wapi/d2d) 的 doc.go 是长篇 Markdown
            desc, has_more = _package_doc_summary(_get_package_doc_lines(d / "doc.go"))
            if has_more:
                desc += "…"
                truncated.append(rel_path.as_posix())
            color_print(f"  {C_BOLD}{C_GREEN}{rel_path.as_posix():30}{C_RESET} {C_GRAY}{go_count:>4} 文件  {desc}{C_RESET}")

        color_print(f"\n  {C_YELLOW}共 {found} 个包{C_RESET}")
        if truncated:
            color_print("  包描述为首段摘要; 查看完整文档: python scripts/search.py list pkg_doc <包名>", C_GRAY)
            color_print(f"  含完整文档的包: {', '.join(truncated)}", C_GRAY)

    elif subcommand == "events":
        if not extra_arg:
            color_print(f"  错误: events 命令需要指定对象名", C_RED)
            color_print(f"  用法: python scripts/search.py list events <对象名>", C_GRAY)
            return
        # 列出指定对象的所有事件 (含继承)
        # 如果对象在edge目录中，自动包含Event开头的函数
        if _is_object_in_edge(extra_arg):
            include_event_prefix = True
        _list_object_events(extra_arg, include_event_prefix)

    elif subcommand == "funcs":
        if not extra_arg:
            color_print(f"  错误: funcs 命令需要指定对象名", C_RED)
            color_print(f"  用法: python scripts/search.py list funcs <对象名>", C_GRAY)
            return
        # 列出指定对象的所有方法 (含继承)
        # 如果对象在edge目录中，自动包含Event开头的函数
        if _is_object_in_edge(extra_arg):
            include_event_prefix = True
        _list_object_funcs(extra_arg, include_event_prefix)

    elif subcommand == "objects":
        if not extra_arg:
            color_print(f"  错误: objects 命令需要指定包名", C_RED)
            color_print(f"  用法: python scripts/search.py list objects <包名>", C_GRAY)
            color_print(f"  提示: 可用包请运行: python scripts/search.py list packages", C_GRAY)
            return
        # 列出指定包的所有公开对象
        _list_package_objects(extra_arg)

    elif subcommand == "pkg_funcs":
        if not extra_arg:
            color_print(f"  错误: pkg_funcs 命令需要指定包名", C_RED)
            color_print(f"  用法: python scripts/search.py list pkg_funcs <包名>", C_GRAY)
            color_print(f"  提示: 可用包请运行: python scripts/search.py list packages", C_GRAY)
            return
        # 列出指定包的所有公开非对象函数 (包级函数, 无接收者)
        _list_package_funcs(extra_arg)

    elif subcommand in ("pkg_doc", "pkgdoc", "package"):
        # 输出指定包 doc.go 的完整包注释
        _list_package_doc(extra_arg)

    else:
        color_print(f"  错误: 未知的 list 子命令 '{subcommand}'", C_RED)
        color_print("  可用: widgets / windows / packages / examples / events / funcs / objects / pkg_funcs / pkg_doc", C_GRAY)


def main():
    parser = argparse.ArgumentParser(
        description="xcgui 源码搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  func <keyword>       搜索函数定义 (支持中英文, 多关键词用 / 分割)
  const <keyword>      搜索常量定义 (支持中英文, 多关键词用 / 分割)
  event <keyword>      搜索事件相关代码 (支持中英文, 多关键词用 / 分割)
  type <keyword>       搜索类型定义 (struct/interface/等, 支持中英文, 多关键词用 / 分割)
  example <keyword>    搜索示例代码 (在 xcgui-example 中搜索, 支持中英文, 多关键词用 / 分割)
  example_name <keyword>  搜索示例名或包注释 (多关键词用 / 分割, 含中文搜包注释, 否则搜示例名)

列表子命令:
  list widgets       列出 widget 包所有公开对象
  list windows       列出 window 包所有公开对象
  list packages      列出所有源码包 (包描述只取首段摘要)
  list examples      列出所有示例
  list objects <包名>       列出指定包的所有公开对象 (含描述)
  list pkg_funcs <包名>     列出指定包的所有公开非对象函数 (包级函数, 无接收者, 按函数名排序)
  list pkg_doc <包名>       输出指定包 doc.go 的完整包文档 (保留 Markdown 结构与代码块)
  list events <对象名>       列出指定对象的所有事件 (含继承链, 不含 Event 开头函数, edge目录自动包含 Event 开头函数)
  list funcs <对象名>        列出指定对象的所有方法 (含继承链, 含事件, 不含 Event 开头函数, edge目录自动包含 Event 开头函数)

包文档:
  list packages 只显示包注释首段摘要; 要读完整文档用 list pkg_doc <包名>,
  包名支持 wapi/d2d、wapi\\d2d 或末段名 d2d.

对象范围:
  list funcs / list events 适用于 source/xcgui 下全部包的对象. 同名对象可用
  "包名.对象名" 指定 (如 app.App / xc.POINT), 不指定时自动选择公开且方法最多的
  那个, 并提示其它同名对象.

常量范围:
  const 覆盖 source/xcgui 下全部包, 包含 xcc (核心常量) / wapi (Windows API 常量)
  / edge (WebView2 常量) / xc 等. 英文匹配常量定义行, 含中文时额外匹配常量
  分组说明与条目注释.

关键词规则:
  - 用 / 分割多个关键词，会同时匹配所有关键词, 支持中英文, 不区分大小写
  - 关键词除了可以搜索函数/常量/事件定义外, 还可以搜索它们的注释, 在关键词含中文时触发
  - `list funcs <对象名>` 和 `list events <对象名>` 命令默认是不会列出以 `Event` 开头的函数的, 除非在最后面再加个 `all` 参数, 一般不需要 `Event` 开头的函数, 这两个命令都会列出 `AddEvent` 开头的函数, 这种事件添加方式更常用. 特别地, 当对象在 edge 目录时, 会自动包含 Event 开头的函数, 因为 edge 目录中的事件是以 `Event` 开头的.

示例:
    python scripts/search.py func button/gettext       # 搜索函数名关键词 (多个关键词用 / 分割)
    python scripts/search.py func 窗口/居中             # 用中文搜索函数注释 (多个关键词用 / 分割)
    python scripts/search.py const button/check        # 搜索常量关键词 (多个关键词用 / 分割)
    python scripts/search.py const 窗口/最小化          # 用中文搜索常量注释 (多个关键词用 / 分割)
    python scripts/search.py event tree/select         # 搜索事件函数名关键词 (多个关键词用 / 分割)
    python scripts/search.py event 窗口/鼠标光标        # 搜索事件函数中文注释关键词 (多个关键词用 / 分割)
    python scripts/search.py type WebViewOptions       # 搜索type名关键词 (多个关键词用 / 分割)
    python scripts/search.py type webview/选项         # 用中文搜索type注释
    python scripts/search.py example event/TabBar      # 搜索示例内容关键词 (多个关键词用 / 分割)
    python scripts/search.py example 按钮/选中/事件     # 搜索示例内容关键词 (多个关键词用 / 分割)
    python scripts/search.py list widgets              # 列出 widget 包所有公开对象
    python scripts/search.py list windows              # 列出 window 包所有公开对象
    python scripts/search.py list packages             # 列出所有源码包
    python scripts/search.py list examples             # 列出所有示例
    python scripts/search.py list events button        # 列出 Button 的所有事件函数名
    python scripts/search.py list funcs button         # 列出 Button 的所有方法名(含继承链,含事件)
    python scripts/search.py list objects window       # 列出 window 包所有公开对象 (含描述)
    python scripts/search.py list pkg_funcs svg        # 列出 svg 包所有公开非对象函数 (包级函数)
    python scripts/search.py list funcs app.App        # 查看非 widget/window 包对象的方法
    python scripts/search.py list funcs xc.POINT       # 用包名区分跨包同名对象
    python scripts/search.py list pkg_doc wapi/d2d     # 查看 wapi/d2d 的完整包文档
    python scripts/search.py example_name 美化/编辑框   # 搜索示例包注释
    python scripts/search.py example_name draw/button  # 搜索示例名
        """,
    )
    parser.add_argument(
        "command",
        choices=["func", "const", "event", "type", "example", "example_name", "list"],
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

    # 验证源码完整性: 目录存在不代表源码完整 (下载中断会留下空目录/半套源码)
    if not SOURCE_DIR.is_dir():
        color_print(f"错误: source 目录不存在: {SOURCE_DIR}", C_RED)
        color_print("请先执行 python scripts/download.py 下载源码", C_RED)
        color_print("请确保在项目根目录 (go-xcgui-dev) 下运行此脚本", C_RED)
        sys.exit(1)

    example_only = args.command in ("example", "example_name") or (
        args.command == "list" and bool(args.args) and args.args[0].lower() == "examples"
    )
    xcgui_ok = _has_go_files(XCGUI_SRC)
    example_ok = _has_go_files(EXAMPLE_SRC)
    if not xcgui_ok:
        color_print(f"警告: 源码目录缺失或不完整: {XCGUI_SRC.relative_to(PROJECT_ROOT).as_posix()}/", C_YELLOW)
    if not example_ok:
        color_print(f"警告: 源码目录缺失或不完整: {EXAMPLE_SRC.relative_to(PROJECT_ROOT).as_posix()}/", C_YELLOW)
    if (example_only and not example_ok) or (not example_only and not xcgui_ok):
        color_print("请先执行 python scripts/download.py 下载源码, 再重试", C_RED)
        sys.exit(2)

    # 处理参数
    if args.command == "list":
        # list 命令: list <subcommand> [extra_arg] [all]
        if len(args.args) == 0:
            color_print("错误: list 命令需要子类型 (widgets/windows/packages/examples/events/funcs/objects/pkg_funcs/pkg_doc)", C_RED)
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
        elif args.command == "example_name":
            search_example_name(keyword)
        elif args.command == "type":
            search_type(keyword)


if __name__ == "__main__":
    main()
