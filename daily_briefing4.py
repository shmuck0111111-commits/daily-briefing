#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_briefing4.py - Taegliches News-Briefing via RSS + Wetter, kein API-Key"""

import requests
import xml.etree.ElementTree as ET
import html as html_module
import os
import warnings
from datetime import datetime, timezone, timedelta
import re

warnings.filterwarnings("ignore")

FEEDS = [
    {"name":"Tagesschau","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml",
        "https://www.tagesschau.de/xml/rss2/"]},
    {"name":"Spiegel Online","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://www.spiegel.de/schlagzeilen/tops/index.rss",
        "https://www.spiegel.de/schlagzeilen/index.rss"]},
    {"name":"FAZ","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://www.faz.net/rss/aktuell/",
        "https://www.faz.net/rss/aktuell/politik/"]},
    {"name":"Zeit Online","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://newsfeed.zeit.de/index",
        "https://newsfeed.zeit.de/politik/index"]},
    {"name":"Süddeutsche Zeitung","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://rss.sueddeutsche.de/rss/Topthemen",
        "https://rss.sueddeutsche.de/rss/politik"]},
    {"name":"ARD Börse","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://boerse.ard.de/rss/wirtschaft.xml",
        "https://www.tagesschau.de/wirtschaft/index~rss2.xml"]},
    {"name":"finanzen.net","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://www.finanzen.net/rss/news",
        "https://www.finanzen.net/nachricht/rss"]},
    {"name":"Deutsche Welle","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://rss.dw.com/xml/rss-de-all",
        "https://rss.dw.com/xml/rss-de-top"]},
    {"name":"n-tv","country":"DE","emoji":"\U0001f1e9\U0001f1ea","urls":[
        "https://www.n-tv.de/rss",
        "https://www.n-tv.de/politik/rss"]},
]

# Hartes Pinning: Kategorie wird gesetzt – aber nur wenn Pflicht-Keywords vorhanden
PINNED_HARD = {
    "ARD Börse":    "Wirtschaft",
    "finanzen.net": "Wirtschaft",
}
# Pflicht-Keywords für PINNED_HARD (Wirtschaft): Artikel ohne diese werden verworfen
WIRTSCHAFT_REQUIRED = {
    "aktien","b\u00f6rse","boerse","dax","mdax","sdax","tecdax",
    "zinsen","leitzins","inflation","konjunktur","rezession",
    "anleihe","rendite","dividende","kurs","kursverlust","kursgewinn",
    "quartalsergebnis","jahresbilanz","gewinnwarnung","umsatzeinbruch",
    "bruttoinlandsprodukt","bundesbank","ezb","fed",
    "handelsbilanz","rohstoff","oel","gold","devisen","ipo","fusion","\u00fcbernahme",
}
# Weiches Pinning: gilt nur als Fallback wenn kein Keyword greift
PINNED_SOFT = {
    "Deutsche Welle": "Sonstiges",
    "n-tv":           "Sonstiges",
}

WMO_CODES = {
    0:"\u2600\ufe0f Klar", 1:"\U0001f324\ufe0f Meist klar", 2:"\u26c5 Teilw. bew\u00f6lkt", 3:"\u2601\ufe0f Bedeckt",
    45:"\U0001f32b\ufe0f Nebel", 48:"\U0001f32b\ufe0f Nebel", 51:"\U0001f326\ufe0f Nieselregen", 53:"\U0001f326\ufe0f Nieselregen",
    55:"\U0001f327\ufe0f Nieselregen", 61:"\U0001f327\ufe0f Regen", 63:"\U0001f327\ufe0f Regen", 65:"\U0001f327\ufe0f Starkregen",
    71:"\U0001f328\ufe0f Schnee", 73:"\U0001f328\ufe0f Schnee", 75:"\u2744\ufe0f Starker Schnee",
    80:"\U0001f326\ufe0f Schauer", 81:"\U0001f327\ufe0f Schauer", 82:"\u26c8\ufe0f Starke Schauer",
    95:"\u26c8\ufe0f Gewitter", 96:"\u26c8\ufe0f Gewitter", 99:"\u26c8\ufe0f Gewitter",
}

CITIES = [
    {"name":"Frankfurt","lat":50.11,"lon":8.68},
    {"name":"Hamburg",  "lat":53.55,"lon":10.00},
    {"name":"Berlin",   "lat":52.52,"lon":13.41},
    {"name":"M\u00fcnchen",  "lat":48.14,"lon":11.58},
]

MAX_ITEMS = 8
MAX_HOURS = 8
NEW_HOURS = 2

if os.path.isdir("docs"):
    OUTPUT_FILE = "docs/index.html"
else:
    _home = os.path.expanduser("~")
    _desktop = os.path.join(_home, "Desktop")
    if not os.path.isdir(_desktop):
        _desktop = _home
    OUTPUT_FILE = os.path.join(_desktop, "daily_briefing.html")

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

CATEGORY_RULES = [
    # ── Konflikte: ausschließlich ausländische Kriegs-/Militärthemen ──────────────
    ("Konflikte", [
        "ukraine","russland","israel","gaza","hamas","iran","syrien","jemen","libanon",
        "krieg","kriegs","soldat","soldaten","waffe","waffen",
        "rakete","raketen","bomben","luftangriff","gefecht","offensive",
        "waffenstillstand","besatzung","terroranschlag","streitkr\u00e4fte",
    ]),
    # ── Wirtschaft: ausschließlich Finanz-/Börsenthemen ──────────────────────────
    # (gilt auch als Pflicht-Filter für finanzen.net / ARD Börse)
    ("Wirtschaft", [
        "aktien","b\u00f6rse","boerse","dax","mdax","sdax","tecdax",
        "zinsen","leitzins","inflation","konjunktur","rezession",
        "anleihe","rendite","dividende","kurs","kursverlust","kursgewinn",
        "quartalsergebnis","jahresbilanz","gewinnwarnung","umsatzeinbruch",
        "bruttoinlandsprodukt","bundesbank","ezb","fed",
        "handelsbilanz","rohstoff","oel","gold","devisen",
        "ipo","fusion","\u00fcbernahme","investition",
    ]),
    # ── Politik: ausschließlich deutsche Innenpolitik ─────────────────────────────
    ("Politik", [
        "bundestag","bundesrat","bundesregierung","bundeskanzler",
        "koalition","koalitionsvertrag","bundeskabinett","landtag",
        "cdu","csu","spd","gr\u00fcne","afd","fdp","bsw",
        "merz","scholz","habeck","baerbock","klingbeil","weidel",
        "lindner","pistorius","s\u00f6der","faeser","lauterbach",
    ]),
    # ── Sonstiges: Fallback – kein Pflicht-Keyword ────────────────────────────────
]

CAT_EMOJI = {
    "Politik":    "\U0001f3db",
    "Wirtschaft": "\U0001f4b0",
    "Konflikte":  "\u2694\ufe0f",
    "Sonstiges":  "\U0001f30d",
}

CAT_ORDER = ["Politik", "Wirtschaft", "Konflikte", "Sonstiges"]
VISIBLE_PER_CAT = 5
MAX_PER_CAT = 8

CAT_MAIN = {"Politik", "Wirtschaft", "Konflikte", "Sonstiges"}

CAT_CSS_KEY = {
    "Politik":    "politik",
    "Wirtschaft": "wirtschaft",
    "Konflikte":  "konflikte",
    "Sonstiges":  "welt",
}

WOCHENTAGE = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
MONATE = ["Januar","Februar","M\u00e4rz","April","Mai","Juni",
          "Juli","August","September","Oktober","November","Dezember"]

# ── Kategorisierung ────────────────────────────────────────────────────────────

def categorize(title, desc):
    txt = (title + " " + desc).lower()
    for cat, keywords in CATEGORY_RULES:
        if any(k in txt for k in keywords):
            return cat
    return "Sonstiges"

# ── Wetter ─────────────────────────────────────────────────────────────────────

def fetch_weather(cities):
    results = []
    for c in cities:
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={c['lat']}&longitude={c['lon']}"
                f"&current=temperature_2m,weathercode,windspeed_10m"
                f"&wind_speed_unit=kmh&timezone=Europe%2FBerlin"
            )
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            d = r.json()["current"]
            code  = d.get("weathercode", 0)
            temp  = round(d.get("temperature_2m", 0))
            wind  = round(d.get("windspeed_10m", 0))
            label = WMO_CODES.get(code, "\U0001f321\ufe0f")
            results.append({"name":c["name"],"temp":temp,"wind":wind,"label":label,"ok":True})
        except Exception:
            results.append({"name":c["name"],"temp":None,"wind":None,"label":"\u2013","ok":False})
    return results

