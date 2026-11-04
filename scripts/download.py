#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载 xcgui 和 xcgui-example 源码 ZIP 并解压到父目录下的 source 目录.

xcgui 的最新 tag 依次从 Gitee / GitCode / CNB / GitHub 动态获取,
任一源失败自动回退到下一个; GitHub 直连排在整条回退链的最后.
若所有 tags API 均失败, 本机有 git 时再走一轮 git ls-remote 兜底
(Gitee / GitCode / GitHub, GitHub 走代理且直连排最后).
源码按 CNB -> Gitee -> GitCode -> GitHub 的平台顺序获取, 每平台先归档 ZIP 再 git clone;
本机有 git 时, 四个平台都可用 git clone --depth 1 兜底, GitHub clone 也走代理且直连排最后.
Gitee / GitCode 的归档 ZIP 需登录, 故只提供 git clone 通道.
GitHub 归档下载使用 ghfast / ghproxy 代理加速, CNB 不走代理.
解压兼容两种归档结构: CNB 是扁平 ZIP, GitHub 带统一顶层目录.
"""

import io
import json
import os
import re
import sys
import shutil
import stat
import subprocess
import tempfile
import zipfile
import urllib.request

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

# GitHub 下载代理列表
PROXIES = [
    ("ghfast", "https://ghfast.top/"),
    ("ghproxy", "https://gh-proxy.org/"),
    ("direct", ""),
]
# CNB 国内可直连, 无需走 GitHub 代理
DIRECT_ONLY = [("direct", "")]

# 归档地址
# 两个平台的归档前缀都到 /refs 为止, 后续统一拼 /tags/{tag}.zip 或 /heads/main.zip
CNB_XCGUI_ARCHIVE = "https://cnb.cool/twgh521/xcgui/-/git/archive/refs"
CNB_EXAMPLE_MAIN_ZIP = "https://cnb.cool/twgh521/xcgui-example/-/git/archive/refs/heads/main.zip"
GITHUB_XCGUI_ARCHIVE = "https://github.com/twgh/xcgui/archive/refs"
GITHUB_EXAMPLE_MAIN_ZIP = "https://github.com/twgh/xcgui-example/archive/refs/heads/main.zip"

# 各平台 git 仓库地址, 实测均支持匿名浅克隆 (tag v1.4.3 / main 分支内容一致)
CNB_XCGUI_REPO = "https://cnb.cool/twgh521/xcgui.git"
CNB_EXAMPLE_REPO = "https://cnb.cool/twgh521/xcgui-example.git"
GITEE_XCGUI_REPO = "https://gitee.com/twgh/xcgui.git"
GITEE_EXAMPLE_REPO = "https://gitee.com/twgh/xcgui-example.git"
GITCODE_XCGUI_REPO = "https://gitcode.com/twgh/xcgui.git"
GITCODE_EXAMPLE_REPO = "https://gitcode.com/twgh/xcgui-example.git"
GITHUB_XCGUI_REPO = "https://github.com/twgh/xcgui.git"
GITHUB_EXAMPLE_REPO = "https://github.com/twgh/xcgui-example.git"
# GitHub git 协议代理前缀 (实测 ghfast / ghproxy 均能 clone 与 ls-remote), 直连自动追加到最后
GITHUB_GIT_PROXIES = ["https://ghfast.top/", "https://gh-proxy.org/"]

# tag 主链, 按优先级排列: 任一源失败自动回退到下一个, GitHub 直连排最后
# 主链全部失败后还有 GIT_TAG_FALLBACKS 的 git ls-remote 兜底轮 (见下方)
# http 源: (名称, "http", tags API 地址, [(代理名, 代理前缀), ...])
#          Gitee / GitCode / GitHub 的 tags API 均无需 token, 返回同构的 {"name": ...} 数组
# git 源:  (名称, "git", 仓库 clone 地址, [])
#          CNB 的 OpenAPI 需 Bearer token, 但 git ls-remote --tags 可匿名列出全部 tag
# ghfast 不代理 api.github.com (实测 403 Invalid input), 故 GitHub 只配 ghproxy + 直连
TAG_SOURCES = [
    ("Gitee", "http", "https://gitee.com/api/v5/repos/twgh/xcgui/tags", [("direct", "")]),
    ("GitCode", "http", "https://api.gitcode.com/api/v5/repos/twgh/xcgui/tags", [("direct", "")]),
    ("CNB", "git", CNB_XCGUI_REPO, []),
    (
        "GitHub", "http", "https://api.github.com/repos/twgh/xcgui/tags",
        [("ghproxy", "https://gh-proxy.org/"), ("direct", "")],
    ),
]
# tags API 主链全部失败后的 git ls-remote 兜底源: (名称, 仓库地址, git 代理前缀)
# CNB 已是主链中的 git 源, 这里不重复; GitHub 代理优先, 直连放最后.
# 实测四个源 (含 GitHub 两个代理) 的 ls-remote --tags 均匿名可用, 最新 tag 一致.
GIT_TAG_FALLBACKS = [
    ("Gitee", GITEE_XCGUI_REPO, []),
    ("GitCode", GITCODE_XCGUI_REPO, []),
    ("GitHub", GITHUB_XCGUI_REPO, GITHUB_GIT_PROXIES),
]
TAGS_PER_PAGE = 100
MAX_TAG_PAGES = 20
# 匹配 v1.4.3 / 1.4.3 / v1.4.3-1, 排除无法解析版本的 tag
VERSION_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(.*)$")
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# 源码获取平台, 按优先级排列. 字段说明:
#   archive      : xcgui 归档前缀, 拼接 /tags/{tag}.zip 或 /heads/main.zip; None 表示不可用
#   example_zip  : xcgui-example 的 main 归档; None 表示不可用
#   zip_channels : 归档下载通道
#   git_proxies  : git clone 时依次尝试的 URL 前缀, 末尾自动追加直连
# Gitee / GitCode 的 archive 实测返回 HTML 登录页, zipball API 为 404/401, 故只提供 git clone.
SOURCE_PLATFORMS = [
    {
        "name": "CNB",
        "xcgui_repo": CNB_XCGUI_REPO,
        "example_repo": CNB_EXAMPLE_REPO,
        "archive": CNB_XCGUI_ARCHIVE,
        "example_zip": CNB_EXAMPLE_MAIN_ZIP,
        "zip_channels": DIRECT_ONLY,
        "git_proxies": [],
    },
    {
        "name": "Gitee",
        "xcgui_repo": GITEE_XCGUI_REPO,
        "example_repo": GITEE_EXAMPLE_REPO,
        "archive": None,
        "example_zip": None,
        "zip_channels": DIRECT_ONLY,
        "git_proxies": [],
    },
    {
        "name": "GitCode",
        "xcgui_repo": GITCODE_XCGUI_REPO,
        "example_repo": GITCODE_EXAMPLE_REPO,
        "archive": None,
        "example_zip": None,
        "zip_channels": DIRECT_ONLY,
        "git_proxies": [],
    },
    {
        "name": "GitHub",
        "xcgui_repo": GITHUB_XCGUI_REPO,
        "example_repo": GITHUB_EXAMPLE_REPO,
        "archive": GITHUB_XCGUI_ARCHIVE,
        "example_zip": GITHUB_EXAMPLE_MAIN_ZIP,
        "zip_channels": PROXIES,
        "git_proxies": GITHUB_GIT_PROXIES,
    },
]


def tag_sort_key(tag_name):
    """把 tag 名转为可比较的排序键, 非版本 tag 返回 None.

    正式版排在带后缀的预发布版之前: (版本号, 1/0, 后缀)
    """
    m = VERSION_TAG_RE.match(tag_name)
    if not m:
        return None
    version = tuple(int(part) for part in m.groups()[:3])
    suffix = m.group(4) or ""
    return (version, 0 if suffix else 1, suffix)


def pick_latest_tag(names):
    """从 tag 名列表中选出版本号最大的一个, 无有效 tag 返回空字符串."""
    candidates = []
    for name in names:
        name = name.strip()
        key = tag_sort_key(name)
        if key is not None:
            candidates.append((key, name))
    return max(candidates)[1] if candidates else ""


def fetch_tag_names(api_url, proxy_prefix=""):
    """分页拉取某个 tags API 的全部 tag 名, 请求失败返回 None."""
    names = []
    for page in range(1, MAX_TAG_PAGES + 1):
        url = f"{api_url}?page={page}&per_page={TAGS_PER_PAGE}"
        if proxy_prefix:
            url = proxy_prefix + url
        try:
            req = urllib.request.Request(url, headers=REQUEST_HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"    请求失败 (第 {page} 页): {e}")
            return None
        if not isinstance(data, list) or not data:
            break
        names.extend(item.get("name", "") for item in data if isinstance(item, dict))
        if len(data) < TAGS_PER_PAGE:
            break
    return names


def git_env():
    """git 子进程环境: 禁止交互式认证, 网络长期无进展时尽早失败."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_HTTP_LOW_SPEED_LIMIT", "1000")
    env.setdefault("GIT_HTTP_LOW_SPEED_TIME", "30")
    return env


