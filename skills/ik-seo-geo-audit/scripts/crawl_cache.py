#!/usr/bin/env python3
"""crawl_cache.py — fetch every page of a multi-host project ONCE, sequentially, into a local cache that all
audit agents read (production servers often stall under parallel crawls).

usage: crawl_cache.py --out DIR --host https://example.com [--host https://blog.example.com ...]
                      [--limit 300] [--delay 0.3] [--extra /llms.txt,/rss.xml]

* URLs come from each host's robots.txt `Sitemap:` lines, else /sitemap.xml (sitemap indexes are followed).
* If the project total exceeds --limit, every host is sampled: all non-blog URLs first (commercial pages),
  then an even sample of blog-like URLs (/blog/, /news/, /articles/, dated paths). The sample is written to
  DIR/_sample.md so the report can say exactly what was covered.
* Output: DIR/_index.json (url, host, status, secs, bytes, file, headers, in_sitemap) + one body file per URL.
"""
import argparse, hashlib, json, re, time, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urljoin

UA = "Mozilla/5.0 (compatible; ik-seo-geo-audit cache)"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None

OPENER = urllib.request.build_opener(NoRedirect)

def get(url, timeout=60):
    t = time.time()
    try:
        r = OPENER.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)
        return r.status, dict(r.headers), r.read(), round(time.time() - t, 2)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read() if e.code not in (301, 302, 307, 308) else b"", round(time.time() - t, 2)
    except Exception as e:
        return "ERR:" + type(e).__name__, {}, b"", round(time.time() - t, 2)

def sitemap_urls(host):
    robots_status, _, robots, _ = get(host.rstrip("/") + "/robots.txt")
    maps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots.decode("utf-8", "ignore")) if robots_status == 200 else []
    maps = maps or [host.rstrip("/") + "/sitemap.xml"]
    urls, seen = [], set()
    while maps:
        m = maps.pop(0)
        if m in seen:
            continue
        seen.add(m)
        st, _, body, _ = get(m)
        if st != 200:
            continue
        txt = body.decode("utf-8", "ignore")
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt)
        if "<sitemapindex" in txt:
            maps += locs
        else:
            urls += locs
    urls = list(dict.fromkeys(urls))
    return urls or [host.rstrip("/") + "/"]  # no sitemap: at least the homepage

BLOGLIKE = re.compile(r"/(blog|news|articles?|posts?|insights|journal)/|/\d{4}/\d{2}/")

def sample(urls, quota):
    core = [u for u in urls if not BLOGLIKE.search(urlsplit(u).path)]
    blog = [u for u in urls if BLOGLIKE.search(urlsplit(u).path)]
    if len(core) >= quota:
        return core[:quota]
    rest = quota - len(core)
    step = max(1, len(blog) // rest) if rest else len(blog) + 1
    return core + blog[::step][:rest]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", action="append", required=True)
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--extra", default="/robots.txt,/sitemap.xml,/llms.txt,/llms-full.txt,/this-page-does-not-exist-404-test")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    per_host = {h.rstrip("/"): sitemap_urls(h) for h in a.host}
    total = sum(len(v) for v in per_host.values())
    plan, notes = [], []
    for h, urls in per_host.items():
        quota = len(urls) if total <= a.limit else max(10, round(a.limit * len(urls) / max(total, 1)))
        chosen = sample(urls, quota) if quota < len(urls) else urls
        notes.append(f"| {h} | {len(urls)} | {len(chosen)} |")
        plan += [(h, u, True) for u in chosen]
        plan += [(h, h + p, False) for p in a.extra.split(",") if p]
    (out / "_sample.md").write_text(
        f"# Crawl coverage\n\nProject total in sitemaps: {total}; limit: {a.limit}; "
        f"{'all URLs crawled' if total <= a.limit else 'sampled: all non-blog URLs first, then an even sample of blog-like URLs'}.\n\n"
        "| Host | URLs in sitemap | Crawled |\n|---|---|---|\n" + "\n".join(notes) + "\n", encoding="utf-8")
    idx = []
    for h, u, insm in plan:
        st, hd, body, secs = get(u)
        f = out / (hashlib.md5(u.encode()).hexdigest()[:12] + ".body")
        f.write_bytes(body)
        idx.append({"url": u, "host": h, "status": st, "secs": secs, "bytes": len(body), "file": f.name,
                    "headers": hd, "in_sitemap": insm})
        time.sleep(a.delay)
    json.dump(idx, open(out / "_index.json", "w"), indent=1, ensure_ascii=False)
    slow = [(i["url"], i["secs"]) for i in idx if isinstance(i["secs"], float) and i["secs"] > 5]
    bad = [(i["url"], i["status"]) for i in idx if i["status"] != 200 and i["in_sitemap"]]
    print(f"cached {len(idx)} responses for {len(per_host)} host(s) -> {out}")
    print(f"slow (>5s): {slow[:10]}")
    print(f"sitemap URLs not 200: {bad[:20]}")

if __name__ == "__main__":
    main()
