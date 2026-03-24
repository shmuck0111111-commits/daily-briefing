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
    {"name":"BBC News","country":"EN","emoji":"\U0001f1ec\U0001f1e7","urls":[
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/rss.xml"]},
    {"name":"Deutsche Welle","country":"EN","emoji":"\U0001f310","urls":[
        "https://rss.dw.com/xml/rss-en-all",
        "https://rss.dw.com/xml/rss-en-top"]},
]

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

MAX_ITEMS = 12
MAX_HOURS = 24
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
    ("Konflikte",   ["ukraine","russland","krieg","angriff","nato","iran","israel",
                     "attack","war","sanctions","military","waffe","terror","soldat",
                     "bomben","rakete","missile","troops","combat","hamas","gaza",
                     "konflikt","gefecht","offensive"]),
    ("Energie",     ["energie","oel","gas","strom","solar","wind","erneuerbar",
                     "energy","oil","pipeline","coal","nuclear","klima","climate",
                     "co2","emission","fossil","atomkraft","windkraft"]),
    ("Europa & EU", ["eu","europa","kommission","br\u00fcssel","bruessel","schengen",
                     "eurozone","europe","commission","von der leyen","ursula"]),
    ("USA",         ["usa","trump","washington","biden","harris","congress","senate",
                     "america","americans","wall street","new york","white house"]),
    ("Wirtschaft",  ["wirtschaft","konjunktur","inflation","zinsen","bundesbank","dax",
                     "aktien","boerse","markt","handel","haushalt","schulden","milliard",
                     "rezession","wachstum","steuer","economy","market","finance","bank",
                     "rate","trade","stock","gdp","recession","interest","tariff","budget",
                     "import","export","zoll","investition"]),
    ("Politik",     ["politik","regierung","minister","kanzler","bundestag","wahl",
                     "partei","koalition","cdu","spd","gruene","afd","fdp","election",
                     "government","parliament","president","policy","vote","abstimmung",
                     "merz","scholz","macron","putin"]),
]

CAT_EMOJI = {
    "Politik":    "\U0001f3db",
    "Wirtschaft": "\U0001f4b0",
    "Konflikte":  "\u2694\ufe0f",
    "Energie":    "\u26a1",
    "Europa & EU":"\U0001f1ea\U0001f1fa",
    "USA":        "\U0001f1fa\U0001f1f8",
    "Welt":       "\U0001f30d",
}

CAT_CSS_KEY = {
    "Politik":    "politik",
    "Wirtschaft": "wirtschaft",
    "Konflikte":  "konflikte",
    "Energie":    "energie",
    "Europa & EU":"europa",
    "USA":        "usa",
    "Welt":       "welt",
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
    return "Welt"

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

def build_weather_html(weather):
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
    return f'<div class="weather-bar">{cards}</div>'

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
  position:sticky;top:0;z-index:100;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);}
.hdr-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
.hdr-left h1{font-size:1.45rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,var(--ac),var(--ac2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hdr-meta{font-size:.75rem;color:var(--mu);margin-top:3px;}
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
  position:sticky;top:70px;z-index:95;
  backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  padding:0 28px;display:flex;gap:2px;}
@media(max-width:720px){.tab-nav{padding:0 16px;top:68px;}}
.tab-btn{padding:10px 18px;font-size:.82rem;font-weight:600;color:var(--mu);
  background:none;border:none;border-bottom:2px solid transparent;
  cursor:pointer;transition:all .2s;white-space:nowrap;}
.tab-btn:hover{color:var(--tx);}
.tab-btn.tab-active{color:var(--ac);border-bottom-color:var(--ac);}
.tab-hidden{display:none!important;}

/* Filter-Bar */
.filter-bar{background:rgba(13,15,24,.75);border-bottom:1px solid var(--bd);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:10px 28px;position:sticky;top:113px;z-index:90;}
@media(max-width:720px){.filter-bar{padding:10px 16px;top:110px;}}
.filter-inner{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:8px;}
.filter-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
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
  display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
@media(max-width:720px){.weather-bar{grid-template-columns:repeat(2,1fr);}}
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
.ni.ni-hidden{max-height:0;padding-top:0;padding-bottom:0;opacity:0;border-bottom:none;pointer-events:none;}
.empty{padding:22px;color:var(--mu);font-size:.82rem;text-align:center;}
.err{padding:14px 16px;color:#f87171;font-size:.76rem;line-height:1.6;word-break:break-word;}
#no-results{display:none;text-align:center;padding:60px 20px;color:var(--mu);}
#no-results.visible{display:block;}
#no-results .nr-icon{font-size:2.5rem;margin-bottom:12px;}
#no-results .nr-text{font-size:.9rem;}

/* Spiel-Tab */
.game-wrap{display:flex;flex-direction:column;align-items:center;padding:28px 16px;gap:16px;}
.game-hint{font-size:.75rem;color:var(--mu);text-align:center;line-height:1.7;}
.game-hint kbd{display:inline-block;background:var(--sf2);border:1px solid var(--bd2);
  border-radius:5px;padding:1px 6px;font-size:.68rem;color:var(--tx2);}
#game-canvas{border-radius:16px;border:1px solid var(--bd);display:block;
  box-shadow:0 0 40px rgba(91,156,246,.08);cursor:none;}

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
    });
  });
});