def fetch_tag_names_via_git(repo_urls):
    """用 git ls-remote --tags 匿名列出远端 tag, 需要本机安装 git; 失败返回 None.

    repo_urls 可为单个字符串或地址列表 (代理优先, 直连兜底), 逐个尝试.
    CNB 的 OpenAPI 需要 Bearer token, 但 git 协议可匿名读取, 故用它作为 tag 源;
    tags API 全部不可用时, Gitee / GitCode / GitHub 也用同样的方式兜底.
    """
    if isinstance(repo_urls, str):
        repo_urls = [repo_urls]
    for repo_url in repo_urls:
        print(f"    git ls-remote 地址: {repo_url}")
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--tags", repo_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20,
                env=git_env(),
            )
        except Exception as e:
            print(f"    请求失败: {e}")
            continue
        if result.returncode != 0:
            reason = result.stderr.strip() or f"git 返回码 {result.returncode}"
            print(f"    请求失败: {reason}")
            continue

        names = []
        for line in result.stdout.splitlines():
            if "refs/tags/" not in line:
                continue
            name = line.split("refs/tags/", 1)[1].strip()
            if name.endswith("^{}"):  # 附注标签的解引用项, 与同名 tag 重复
                continue
            names.append(name)
        if names:
            return names
        print("    远端没有返回任何 tag")
    return None