def build_weather_html(weather, tod_class=""):
    cards = ""
    for w in weather:
        if w["ok"]:
            cards += (
                f'<div class="wc"><div class="wc-city">{w["name"]}</div>'
                f'<div class="wc-main">{w["label"]}</div>'
                f'<div class="wc-temp">{w["temp"]}\u00b0C</div>'
                f'<div class="wc-wind">\U0001f4a8 {w["wind"]} km/h</div></div>'
            )
        else:
            cards += f'<div class="wc"><div class="wc-city">{w["name"]}</div><div class="wc-main">\u2013</div></div>'
    return f'<div class="weather-bar {tod_class}">{cards}</div>'

# ── RSS ─────────────────────────────────────────────────────────────────────────

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
            items.append({"title":title,"link":link,"desc":desc,"pubdate":pubdate,"pub_dt":pub_dt})
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

def sort_key_dt(item):
    dt = item.get("pub_dt")
    if dt is None:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

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

def is_new(pub_dt):
    if pub_dt is None:
        return False
    try:
        now = datetime.now(timezone.utc)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        return (now - pub_dt) <= timedelta(hours=NEW_HOURS)
    except:
        return False

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

def pub_ts(pub_dt):
    if not pub_dt:
        return "0"
    try:
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        return str(int(pub_dt.timestamp()))
    except:
        return "0"

# ── Dedup & Unified Feed ────────────────────────────────────────────────────────

def _title_tokens(title):
    t = re.sub(r'[^\w\s]', '', title.lower())
    stopwords = {'der','die','das','ein','eine','und','oder','mit','von','zu','im','in',
                 'an','auf','bei','für','ist','sind','hat','haben','wird','werden','nach',
                 'the','a','an','of','in','at','on','for','to','by','is','are','has','have',
                 'as','its','it','this','that','with','from','but','not','new','nach','über'}
    return {w for w in t.split() if len(w) > 3 and w not in stopwords}

def deduplicate(items):
    seen = []
    result = []
    for item in items:
        tokens = _title_tokens(item['title'])
        if not tokens:
            result.append(item)
            continue
        dup = False
        for s in seen:
            overlap = len(tokens & s) / max(1, min(len(tokens), len(s)))
            if overlap >= 0.55:
                dup = True
                break
        if not dup:
            seen.append(tokens)
            result.append(item)
    return result

def build_unified_feed(results):
    all_items = []
    for r in results:
        for item in r["items"]:
            it = dict(item)
            it["_source"]  = r["name"]
            it["_emoji"]   = r["emoji"]
            it["_country"] = r["country"]
            all_items.append(it)
    all_items.sort(key=sort_key_dt, reverse=True)
    return deduplicate(all_items)

def _article_row(it, overflow=False):
    cat         = it.get("category", "Welt")
    cat_display = cat if cat in CAT_MAIN else "Sonstiges"
    t      = html_module.escape(it["title"])
    lk     = html_module.escape(it["link"])
    d      = f'<div class="nd">{html_module.escape(it["desc"])}</div>' if it["desc"] else ""
    ts     = fmt_time(it["pub_dt"], it["pubdate"])
    age    = age_label(it["pub_dt"])
    nm     = f'<span class="nm">{ts} &middot; {age}</span>' if ts else ""
    nb     = '<span class="ni-new">NEU</span>' if is_new(it["pub_dt"]) else ""
    src     = it.get("_source", "")
    sbadge  = f'<span class="ni-src ni-src-de">{html_module.escape(src)}</span>'
    src_esc = html_module.escape(src)
    ovf_style = ' style="display:none"' if overflow else ""
    ovf_cls   = " ni-overflow" if overflow else ""
    return (
        f'<div class="ni reveal{ovf_cls}" data-src="{src_esc}" data-cat="{html_module.escape(cat_display)}" data-ts="{pub_ts(it["pub_dt"])}"{ovf_style}>'
        f'<a href="{lk}" target="_blank" rel="noopener">'
        f'<div class="ni-top"><div class="nt">{t}</div><div class="ni-top-right">{sbadge}<span class="ni-arr">&#8594;</span></div></div>'
        f'{d}<div class="ni-foot">{nm}{nb}</div></a></div>'
    )

def build_feed_html(unified_items):
    if not unified_items:
        return '<div class="cat-section"><div class="feed-list"><div class="empty">Keine aktuellen Artikel gefunden.</div></div></div>'
    groups = {cat: [] for cat in CAT_ORDER}
    for it in unified_items:
        cat = it.get("category", "Welt")
        groups[cat if cat in CAT_MAIN else "Sonstiges"].append(it)
    sections = ""
    for cat in CAT_ORDER:
        items = groups[cat]
        if not items:
            continue
        emoji = CAT_EMOJI.get(cat, "\U0001f30d")
        ckey  = CAT_CSS_KEY.get(cat, "welt")
        items = items[:MAX_PER_CAT]
        cnt   = len(items)
        rows  = "".join(
            _article_row(it, overflow=(i >= VISIBLE_PER_CAT))
            for i, it in enumerate(items)
        )
        hidden = cnt - VISIBLE_PER_CAT
        more_btn = (
            f'<button class="cat-sec-more" data-expanded="false" data-hidden="{hidden}">+{hidden} weitere</button>'
            if hidden > 0 else ""
        )
        sections += (
            f'<div class="cat-section" data-section="{html_module.escape(cat)}">'
            f'<div class="cat-sec-hdr cat-sec-{ckey}">'
            f'<span class="cat-sec-icon">{emoji}</span>'
            f'<span class="cat-sec-name">{html_module.escape(cat)}</span>'
            f'<span class="cat-sec-count">{cnt}</span>'
            f'{more_btn}'
            f'</div>'
            f'<div class="feed-list">{rows}</div>'
            f'</div>'
        )
    return sections

# ── CSS ─────────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#08090e;--sf:#12151f;--sf2:#181c2a;--bd:#1e2235;--bd2:#252a3d;
  --ac:#5b9cf6;--ac2:#8b72f8;--ac3:#f06292;
  --tx:#f0f2f8;--tx2:#b8bdd4;--mu:#6b7194;--new:#10b981;
  --cat-politik:#5b9cf6;--cat-wirtschaft:#10b981;--cat-konflikte:#f87171;
  --cat-energie:#fbbf24;--cat-europa:#8b72f8;--cat-usa:#f97316;--cat-welt:#6b7194;
}
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{font-family:"Inter",system-ui,sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;padding-bottom:80px;overflow-x:hidden;}

/* Scroll-Fortschrittsbalken */
#progress-bar{position:fixed;top:0;left:0;height:2px;width:0%;z-index:9999;
  background:linear-gradient(90deg,var(--ac),var(--ac2),var(--ac3));
  transition:width .1s linear;box-shadow:0 0 8px rgba(91,156,246,.6);}

/* Hintergrund */
.bg-anim{position:fixed;inset:0;z-index:-1;
  background:radial-gradient(ellipse at 15% 10%,rgba(91,156,246,.09) 0%,transparent 55%),
             radial-gradient(ellipse at 85% 80%,rgba(139,114,248,.07) 0%,transparent 55%),
             radial-gradient(ellipse at 50% 50%,rgba(240,98,146,.04) 0%,transparent 60%),#08090e;
  animation:bgshift 12s ease-in-out infinite alternate;}
@keyframes bgshift{0%{background-position:0% 0%;}50%{background-position:100% 50%;}100%{background-position:0% 100%;}}

/* Header */
.hdr{background:rgba(13,15,24,.88);border-bottom:1px solid var(--bd);padding:18px 28px 14px;
  z-index:100;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);}