// ── Filter ──────────────────────────────────────────────────────────────────────
let activeSrc = 'all', activeCat = 'all';

function applyFilters() {
  const items = document.querySelectorAll('.ni[data-src]');
  let visible = 0;
  items.forEach(ni => {
    const ok = (activeSrc === 'all' || ni.dataset.src === activeSrc) &&
               (activeCat === 'all' || ni.dataset.cat === activeCat);
    ni.classList.toggle('ni-hidden', !ok);
    if (ok) visible++;
  });
  document.querySelectorAll('.card[data-src]').forEach(card => {
    card.classList.toggle('empty-card', !card.querySelectorAll('.ni:not(.ni-hidden)').length);
  });
  const noRes = document.getElementById('no-results');
  if (noRes) noRes.classList.toggle('visible', visible === 0);
  const res = document.getElementById('filter-result');
  if (res) {
    if (activeSrc === 'all' && activeCat === 'all')
      res.innerHTML = '<span>' + items.length + '</span> Artikel geladen';
    else
      res.innerHTML = '<span>' + visible + '</span> von ' + items.length + ' Artikeln sichtbar';
  }
  const clr = document.getElementById('clear-btn');
  if (clr) clr.classList.toggle('visible', activeSrc !== 'all' || activeCat !== 'all');
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
      const f = btn.dataset.filter, v = btn.dataset.val;
      if (f === 'source') {
        activeSrc = v;
        document.querySelectorAll('.flt-btn[data-filter="source"]').forEach(b => b.classList.remove('active'));
      } else {
        activeCat = v;
        document.querySelectorAll('.flt-btn[data-filter="cat"]').forEach(b => b.classList.remove('active'));
      }
      btn.classList.add('active');
      applyFilters();
    });
  });
  const clr = document.getElementById('clear-btn');
  if (clr) clr.addEventListener('click', () => {
    activeSrc = activeCat = 'all';
    document.querySelectorAll('.flt-btn').forEach(b => b.classList.toggle('active', b.dataset.val === 'all'));
    applyFilters();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && clr) clr.click(); });
});

