#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载 xcgui 和 xcgui-example 源码 ZIP 并解压到父目录下的 source 目录.

自动使用代理加速下载:
  - ghfast: https://ghfast.top/
  - llkk: https://gh.llkk.cc/
  - direct: 直连
"""

import io
import os
import sys
import shutil
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

# 代理列表
PROXIES = [
    ("ghfast", "https://ghfast.top/"),
    ("llkk", "https://gh.llkk.cc/"),
    ("direct", ""),
]


def get_latest_xcgui_version():
    """获取 xcgui 最新 release 版本号, 失败返回空字符串."""
    url = "https://cnb.cool/twgh521/xcguidll/-/git/raw/main/xcgui-latest.txt?download=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            version = resp.read().decode("utf-8").strip()
            if version:
                return version
    except Exception as e:
        print(f"获取 xcgui 最新版本号失败: {e}")
    return ""


def build_download_url(original_url, proxy_url):
    """构建下载 URL, 代理方式是在原始 URL 前加上代理地址."""
    if not proxy_url:
        return original_url
    return proxy_url + original_url


def download_file_with_proxies(original_url, desc=""):
    """依次尝试所有代理下载文件, 返回字节数据或 None."""
    for proxy_name, proxy_url in PROXIES:
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

    print("所有代理均下载失败")
    return None


def clear_directory(dir_path):
    """清空目录下的所有内容，但保留目录本身."""
    if not os.path.exists(dir_path):
        return
    
    print(f"  清空目录: {dir_path}")
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"  警告: 无法删除 {item_path}: {e}")

def extract_zip(zip_data, extract_to, top_dir_name):
    """解压 ZIP 数据到指定目录, 并将顶层目录重命名为 top_dir_name."""
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # 获取 ZIP 中的顶层目录名
        top_dir = zf.namelist()[0].split("/")[0]
        extract_path = os.path.join(extract_to, top_dir)
        final_path = os.path.join(extract_to, top_dir_name)

        # 解压
        zf.extractall(extract_to)
        print(f"  解压完成: {extract_path}")

        # 重命名顶层目录
        if os.path.exists(final_path):
            shutil.rmtree(final_path)
        os.rename(extract_path, final_path)
        print(f"  重命名: {top_dir} -> {top_dir_name}")
        return final_path


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

    # 获取 xcgui 最新版本号
    xcgui_version = get_latest_xcgui_version()
    if xcgui_version:
        print(f"xcgui 最新版本号: {xcgui_version}")
        xcgui_url = f"https://github.com/twgh/xcgui/archive/refs/tags/v{xcgui_version}.zip"
    else:
        print("获取版本号失败, 使用 main 分支下载 xcgui")
        xcgui_url = "https://github.com/twgh/xcgui/archive/refs/heads/main.zip"

    example_url = "https://github.com/twgh/xcgui-example/archive/refs/heads/main.zip"

    # 记录下载失败的仓库
    failed_repos = []

    # 下载并解压 xcgui
    print("\n====== 处理 xcgui ======")
    xcgui_data = download_file_with_proxies(xcgui_url, "xcgui")
    if xcgui_data:
        extract_zip(xcgui_data, source_dir, "xcgui")
    else:
        print("xcgui 下载失败")
        failed_repos.append(("xcgui", xcgui_url))

    # 下载并解压 xcgui-example
    print("\n====== 处理 xcgui-example ======")
    example_data = download_file_with_proxies(example_url, "xcgui-example")
    if example_data:
        extract_zip(example_data, source_dir, "xcgui-example")
    else:
        print("xcgui-example 下载失败")
        failed_repos.append(("xcgui-example", example_url))

    # 打印最终结果
    print("\n==============================")
    total = 2  # xcgui 和 xcgui-example
    success = total - len(failed_repos)
    if not failed_repos:
        print("所有操作完成!")
    else:
        print(f"部分下载失败 ({success}/{total} 成功)")
        print(f"\n你可以手动下载以下文件并解压到: {os.path.abspath(source_dir)}")
        for name, url in failed_repos:
            print(f"  {name}: {url}")
            print(f"    解压后将文件夹重命名为: {name}")

    print(f"\n当前 source 目录内容: {os.listdir(source_dir)}")


if __name__ == "__main__":
    main()