.hdr-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
.hdr-left h1{font-size:1.45rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,var(--ac),var(--ac2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hdr-greeting{font-size:.88rem;font-weight:500;color:var(--tx2);margin-top:2px;}
.hdr-meta{font-size:.72rem;color:var(--mu);margin-top:2px;}
.hdr-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.pill-ac{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:20px;
  font-size:.7rem;font-weight:600;background:rgba(91,156,246,.12);border:1px solid rgba(91,156,246,.3);color:var(--ac);}
.live{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:20px;
  font-size:.65rem;font-weight:700;letter-spacing:.5px;
  background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);color:var(--new);}
.live::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--new);animation:pulse 1.5s infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.3;transform:scale(.7);}}
.btn-r{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;border-radius:20px;
  font-size:.73rem;font-weight:600;
  background:linear-gradient(135deg,rgba(91,156,246,.15),rgba(139,114,248,.15));
  border:1px solid rgba(91,156,246,.32);color:var(--ac);cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-r:hover{background:linear-gradient(135deg,rgba(91,156,246,.28),rgba(139,114,248,.28));transform:translateY(-1px);}
@media(max-width:720px){.hdr-right{display:none;}}

/* Tab-Navigation */
.tab-nav{background:rgba(13,15,24,.88);border-bottom:1px solid var(--bd);
  z-index:95;
  backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  padding:0 28px;display:flex;gap:2px;align-items:center;}
@media(max-width:720px){.tab-nav{padding:0 12px;}}
.tab-right{margin-left:auto;display:flex;align-items:center;gap:2px;}
.view-btn{background:none;border:none;color:var(--mu);cursor:pointer;
  padding:8px 10px;font-size:1.1rem;line-height:1;border-radius:8px;
  transition:color .18s,background .18s;}
.view-btn:hover{color:var(--tx);background:rgba(255,255,255,.06);}
.view-btn.active{color:var(--ac);}
.tab-btn{padding:10px 18px;font-size:.82rem;font-weight:600;color:var(--mu);
  background:none;border:none;border-bottom:2px solid transparent;
  cursor:pointer;transition:all .2s;white-space:nowrap;}
.tab-btn:hover{color:var(--tx);}
.tab-btn.tab-active{color:var(--ac);border-bottom-color:var(--ac);}
.tab-hidden{display:none!important;}

/* Filter-Bar */
.filter-bar{background:rgba(13,15,24,.75);border-bottom:1px solid var(--bd);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:10px 28px;z-index:90;}
@media(max-width:720px){.filter-bar{padding:10px 16px;}}
.filter-inner{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:8px;}
.filter-row{display:flex;align-items:center;gap:8px;flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:4px;scrollbar-width:none;}
.filter-row::-webkit-scrollbar{height:3px;}
.filter-row::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:3px;}
.filter-label{font-size:.6rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--mu);min-width:52px;}
@media(max-width:720px){.filter-label{display:none;}}
.flt-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;
  font-size:.68rem;font-weight:600;background:var(--sf);border:1px solid var(--bd);
  color:var(--tx2);cursor:pointer;transition:all .18s;white-space:nowrap;}
.flt-btn:hover{border-color:var(--bd2);color:var(--tx);}
.flt-btn.active{background:rgba(91,156,246,.15);border-color:rgba(91,156,246,.4);color:var(--ac);}
.flt-count{font-size:.55rem;background:var(--bd2);color:var(--mu);padding:1px 5px;border-radius:20px;transition:all .18s;}
.flt-btn.active .flt-count{background:rgba(91,156,246,.25);color:var(--ac);}
.filter-footer{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;min-height:22px;}
#filter-result{font-size:.7rem;color:var(--mu);}
#filter-result span{color:var(--ac);font-weight:700;}
#clear-btn{display:none;font-size:.68rem;font-weight:600;color:var(--ac3);
  background:rgba(240,98,146,.08);border:1px solid rgba(240,98,146,.25);
  padding:3px 10px;border-radius:20px;cursor:pointer;transition:all .18s;}
#clear-btn:hover{background:rgba(240,98,146,.18);}
#clear-btn.visible{display:inline-flex;}

/* Wetter */
.weather-bar{max-width:1200px;margin:18px auto 0;padding:0 16px;
  display:grid;grid-template-columns:repeat(4,1fr);gap:12px;
  border-radius:16px;transition:background .4s;}
@media(max-width:720px){.weather-bar{grid-template-columns:repeat(2,1fr);}}
.tod-morning .wc{border-color:rgba(251,191,36,.3);}
.tod-morning .wc:hover{border-color:rgba(251,191,36,.55);}
.tod-evening .wc{border-color:rgba(249,115,22,.3);}
.tod-evening .wc:hover{border-color:rgba(249,115,22,.55);}
.tod-night .wc{border-color:rgba(139,114,248,.3);}
.tod-night .wc:hover{border-color:rgba(139,114,248,.5);}
.wc{background:var(--sf);border:1px solid var(--bd);border-radius:14px;padding:13px 16px;
  display:flex;flex-direction:column;gap:2px;transition:border-color .2s;}
.wc:hover{border-color:var(--bd2);}
.wc-city{font-size:.68rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--mu);}
.wc-main{font-size:.82rem;color:var(--tx2);margin-top:4px;}
.wc-temp{font-size:1.5rem;font-weight:800;color:var(--tx);line-height:1.1;}
.wc-wind{font-size:.68rem;color:var(--mu);margin-top:3px;}

/* Layout */
.wrap{max-width:1200px;margin:0 auto;padding:24px 16px;}
.slabel{font-size:.68rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--mu);margin-bottom:12px;padding-left:2px;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:26px;}
@media(max-width:720px){.grid{grid-template-columns:1fr;}}

/* Karten */
.card{background:var(--sf);border:1px solid var(--bd);border-radius:16px;overflow:hidden;
  display:flex;flex-direction:column;
  opacity:0;transform:translateY(22px);animation:cardin .55s ease forwards;
  transition:border-color .2s,box-shadow .2s;}
.card:hover{border-color:var(--bd2);box-shadow:0 10px 36px rgba(0,0,0,.45);}
.card:nth-child(1){animation-delay:.05s;}.card:nth-child(2){animation-delay:.15s;}
.card:nth-child(3){animation-delay:.25s;}.card:nth-child(4){animation-delay:.35s;}
@keyframes cardin{to{opacity:1;transform:translateY(0);}}
.card.empty-card{opacity:.35;pointer-events:none;}
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
.card-empty-msg{padding:22px;color:var(--mu);font-size:.82rem;text-align:center;display:none;}
.card.empty-card .card-empty-msg{display:block;}

/* Artikel */
.nlist{flex:1;}
.ni{padding:12px 16px;border-bottom:1px solid var(--bd);
  transition:background .15s,opacity .22s,max-height .28s,padding .22s;overflow:hidden;max-height:300px;}
.ni:last-child{border-bottom:none;}
.ni:hover{background:var(--sf2);}
.ni:hover .ni-arr{opacity:1;transform:translateX(0);}
.ni a{text-decoration:none;color:inherit;display:block;}
.ni-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;}
.ni-top-right{display:flex;align-items:center;gap:5px;flex-shrink:0;margin-top:1px;}
.nt{font-size:.855rem;font-weight:600;color:var(--tx);line-height:1.45;margin-bottom:5px;flex:1;transition:color .15s;}
.ni:hover .nt{color:var(--ac);}
.ni-arr{color:var(--ac);font-size:.72rem;opacity:0;transform:translateX(-5px);transition:all .18s;flex-shrink:0;margin-top:2px;}
.nd{font-size:.73rem;color:var(--tx2);line-height:1.5;margin-bottom:6px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.ni-foot{display:flex;align-items:center;gap:7px;flex-wrap:wrap;}
.nm{font-size:.67rem;color:var(--mu);}
.ni-new{font-size:.58rem;font-weight:700;letter-spacing:.5px;
  background:rgba(16,185,129,.1);color:var(--new);border:1px solid rgba(16,185,129,.25);
  padding:1px 6px;border-radius:20px;animation:newpulse 2s ease-in-out infinite;}
@keyframes newpulse{0%,100%{opacity:1;}50%{opacity:.5;}}
.ni-cat{font-size:.55rem;font-weight:700;letter-spacing:.4px;padding:1px 6px;border-radius:20px;text-transform:uppercase;}
.ni-cat-politik   {background:rgba(91,156,246,.1);color:var(--cat-politik);border:1px solid rgba(91,156,246,.25);}
.ni-cat-wirtschaft{background:rgba(16,185,129,.1);color:var(--cat-wirtschaft);border:1px solid rgba(16,185,129,.25);}
.ni-cat-konflikte {background:rgba(248,113,113,.1);color:var(--cat-konflikte);border:1px solid rgba(248,113,113,.25);}
.ni-cat-energie   {background:rgba(251,191,36,.1);color:var(--cat-energie);border:1px solid rgba(251,191,36,.25);}
.ni-cat-europa    {background:rgba(139,114,248,.1);color:var(--cat-europa);border:1px solid rgba(139,114,248,.25);}
.ni-cat-usa       {background:rgba(249,115,22,.1);color:var(--cat-usa);border:1px solid rgba(249,115,22,.25);}
.ni-cat-welt      {background:rgba(107,113,148,.1);color:var(--cat-welt);border:1px solid rgba(107,113,148,.25);}
.ni{position:relative;}
.ni::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:transparent;transition:background .18s;}
.ni[data-cat="Politik"]:hover::before{background:var(--cat-politik);}
.ni[data-cat="Wirtschaft"]:hover::before{background:var(--cat-wirtschaft);}
.ni[data-cat="Konflikte"]:hover::before{background:var(--cat-konflikte);}
.ni[data-cat="Welt"]:hover::before,.ni[data-cat="Sonstiges"]:hover::before{background:var(--cat-welt);}
.ni.ni-hidden{max-height:0;padding-top:0;padding-bottom:0;opacity:0;border-bottom:none;pointer-events:none;}
.ni-src{font-size:.55rem;font-weight:700;padding:1px 6px;border-radius:20px;
  background:var(--bd2);color:var(--mu);border:1px solid var(--bd);white-space:nowrap;}
