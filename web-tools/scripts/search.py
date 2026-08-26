#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络搜索工具 — 用 Obscura 无头浏览器渲染 Bing / Google / GitHub 后抽取结果。
Bing/Google 走真实浏览器渲染（反爬强、不易被 429）；GitHub 先渲染搜索页，
被限流时自动降级官方 REST API（稳定，含 star/语言/代码搜索）。

用法:
  python3 search.py "python asyncio"                    # 三引擎并行 (bing+google+github)
  python3 search.py "python asyncio" -e bing            # 仅 Bing
  python3 search.py "fastapi" -e github -n 10           # GitHub 10 条 (含 star/语言)
  python3 search.py "asyncio" -e github -t code         # GitHub 代码搜索 (API)
  python3 search.py "docker 教程" -e bing --cn           # Bing 中文站
  python3 search.py "x" -e all -j                       # JSON 输出

环境变量:
  OBSCURA_BIN      Obscura 二进制路径 (默认 scripts/bin/obscura)
  GITHUB_TOKEN     GitHub API 限流 60/h -> 5000/h (代码搜索必需)
  SEARCH_TIMEOUT   每引擎超时秒 (默认 45，渲染页面较慢)

输出: 按引擎分节的 Markdown；-j 输出 JSON 数组。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
NOTES = []            # 引擎跳过的极简原因，统一在退出前以一行输出
MIN_STARS = int(os.environ.get("GH_MIN_STARS", "30"))   # GitHub 最低 star，过滤垃圾仓
SKIP_OR_WORDS = {"graph", "agent", "llm", "ai", "code", "data", "tool", "system",
                 "open", "source", "project", "library", "framework", "python",
                 "memory", "mem", "knowledge", "temporal", "search", "build",
                 "based", "using", "with", "for", "ai"}   # 太泛的词不参与 OR 兜底
BIN = os.environ.get("OBSCURA_BIN", os.path.join(SCRIPT_DIR, "bin", "obscura"))

NAV_URL_HINTS = ("bing.com/search", "news/", "images/", "videos/", "academic/",
                 "dict/", "maps", "travel", "flights", "javascript:", "microsoft",
                 "/search?q=", "google.com/", "webcache", "#", "support.google")
GOOGLE_CAPTCHA_HINTS = ("unusual traffic", "captcha", "not a robot", "terms of service",
                        "Why did this happen", "before proceeding")


# ------------------------------------------------------------ 无头渲染 ----
def render_markdown(url, timeout, stealth=True):
    """用 Obscura 无头浏览器渲染页面，返回 markdown 文本（纯文本）。"""
    cmd = [BIN, "fetch", url, "--wait-until", "networkidle0",
           "--dump", "markdown", "--timeout", str(timeout), "-q"]
    if stealth:
        cmd.append("--stealth")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 20,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.stderr.write(f"找不到 Obscura 二进制 ({BIN})，先运行 bash scripts/download.sh\n")
        sys.exit(2)
    except subprocess.TimeoutExpired:
        return ""
    return r.stdout


def _clean_md(s):
    s = re.sub(r"!\[[^]]*\]\([^)]*\)", "", s)      # 去图片 ![x](y)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)          # 去加粗
    s = re.sub(r"\[(.*?)\]\([^)]+\)", r"\1", s)     # 去行内链接保留文字
    s = re.sub(r"[#>*`_~]+", "", s)                  # 去 markdown 符号
    return re.sub(r"\s+", " ", s).strip()


