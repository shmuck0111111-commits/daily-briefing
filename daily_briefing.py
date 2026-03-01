#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_briefing.py - Taegliches News-Briefing via RSS + Wetter, kein API-Key"""

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

# WMO Wettercodes -> Emoji + Text
WMO_CODES = {
    0:"☀️ Klar", 1:"🌤️ Meist klar", 2:"⛅ Teilw. bewölkt", 3:"☁️ Bedeckt",
    45:"🌫️ Nebel", 48:"🌫️ Nebel", 51:"🌦️ Nieselregen", 53:"🌦️ Nieselregen",
    55:"🌧️ Nieselregen", 61:"🌧️ Regen", 63:"🌧️ Regen", 65:"🌧️ Starkregen",
    71:"🌨️ Schnee", 73:"🌨️ Schnee", 75:"❄️ Starker Schnee",
    80:"🌦️ Schauer", 81:"🌧️ Schauer", 82:"⛈️ Starke Schauer",
    95:"⛈️ Gewitter", 96:"⛈️ Gewitter", 99:"⛈️ Gewitter",
}

CITIES = [
    {"name":"Frankfurt","lat":50.11,"lon":8.68},
    {"name":"Hamburg",  "lat":53.55,"lon":10.00},
    {"name":"Berlin",   "lat":52.52,"lon":13.41},
    {"name":"München",  "lat":48.14,"lon":11.58},
]

MAX_ITEMS = 12
MAX_HOURS = 24
NEW_HOURS = 2  # NEU-Badge nur wenn juenger als 2 Stunden

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

WOCHENTAGE = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
MONATE = ["Januar","Februar","M\u00e4rz","April","Mai","Juni",
          "Juli","August","September","Oktober","November","Dezember"]

# ── Wetter ────────────────────────────────────────────────────────────────────

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
            label = WMO_CODES.get(code, "🌡️")
            results.append({"name": c["name"], "temp": temp, "wind": wind, "label": label, "ok": True})
        except Exception:
            results.append({"name": c["name"], "temp": None, "wind": None, "label": "–", "ok": False})
    return results

def build_weather_html(weather):
    cards = ""
    for w in weather:
        if w["ok"]:
            cards += (
                f'<div class="wc">'
                f'<div class="wc-city">{w["name"]}</div>'
                f'<div class="wc-main">{w["label"]}</div>'
                f'<div class="wc-temp">{w["temp"]}°C</div>'
                f'<div class="wc-wind">💨 {w["wind"]} km/h</div>'
                f'</div>'
            )
        else:
            cards += f'<div class="wc"><div class="wc-city">{w["name"]}</div><div class="wc-main">–</div></div>'
    return f'<div class="weather-bar">{cards}</div>'

# ── RSS ────────────────────────────────────────────────────────────────────────

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

def is_new(pub_dt):
    """Gibt True zurueck wenn Artikel juenger als NEW_HOURS ist."""
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

# ── CSS ────────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#08090e;--sf:#12151f;--sf2:#181c2a;--bd:#1e2235;--bd2:#252a3d;
  --ac:#5b9cf6;--ac2:#8b72f8;--ac3:#f06292;
  --tx:#f0f2f8;--tx2:#b8bdd4;--mu:#6b7194;--new:#10b981;
}
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{
  font-family:"Inter",system-ui,sans-serif;
  background:var(--bg);color:var(--tx);min-height:100vh;padding-bottom:80px;
  overflow-x:hidden;
}
.bg-anim{
  position:fixed;inset:0;z-index:-1;
  background:
    radial-gradient(ellipse at 15% 10%,rgba(91,156,246,.09) 0%,transparent 55%),
    radial-gradient(ellipse at 85% 80%,rgba(139,114,248,.07) 0%,transparent 55%),
    radial-gradient(ellipse at 50% 50%,rgba(240,98,146,.04) 0%,transparent 60%),
    #08090e;
  animation:bgshift 12s ease-in-out infinite alternate;
}
@keyframes bgshift{
  0%  {background-position:0% 0%;}
  50% {background-position:100% 50%;}
  100%{background-position:0% 100%;}
}
.hdr{
  background:rgba(13,15,24,.88);
  border-bottom:1px solid var(--bd);
  padding:20px 28px 16px;
  position:sticky;top:0;z-index:100;
  backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
}
.hdr-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
.hdr-left h1{
  font-size:1.45rem;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,var(--ac),var(--ac2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.hdr-meta{font-size:.75rem;color:var(--mu);margin-top:3px;}
.hdr-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.pill-ac{
  display:inline-flex;align-items:center;gap:5px;padding:4px 12px;
  border-radius:20px;font-size:.7rem;font-weight:600;
  background:rgba(91,156,246,.12);border:1px solid rgba(91,156,246,.3);color:var(--ac);
}
.live{
  display:inline-flex;align-items:center;gap:5px;padding:4px 11px;
  border-radius:20px;font-size:.65rem;font-weight:700;letter-spacing:.5px;
  background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);color:var(--new);
}
.live::before{
  content:"";width:6px;height:6px;border-radius:50%;background:var(--new);
  animation:pulse 1.5s infinite;
}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.3;transform:scale(.7);}}
.btn-r{
  display:inline-flex;align-items:center;gap:5px;padding:6px 14px;
  border-radius:20px;font-size:.73rem;font-weight:600;
  background:linear-gradient(135deg,rgba(91,156,246,.15),rgba(139,114,248,.15));
  border:1px solid rgba(91,156,246,.32);color:var(--ac);
  cursor:pointer;text-decoration:none;transition:all .2s;
}
.btn-r:hover{background:linear-gradient(135deg,rgba(91,156,246,.28),rgba(139,114,248,.28));transform:translateY(-1px);}
@media(max-width:720px){.hdr-right{display:none;}}