.ni-src-de{border-color:rgba(230,57,70,.25);color:#ff8fa3;background:rgba(230,57,70,.08);}
.ni-src-en{border-color:rgba(86,180,233,.25);color:#7dd3fc;background:rgba(86,180,233,.08);}
.empty{padding:22px;color:var(--mu);font-size:.82rem;text-align:center;}
.err{padding:14px 16px;color:#f87171;font-size:.76rem;line-height:1.6;word-break:break-word;}
#no-results{display:none;text-align:center;padding:60px 20px;color:var(--mu);}
#no-results.visible{display:block;}
#no-results .nr-icon{font-size:2.5rem;margin-bottom:12px;}
#no-results .nr-text{font-size:.9rem;}
.stand-bar{max-width:1200px;margin:14px auto 0;padding:0 16px;}
.stand-inner{background:rgba(16,185,129,.05);border:1px solid rgba(16,185,129,.18);
  border-radius:10px;padding:8px 14px;display:flex;align-items:center;gap:8px;font-size:.7rem;color:var(--mu);}
.stand-dot{width:6px;height:6px;border-radius:50%;background:var(--new);animation:pulse 1.5s infinite;flex-shrink:0;}
.stand-inner strong{color:var(--tx2);}
.feed-list{background:var(--sf);border:1px solid var(--bd);overflow:hidden;}
.cat-section{margin-bottom:20px;}
.cat-sec-hdr{display:flex;align-items:center;gap:8px;padding:10px 16px;
  background:var(--sf2);border:1px solid var(--bd);border-bottom:none;
  border-radius:14px 14px 0 0;}
.cat-section .feed-list{border-radius:0 0 14px 14px;border-top:none;}
.cat-sec-icon{font-size:1rem;line-height:1;}
.cat-sec-name{font-size:.82rem;font-weight:700;color:var(--tx);}
.cat-sec-count{font-size:.6rem;font-weight:700;background:var(--bd2);color:var(--mu);padding:2px 7px;border-radius:20px;}
.cat-sec-more{margin-left:auto;font-size:.68rem;font-weight:600;color:var(--ac);
  background:rgba(91,156,246,.08);border:1px solid rgba(91,156,246,.22);
  padding:3px 11px;border-radius:20px;cursor:pointer;transition:all .18s;}
.cat-sec-more:hover{background:rgba(91,156,246,.2);}
.cat-sec-konflikte{border-left:3px solid var(--cat-konflikte);}
.cat-sec-konflikte  .cat-sec-name{color:var(--cat-konflikte);}
.cat-sec-politik{border-left:3px solid var(--cat-politik);}
.cat-sec-politik    .cat-sec-name{color:var(--cat-politik);}
.cat-sec-wirtschaft{border-left:3px solid var(--cat-wirtschaft);}
.cat-sec-wirtschaft .cat-sec-name{color:var(--cat-wirtschaft);}
.cat-sec-welt,.cat-sec-sonstiges{border-left:3px solid var(--cat-welt);}
.cat-sec-welt .cat-sec-name,.cat-sec-sonstiges .cat-sec-name{color:var(--cat-welt);}

/* Spiel-Tab */
.game-wrap{display:flex;flex-direction:column;align-items:center;padding:20px 16px;gap:12px;}
#game-ui{position:relative;display:inline-block;}
#game-canvas{border-radius:16px;border:1px solid var(--bd);display:block;
  box-shadow:0 0 30px rgba(91,156,246,.08);}
.game-overlay{position:absolute;inset:0;border-radius:16px;background:rgba(8,9,14,.88);
  display:flex;align-items:center;justify-content:center;text-align:center;padding:20px;}
.go-inner{display:flex;flex-direction:column;align-items:center;gap:10px;}
.go-title{font-size:1.8rem;font-weight:800;
  background:linear-gradient(135deg,var(--ac),var(--ac2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.go-gameover{font-size:1.5rem;font-weight:800;color:#f87171;}
.go-sub{font-size:.75rem;color:var(--tx2);line-height:1.6;max-width:240px;}
.go-keys{font-size:.68rem;color:var(--mu);}
.go-keys kbd{display:inline-block;background:var(--sf2);border:1px solid var(--bd2);
  border-radius:4px;padding:1px 5px;font-size:.62rem;color:var(--tx2);}
.go-score-val{font-size:1.7rem;font-weight:800;color:var(--tx);}
.go-record{font-size:.8rem;color:var(--ac2);}
.go-newrecord{font-size:.82rem;font-weight:700;color:#fbbf24;}
.go-ask{font-size:.82rem;color:var(--tx2);}
.go-btns{display:flex;gap:8px;}
.go-btn{padding:8px 24px;border-radius:20px;font-size:.8rem;font-weight:700;cursor:pointer;border:none;
  background:linear-gradient(135deg,var(--ac),var(--ac2));color:#fff;transition:opacity .15s;}
.go-btn:hover{opacity:.82;}
.go-btn-sec{background:none!important;border:1px solid var(--bd2)!important;color:var(--tx2)!important;}

/* Kompaktmodus */
body.compact .nd{display:none;}
body.compact .ni{padding:8px 16px;}
body.compact .ni-foot{margin-top:2px;}

/* Light Mode */
body.light{
  --bg:#f0f2f8;--sf:#ffffff;--sf2:#e6e9f4;--bd:#d0d4e8;--bd2:#b8bdd4;
  --ac:#2d6fd4;--ac2:#5b3ec8;--ac3:#d04070;
  --tx:#0d0f1c;--tx2:#2a3060;--mu:#6070a0;--new:#047857;
  --cat-politik:#2d6fd4;--cat-wirtschaft:#047857;--cat-konflikte:#c0392b;
  --cat-energie:#c07800;--cat-europa:#5b3ec8;--cat-usa:#c05000;--cat-welt:#506080;
}
body.light .bg-anim{
  background:radial-gradient(ellipse at 15% 10%,rgba(45,111,212,.07) 0%,transparent 55%),
             radial-gradient(ellipse at 85% 80%,rgba(91,62,200,.05) 0%,transparent 55%),#f0f2f8;}
body.light .hdr,body.light .tab-nav,body.light .filter-bar{
  background:rgba(240,242,248,.92);border-color:var(--bd);}
body.light #progress-bar{background:linear-gradient(90deg,var(--ac),var(--ac2),var(--ac3));}
body.light .view-btn:hover{background:rgba(0,0,0,.06);}

/* Scroll-reveal & Footer */
.reveal{opacity:0;transform:translateY(18px);transition:opacity .5s ease,transform .5s ease;}
.reveal.visible{opacity:1;transform:translateY(0);}
.foot{text-align:center;color:var(--mu);font-size:.7rem;margin-top:36px;padding:18px;border-top:1px solid var(--bd);}
"""

# ── JavaScript ──────────────────────────────────────────────────────────────────

JS = """
<script>
// ── Fortschrittsbalken ─────────────────────────────────────────────────────────
const pb = document.getElementById('progress-bar');
window.addEventListener('scroll', () => {
  const d = document.documentElement;
  pb.style.width = (d.scrollTop / (d.scrollHeight - d.clientHeight) * 100) + '%';
}, {passive:true});

// ── Service Worker ─────────────────────────────────────────────────────────────
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');

// ── Scroll-Reveal ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); }});
  }, {threshold:.08});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
});

// ── Tabs ────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.forEach(b => b.classList.remove('tab-active'));
      btn.classList.add('tab-active');
      const target = btn.dataset.tab;
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('tab-hidden'));
      document.getElementById('tab-' + target).classList.remove('tab-hidden');
      // Filter-bar nur im News-Tab anzeigen
      const fb = document.getElementById('filter-bar');
      if (fb) fb.style.display = target === 'news' ? '' : 'none';
      if (target === 'game' && window.initGame) window.initGame();
    });
  });
});