def parse_md_entries(md, nav_hints, min_snip=0):
    """从 markdown 中抽取 `## [Title](url)` 条目及其后跟随的摘要行。"""
    out = []
    m = re.search(r"^##\s+\[(?P<title>.+?)\]\((?P<url>[^)\s]+)\)", md, re.M)
    pos, end = m.span() if m else (0, 0)
    for am in re.finditer(r"^##\s+\[(?P<title>.+?)\]\((?P<url>[^)\s]+)\)", md, re.M):
        url = am.group("url").strip()
        title = _clean_md(am.group("title"))
        if not url.startswith("http"):
            continue
        if any(h in url for h in nav_hints):
            continue
        seg = md[am.end():]
        nxt = re.search(r"^##\s+\[", seg, re.M)
        body = seg[: nxt.start()] if nxt else seg
        lines = []
        for ln in body.splitlines():
            if re.match(r"^\s*\d+\.\s*!?\[", ln):
                break            # 下一结果的列表项残渣(数字. [..])，终止本条
            ln = _clean_md(ln)
            ln = ln.strip("· \t")
            if not ln:
                if lines:          # 已收集到内容，遇到空行则结束本条
                    break
                continue            # 跳过标题后的前导空行
            if re.match(r"^\d+\.\s*$", ln):
                break
            lines.append(ln)
        snippet = " ".join(lines).strip()
        if min_snip and len(snippet) < min_snip:
            continue
        out.append({"title": title, "url": url, "snippet": snippet})
    # 去重（markdown 中同一结果可能重复出现）
    seen, uniq = set(), []
    for it in out:
        key = it["url"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq


# ----------------------------------------------------------------- Bing ----
def search_bing(query, num, timeout, cn=False):
    params = urllib.parse.urlencode(
        {"q": query, "count": num, "setlang": "zh-hans" if cn else "en"})
    base = "https://www.bing.com/search" if cn else "https://www.bing.com/search"
    md = render_markdown(f"{base}?{params}&FORM=QBLH", timeout)
    res = parse_md_entries(md, NAV_URL_HINTS)
    for it in res:
        it["engine"] = "bing"
    return res[:num]


# --------------------------------------------------------------- Google ----
def search_google(query, num, timeout):
    params = urllib.parse.urlencode({"q": query, "num": min(num, 20),
                                     "hl": "en", "gl": "us"})
    url = f"https://www.google.com/search?{params}"
    md = render_markdown(url, timeout)
    low = md.lower()
    if any(h in low for h in GOOGLE_CAPTCHA_HINTS):
        NOTES.append("google:blocked")
        return []
    res = parse_md_entries(md, NAV_URL_HINTS)
    for it in res:
        it["engine"] = "google"
    return res[:num]


# GitHub topics 页解析（无头浏览器渲染 github.com/topics/<slug>，云 IP 也能通）
RE_TOPIC_BLOCK = re.compile(
    r"###\s+\[(?P<owner>[^]]+)\]\(/\S+\)\s*/\s*\n(?P<rest>.*?)(?=###\s+\[|$)",
    re.S)


def _gh_topic_slugs(query):
    """query -> 候选 topics slug。记忆类 query 优先常用主题，否则 kebab-case(query)。"""
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    cands = [slug]
    low = query.lower()
    if any(k in low for k in ("memory", "mem", "rag", "knowledge", "context", "agent")):
        cands = ["agent-memory", "memory", "rag", "knowledge-graph", "llm-agents"] + cands
    return list(dict.fromkeys(cands))


def parse_github_topics(md, num):
    out = []
    for m in RE_TOPIC_BLOCK.finditer(md):
        owner = m.group("owner").strip()
        rest = m.group("rest")
        rm = re.search(r"\[(?P<repo>[^]]+)\]\(/(?P<owner2>[^/]+)/(?P<path>[^)]+)\)",
                       rest.split("- [Code]")[0])
        if not rm or rm.group("owner2") != owner:
            # 备选：直接找 /owner/repo 形式
            rm = re.search(r"\[(?P<repo>[^]]+)\]\(/%s/(?P<path>[^)]+)\)" % re.escape(owner), rest)
            if not rm:
                continue
            repo, path = rm.group("repo"), rm.group("path")
        else:
            repo, path = rm.group("repo"), rm.group("path")
        full = f"{owner}/{repo}" if repo != path else f"{owner}/{path}"
        sm = re.search(r"Star\s*([\d.,]+\s*[kK]?)", rest)
        star = (sm.group(1).replace(" ", "") if sm else "")
        # 描述：取 「- Code」 段之后到 "Updated" 前的首个长文本段（跳过 topics 标签）
        body = rest.split("- [Code]")[-1].split("- Updated")[0]
        desc = ""
        for para in re.findall(r"\n\s{6,}([^\n\[]{20,})", body):
            t = para.strip()
            if len(t) >= 12 and not t.startswith("·") and "]" not in t:
                desc = t
                break
        if full.startswith("/"):
            full = full[1:]
        if "." not in full.replace("/", "."):
            continue
        out.append({"title": full, "url": f"https://github.com/{full}",
                    "snippet": (f"{desc} | :star:{star}" if star else desc), "engine": "github"})
        if len(out) >= num:
            break
    return out

# --------------------------------------------------------------- GitHub ----
def _gh_req(q, endpoint, per_page, timeout):
    params = urllib.parse.urlencode({"q": q, "per_page": per_page, "sort": "stars"})
    url = f"https://api.github.com/search/{endpoint}?{params}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "web-search-skill"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _gh_repo_out(it):
    title = it.get("full_name", "")
    url = it.get("html_url", "")
    desc = (it.get("description") or "").strip()
    snip = (desc[:220] + "…") if len(desc) > 220 else desc
    lang = it.get("language") or "?"
    snip += " | :star:%d | %s" % (it.get("stargazers_count", 0), lang)
    return {"title": title, "url": url, "snippet": snip, "engine": "github",
            "stars": it.get("stargazers_count", 0), "_desc": desc}


def _gh_repo_search(query, num, timeout, min_stars):
    words = [w for w in re.split(r"[\s,，、]+", query.strip()) if w and len(w) > 1]
    # 只跑 1~2 次 API（未认证 60/h 很稀缺，避免 4 轮直接打满）：
    #  R1 跨字段查询 in:name,in:description,in:readme：query 各词在任一字段 AND 命中，
    #      README 命中主题类项目（awesome-list/记忆库），name/desc 命中命名项目，
    #      vllm/ComfyUI 这类只因正文含 memory 的无关大仓被 AND 全词挡在门外。
    rounds = [f"{query} in:name in:description in:readme"]
    #  R2 专名救场：OR 只留给“专有名词”（剔除 graph/agent/memory 等通用词），
    #      捞回 zep/langmem/cognee 这类命名字段含关键词但 R1 撞空的知名项目。
    or_words = [w for w in words if w.lower() not in SKIP_OR_WORDS]
    if or_words:
        rounds.append(" OR ".join(or_words) + " in:name in:description")

    seen, picked = set(), []
    for q in rounds:
        try:
            data = _gh_req(q, "repositories", 40, timeout)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                NOTES.append("github:rate-limit(需 GITHUB_TOKEN)" if not os.environ.get("GITHUB_TOKEN")
                             else "github:rate-limit")
            continue
        except urllib.error.URLError:
            continue
        for it in data.get("items", []):
            stars = it.get("stargazers_count", 0)
            if stars < min_stars:
                continue
            if it.get("fork"):
                continue
            full = it.get("full_name", "")
            if full in seen:
                continue
            seen.add(full)
            picked.append(_gh_repo_out(it))
    # 质量优先：有描述的排在空描述前；同质量按 star
    picked.sort(key=lambda r: (r["_desc"] != "", -r["stars"]))
    for r in picked:
        r.pop("_desc", None)
        r.pop("stars", None)
    return picked[:num]


def _gh_api(query, num, kind, timeout, min_stars=30):
    if kind == "repo":
        return _gh_repo_search(query, num, timeout, min_stars)
    # code 搜索（需 GITHUB_TOKEN），单轮 best effort
    try:
        data = _gh_req(query, "code", min(num, 30), timeout)
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None  # 交给上层提示 token
    out = []
    for it in data.get("items", [])[:num]:
        repo = it.get("repository", {}).get("full_name", "")
        title = repo + " · " + (it.get("name") or it.get("path", ""))
        url = it.get("html_url", "")
        out.append({"title": title, "url": url,
                    "snippet": (it.get("path") or "").strip() + f" | in {repo}",
                    "engine": "github"})
    return out


_GH_RATE_LIMITED = False   # 本次运行已发现 github.com/search 被限流，后续跳过该渲染


def search_github(query, num, timeout, kind="repo", min_stars=None):
    if min_stars is None:
        min_stars = MIN_STARS
    type_map = {"repo": "repositories", "code": "code"}
    global _GH_RATE_LIMITED

    # 1) 无头浏览器渲染 github.com/search （住宅 IP 正常；云/数据中心 IP 常被二次限流）
    if kind == "repo" and not _GH_RATE_LIMITED:
        url = ("https://github.com/search?q=" + urllib.parse.quote(query) +
               "&type=repositories")
        md = render_markdown(url, timeout)
        if re.search(r"too many requests|rate limit", md, re.I) or not md:
            _GH_RATE_LIMITED = True
            NOTES.append("github:html-limited(本机数据中心IP被GitHub二次限流, 改用 topics 渲染)")
        else:
            res = parse_md_entries(md, NAV_URL_HINTS)
            if res:
                for it in res:
                    it["engine"] = "github"
                return res[:num]

    # 2) 无头浏览器渲染 github.com/topics/<slug>（云 IP 可靠，返回仓库列表）
    if kind == "repo":
        for slug in _gh_topic_slugs(query):
            if not slug:
                continue
            md = render_markdown(f"https://github.com/topics/{slug}", timeout)
            res = parse_github_topics(md, num)
            if res and len(res) >= 1:
                return res[:num]

    # 3) 兜底：官方 REST API（token 可 5000/h；无 token 60/h 且代码搜索必需）
    try:
        got = _gh_api(query, num, kind, timeout, min_stars=min_stars)
        if got is not None:
            return got
        NOTES.append("github:code-search需 GITHUB_TOKEN")
        return []
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        code = getattr(e, "code", "?")
        NOTES.append(f"github:fail(HTTP {code})" + ("" if os.environ.get("GITHUB_TOKEN") else ", 需 GITHUB_TOKEN"))
        return []


# ------------------------------------------------------------------ main ----
def fmt_md(results, brief=False):
    blocks = []
    cut = 60 if brief else 140
    for eng in ("bing", "google", "github"):
        items = [r for r in results if r["engine"] == eng]
        if not items:
            continue
        blocks.append(f"## {eng.title()} x{len(items)}")
        for i, it in enumerate(items, 1):
            u = it["url"]
            blocks.append(f"{i}. {it['title'] or '—'} — {u}")
            s = (it.get("snippet") or "").strip()
            if s:
                blocks.append(f"   {s[:cut]}")
        blocks.append("")
    return "\n".join(blocks)


def main():
    ap = argparse.ArgumentParser(
        description="网络搜索工具（Obscura 无头浏览器渲染 Bing/Google/GitHub）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(__doc__.split("环境变量:")[0]).strip())
    ap.add_argument("query", help="搜索关键词 / GitHub 搜索语法")
    ap.add_argument("-e", "--engine", choices=["bing", "google", "github", "all"],
                    default="all", help="搜索引擎 / 默认 all 并行三引擎")
    ap.add_argument("-t", "--type", choices=["repo", "code"], default="repo",
                    help="GitHub 搜索类型 repo|code（默认 repo）")
    ap.add_argument("-n", "--num", type=int, default=5, help="每引擎结果数（默认 5）")
    ap.add_argument("-j", "--json", action="store_true", help="输出 JSON 数组")
    ap.add_argument("--cn", action="store_true", help="Bing 中文检索")
    ap.add_argument("--min-stars", type=int, default=MIN_STARS,
                    help="GitHub 最低 star 过滤（默认30，0=不过滤）")
    ap.add_argument("--brief", action="store_true",
                    help="精简输出：摘要截到 60 字符（省 token）")
    ap.add_argument("--no-stealth", action="store_true", help="关闭反检测指纹")
    args = ap.parse_args()

    timeout = int(os.environ.get("SEARCH_TIMEOUT", "45"))
    stealth = not args.no_stealth

    engines = {"bing", "google", "github"} if args.engine == "all" else {args.engine}
    results = []
    for eng in sorted(engines):
        try:
            if eng == "bing":
                got = search_bing(args.query, args.num, timeout, cn=args.cn)
            elif eng == "google":
                got = search_google(args.query, args.num, timeout)
            else:
                got = search_github(args.query, args.num, timeout, kind=args.type,
                                    min_stars=args.min_stars)
        except Exception as e:
            NOTES.append(f"{eng}:fail({type(e).__name__})")
            got = []
        results.extend(got)

    if not results:
        sys.stderr.write("NONE" + (f" ({'; '.join(NOTES)})" if NOTES else "") + "\n")
        sys.exit(1)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if NOTES:
            sys.stderr.write("> " + "; ".join(NOTES) + "\n")
        print(fmt_md(results, brief=args.brief))


if __name__ == "__main__":
    main()