/* Wetter-Bar */
.weather-bar{
  max-width:1200px;margin:18px auto 0;padding:0 16px;
  display:grid;grid-template-columns:repeat(4,1fr);gap:12px;
}
@media(max-width:720px){.weather-bar{grid-template-columns:repeat(2,1fr);}}
.wc{
  background:var(--sf);border:1px solid var(--bd);border-radius:14px;
  padding:13px 16px;display:flex;flex-direction:column;gap:2px;
  transition:border-color .2s;
}
.wc:hover{border-color:var(--bd2);}
.wc-city{font-size:.68rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--mu);}
.wc-main{font-size:.82rem;color:var(--tx2);margin-top:4px;}
.wc-temp{font-size:1.5rem;font-weight:800;color:var(--tx);line-height:1.1;}
.wc-wind{font-size:.68rem;color:var(--mu);margin-top:3px;}

.wrap{max-width:1200px;margin:0 auto;padding:24px 16px;}
.slabel{
  font-size:.68rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--mu);margin-bottom:12px;padding-left:2px;
}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:26px;}
@media(max-width:720px){.grid{grid-template-columns:1fr;}}
.card{
  background:var(--sf);border:1px solid var(--bd);border-radius:16px;
  overflow:hidden;display:flex;flex-direction:column;
  opacity:0;transform:translateY(22px);
  animation:cardin .55s ease forwards;
  transition:border-color .2s,box-shadow .2s;
}
.card:hover{border-color:var(--bd2);box-shadow:0 10px 36px rgba(0,0,0,.45);}
.card:nth-child(1){animation-delay:.05s;}
.card:nth-child(2){animation-delay:.15s;}
.card:nth-child(3){animation-delay:.25s;}
.card:nth-child(4){animation-delay:.35s;}
@keyframes cardin{to{opacity:1;transform:translateY(0);}}
.card-hdr{
  padding:13px 16px;display:flex;align-items:center;gap:9px;
  border-bottom:1px solid var(--bd);background:var(--sf2);
  position:relative;overflow:hidden;
}
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
.ni-arr{color:var(--ac);font-size:.72rem;opacity:0;transform:translateX(-5px);transition:all .18s;flex-shrink:0;margin-top:2px;}
.nd{font-size:.73rem;color:var(--tx2);line-height:1.5;margin-bottom:6px;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.ni-foot{display:flex;align-items:center;gap:7px;}
.nm{font-size:.67rem;color:var(--mu);}
.ni-new{
  font-size:.58rem;font-weight:700;letter-spacing:.5px;
  background:rgba(16,185,129,.1);color:var(--new);
  border:1px solid rgba(16,185,129,.25);padding:1px 6px;border-radius:20px;
  animation:newpulse 2s ease-in-out infinite;
}
@keyframes newpulse{0%,100%{opacity:1;}50%{opacity:.5;}}
.empty{padding:22px;color:var(--mu);font-size:.82rem;text-align:center;}
.err{padding:14px 16px;color:#f87171;font-size:.76rem;line-height:1.6;word-break:break-word;}
.foot{
  text-align:center;color:var(--mu);font-size:.7rem;
  margin-top:36px;padding:18px;border-top:1px solid var(--bd);
}
.reveal{opacity:0;transform:translateY(18px);transition:opacity .5s ease,transform .5s ease;}
.reveal.visible{opacity:1;transform:translateY(0);}
"""

MANIFEST = '{"name":"Daily Briefing","short_name":"Briefing","description":"Taegliches News-Briefing: Politik, Wirtschaft, EU","start_url":"/daily-briefing/","display":"standalone","background_color":"#08090e","theme_color":"#08090e","orientation":"portrait","icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png"},{"src":"icon-512.png","sizes":"512x512","type":"image/png"}]}'

SW_JS = """
const CACHE = "briefing-v3";
const ASSETS = ["./"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});
self.addEventListener("fetch", e => {
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""

JS = """
<script>
if("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
document.addEventListener("DOMContentLoaded", () => {
  const els = document.querySelectorAll(".reveal");
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if(e.isIntersecting){ e.target.classList.add("visible"); io.unobserve(e.target); } });
  }, {threshold: 0.08});
  els.forEach(el => io.observe(el));
});
</script>
"""

# ── HTML-Bausteine ─────────────────────────────────────────────────────────────

def build_card(r, idx):
    bdg   = "de" if r["country"] == "DE" else "en"
    items = r["items"]
    if r["error"] and not items:
        e    = html_module.escape(r["error"][:200])
        body = f'<div class="err">&#9888; Feed nicht erreichbar:<br><small>{e}</small></div>'
    elif not items:
        body = '<div class="empty">Keine aktuellen Artikel gefunden.</div>'
    else:
        rows = ""
        for it in items:
            t   = html_module.escape(it["title"])
            lk  = html_module.escape(it["link"])
            d   = (f'<div class="nd">{html_module.escape(it["desc"])}</div>' if it["desc"] else "")
            ts  = fmt_time(it["pub_dt"], it["pubdate"])
            age = age_label(it["pub_dt"])
            nm  = f'<span class="nm">{ts} &middot; {age}</span>' if ts else ""
            nb  = '<span class="ni-new">NEU</span>' if is_new(it["pub_dt"]) else ""
            rows += (
                f'<div class="ni reveal"><a href="{lk}" target="_blank" rel="noopener">'
                f'<div class="ni-top"><div class="nt">{t}</div><span class="ni-arr">&#8594;</span></div>'
                f'{d}<div class="ni-foot">{nm}{nb}</div></a></div>'
            )
        body = f'<div class="nlist">{rows}</div>'
    cnt = f'<span class="card-cnt">{len(items)} Artikel</span>' if items else ""
    return (
        f'<div class="card card-{bdg}"><div class="card-hdr">'
        f'<span class="card-em">{r["emoji"]}</span>'
        f'<span class="card-name">{r["name"]}</span>'
        f'{cnt}<span class="card-bdg bdg-{bdg}">{r["country"]}</span></div>{body}</div>'
    )

def build_page(results, weather, now):
    wd    = WOCHENTAGE[now.weekday()]
    monat = MONATE[now.month - 1]
    ds    = f"{now.strftime('%d.')} {monat} {now.strftime('%Y')}"
    ts    = now.strftime("%H:%M")
    total = sum(r["count"] for r in results)
    de_c  = "".join(build_card(r, i) for i, r in enumerate(x for x in results if x["country"] == "DE"))
    en_c  = "".join(build_card(r, i) for i, r in enumerate(x for x in results if x["country"] == "EN"))
    whtml = build_weather_html(weather)
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
        "<div class='bg-anim'></div>"
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
        f"{whtml}"
        "<div class='wrap'>"
        "<div class='slabel'>\U0001f1e9\U0001f1ea Deutschland &amp; Europa</div>"
        f"<div class='grid'>{de_c}</div>"
        "<div class='slabel'>\U0001f310 International</div>"
        f"<div class='grid'>{en_c}</div>"
        f"<div class='foot'>Stand: {wd}, {ds} &middot; {ts} Uhr &middot; Tagesschau &middot; Spiegel &middot; BBC &middot; DW &middot; Wetter: open-meteo.com</div>"
        "</div>"
        f"{JS}"
        "</body></html>"
    )

# ── Main ───────────────────────────────────────────────────────────────────────

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