// ── Filter ──────────────────────────────────────────────────────────────────────
let activeSrc = 'all';

function applyFilters() {
  const items = document.querySelectorAll('.ni[data-src]');
  let visible = 0;
  items.forEach(ni => {
    const overflowHidden = ni.classList.contains('ni-overflow') && ni.style.display === 'none';
    const ok = (activeSrc === 'all' || ni.dataset.src === activeSrc) && !overflowHidden;
    ni.classList.toggle('ni-hidden', !ok);
    if (ok) visible++;
  });
  document.querySelectorAll('.cat-section').forEach(sec => {
    const has = sec.querySelectorAll('.ni:not(.ni-hidden)').length > 0;
    sec.style.display = has ? '' : 'none';
  });
  const noRes = document.getElementById('no-results');
  if (noRes) noRes.classList.toggle('visible', visible === 0);
  const res = document.getElementById('filter-result');
  if (res) {
    if (activeSrc === 'all')
      res.innerHTML = '<span>' + items.length + '</span> Artikel geladen';
    else
      res.innerHTML = '<span>' + visible + '</span> von ' + items.length + ' Artikeln sichtbar';
  }
  const clr = document.getElementById('clear-btn');
  if (clr) clr.classList.toggle('visible', activeSrc !== 'all');
}

function updateCounts() {
  const items = document.querySelectorAll('.ni[data-src]');
  const sc = {}, cc = {};
  items.forEach(ni => {
    sc[ni.dataset.src] = (sc[ni.dataset.src] || 0) + 1;
    cc[ni.dataset.cat] = (cc[ni.dataset.cat] || 0) + 1;
  });
  document.querySelectorAll('.flt-btn[data-filter="source"]').forEach(b => {
    const cnt = b.querySelector('.flt-count');
    if (cnt) cnt.textContent = b.dataset.val === 'all' ? items.length : (sc[b.dataset.val] || 0);
  });
  document.querySelectorAll('.flt-btn[data-filter="cat"]').forEach(b => {
    const cnt = b.querySelector('.flt-count');
    if (cnt) cnt.textContent = b.dataset.val === 'all' ? items.length : (cc[b.dataset.val] || 0);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  updateCounts();
  applyFilters();
  document.querySelectorAll('.flt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      activeSrc = btn.dataset.val;
      document.querySelectorAll('.flt-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
    });
  });
  const clr = document.getElementById('clear-btn');
  if (clr) clr.addEventListener('click', () => {
    activeSrc = 'all';
    document.querySelectorAll('.flt-btn').forEach(b => b.classList.toggle('active', b.dataset.val === 'all'));
    applyFilters();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && clr) clr.click(); });
});

// ── Theme & Kompakt Toggles ─────────────────────────────────────────────────────
(function() {
  const body = document.body;
  const themeBtn   = document.getElementById('theme-btn');
  const compactBtn = document.getElementById('compact-btn');

  function applyTheme(light) {
    body.classList.toggle('light', light);
    if (themeBtn) { themeBtn.classList.toggle('active', light); themeBtn.title = light ? 'Dunkelmodus' : 'Hellmodus'; }
    localStorage.setItem('db_light', light ? '1' : '0');
  }
  function applyCompact(on) {
    body.classList.toggle('compact', on);
    if (compactBtn) compactBtn.classList.toggle('active', on);
    localStorage.setItem('db_compact', on ? '1' : '0');
  }

  // Gespeicherte Präferenzen laden
  applyTheme(localStorage.getItem('db_light') === '1');
  applyCompact(localStorage.getItem('db_compact') === '1');

  if (themeBtn)   themeBtn.addEventListener('click',   () => applyTheme(!body.classList.contains('light')));
  if (compactBtn) compactBtn.addEventListener('click', () => applyCompact(!body.classList.contains('compact')));
})();

// ── Kategorie-Sektionen expand/collapse ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.cat-sec-more').forEach(btn => {
    btn.addEventListener('click', () => {
      const sec = btn.closest('.cat-section');
      const expanded = btn.dataset.expanded === 'true';
      const hidden = parseInt(btn.dataset.hidden || '0');
      sec.querySelectorAll('.ni-overflow').forEach(ni => {
        ni.style.display = expanded ? 'none' : '';
        ni.classList.toggle('ni-hidden', expanded);
      });
      btn.dataset.expanded = expanded ? 'false' : 'true';
      btn.textContent = expanded ? '+' + hidden + ' weitere' : '↑ Weniger';
      // Recount filter results
      applyFilters();
    });
  });
});

