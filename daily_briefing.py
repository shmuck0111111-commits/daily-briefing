#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_briefing.py - fuer GitHub Actions"""

import requests
import xml.etree.ElementTree as ET
import html as html_module
import os
import warnings
from datetime import datetime, timezone, timedelta
import re

warnings.filterwarnings("ignore")

FEEDS = [
    {"name":"Tagesschau","country":"DE","emoji":"🇩🇪","urls":[
        "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml",
        "https://www.tagesschau.de/xml/rss2/"]},
    {"name":"Spiegel Online","country":"DE","emoji":"🇩🇪","urls":[
        "https://www.spiegel.de/schlagzeilen/tops/index.rss",
        "https://www.spiegel.de/schlagzeilen/index.rss"]},
    {"name":"BBC News","country":"EN","emoji":"🇬🇧","urls":[
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/rss.xml"]},
    {"name":"Deutsche Welle","country":"EN","emoji":"🌐","urls":[
        "https://rss.dw.com/xml/rss-en-all",
        "https://rss.dw.com/xml/rss-en-top"]},
]

MAX_ITEMS = 12
MAX_HOURS = 24
OUTPUT_FILE = "docs/index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

KEYWORDS = [
    "politik","regierung","minister","kanzler","bundestag","wahl","partei",
    "koalition","cdu","spd","gruene","afd","fdp",
    "eu","europa","kommission","nato","ukraine","russland","china","usa",
    "trump","merz","scholz","macron","putin",
    "wirtschaft","konjunktur","inflation","zinsen","ezb","bundesbank",
    "dax","aktien","boerse","markt","energie","oel","gas","handel",
    "haushalt","schulden","milliard","rezession","wachstum","steuer",
    "economy","market","finance","bank","rate","trade","stock",
    "election","government","war","sanctions","europe","germany",
    "parliament","president","policy","budget","crisis","tariff",
    "gdp","recession","fed","ecb","interest","iran","israel","attack",
]

def get_text(el):
    if el is None or el.text is None:
        return ""
    return el.text.strip()

def strip_ns(s):
    s = re.sub(r' xmlns(?::[a-zA-Z0-9]+)?="[^"]*"', "", s)
    s = re.sub(r"<(/?)[a-zA-Z0-9]+:([a-zA-Z0-9]+)", r"<\1\2", s)
    return s

def clean_desc(s):
    s = re.sub(r"<[^>]+>", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:220]

def parse_one(url, max_items):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    raw = r.content.decode("utf-8", errors="replace")
    raw = strip_ns(raw)
    root = ET.fromstring(raw.encode("utf-8"))
    items = []
    for item in root.iter("item"):
        title   = html_module.unescape(get_text(item.find("title")))
        link    = get_text(item.find("link")) or "#"
        desc    = html_module.unescape(get_text(item.find("description")))
        pubdate = get_text(item.find("pubDate"))
        desc    = clean_desc(desc)
        pub_dt  = parse_date(pubdate)
        if title:
            items.append({"title":title,"link":link,"desc":desc,
                          "pubdate":pubdate,"pub_dt":pub_dt})
        if len(items) >= max_items:
            break
    return items

def parse_feed(urls, max_items=12):
    last_err = ""
    for url in urls:
        try:
            items = parse_one(url, max_items)
            if items:
                return items, ""
        except Exception as e:
            last_err = str(e)
    return [], last_err

def parse_date(s):
    if not s:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S +0000",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return None

def is_recent(pub_dt):
    if pub_dt is None:
        return True
    try:
        now = datetime.now(timezone.utc)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        return (now - pub_dt) <= timedelta(hours=MAX_HOURS)
    except:
        return True

def is_relevant(title, desc):
    txt = (title + " " + desc).lower()
    return any(k in txt for k in KEYWORDS)

def fmt_time(pub_dt, pubdate):
    if pub_dt:
        try:
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            return pub_dt.astimezone().strftime("%H:%M")
        except:
            pass
    return pubdate[:5] if pubdate else ""

def age_label(pub_dt):
    if not pub_dt:
        return ""
    try:
        now = datetime.now(timezone.utc)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        diff = now - pub_dt
        mins = int(diff.total_seconds() / 60)
        if mins < 60:
            return f"vor {mins} Min"
        return f"vor {mins // 60} Std"
    except:
        return ""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#08090e;--bg2:#0d0f18;--sf:#12151f;--sf2:#181c2a;--bd:#1e2235;--bd2:#252a3d;
      --ac:#5b9cf6;--ac2:#8b72f8;--tx:#f0f2f8;--tx2:#b8bdd4;--mu:#6b7194;--new:#10b981;}
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{font-family:"Inter",system-ui,sans-serif;background:var(--bg);color:var(--tx);
     min-height:100vh;padding-bottom:80px;
     background-image:radial-gradient(ellipse at 20% 0%,rgba(91,156,246,.06) 0%,transparent 60%),
                      radial-gradient(ellipse at 80% 100%,rgba(139,114,248,.05) 0%,transparent 60%);}
.hdr{background:rgba(13,15,24,.92);border-bottom:1px solid var(--bd);padding:20px 24px 16px;
     position:sticky;top:0;z-index:100;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);}
.hdr-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
.hdr-left h1{font-size:1.45rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,var(--ac),var(--ac2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hdr-meta{font-size:.75rem;color:var(--mu);margin-top:3px;}
.hdr-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.pill{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:20px;
      font-size:.7rem;font-weight:600;border:1px solid var(--bd2);background:var(--sf);color:var(--tx2);}
.pill-ac{background:rgba(91,156,246,.12);border-color:rgba(91,156,246,.3);color:var(--ac);}
.live{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;
      font-size:.65rem;font-weight:700;background:rgba(16,185,129,.12);
      border:1px solid rgba(16,185,129,.3);color:var(--new);letter-spacing:.5px;}
.live::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--new);animation:pulse 1.5s infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.4;transform:scale(.8);}}
.btn-r{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;border-radius:20px;
       font-size:.73rem;font-weight:600;
       background:linear-gradient(135deg,rgba(91,156,246,.18),rgba(139,114,248,.18));
       border:1px solid rgba(91,156,246,.35);color:var(--ac);cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-r:hover{background:linear-gradient(135deg,rgba(91,156,246,.3),rgba(139,114,248,.3));transform:translateY(-1px);}
.wrap{max-width:1200px;margin:0 auto;padding:24px 16px;}
.slabel{font-size:.68rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
        color:var(--mu);margin-bottom:12px;padding-left:2px;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:26px;}
@media(max-width:720px){.grid{grid-template-columns:1fr;}.hdr-right{display:none;}}
.card{background:var(--sf);border:1px solid var(--bd);border-radius:16px;overflow:hidden;
      display:flex;flex-direction:column;transition:border-color .2s,box-shadow .2s;}
.card:hover{border-color:var(--bd2);box-shadow:0 8px 32px rgba(0,0,0,.4);}
.card-hdr{padding:13px 16px;display:flex;align-items:center;gap:9px;
          border-bottom:1px solid var(--bd);background:var(--sf2);position:relative;overflow:hidden;}
.card-hdr::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;}
.card-de .card-hdr::before{background:linear-gradient(180deg,#e63946,#ff8fa3);}
.card-en .card-hdr::before{background:linear-gradient(180deg,#56b4e9,#74c7f0);}
.card-em{font-size:1.2rem;line-height:1;}
.card-name{font-weight:700;font-size:.9rem;}
.card-cnt{font-size:.63rem;font-weight:600;background:var(--bd2);color:var(--mu);padding:2px 7px;border-radius:20px;}
.card-bdg{margin-left:auto;font-size:.63rem;font-weight:700;padding:2px 8px;border-radius:20px;}
.bdg-de{background:rgba(230,57,70,.12);color:#ff6b6b;border:1px solid rgba(230,57,70,.25);}
.bdg-en{background:rgba(86,180,233,.12);color:#56b4e9;border:1px solid rgba(86,180,233,.25);}
.nlist{flex:1;}
.ni{padding:12px 16px;border-bottom:1px solid var(--bd);transition:background .15s;}
.ni:last-child{border-bottom:none;}
.ni:hover{background:var(--sf2);}
.ni:hover .ni-arr{opacity:1;transform:translateX(0);}
.ni a{text-decoration:none;color:inherit;display:block;}
.ni-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;}
.nt{font-size:.855rem;font-weight:600;color:var(--tx);line-height:1.45;margin-bottom:5px;flex:1;transition:color .15s;}
.ni:hover .nt{color:var(--ac);}
.ni-arr{color:var(--ac);font-size:.72rem;opacity:0;transform:translateX(-4px);transition:all .15s;flex-shrink:0;margin-top:2px;}
.nd{font-size:.73rem;color:var(--tx2);line-height:1.5;margin-bottom:6px;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.ni-foot{display:flex;align-items:center;gap:7px;}
.nm{font-size:.67rem;color:var(--mu);}
.ni-new{font-size:.58rem;font-weight:700;letter-spacing:.5px;
        background:rgba(16,185,129,.1);color:var(--new);border:1px solid rgba(16,185,129,.25);
        padding:1px 6px;border-radius:20px;}
.empty{padding:22px;color:var(--mu);font-size:.82rem;text-align:center;}
.err{padding:14px 16px;color:#f87171;font-size:.76rem;line-height:1.6;word-break:break-word;}
.foot{text-align:center;color:var(--mu);font-size:.7rem;margin-top:36px;
      padding:18px;border-top:1px solid var(--bd);}
"""

MANIFEST = '''{"name":"Daily Briefing","short_name":"Briefing",
"description":"Taegliches News-Briefing: Politik, Wirtschaft, EU",
"start_url":"/daily-briefing/","display":"standalone",
"background_color":"#08090e","theme_color":"#08090e",
"orientation":"portrait",
"icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png"},
         {"src":"icon-512.png","sizes":"512x512","type":"image/png"}]}'''

SW_JS = """
const CACHE = "briefing-v1";
const ASSETS = ["./"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});
self.addEventListener("fetch", e => {
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
"""

def build_card(r):
    bdg   = "de" if r["country"] == "DE" else "en"
    items = r["items"]
    if r["error"] and not items:
        e    = html_module.escape(r["error"][:200])
        body = f'<div class="err">&#9888; Feed nicht erreichbar:<br><small>{e}</small></div>'
    elif not items:
        body = '<div class="empty">Keine aktuellen Artikel.</div>'
    else:
        rows = ""
        for i, it in enumerate(items):
            t   = html_module.escape(it["title"])
            lk  = html_module.escape(it["link"])
            d   = (f'<div class="nd">{html_module.escape(it["desc"])}</div>' if it["desc"] else "")
            ts  = fmt_time(it["pub_dt"], it["pubdate"])
            age = age_label(it["pub_dt"])
            nm  = f'<span class="nm">{ts} &middot; {age}</span>' if ts else ""
            nb  = '<span class="ni-new">NEU</span>' if i < 2 else ""
            rows += (
                f'<div class="ni"><a href="{lk}" target="_blank" rel="noopener">'
                f'<div class="ni-top"><div class="nt">{t}</div><span class="ni-arr">&#8594;</span></div>'
                f'{d}<div class="ni-foot">{nm}{nb}</div></a></div>'
            )
        body = f'<div class="nlist">{rows}</div>'
    cnt = f'<span class="card-cnt">{len(items)} Artikel</span>' if items else ""
    return (
        f'<div class="card card-{bdg}"><div class="card-hdr">'
        f'<span class="card-em">{r["emoji"]}</span><span class="card-name">{r["name"]}</span>'
        f'{cnt}<span class="card-bdg bdg-{bdg}">{r["country"]}</span></div>{body}</div>'
    )

def build_page(results, now):
    ds    = now.strftime("%d. %B %Y")
    ts    = now.strftime("%H:%M")
    wd    = now.strftime("%A")
    total = sum(r["count"] for r in results)
    de_c  = "".join(build_card(r) for r in results if r["country"] == "DE")
    en_c  = "".join(build_card(r) for r in results if r["country"] == "EN")
    return (
        "<!DOCTYPE html><html lang='de'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='mobile-web-app-capable' content='yes'>"
        "<meta name='apple-mobile-web-app-capable' content='yes'>"
        "<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>"
        "<meta name='theme-color' content='#08090e'>"
        f"<title>Daily Briefing &ndash; {ds}</title>"
        "<link rel='manifest' href='manifest.json'>"
        "<link rel='apple-touch-icon' href='icon-192.png'>"
        f"<style>{CSS}</style>"
        "<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('sw.js');</script>"
        "</head><body>"
        "<div class='hdr'><div class='hdr-inner'>"
        "<div class='hdr-left'>"
        f"<h1>&#128240; Daily Briefing</h1>"
        f"<div class='hdr-meta'>{wd}, {ds} &middot; {ts} Uhr &middot; Politik &middot; Wirtschaft &middot; EU/Welt</div>"
        "</div>"
        "<div class='hdr-right'>"
        f"<span class='pill pill-ac'>&#128240; {total} Artikel</span>"
        "<span class='live'>LIVE</span>"
        "<a class='btn-r' href='javascript:location.reload()'>&#8635; Reload</a>"
        "</div></div></div>"
        "<div class='wrap'>"
        "<div class='slabel'>🇩🇪 Deutschland &amp; Europa</div>"
        f"<div class='grid'>{de_c}</div>"
        "<div class='slabel'>🌐 International</div>"
        f"<div class='grid'>{en_c}</div>"
        f"<div class='foot'>Stand: {ds} {ts} Uhr &middot; Tagesschau &middot; Spiegel &middot; BBC &middot; DW &middot; Kein API-Key</div>"
        "</div></body></html>"
    )

def main():
    print("Daily Briefing generieren...")
    now = datetime.now(timezone.utc)
    os.makedirs("docs", exist_ok=True)
    results = []
    for feed in FEEDS:
        print(f"  {feed['name']}...", end=" ", flush=True)
        raw, err = parse_feed(feed["urls"], MAX_ITEMS)
        filtered = [i for i in raw if is_recent(i["pub_dt"]) and is_relevant(i["title"], i["desc"])]
        if len(filtered) < 3 and raw:
            filtered = [i for i in raw if is_recent(i["pub_dt"])]
        if not filtered:
            filtered = raw
        print(f"{len(filtered)} Artikel")
        results.append({"name":feed["name"],"country":feed["country"],
                        "emoji":feed["emoji"],"items":filtered,
                        "count":len(filtered),"error":err})
    page = build_page(results, now)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page)
    with open("docs/manifest.json", "w", encoding="utf-8") as f:
        f.write(MANIFEST)
    with open("docs/sw.js", "w", encoding="utf-8") as f:
        f.write(SW_JS)
    print(f"Fertig: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