def get_latest_xcgui_tag():
    """按 TAG_SOURCES 顺序获取最新 tag, 全部失败返回空字符串.

    每个源可能对应多个访问方式 (不同代理 / git 协议), 逐个尝试;
    取到 tag 列表后统一按语义版本排序, 不依赖各平台返回顺序.
    主链全部失败后, 若本机有 git 再走一轮 GIT_TAG_FALLBACKS 的 ls-remote 兜底.
    """
    for index, (source_name, kind, target, proxies) in enumerate(TAG_SOURCES):
        if kind == "git":
            if has_git():
                attempts = [
                    (f"{source_name} (git ls-remote)", lambda t=target: fetch_tag_names_via_git(t))
                ]
            else:
                print(f"  跳过 {source_name}: 本机未安装 git")
                attempts = []
        else:
            # 默认参数绑定当次的 target / 代理前缀, 避免闭包延后取值
            attempts = []
            for proxy_name, proxy_prefix in proxies:
                label = source_name if proxy_name == "direct" else f"{source_name} ({proxy_name} 代理)"
                attempts.append(
                    (label, lambda t=target, p=proxy_prefix: fetch_tag_names(t, p))
                )

        for label, fetch in attempts:
            print(f"  尝试 {label} ...")
            names = fetch()
            if names is None:
                continue
            latest_tag = pick_latest_tag(names)
            if latest_tag:
                print(f"  来源: {label}, 共 {len(names)} 个 tag, 最新: {latest_tag}")
                return latest_tag
            print(f"  {label} 没有可解析的版本 tag")

        if index < len(TAG_SOURCES) - 1:
            print(f"  {source_name} 不可用, 尝试下一个数据源")
        else:
            print(f"  {source_name} 不可用")

    # 主链全挂: API 被限流 / 拦截时, git 协议往往仍可用, 再兜一轮
    if not has_git():
        print("  跳过 git ls-remote 兜底: 本机未安装 git")
        print("所有 tag 数据源均获取失败")
        return ""
    print("  所有 tags API 均不可用, 尝试 git ls-remote 兜底")
    for source_name, repo_url, git_proxies in GIT_TAG_FALLBACKS:
        label = f"{source_name} (git ls-remote 兜底)"
        print(f"  尝试 {label} ...")
        names = fetch_tag_names_via_git(git_remote_urls(repo_url, git_proxies))
        latest_tag = pick_latest_tag(names) if names else ""
        if latest_tag:
            print(f"  来源: {label}, 共 {len(names)} 个 tag, 最新: {latest_tag}")
            return latest_tag
        print(f"  {label} 不可用")
    print("所有 tag 数据源均获取失败")
    return ""


