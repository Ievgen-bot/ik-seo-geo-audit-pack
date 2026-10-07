#!/usr/bin/env python3
"""classify_excluded.py — live-check every URL from the Search Console "not indexed" export and classify it.

usage: classify_excluded.py --excluded excluded.tsv --sitemap-urls urls.txt --out classified.tsv
  excluded.tsv: reason<TAB>url<TAB>last_crawl (one row per URL, as read from the GSC UI)
  urls.txt:     one URL per line = all URLs of the live sitemap(s) of the project

Classes (the owner's decisions can override them later):
  target page          200 + meta robots index + in the sitemap -> should be indexed
  intentionally closed noindex + not in the sitemap (deliberately hidden)
  duplicate host/URL   http / www / trailing-slash variants, redirects, canonical alternates
  legacy CMS           leftovers of an old CMS (wp-admin, ?page_id=, ?s=, /feed/, shop/checkout pages) -> 404/redirect
  other                needs a decision (dead host, redirect to 404, live page missing from the sitemap)
"""
import argparse, csv, re, urllib.error, urllib.request

LEGACY = re.compile(r"(wp-admin|wp-content|wp-json|\?page_id=|\?p=\d|\?s=|/feed/?$|/tag/|/author/|checkout|/cart|/shop)")
UA = "Mozilla/5.0 (compatible; ik-seo-geo-audit live-check)"

class NR(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None
OP = urllib.request.build_opener(NR)

def fetch(u):
    try:
        r = OP.open(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=30)
        return r.status, r.headers, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, (e.read().decode("utf-8", "ignore") if e.code not in (301, 302, 307, 308) else "")
    except Exception as e:
        return "ERR:" + type(e).__name__, {}, ""

def follow(u):
    hops, cur = [], u
    for _ in range(6):
        st, h, body = fetch(cur)
        hops.append(str(st))
        if st in (301, 302, 307, 308) and h.get("Location"):
            cur = urllib.request.urljoin(cur, h["Location"]); continue
        return hops, cur, st, h, body
    return hops, cur, st, h, body

def robots_meta(body):
    m = re.search(r'<meta[^>]+name="robots"[^>]*content="([^"]*)"', body, re.I) or \
        re.search(r'<meta[^>]+content="([^"]*)"[^>]*name="robots"', body, re.I)
    return m.group(1) if m else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excluded", required=True); ap.add_argument("--sitemap-urls", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sm = {l.strip() for l in open(a.sitemap_urls, encoding="utf-8") if l.strip()}
    rows = [l.rstrip("\n").split("\t") for l in open(a.excluded, encoding="utf-8") if l.strip()]
    out = []
    for r in rows:
        reason, url, crawl = (r + ["", ""])[:3]
        if "*" in url:
            out.append([reason, url, crawl, "pattern", "", "", "legacy CMS", "pattern rule from robots.txt", "nothing"]); continue
        hops, fin, last, h, body = follow(url)
        ro = robots_meta(body); host_dup = url.startswith("http://") or "://www." in url
        in_sm = fin in sm or url in sm
        if str(last).startswith("ERR"):
            c, why, act = "other", "host does not resolve / no response", "301 the old host or remove it from the index (owner decision)"
        elif last == 404 and (LEGACY.search(url) or host_dup):
            c, why, act = "legacy CMS", "old CMS URL, now 404", "nothing (drops out by itself)"
        elif last == 404:
            c, why, act = "other", "URL is 404 now" + (" after a redirect" if len(hops) > 1 else ""), "301 to the closest page or keep 404 (decide)"
        elif re.search(r"redirect|переспрям|переадрес|canonical|канонічн|каноничес|alternate|альтернатив", reason, re.I) or (len(hops) > 1 and in_sm):
            c, why, act = "duplicate host/URL", f"redirects ({len(hops)-1} hop(s)) to the canonical URL", "nothing; shorten chains of 3+ hops"
        elif "noindex" in ro and not in_sm:
            c, why, act = "intentionally closed" if not host_dup else "duplicate host/URL", "noindex + not in the sitemap", "nothing if deliberate"
        elif in_sm and "noindex" not in ro:
            c, why, act = "target page", "200, indexable and in the sitemap: Google's data is older than the page's current state or it was not crawled yet", "inspect URL; request indexing only for key pages after approval"
        elif LEGACY.search(url):
            c, why, act = "legacy CMS", "old CMS parameter/path", "nothing"
        else:
            c, why, act = "other", f"live page ({'/'.join(hops)}) not in the sitemap, robots='{ro}'", "decide: add to the sitemap or close it"
        out.append([reason, url, crawl, ">".join(hops), fin if fin != url else "", ro, c, why, act])
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["gsc_reason", "url", "gsc_last_crawl", "hops", "final_url", "meta_robots_live", "class", "why", "action"])
        w.writerows(out)
    from collections import Counter
    print(Counter(o[6] for o in out), len(out))

if __name__ == "__main__":
    main()
