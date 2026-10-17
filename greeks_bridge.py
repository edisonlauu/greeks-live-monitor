#!/usr/bin/env python3
"""Public Telegram options channel bridge; no trading/account access."""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

CHANNELS = ("greekslivenews2", "laevitas")
UTC = timezone.utc
HEADERS = {"User-Agent": "Mozilla/5.0"}
def utcnow(): return datetime.now(UTC)
def parse_dt(value):
    if not value: return None
    try:
        d = datetime.fromisoformat(value.replace("Z","+00:00"))
        return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
    except (ValueError, TypeError): return None
def json_read(p, fallback):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError): return fallback
def json_write(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True)+"\n",encoding="utf-8")
def parse_html(html, channel):
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for node in soup.select(".tgme_widget_message[data-post]"):
        match=re.fullmatch(re.escape(channel)+r"/(\d+)",node.get("data-post",""),re.I)
        if not match: continue
        n=int(match.group(1))
        time=node.select_one("time[datetime]")
        d=parse_dt(time.get("datetime")) if time else None
        textnode=node.select_one(".tgme_widget_message_text")
        content=textnode.get_text("\n",strip=True) if textnode else ""
        out.append({"key":f"{channel}/{n}","channel":channel,"post_id":n,
          "utc":d.isoformat() if d else None,"text":content,
          "url":f"https://t.me/{channel}/{n}","source":"public_html",
          "has_media":bool(node.select_one(".tgme_widget_message_photo_wrap, .tgme_widget_message_video_wrap")),
          "has_verified_timestamp":bool(d)})
    return out
def html_collect(channel,last_seen):
    records={}; before=None; log=[]; previous_oldest=None
    for page in range(15):
        url=f"https://t.me/s/{channel}"+(f"?before={before}" if before else "")
        try:
            res=requests.get(url,headers=HEADERS,timeout=20);res.raise_for_status()
            batch=parse_html(res.text,channel)
            if not batch: raise ValueError("no extractable posts")
            log.append({"ok":True,"count":len(batch)})
        except Exception as exc:
            log.append({"ok":False,"error":str(exc)[:250]});break
        for msg in batch: records[msg["key"]]=msg
        oldest=min(m["post_id"] for m in batch)
        if oldest==previous_oldest or (last_seen is not None and oldest<=last_seen):break
        previous_oldest=oldest; before=oldest
        if last_seen is None and page>=1:break
    return list(records.values()),{"ok":any(x["ok"] for x in log),"pages":log,"pagination_limited":len(log)>=15}
def rss_collect(channel):
    try:
        res=requests.get(f"https://rsshub.app/telegram/channel/{quote(channel)}",headers=HEADERS,timeout=20)
        res.raise_for_status()
        root=ET.fromstring(res.text); out=[]
        for item in root.findall(".//item"):
            link=item.findtext("link","")
            match=re.search(r"t\.me/(?:s/)?"+re.escape(channel)+r"/(\d+)",link)
            if not match: continue
            n=int(match.group(1));raw=item.findtext("pubDate")
            try: d=parsedate_to_datetime(raw).astimezone(UTC) if raw else None
            except (ValueError,TypeError,IndexError): d=None
            content=BeautifulSoup(item.findtext("description") or item.findtext("title") or "","html.parser").get_text("\n",strip=True)
            out.append({"key":f"{channel}/{n}","channel":channel,"post_id":n,"utc":d.isoformat() if d else None,
                        "text":content,"url":f"https://t.me/{channel}/{n}","source":"rsshub",
                        "has_verified_timestamp":bool(d),"has_media":False})
        return out,{"ok":bool(out),"count":len(out)}
    except Exception as exc:return [],{"ok":False,"error":str(exc)[:250]}
def rank(msg):
    return (msg["source"]=="mtproto",bool(msg.get("has_verified_timestamp")),len(msg.get("text","")))
def collect(folder):
    folder.mkdir(parents=True, exist_ok=True)
    history_path=folder/"messages.json"
    first=not history_path.exists()
    saved={m["key"]:m for m in json_read(history_path,[]) if isinstance(m,dict) and m.get("key")}
    now=utcnow(); old_ids={c:max((int(x["post_id"]) for x in saved.values() if x.get("channel")==c),default=None) for c in CHANNELS}
    snapshot={}; new=[]
    for channel in CHANNELS:
        posts,hs=html_collect(channel,old_ids[channel])
        newest=max((parse_dt(p.get("utc")) for p in posts if parse_dt(p.get("utc"))),default=None)
        rss,rs=rss_collect(channel) if not newest or now-newest>timedelta(hours=24) else ([],{"ok":False,"skipped":"recent HTML available"})
        all_posts=posts+rss
        for p in all_posts:
            if p["key"] not in saved and not first:
                age=(now-parse_dt(p.get("utc"))).total_seconds()/3600 if parse_dt(p.get("utc")) else None
                if age is not None and -0.1<=age<=2: new.append(p)
            if p["key"] not in saved or rank(p)>rank(saved[p["key"]]):saved[p["key"]]=p
        newest=max((p for p in saved.values() if p.get("channel")==channel and parse_dt(p.get("utc"))),
                    key=lambda p:parse_dt(p["utc"]),default=None)
        dt=parse_dt(newest["utc"]) if newest else None
        reachable=hs["ok"] or rs["ok"]
        freshness=bool(dt and -timedelta(minutes=5)<=now-dt<=timedelta(hours=24))
        snapshot[channel]={"state":"recent_post_verified" if freshness else "reachable_but_freshness_not_established" if reachable else "source_read_failed",
                           "latest_utc":newest["utc"] if newest else None,"latest_url":newest["url"] if newest else None,
                           "methods":{"public_html":hs,"rsshub":rs}}
    cutoff=now-timedelta(days=45)
    archive=sorted((p for p in saved.values() if parse_dt(p.get("utc")) and parse_dt(p["utc"])>=cutoff),
                  key=lambda p:(p["utc"],p["key"]))
    new.sort(key=lambda p:(p["utc"],p["key"]))
    latest={"checked_at_utc":now.isoformat(),"baseline_only":first,"channels":snapshot,
            "new_posts":new[-100:],"new_post_count":len(new),"archive_45d_count":len(archive),
            "data_source":"public Telegram pages and RSSHub; NOT official Greeks.live Data Lab",
            "note":"No new posts is not a data outage. A green workflow does not prove a fresh source.",
            "source_freshness_confirmed":any(v["state"]=="recent_post_verified" for v in snapshot.values())}
    json_write(history_path,archive);json_write(folder/"latest.json",latest)
    print(json.dumps({"new_post_count":len(new),"channels":{c:v["state"] for c,v in snapshot.items()}},ensure_ascii=False))
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",default="data")
    args=parser.parse_args()
    collect(Path(args.data_dir))