def build_download_url(original_url, proxy_url):
    """构建下载 URL, 代理方式是在原始 URL 前加上代理地址."""
    if not proxy_url:
        return original_url
    return proxy_url + original_url


def download_file_with_proxies(original_url, desc="", proxies=None):
    """依次尝试给定通道下载文件, 返回字节数据或 None."""
    if proxies is None:
        proxies = PROXIES
    for proxy_name, proxy_url in proxies:
        url = build_download_url(original_url, proxy_url)
        proxy_display = "直连" if proxy_name == "direct" else proxy_name
        print(f"  使用代理: {proxy_display}")
        if proxy_url:
            print(f"  代理地址: {proxy_url}")
        print(f"  下载地址: {url}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                print(f"  下载完成, 大小: {len(data)} 字节")
                return data
        except Exception as e:
            print(f"  下载失败: {e}")
            if proxy_name != "direct":
                print("  尝试下一个代理...")
            continue

    print("该下载源的所有通道均失败")
    return None


def has_git():
    """本机是否安装了 git."""
    return shutil.which("git") is not None


def remove_git_dir(git_dir):
    """删除 clone 产生的 .git (含只读对象文件), 返回是否清除干净."""
    for root, _dirs, files in os.walk(git_dir):
        for filename in files:
            try:
                os.chmod(os.path.join(root, filename), stat.S_IWRITE)
            except Exception:
                pass
    shutil.rmtree(git_dir, ignore_errors=True)
    return not os.path.exists(git_dir)


def clone_repo(repo_urls, ref, source_dir, name):
    """按地址顺序 git clone --depth 1 指定 tag/分支到 source_dir/name, 成功返回 True.

    repo_urls 可为单个字符串或地址列表 (代理优先, 直连兜底), 逐个尝试;
    浅克隆到临时目录 -> 移除 .git -> 整体移动, 保持 source 目录干净.
    """
    if isinstance(repo_urls, str):
        repo_urls = [repo_urls]
    final_path = os.path.join(source_dir, name)
    staging = tempfile.mkdtemp(prefix=f"_{name}_git_", dir=source_dir)
    try:
        for index, repo_url in enumerate(repo_urls):
            if index:
                # 上次失败可能留下半成品; git 要求目标目录为空, 且 .git 内含只读对象
                remove_git_dir(os.path.join(staging, ".git"))
                clear_directory(staging, quiet=True)
            print(f"  git clone 地址: {repo_url}")
            cmd = [
                "git", "clone", "--depth", "1", "--single-branch",
                "--branch", ref, repo_url, staging,
            ]
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                    env=git_env(),
                )
            except Exception as e:
                print(f"  git clone 异常: {e}")
                continue
            if result.returncode != 0:
                lines = (result.stderr or result.stdout).strip().splitlines()
                print(f"  git clone 失败: {lines[-1] if lines else result.returncode}")
                print("  尝试下一个 git 地址...")
                continue

            git_dir = os.path.join(staging, ".git")
            if os.path.isdir(git_dir) and not remove_git_dir(git_dir):
                print("  警告: 无法清除 .git 目录, 源码仍可用")
            if os.path.exists(final_path):
                shutil.rmtree(final_path)
            shutil.move(staging, final_path)
            print(f"  目录就绪: {final_path} (git clone {ref})")
            return True
        return False
    finally:
        if os.path.isdir(staging):
            shutil.rmtree(staging, ignore_errors=True)