// ── STELLAR JUMP ───────────────────────────────────────────────────────────────
(function() {
  const canvas = document.getElementById('game-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H;

  const GRAV = 0.38, JUMP = -13, SPEED = 4.5;
  const PLW = 30, PLH = 30;
  const PTW = 74, PTH = 11;

  let state = 'idle', score = 0, hi = +localStorage.getItem('jump_hi') || 0;
  let camY = 0, totalH = 0;
  let platforms = [], particles = [], stars = [];
  let player = {x:0, y:0, vx:0, vy:0};
  let keys = {}, touchX = null, touchDX = 0;
  let animFrame;

  function resize() {
    const wrap = canvas.parentElement;
    W = canvas.width  = Math.min(420, wrap.clientWidth - 32);
    H = canvas.height = Math.min(650, window.innerHeight - 220);
    if (stars.length) initStars();
  }

  function initStars() {
    stars = Array.from({length:55}, () => ({
      x: Math.random() * W, y: Math.random() * H * 4,
      r: Math.random() * 1.4 + 0.3, a: Math.random() * 0.55 + 0.15,
    }));
  }

  function mkPlat(y) {
    const moving = Math.random() < 0.18;
    const bounce = !moving && Math.random() < 0.13;
    return { x: Math.random() * (W - PTW - 20) + 10, y,
             vx: moving ? (Math.random()>.5 ? 1.9 : -1.9) : 0,
             type: moving ? 'move' : bounce ? 'bounce' : 'normal' };
  }

  function reset() {
    score = 0; camY = 0; totalH = 0; platforms = []; particles = [];
    player = { x: W/2 - PLW/2, y: H - 120, vx: 0, vy: 0 };
    platforms.push({ x: W/2 - PTW/2, y: H - 80, vx: 0, type: 'normal' });
    for (let i = 1; i < 16; i++) platforms.push(mkPlat(H - 80 - i * 82));
    player.vy = JUMP;
    initStars();
  }

  function spawnPart(x, y, col) {
    for (let i = 0; i < 7; i++)
      particles.push({ x, y, vx:(Math.random()-.5)*5, vy:(Math.random()-.5)*5-2,
        life:1, decay:.04+Math.random()*.02, col, r:2+Math.random()*2 });
  }

  function update() {
    if (state !== 'playing') return;
    let mvx = 0;
    if (keys['ArrowLeft']  || keys['a'] || keys['A']) mvx = -SPEED;
    if (keys['ArrowRight'] || keys['d'] || keys['D']) mvx =  SPEED;
    if (touchX !== null) mvx = touchDX * 0.13;
    player.vx = player.vx * 0.7 + mvx * 0.3;
    player.vy += GRAV;
    player.x  += player.vx;
    player.y  += player.vy;
    if (player.x + PLW < 0) player.x = W;
    if (player.x > W)       player.x = -PLW;
    const sy = player.y - camY;
    if (sy < H * 0.38) { const d = H * 0.38 - sy; camY -= d; totalH += d; score = Math.round(totalH / 8); }
    if (player.vy > 0) {
      for (const p of platforms) {
        const ps = p.y - camY;
        const px = player.x + PLW * 0.1, pw = PLW * 0.8;
        if (px + pw > p.x && px < p.x + PTW &&
            player.y + PLH >= ps && player.y + PLH <= ps + PTH + player.vy + 1) {
          player.y = ps - PLH;
          player.vy = p.type === 'bounce' ? JUMP * 1.38 : JUMP;
          spawnPart(player.x + PLW/2, ps,
            p.type === 'move' ? '#8b72f8' : p.type === 'bounce' ? '#10b981' : '#5b9cf6');
        }
      }
    }
    platforms.forEach(p => { if (p.type === 'move') { p.x += p.vx; if (p.x < 0 || p.x + PTW > W) p.vx *= -1; }});
    platforms = platforms.filter(p => p.y - camY < H + 60);
    const top = Math.min(...platforms.map(p => p.y));
    while (platforms.length < 18) platforms.push(mkPlat(top - 72 - Math.random() * 32));
    particles.forEach(p => { p.x += p.vx; p.y += p.vy; p.vy += .12; p.life -= p.decay; });
    particles = particles.filter(p => p.life > 0);
    if (player.y - camY > H + 80) {
      state = 'dead';
      if (score > hi) { hi = score; localStorage.setItem('jump_hi', hi); }
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
    ctx.fillStyle = '#08090e'; ctx.fillRect(0, 0, W, H);
    // Sterne
    const off = (camY * .12) % (H * 4 + 200);
    stars.forEach(s => {
      const sy = ((s.y + off) % (H * 4 + 200)) - 100;
      if (sy < -4 || sy > H + 4) return;
      ctx.globalAlpha = s.a * (.6 + .4 * Math.sin(Date.now()/1400 + s.x));
      ctx.fillStyle = '#f0f2f8';
      ctx.beginPath(); ctx.arc(s.x, sy, s.r, 0, Math.PI*2); ctx.fill();
    });
    ctx.globalAlpha = 1;
    // Plattformen
    const cols = { normal:['#5b9cf6','#3a7bd5'], move:['#8b72f8','#6a50d8'], bounce:['#10b981','#0d9268'] };
    platforms.forEach(p => {
      const ps = p.y - camY;
      if (ps < -PTH || ps > H + 5) return;
      const [c1, c2] = cols[p.type] || cols.normal;
      const g = ctx.createLinearGradient(p.x, ps, p.x, ps + PTH);
      g.addColorStop(0, c1); g.addColorStop(1, c2);
      ctx.fillStyle = g; ctx.shadowColor = c1; ctx.shadowBlur = 10;
      rr(p.x, ps, PTW, PTH, 5); ctx.fill(); ctx.shadowBlur = 0;
    });
    // Partikel
    particles.forEach(p => {
      ctx.globalAlpha = Math.max(0, p.life); ctx.fillStyle = p.col;
      ctx.beginPath(); ctx.arc(p.x, p.y - camY, p.r, 0, Math.PI*2); ctx.fill();
    });
    ctx.globalAlpha = 1;
    // Spieler
    const px = player.x, ps2 = player.y - camY;
    const g2 = ctx.createRadialGradient(px+PLW/2, ps2+PLH/2, 2, px+PLW/2, ps2+PLH/2, PLW/2);
    g2.addColorStop(0,'#ffffff'); g2.addColorStop(.45,'#5b9cf6'); g2.addColorStop(1,'#8b72f8');
    ctx.fillStyle = g2; ctx.shadowColor = '#5b9cf6'; ctx.shadowBlur = 16;
    rr(px, ps2, PLW, PLH, 7); ctx.fill(); ctx.shadowBlur = 0;
    // HUD Score
    ctx.fillStyle = 'rgba(13,15,24,.78)'; rr(10,10,100,48,8); ctx.fill();
    ctx.fillStyle = '#5b9cf6'; ctx.font = 'bold 9px Inter,sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('HÖHE', 20, 26);
    ctx.fillStyle = '#f0f2f8'; ctx.font = 'bold 17px Inter,sans-serif';
    ctx.fillText(score + 'm', 20, 47);
    // HUD Highscore
    ctx.fillStyle = 'rgba(13,15,24,.78)'; rr(W-110,10,100,48,8); ctx.fill();
    ctx.fillStyle = '#8b72f8'; ctx.font = 'bold 9px Inter,sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('REKORD', W-20, 26);
    ctx.fillStyle = '#f0f2f8'; ctx.font = 'bold 17px Inter,sans-serif';
    ctx.fillText(hi + 'm', W-20, 47);
    ctx.textAlign = 'left';
    // Overlays
    if (state === 'idle' || state === 'dead') {
      ctx.fillStyle = 'rgba(8,9,14,.8)'; ctx.fillRect(0,0,W,H);
      ctx.textAlign = 'center';
      if (state === 'idle') {
        ctx.shadowColor = '#5b9cf6'; ctx.shadowBlur = 22;
        ctx.fillStyle = '#f0f2f8'; ctx.font = 'bold 36px Inter,sans-serif'; ctx.fillText('STELLAR', W/2, H/2-52);
        ctx.fillStyle = '#5b9cf6'; ctx.font = 'bold 36px Inter,sans-serif'; ctx.fillText('JUMP', W/2, H/2-12);
        ctx.shadowBlur = 0;
        ctx.fillStyle = '#b8bdd4'; ctx.font = '13px Inter,sans-serif'; ctx.fillText('Leertaste drücken oder tippen', W/2, H/2+28);
        ctx.fillStyle = '#6b7194'; ctx.font = '12px Inter,sans-serif'; ctx.fillText('← → zum Steuern', W/2, H/2+50);
        ctx.font = '11px Inter,sans-serif';
        ctx.fillStyle = '#5b9cf6'; ctx.fillText('■ Normal', W/2-75, H/2+88);
        ctx.fillStyle = '#8b72f8'; ctx.fillText('■ Bewegt', W/2+2,  H/2+88);
        ctx.fillStyle = '#10b981'; ctx.fillText('■ Boost',  W/2+78, H/2+88);
      } else {
        ctx.shadowColor = '#f87171'; ctx.shadowBlur = 14;
        ctx.fillStyle = '#f87171'; ctx.font = 'bold 27px Inter,sans-serif'; ctx.fillText('GAME OVER', W/2, H/2-56);
        ctx.shadowBlur = 0;
        ctx.fillStyle = '#f0f2f8'; ctx.font = 'bold 26px Inter,sans-serif'; ctx.fillText(score + 'm', W/2, H/2-12);
        ctx.fillStyle = '#8b72f8'; ctx.font = '13px Inter,sans-serif'; ctx.fillText('Rekord: ' + hi + 'm', W/2, H/2+16);
        if (score > 0 && score >= hi) {
          ctx.shadowColor = '#fbbf24'; ctx.shadowBlur = 10;
          ctx.fillStyle = '#fbbf24'; ctx.font = 'bold 13px Inter,sans-serif'; ctx.fillText('NEUER REKORD!', W/2, H/2+40);
          ctx.shadowBlur = 0;
        }
        ctx.fillStyle = '#5b9cf6'; ctx.font = 'bold 13px Inter,sans-serif'; ctx.fillText('Nochmal? Leertaste / Tippen', W/2, H/2+66);
      }
      ctx.textAlign = 'left';
    }
  }

  function loop() { update(); draw(); animFrame = requestAnimationFrame(loop); }

  // Eingabe
  document.addEventListener('keydown', e => {
    keys[e.key] = true;
    if (e.key === ' ' && document.getElementById('tab-game') &&
        !document.getElementById('tab-game').classList.contains('tab-hidden')) {
      e.preventDefault();
      if (state !== 'playing') { state = 'playing'; reset(); }
    }
  });
  document.addEventListener('keyup', e => { delete keys[e.key]; });
  canvas.addEventListener('touchstart', e => {
    touchX = e.touches[0].clientX;
    if (state !== 'playing') { state = 'playing'; reset(); }
    e.preventDefault();
  }, {passive:false});
  canvas.addEventListener('touchmove', e => {
    if (touchX !== null) touchDX = e.touches[0].clientX - touchX;
    e.preventDefault();
  }, {passive:false});
  canvas.addEventListener('touchend', () => { touchDX = 0; touchX = null; });

  window.addEventListener('resize', resize);
  resize(); reset(); loop();
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
    all_cats = list(CAT_EMOJI.keys())
    sb = '<button class="flt-btn active" data-filter="source" data-val="all">Alle <span class="flt-count"></span></button>'
    for r in results:
        n = html_module.escape(r["name"])
        sb += f'<button class="flt-btn" data-filter="source" data-val="{n}">{r["emoji"]} {n} <span class="flt-count">0</span></button>'
    cb = '<button class="flt-btn active" data-filter="cat" data-val="all">Alle <span class="flt-count"></span></button>'
    for cat in all_cats:
        cb += f'<button class="flt-btn" data-filter="cat" data-val="{html_module.escape(cat)}">{html_module.escape(cat)} <span class="flt-count">0</span></button>'
    return (
        f'<div class="filter-bar" id="filter-bar">'
        f'<div class="filter-inner">'
        f'<div class="filter-row"><span class="filter-label">Quelle</span>{sb}</div>'
        f'<div class="filter-row"><span class="filter-label">Kategorie</span>{cb}</div>'
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
    total = sum(r["count"] for r in results)
    de_c  = "".join(build_card(r) for r in results if r["country"] == "DE")
    en_c  = "".join(build_card(r) for r in results if r["country"] == "EN")
    whtml = build_weather_html(weather)
    fbar  = build_filter_bar(results)
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
        f"<div class='hdr-meta'>{wd}, {ds} &middot; {ts} Uhr &middot; Politik &middot; Wirtschaft &middot; EU/Welt</div>"
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
        "</div>"

        # Filter-Bar (nur News-Tab)
        f"{fbar}"

        # Tab: News
        "<div id='tab-news' class='tab-content'>"
        f"{whtml}"
        "<div class='wrap'>"
        "<div class='slabel'>\U0001f1e9\U0001f1ea Deutschland &amp; Europa</div>"
        f"<div class='grid'>{de_c}</div>"
        "<div class='slabel'>\U0001f310 International</div>"
        f"<div class='grid'>{en_c}</div>"
        '<div id="no-results"><div class="nr-icon">\U0001f50d</div><div class="nr-text">Keine Artikel für diesen Filter.</div></div>'
        f"<div class='foot'>Stand: {wd}, {ds} &middot; {ts} Uhr &middot; Tagesschau &middot; Spiegel &middot; BBC &middot; DW &middot; Wetter: open-meteo.com</div>"
        "</div></div>"

        # Tab: Spiel
        "<div id='tab-game' class='tab-content tab-hidden'>"
        "<div class='game-wrap'>"
        "<canvas id='game-canvas'></canvas>"
        "<div class='game-hint'>"
        "<kbd>&#8592;</kbd> <kbd>&#8594;</kbd> oder <kbd>A</kbd> <kbd>D</kbd> steuern &nbsp;&middot;&nbsp; "
        "<kbd>Leertaste</kbd> starten &nbsp;&middot;&nbsp; Auf dem Handy tippen &amp; wischen"
        "</div></div></div>"

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
        for item in filtered:
            item["category"] = categorize(item["title"], item.get("desc", ""))
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