// ── STELLAR JUMP ───────────────────────────────────────────────────────────────
(function() {
  const canvas = document.getElementById('game-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H;

  const GRAV = 0.4, JUMP = -11.5, SPEED = 4.0;
  const PLW = 24, PLH = 24;
  const PTW = 64, PTH = 10;
  const MIN_PLAT_GAP = 10;

  // Zone ab je 200 Punkte. Jede Zone hat eigene Atmosphäre + Partikel-Effekt.
  const ZONES = [
    { bg:'#08090e', tint:null,                    starC:'#f0f2f8' },  // 0: Tiefer Weltraum
    { bg:'#070e0d', tint:'rgba(6,78,59,.09)',      starC:'#6ee7b7' },  // 1: Aurora Borealis
    { bg:'#07080f', tint:'rgba(14,116,144,.09)',   starC:'#7dd3fc' },  // 2: Biolumineszenz
    { bg:'#0f0c06', tint:'rgba(120,53,15,.09)',    starC:'#fcd34d' },  // 3: Sonnenkorona
    { bg:'#09060f', tint:'rgba(88,28,135,.10)',    starC:'#e879f9' },  // 4: Hyperraum
  ];

  let state = 'idle', score = 0, hi = +localStorage.getItem('jump_hi') || 0;
  let camY = 0, totalH = 0;
  let platforms = [], particles = [], stars = [], ambients = [];
  let player = {x:0, y:0, vx:0, vy:0};
  let keys = {}, touchX = null, touchDX = 0;
  // Sanfter Zonenübergang: fromZone → toZone über ~2s
  let fromZone = 0, toZone = 0, zoneBlend = 1;

  function resize() {
    const wrap = canvas.parentElement;
    W = canvas.width  = Math.min(320, wrap.clientWidth - 24);
    H = canvas.height = Math.min(460, window.innerHeight - 200);
    if (stars.length) initStars();
  }

  function initStars() {
    stars = Array.from({length:40}, () => ({
      x: Math.random() * W, y: Math.random() * H * 4,
      r: Math.random() * 1.2 + 0.3, a: Math.random() * 0.5 + 0.15,
    }));
  }

  function mkPlat(y, existing) {
    const moving = Math.random() < 0.15;
    const bounce = !moving && Math.random() < 0.12;
    let x, tries = 0;
    do {
      x = Math.random() * (W - PTW - 16) + 8;
      tries++;
    } while (tries < 20 && existing && existing.some(p =>
      Math.abs(p.y - y) < PTH + MIN_PLAT_GAP &&
      x + PTW + MIN_PLAT_GAP > p.x && x - MIN_PLAT_GAP < p.x + PTW
    ));
    return { x, y, vx: moving ? (Math.random()>.5 ? 1.6 : -1.6) : 0,
             type: moving ? 'move' : bounce ? 'bounce' : 'normal' };
  }

  function reset() {
    score = 0; camY = 0; totalH = 0; platforms = []; particles = []; ambients = [];
    fromZone = 0; toZone = 0; zoneBlend = 1;
    player = { x: W/2 - PLW/2, y: H - 100, vx: 0, vy: 0 };
    platforms.push({ x: W/2 - PTW/2, y: H - 65, vx: 0, type: 'normal' });
    for (let i = 1; i < 16; i++) platforms.push(mkPlat(H - 65 - i * 75, platforms));
    player.vy = JUMP;
    initStars();
  }

  function spawnPart(x, y, col) {
    for (let i = 0; i < 6; i++)
      particles.push({ x, y, vx:(Math.random()-.5)*4, vy:(Math.random()-.5)*4-2,
        life:1, decay:.05+Math.random()*.02, col, r:1.5+Math.random()*1.5 });
  }

  // Ambient-Partikel erzeugen – alle y-Koordinaten korrekt camY-relativ
  function mkAmbient(z) {
    const ax = Math.random() * W;
    // Weltkoordinate = aktueller Kamera-Oberpunkt + zufällige Bildschirmposition
    const ay = camY + Math.random() * H;
    if (z === 1) {
      // Aurora: senkrechte Vorhänge, sinken langsam (≈ Kamerageschw. → bleiben im Bild)
      return { x:ax, y:ay,
               vx:(Math.random()-.5)*.25, vy:.2+Math.random()*.15,
               h:35+Math.random()*55, w:1.4+Math.random(),
               phase:Math.random()*Math.PI*2, spd:.015+Math.random()*.015,
               a:.07+Math.random()*.08,
               col:['#6ee7b7','#2dd4bf','#34d399'][Math.floor(Math.random()*3)], t:'curtain' };
    } else if (z === 2) {
      // Biolumineszenz: Orbs spawnen im unteren Bildbereich, treiben sanft auf
      return { x:ax, y:camY + H*.7 + Math.random()*H*.35,
               vx:(Math.random()-.5)*.18, vy:-.12-.08*Math.random(),
               r:2+Math.random()*2.5, pulse:Math.random()*Math.PI*2, ps:.025+Math.random()*.02,
               a:.12+Math.random()*.10,
               col:['#7dd3fc','#67e8f9','#a5f3fc'][Math.floor(Math.random()*3)], t:'orb' };
    } else if (z === 3) {
      // Sonnenkorona: Strahlen von rechts oben – y korrekt camY-relativ
      const ang = Math.PI*(.52+Math.random()*.42);
      const spd = 1.6+Math.random()*1.4;
      return { x:W+8, y:camY + Math.random()*H*.65,
               vx:-Math.cos(ang)*spd, vy:Math.sin(ang)*spd,
               len:10+Math.random()*16, r:.75,
               a:.16+Math.random()*.12,
               col:['#fbbf24','#fb923c','#fde68a'][Math.floor(Math.random()*3)], t:'streak' };
    } else {
      // Hyperraum: radialer Warp vom Bildschirmzentrum – y korrekt camY-relativ
      const ang = Math.random()*Math.PI*2;
      const d = 12+Math.random()*32;
      const spd = 2.4+Math.random()*2.2;
      return { x:W/2+Math.cos(ang)*d, y:camY+H/2+Math.sin(ang)*d,
               vx:Math.cos(ang)*spd, vy:Math.sin(ang)*spd,
               len:8+Math.random()*16, r:.7,
               a:.18+Math.random()*.13,
               col:['#f0f2f8','#a5f3fc','#e879f9'][Math.floor(Math.random()*3)], t:'streak' };
    }
  }

  function tickAmbients(z) {
    if (z === 0) { ambients = []; return; }
    // Hyperraum braucht mehr Partikel für dichten Warp-Effekt
    const tgt = z === 1 ? 10 : z === 2 ? 10 : z === 3 ? 12 : 16;
    if (ambients.length < tgt) ambients.push(mkAmbient(z));
    ambients.forEach(a => {
      a.x += a.vx; a.y += a.vy;
      if (a.t === 'curtain') a.phase += a.spd;
      if (a.t === 'orb')     a.pulse += a.ps;
    });
    // Nur sichtbare behalten (Bildschirmkoordinaten prüfen)
    ambients = ambients.filter(a => {
      const sy = a.y - camY;
      return sy > -80 && sy < H + 80 && a.x > -30 && a.x < W + 30;
    });
  }

  function drawAmbients(blend) {
    if (!ambients.length) return;
    ambients.forEach(a => {
      const sy = a.y - camY;
      const alpha = a.a * blend;
      if (a.t === 'curtain') {
        ctx.globalAlpha = alpha;
        ctx.strokeStyle = a.col; ctx.lineWidth = a.w;
        ctx.beginPath();
        const sx = a.x + Math.sin(a.phase) * 6;
        ctx.moveTo(sx, sy);
        ctx.lineTo(sx + Math.sin(a.phase + 1.3) * 5, sy + a.h);
        ctx.stroke();
        ctx.lineWidth = 1;
      } else if (a.t === 'orb') {
        const pr = a.r * (1 + .3 * Math.sin(a.pulse));
        ctx.shadowColor = a.col; ctx.shadowBlur = pr * 6;
        ctx.globalAlpha = alpha * .55;
        ctx.fillStyle = a.col;
        ctx.beginPath(); ctx.arc(a.x, sy, pr, 0, Math.PI*2); ctx.fill();
        ctx.shadowBlur = 0;
        ctx.globalAlpha = alpha * .4;
        ctx.fillStyle = '#fff';
        ctx.beginPath(); ctx.arc(a.x, sy, pr * .32, 0, Math.PI*2); ctx.fill();
      } else {
        ctx.globalAlpha = alpha;
        ctx.strokeStyle = a.col; ctx.lineWidth = a.r * 2;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(a.x, sy);
        ctx.lineTo(a.x - a.vx * a.len, sy - a.vy * a.len);
        ctx.stroke();
        ctx.lineWidth = 1; ctx.lineCap = 'butt';
      }
    });
    ctx.globalAlpha = 1;
  }

  function showOverlay(which) {
    const ov = document.getElementById('game-overlay');
    if (!ov) return;
    ov.style.display = 'flex';
    const idle = document.getElementById('go-idle');
    const dead = document.getElementById('go-dead');
    if (idle) idle.style.display = which === 'idle' ? '' : 'none';
    if (dead) dead.style.display = which === 'dead' ? '' : 'none';
    if (which === 'dead') {
      const sc  = document.getElementById('go-score');
      const rec = document.getElementById('go-record');
      const nr  = document.getElementById('go-newrecord');
      if (sc)  sc.textContent  = score + 'm';
      if (rec) rec.textContent = 'Rekord: ' + hi + 'm';
      if (nr)  nr.style.display = (score > 0 && score >= hi) ? '' : 'none';
    }
  }

  function hideOverlay() {
    const ov = document.getElementById('game-overlay');
    if (ov) ov.style.display = 'none';
  }

  function startGame() { state = 'playing'; reset(); hideOverlay(); }

  function goToNews() {
    const nb = document.querySelector('.tab-btn[data-tab="news"]');
    if (nb) nb.click();
  }

  function update() {
    if (state !== 'playing') return;
    let mvx = 0;
    if (keys['ArrowLeft']  || keys['a'] || keys['A']) mvx = -SPEED;
    if (keys['ArrowRight'] || keys['d'] || keys['D']) mvx =  SPEED;
    if (touchX !== null) mvx = touchDX * 0.14;
    player.vx = player.vx * 0.72 + mvx * 0.28;
    const prevY = player.y;
    player.vy += GRAV;
    player.x  += player.vx;
    player.y  += player.vy;
    if (player.x + PLW < 0) player.x = W;
    if (player.x > W)       player.x = -PLW;
    const sy = player.y - camY;
    if (sy < H * 0.38) { const d = H * 0.38 - sy; camY -= d; totalH += d; score = Math.round(totalH / 7); }
    if (player.vy > 0) {
      const prevBottom = prevY + PLH;
      const currBottom = player.y + PLH;
      const pleft  = player.x + PLW * 0.15;
      const pright = pleft + PLW * 0.7;
      for (const p of platforms) {
        if (pright > p.x && pleft < p.x + PTW &&
            prevBottom <= p.y + 2 && currBottom >= p.y) {
          player.y = p.y - PLH;
          player.vy = p.type === 'bounce' ? JUMP * 1.35 : JUMP;
          spawnPart(player.x + PLW/2, p.y,
            p.type === 'move' ? '#8b72f8' : p.type === 'bounce' ? '#10b981' : '#5b9cf6');
          break;
        }
      }
    }
    platforms.forEach(p => { if (p.type === 'move') { p.x += p.vx; if (p.x < 0 || p.x + PTW > W) p.vx *= -1; }});
    platforms = platforms.filter(p => p.y - camY < H + 60);
    const top = Math.min(...platforms.map(p => p.y));
    while (platforms.length < 18) platforms.push(mkPlat(top - 68 - Math.random() * 28, platforms));
    particles.forEach(p => { p.x += p.vx; p.y += p.vy; p.vy += .1; p.life -= p.decay; });
    particles = particles.filter(p => p.life > 0);
    // Zonen-Übergang: sanft über ~2s (120 frames)
    const newZ = Math.min(4, Math.floor(score / 200));
    if (newZ !== toZone) { fromZone = toZone; toZone = newZ; zoneBlend = 0; ambients = []; }
    if (zoneBlend < 1) zoneBlend = Math.min(1, zoneBlend + 0.008);
    tickAmbients(toZone);
    if (player.y - camY > H + 80) {
      state = 'dead';
      if (score > hi) { hi = score; localStorage.setItem('jump_hi', hi); }
      showOverlay('dead');
    }
  }

  function rr(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x+r,y); ctx.lineTo(x+w-r,y); ctx.quadraticCurveTo(x+w,y,x+w,y+r);
    ctx.lineTo(x+w,y+h-r); ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    ctx.lineTo(x+r,y+h); ctx.quadraticCurveTo(x,y+h,x,y+h-r);
    ctx.lineTo(x,y+r); ctx.quadraticCurveTo(x,y,x+r,y); ctx.closePath();
  }

  function draw() {
    const zA = ZONES[fromZone], zB = ZONES[toZone], b = zoneBlend;
    // ── Hintergrund: alte Zone → neue Zone überblenden
    ctx.fillStyle = zA.bg; ctx.fillRect(0, 0, W, H);
    if (b < 1) {
      ctx.globalAlpha = b; ctx.fillStyle = zB.bg; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1;
    }
    // Tints einblenden
    if (zA.tint && b < 1) {
      ctx.fillStyle = zA.tint; ctx.globalAlpha = 1 - b; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1;
    }
    if (zB.tint) {
      ctx.fillStyle = zB.tint; ctx.globalAlpha = b; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1;
    }
    // ── Sterne: Farbe zwischen Zonen überblenden
    const off = (camY * .12) % (H * 4 + 200);
    stars.forEach(s => {
      const sy = ((s.y + off) % (H * 4 + 200)) - 100;
      if (sy < -4 || sy > H + 4) return;
      const al = s.a * (.6 + .4 * Math.sin(Date.now()/1400 + s.x));
      if (b < 1 && zA.starC !== zB.starC) {
        ctx.globalAlpha = al * (1 - b); ctx.fillStyle = zA.starC;
        ctx.beginPath(); ctx.arc(s.x, sy, s.r, 0, Math.PI*2); ctx.fill();
      }
      ctx.globalAlpha = al * b; ctx.fillStyle = zB.starC;
      ctx.beginPath(); ctx.arc(s.x, sy, s.r, 0, Math.PI*2); ctx.fill();
    });
    ctx.globalAlpha = 1;
    // ── Ambients einblenden (erscheinen sanft mit zoneBlend)
    drawAmbients(b);
    // ── Plattformen
    const cols = { normal:['#5b9cf6','#3a7bd5'], move:['#8b72f8','#6a50d8'], bounce:['#10b981','#0d9268'] };
    platforms.forEach(p => {
      const ps = p.y - camY;
      if (ps < -PTH || ps > H + 5) return;
      const [c1, c2] = cols[p.type] || cols.normal;
      const g = ctx.createLinearGradient(p.x, ps, p.x, ps + PTH);
      g.addColorStop(0, c1); g.addColorStop(1, c2);
      ctx.fillStyle = g; ctx.shadowColor = c1; ctx.shadowBlur = 8;
      rr(p.x, ps, PTW, PTH, 4); ctx.fill(); ctx.shadowBlur = 0;
    });
    // ── Partikel
    particles.forEach(p => {
      ctx.globalAlpha = Math.max(0, p.life); ctx.fillStyle = p.col;
      ctx.beginPath(); ctx.arc(p.x, p.y - camY, p.r, 0, Math.PI*2); ctx.fill();
    });
    ctx.globalAlpha = 1;
    // ── Spieler
    const px = player.x, ps2 = player.y - camY;
    const g2 = ctx.createRadialGradient(px+PLW/2, ps2+PLH/2, 2, px+PLW/2, ps2+PLH/2, PLW/2);
    g2.addColorStop(0,'#ffffff'); g2.addColorStop(.45,'#5b9cf6'); g2.addColorStop(1,'#8b72f8');
    ctx.fillStyle = g2; ctx.shadowColor = '#5b9cf6'; ctx.shadowBlur = 12;
    rr(px, ps2, PLW, PLH, 5); ctx.fill(); ctx.shadowBlur = 0;
    // ── HUD
    ctx.fillStyle = 'rgba(13,15,24,.82)'; rr(7,7,80,38,6); ctx.fill();
    ctx.fillStyle = '#5b9cf6'; ctx.font = 'bold 8px Inter,sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('H\u00d6HE', 15, 21);
    ctx.fillStyle = '#f0f2f8'; ctx.font = 'bold 14px Inter,sans-serif';
    ctx.fillText(score + 'm', 15, 37);
    ctx.fillStyle = 'rgba(13,15,24,.82)'; rr(W-87,7,80,38,6); ctx.fill();
    ctx.fillStyle = '#8b72f8'; ctx.font = 'bold 8px Inter,sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('REKORD', W-15, 21);
    ctx.fillStyle = '#f0f2f8'; ctx.font = 'bold 14px Inter,sans-serif';
    ctx.fillText(hi + 'm', W-15, 37);
    ctx.textAlign = 'left';
  }

  function loop() { update(); draw(); requestAnimationFrame(loop); }

  document.addEventListener('keydown', e => {
    keys[e.key] = true;
    if (e.key === ' ' && state === 'playing') e.preventDefault();
  });
  document.addEventListener('keyup', e => { delete keys[e.key]; });
  canvas.addEventListener('touchstart', e => {
    if (state !== 'playing') return;
    touchX = e.touches[0].clientX; e.preventDefault();
  }, {passive:false});
  canvas.addEventListener('touchmove', e => {
    if (touchX !== null) touchDX = e.touches[0].clientX - touchX;
    e.preventDefault();
  }, {passive:false});
  canvas.addEventListener('touchend', () => { touchDX = 0; touchX = null; });

  document.addEventListener('DOMContentLoaded', () => {
    const bs = document.getElementById('btn-start');
    const bj = document.getElementById('btn-ja');
    const bn = document.getElementById('btn-nein');
    if (bs) bs.addEventListener('click', startGame);
    if (bj) bj.addEventListener('click', startGame);
    if (bn) bn.addEventListener('click', goToNews);
  });

  let gameStarted = false;
  window.addEventListener('resize', () => { if (gameStarted) resize(); });
  window.initGame = function() {
    resize();
    if (!gameStarted) { gameStarted = true; showOverlay('idle'); loop(); }
  };
})();
</script>
"""

MANIFEST = '{"name":"Daily Briefing","short_name":"Briefing","description":"Taegliches News-Briefing: Politik, Wirtschaft, EU","start_url":"/daily-briefing/","display":"standalone","background_color":"#08090e","theme_color":"#08090e","orientation":"portrait","icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png"},{"src":"icon-512.png","sizes":"512x512","type":"image/png"}]}'

SW_JS = """
const CACHE = "briefing-v5";
const ASSETS = ["./"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});
self.addEventListener("fetch", e => {
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""

# ── HTML-Bausteine ─────────────────────────────────────────────────────────────

def build_filter_bar(results):
    sb = '<button class="flt-btn active" data-filter="source" data-val="all">Alle <span class="flt-count"></span></button>'
    for r in results:
        n = html_module.escape(r["name"])
        sb += f'<button class="flt-btn" data-filter="source" data-val="{n}">{n} <span class="flt-count">0</span></button>'
    return (
        f'<div class="filter-bar" id="filter-bar">'
        f'<div class="filter-inner">'
        f'<div class="filter-row">{sb}</div>'
        f'<div class="filter-footer">'
        f'<div id="filter-result"></div>'
        f'<button id="clear-btn">&#10005; Zurücksetzen &nbsp;<kbd style="font-size:.55rem;opacity:.6">ESC</kbd></button>'
        f'</div></div></div>'
    )

def build_card(r):
    bdg   = "de" if r["country"] == "DE" else "en"
    src   = html_module.escape(r["name"])
    items = r["items"]
    if r["error"] and not items:
        body = f'<div class="err">&#9888; Feed nicht erreichbar:<br><small>{html_module.escape(r["error"][:200])}</small></div>'
    elif not items:
        body = '<div class="empty">Keine aktuellen Artikel gefunden.</div>'
    else:
        rows = ""
        for it in items:
            t      = html_module.escape(it["title"])
            lk     = html_module.escape(it["link"])
            d      = f'<div class="nd">{html_module.escape(it["desc"])}</div>' if it["desc"] else ""
            ts     = fmt_time(it["pub_dt"], it["pubdate"])
            age    = age_label(it["pub_dt"])
            nm     = f'<span class="nm">{ts} &middot; {age}</span>' if ts else ""
            nb     = '<span class="ni-new">NEU</span>' if is_new(it["pub_dt"]) else ""
            cat    = it.get("category", "Welt")
            ckey   = CAT_CSS_KEY.get(cat, "welt")
            cbadge = f'<span class="ni-cat ni-cat-{ckey}">{html_module.escape(cat)}</span>'
            rows += (
                f'<div class="ni reveal" data-src="{src}" data-cat="{html_module.escape(cat)}" data-ts="{pub_ts(it["pub_dt"])}">'
                f'<a href="{lk}" target="_blank" rel="noopener">'
                f'<div class="ni-top"><div class="nt">{t}</div><span class="ni-arr">&#8594;</span></div>'
                f'{d}<div class="ni-foot">{nm}{nb}{cbadge}</div></a></div>'
            )
        body = f'<div class="nlist">{rows}</div>'
    cnt = f'<span class="card-cnt">{len(items)} Artikel</span>' if items else ""
    return (
        f'<div class="card card-{bdg}" data-src="{src}">'
        f'<div class="card-hdr">'
        f'<span class="card-em">{r["emoji"]}</span><span class="card-name">{r["name"]}</span>'
        f'{cnt}<span class="card-bdg bdg-{bdg}">{r["country"]}</span></div>'
        f'{body}'
        f'<div class="card-empty-msg">Keine Artikel für diesen Filter.</div>'
        f'</div>'
    )

def build_page(results, weather, now):
    wd    = WOCHENTAGE[now.weekday()]
    monat = MONATE[now.month - 1]
    ds    = f"{now.strftime('%d.')} {monat} {now.strftime('%Y')}"
    ts    = now.strftime("%H:%M")
    h     = now.hour
    if   5 <= h < 10: greeting = "Guten Morgen"
    elif 10 <= h < 13: greeting = "Was ist los?"
    elif 13 <= h < 18: greeting = "Guten Nachmittag"
    elif 18 <= h < 22: greeting = "Guten Abend"
    else:              greeting = "Noch wach?"
    if   5 <= h <  9: tod = "tod-morning"
    elif 17 <= h < 21: tod = "tod-evening"
    elif h >= 21 or h < 5: tod = "tod-night"
    else:              tod = "tod-day"
    unified = build_unified_feed(results)
    total   = len(unified)
    feed_html = build_feed_html(unified)
    whtml = build_weather_html(weather, tod)
    fbar  = build_filter_bar(results)
    src_names = " &middot; ".join(r["name"] for r in results)
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
        "</head><body>"
        '<div id="progress-bar"></div>'
        "<div class='bg-anim'></div>"

        # Header
        "<div class='hdr'><div class='hdr-inner'>"
        "<div class='hdr-left'>"
        "<h1>&#128240; Daily Briefing</h1>"
        f"<div class='hdr-greeting'>{greeting}</div>"
        f"<div class='hdr-meta'>{wd}, {ds} &middot; {ts} Uhr</div>"
        "</div>"
        "<div class='hdr-right'>"
        f"<span class='pill-ac'>&#128240; {total} Artikel</span>"
        "<span class='live'>LIVE</span>"
        "<a class='btn-r' href='javascript:location.reload()'>&#8635; Aktualisieren</a>"
        "</div></div></div>"

        # Tab-Navigation
        "<div class='tab-nav'>"
        "<button class='tab-btn tab-active' data-tab='news'>&#128240; News</button>"
        "<button class='tab-btn' data-tab='game'>&#127918; Spiel</button>"
        "<div class='tab-right'>"
        "<button class='view-btn' id='compact-btn' title='Kompaktansicht'>&#8803;</button>"
        "<button class='view-btn' id='theme-btn' title='Hell/Dunkel'>&#9788;</button>"
        "</div></div>"

        # Filter-Bar (nur News-Tab)
        f"{fbar}"

        # Tab: News
        "<div id='tab-news' class='tab-content'>"
        f"{whtml}"
        "<div class='wrap'>"
        f"{feed_html}"
        '<div id="no-results"><div class="nr-icon">\U0001f50d</div><div class="nr-text">Keine Artikel für diesen Filter.</div></div>'
        f"<div class='foot'>{src_names} &middot; Wetter: open-meteo.com</div>"
        "</div></div>"

        # Tab: Spiel
        "<div id='tab-game' class='tab-content tab-hidden'>"
        "<div class='game-wrap'>"
        "<div id='game-ui'>"
        "<canvas id='game-canvas'></canvas>"
        "<div class='game-overlay' id='game-overlay' style='display:none'>"
        "<div class='go-inner' id='go-idle'>"
        "<div class='go-title'>STELLAR JUMP</div>"
        "<div class='go-sub'>Springe von Plattform zu Plattform &ndash; so hoch wie m&ouml;glich!</div>"
        "<div class='go-keys'><kbd>&#8592;</kbd> <kbd>&#8594;</kbd> steuern &nbsp;&middot;&nbsp; Handy: wischen</div>"
        "<button class='go-btn' id='btn-start'>&#9654; Starten</button>"
        "</div>"
        "<div class='go-inner' id='go-dead' style='display:none'>"
        "<div class='go-gameover'>GAME OVER</div>"
        "<div class='go-score-val' id='go-score'></div>"
        "<div class='go-record' id='go-record'></div>"
        "<div class='go-newrecord' id='go-newrecord' style='display:none'>&#127942; NEUER REKORD!</div>"
        "<div class='go-ask'>M&ouml;chtest du nochmal spielen?</div>"
        "<div class='go-btns'>"
        "<button class='go-btn' id='btn-ja'>Ja</button>"
        "<button class='go-btn go-btn-sec' id='btn-nein'>Nein</button>"
        "</div></div>"
        "</div></div>"
        "</div></div>"

        f"{JS}"
        "</body></html>"
    )

# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    print("Daily Briefing wird generiert...")
    now = datetime.now()
    os.makedirs("docs", exist_ok=True)

    print("  Wetter wird geladen...", end=" ", flush=True)
    weather = fetch_weather(CITIES)
    print("OK")

    results = []
    for feed in FEEDS:
        print(f"  {feed['name']}...", end=" ", flush=True)
        raw, err = parse_feed(feed["urls"], MAX_ITEMS)
        filtered = [i for i in raw if is_recent(i["pub_dt"]) and is_relevant(i["title"], i["desc"])]
        if len(filtered) < 3 and raw:
            filtered = [i for i in raw if is_recent(i["pub_dt"])]
        if not filtered:
            filtered = raw
        # Chronologisch sortieren: neueste zuerst
        filtered.sort(key=sort_key_dt, reverse=True)
        # Kategorie zuweisen
        hard = PINNED_HARD.get(feed["name"])
        soft = PINNED_SOFT.get(feed["name"])
        accepted = []
        for item in filtered:
            if hard:
                txt = (item["title"] + " " + item.get("desc", "")).lower()
                if any(k in txt for k in WIRTSCHAFT_REQUIRED):
                    item["category"] = hard
                    accepted.append(item)
                # kein Wirtschafts-Keyword → Artikel verwerfen
            else:
                cat = categorize(item["title"], item.get("desc", ""))
                item["category"] = soft if (soft and cat == "Sonstiges") else cat
                accepted.append(item)
        filtered = accepted
        print(f"{len(filtered)} Artikel")
        results.append({"name":feed["name"],"country":feed["country"],
                        "emoji":feed["emoji"],"items":filtered,
                        "count":len(filtered),"error":err})

    page = build_page(results, weather, now)
    out  = OUTPUT_FILE
    os.makedirs(os.path.dirname(out) if os.path.dirname(out) else ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    with open("docs/manifest.json", "w", encoding="utf-8") as f:
        f.write(MANIFEST)
    with open("docs/sw.js", "w", encoding="utf-8") as f:
        f.write(SW_JS)
    print(f"Gespeichert: {out}")
    try:
        import webbrowser
        webbrowser.open(out)
    except:
        pass
    print("Fertig!")

if __name__ == "__main__":
    main()