def git_remote_urls(repo_url, proxy_prefixes):
    """构造 git 远端候选地址 (ls-remote / clone 共用): 代理优先, 直连始终放最后."""
    return [prefix + repo_url for prefix in proxy_prefixes] + [repo_url]


def build_download_candidates(tag):
    """构造获取源码的候选: (xcgui 候选, xcgui-example 候选).

    每项为 (说明, 类型, 参数):
      "zip" -> (URL, 通道列表)
      "git" -> (仓库地址列表, tag/分支), 按列表顺序 clone; 仅在本机有 git 时加入
    按 ref 分层: 先尝试最新 tag 下的全部平台, 再尝试 main 分支下的全部平台;
    同一 ref 内按 SOURCE_PLATFORMS 顺序, 每个平台先归档 ZIP 再 git clone.
    """
    git_ok = has_git()
    ref_levels = []
    if tag:
        ref_levels.append((tag, f"tag {tag}", True))
    ref_levels.append(("main", "main", False))

    xcgui = []
    for ref, ref_label, is_tag in ref_levels:
        for platform in SOURCE_PLATFORMS:
            name = platform["name"]
            if platform["archive"]:
                suffix = f"tags/{ref}.zip" if is_tag else "heads/main.zip"
                xcgui.append((
                    f"{name} {ref_label} (ZIP)", "zip",
                    (f"{platform['archive']}/{suffix}", platform["zip_channels"]),
                ))
            if git_ok:
                xcgui.append((
                    f"{name} {ref_label} (git clone)", "git",
                    (git_remote_urls(platform["xcgui_repo"], platform["git_proxies"]), ref),
                ))

    example = []
    for platform in SOURCE_PLATFORMS:
        name = platform["name"]
        if platform["example_zip"]:
            example.append((
                f"{name} main (ZIP)", "zip",
                (platform["example_zip"], platform["zip_channels"]),
            ))
        if git_ok:
            example.append((
                f"{name} main (git clone)", "git",
                (git_remote_urls(platform["example_repo"], platform["git_proxies"]), "main"),
            ))
    return xcgui, example


def fetch_repo_source(candidates, name, source_dir):
    """按候选顺序获取源码到 source_dir/name, 返回 (是否成功, 最后尝试的说明)."""
    last = ""
    for desc, kind, payload in candidates:
        last = desc
        print(f"  候选来源: {desc}")
        if kind == "zip":
            url, proxies = payload
            data = download_file_with_proxies(url, desc=desc, proxies=proxies)
            if data and data[:2] == b"PK":
                extract_zip(data, source_dir, name)
                return True, desc
            if data:
                print("  返回内容不是 ZIP (可能被拦截或为错误页), 尝试下一个候选")
            else:
                print(f"  {desc} 失败, 尝试下一个候选")
        elif kind == "git":
            repo_urls, ref = payload
            if clone_repo(repo_urls, ref, source_dir, name):
                return True, desc
            print(f"  {desc} 失败, 尝试下一个候选")
    return False, last


def clear_directory(dir_path, quiet=False):
    """清空目录下的所有内容，但保留目录本身."""
    if not os.path.exists(dir_path):
        return

    if not quiet:
        print(f"  清空目录: {dir_path}")
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            if not quiet:
                print(f"  警告: 无法删除 {item_path}: {e}")


