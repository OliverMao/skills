#!/usr/bin/env python3
"""
vision-augment / setup.py
==========================
独立的视觉模型配置工具：查看、设置、清除、测试配置。

用法：
    python3 setup.py                 # 查看当前配置（来源与脱敏值）
    python3 setup.py --set           # 交互式重新设置并持久化
    python3 setup.py --clear         # 删除持久化配置
    python3 setup.py --test          # 用当前配置测试连通性

配置优先级：命令行临时参数 > 环境变量 > 持久化配置文件。
"""

import argparse
import json
import sys

import config


def anonymize(key: str, val):
    if val is None:
        return None
    if key == "api_key" and val and val != "dummy":
        return val[:3] + "***" + val[-2:]
    return val


def show():
    file_cfg = config.load_config()
    merged = config.resolve_config({})
    print("== vision-augment 配置 ==")
    print("配置文件:", config.config_path())
    print("来源:", )
    if file_cfg:
        print("  持久化配置存在:", "是")
    else:
        print("  持久化配置存在: 否")
    for env, key, label in config.FIELDS:
        src = "未设置"
        val = merged.get(key)
        if val:
            if env in __import__("os").environ:
                src = "环境变量"
            elif key in file_cfg:
                src = "配置文件"
        print(f"  {label}:")
        print(f"    {key} = {anonymize(key, val)}  [{src}]")
    max_size = merged.get("max_size")
    print(f"  max_size = {max_size}  [{ '环境变量' if 'VISION_MAX_SIZE' in __import__('os').environ else ('配置文件' if 'max_size' in file_cfg else '默认 1024') }]")
    conf = config.is_configured(merged)
    print("状态:", "✔ 已配置，可调用 describe.py" if conf else "✘ 未配置完整，请运行 --set")


def do_set():
    cfg = config.ask_and_persist(config.load_config())
    print("当前生效配置:", json.dumps({k: anonymize(k, v) for k, v in cfg.items()}, ensure_ascii=False, indent=2))
    return 0


def do_clear():
    p = config.config_path()
    if p.exists():
        p.unlink()
        print(f"✔ 已删除配置 {p}")
    else:
        print("没有持久化配置可删除。")
    return 0


def do_test():
    merged = config.resolve_config({})
    if not config.is_configured(merged):
        print("✘ 未配置完整，请先运行 setup.py --set", file=sys.stderr)
        return 2
    # 直接做 API 连通性检查
    import urllib.request
    import urllib.error
    base = config.norm_base(merged["api_base"])
    payload = {
        "model": merged["model"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {merged.get('api_key','dummy')}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
        if "error" in body.lower()[:200] and "\"error\"" in body:
            print("⚠ 网关返回错误:", body[:500])
            return 4
        print("✔ API 连通并响应:", body[:300])
        return 0
    except urllib.error.HTTPError as e:
        print(f"✘ API 返回 {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"✘ 连接失败: {e}", file=sys.stderr)
        return 4


def main():
    p = argparse.ArgumentParser(description="vision-augment 配置工具")
    p.add_argument("--set", action="store_true", help="交互设置并持久化")
    p.add_argument("--clear", action="store_true", help="删除持久化配置")
    p.add_argument("--test", action="store_true", help="测试 API 连通性")
    args = p.parse_args()

    if args.set:
        return do_set()
    if args.clear:
        return do_clear()
    if args.test:
        return do_test()
    show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