def get_zip_top_dir(names):
    """若 ZIP 全部条目位于同一顶层目录下则返回该目录名, 否则返回 None (扁平归档)."""
    entries = [n for n in names if n and not n.startswith("/")]
    if not entries or not any("/" in n.rstrip("/") for n in entries):
        return None
    roots = {n.split("/")[0] for n in entries}
    if len(roots) != 1:
        return None
    root = next(iter(roots))
    if all(n.rstrip("/") == root or n.startswith(root + "/") for n in entries):
        return root
    return None


def extract_zip(zip_data, extract_to, top_dir_name):
    """解压仓库归档到 extract_to/top_dir_name.

    兼容两种结构: GitHub 归档带统一顶层目录 (xcgui-1.4.3/), CNB 归档为扁平结构.
    先解压到临时目录再整体移动, 避免把归档内容散落到 source 根目录.
    """
    final_path = os.path.join(extract_to, top_dir_name)
    staging = tempfile.mkdtemp(prefix=f"_{top_dir_name}_", dir=extract_to)
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            top_dir = get_zip_top_dir(zf.namelist())
            zf.extractall(staging)

        source = os.path.join(staging, top_dir) if top_dir else staging
        layout = f"顶层目录 {top_dir}" if top_dir else "扁平结构"
        print(f"  解压完成: {layout}, {len(os.listdir(source))} 个顶层条目")

        if os.path.exists(final_path):
            shutil.rmtree(final_path)
        shutil.move(source, final_path)
        print(f"  目录就绪: {final_path}")
        return final_path
    finally:
        if os.path.isdir(staging):
            shutil.rmtree(staging, ignore_errors=True)


def main():
    # 获取脚本所在目录的父目录 (项目根目录)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    source_dir = os.path.join(project_root, "source")

    # 创建 source 目录
    os.makedirs(source_dir, exist_ok=True)
    print(f"source 目录: {source_dir}")
    
    # 清空 source 目录
    print("\n====== 清空 source 目录 ======")
    clear_directory(source_dir)
    print()

    # 按 Gitee -> GitCode -> CNB -> GitHub 依次获取最新 tag (GitHub 直连排最后), 失败自动回退
    xcgui_tag = get_latest_xcgui_tag()
    if xcgui_tag:
        print(f"xcgui 最新 tag: {xcgui_tag}")
    else:
        print("获取 tag 失败, 只能使用 main 分支源码")

    xcgui_candidates, example_candidates = build_download_candidates(xcgui_tag)

    # 记录下载失败的仓库
    failed_repos = []

    for name, candidates in (
        ("xcgui", xcgui_candidates),
        ("xcgui-example", example_candidates),
    ):
        print(f"\n====== 处理 {name} ======")
        ok, used = fetch_repo_source(candidates, name, source_dir)
        if not ok:
            print(f"{name} 获取失败 (最后尝试: {used})")
            failed_repos.append((name, candidates))

    # 打印最终结果
    print("\n==============================")
    total = 2  # xcgui 和 xcgui-example
    success = total - len(failed_repos)
    if not failed_repos:
        print("所有操作完成!")
    else:
        print(f"部分源码获取失败 ({success}/{total} 成功)")
        print(f"\n你可以手动获取以下源码并放到: {os.path.abspath(source_dir)}")
        for name, candidates in failed_repos:
            print(f"  {name} 可选获取方式:")
            for desc, kind, payload in candidates:
                if kind == "zip":
                    print(f"    {desc}: {payload[0]}")
                else:
                    urls, ref = payload
                    print(f"    {desc}: git clone --depth 1 --branch {ref} <下列地址>")
                    for url in urls:
                        print(f"      {url}")
            print(f"    最终目录名应为: {name}")

    print(f"\n当前 source 目录内容: {os.listdir(source_dir)}")


if __name__ == "__main__":
    main()
