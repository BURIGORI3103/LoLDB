"""折りたたみを含むwiki相性欄を、対象群・説明・敵味方別に集計する。"""
import concurrent.futures
import argparse
import json
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

from tqdm import tqdm

BASE = Path(__file__).resolve().parent
CACHE = BASE.parent / "scratch/wiki_matchup_html"


class MatchupHTML(HTMLParser):
    """非表示CSSに関係なく相性セクションの順序と画像IDを保持する。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.body = False
        self.heading = None
        self.heading_text = []
        self.active = False
        self.parts = []
        self.anchor = ""
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "body":
            self.body = True
        if not self.body:
            return
        if tag in ("script", "style"):
            self.skip += 1
        if self.skip:
            return
        if tag in ("h2", "h3"):
            self.heading = tag
            self.heading_text = []
        if self.heading and tag == "a" and attrs.get("class") == "anchor_super":
            self.pending_anchor = attrs.get("id", "")
        if not self.active or self.heading:
            return
        if tag in ("br", "p", "strong", "em", "li", "div", "tr"):
            self.parts.append("\n")
        if tag == "img":
            match = re.search(r"/ico_([^/.]+)\.(?:jpg|png|webp)", attrs.get("src", ""), re.I)
            if match:
                self.parts.append("[[" + match.group(1) + "]]")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if self.skip:
            return
        if tag == self.heading:
            text = "".join(self.heading_text)
            self.active = "相性" in text and ("対策" in text or "カウンター" in text)
            if self.active:
                self.anchor = getattr(self, "pending_anchor", "")
            self.heading = None
        if self.active and tag in ("p", "strong", "em", "li", "div", "tr"):
            self.parts.append("\n")

    def handle_data(self, text):
        if self.skip:
            return
        if self.heading:
            self.heading_text.append(text)
        elif self.active:
            self.parts.append(text)


def parse_matchups(html, names):
    parser = MatchupHTML()
    parser.feed(html)
    normalize = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    lookup = {normalize(cid): cid for cid in names}
    lookup.update({"wukong": "MonkeyKing", "renataglasc": "Renata"})
    relation, advantage = "enemy", None
    records, pending = [], None

    def flush():
        nonlocal pending
        if pending:
            text = re.sub(r"\s+", " ", " ".join(pending.pop("parts"))).strip()
            if len(text) >= 15:
                pending["text"] = text
                pending["has_caveat"] = any(x in text for x in ("ただし", "但し", "例外", "一部", "除く"))
                records.append(pending)
            pending = None

    for line in (re.sub(r"[ \t\r]+", " ", x).strip() for x in "".join(parser.parts).split("\n")):
        if not line:
            continue
        if "敵との相性" in line or "味方との相性" in line:
            flush()
            relation = "ally" if "味方" in line else "enemy"
            advantage = None
            continue
        if re.match(r"^(?:(?:有利|不利|良い|悪い)\s*(?:[（(]|$)|Strong\s+(?:Against|With)|Weak\s+(?:Against|With))", line, re.I) and "[[" not in line:
            flush()
            advantage = "unfavorable" if re.match(r"不利|悪い|Weak", line, re.I) else "favorable"
            if re.search(r"With", line, re.I):
                relation = "ally"
            elif re.search(r"Against", line, re.I):
                relation = "enemy"
            continue
        head = re.match(r"^(?P<prefix>(?:(?:共通|(?:TOP|MID|JG|JUG|ADC|SUP)(?:運用)?)\s*[:：]\s*)?)(?P<icons>(?:\[\[[^\]]+\]\]\s*)+)(?P<label>.*)$", line, re.I)
        if head and advantage:
            flush()
            ids = [lookup.get(normalize(x)) for x in re.findall(r"\[\[([^\]]+)\]\]", head["icons"])]
            ids = list(dict.fromkeys(x for x in ids if x))
            if ids:
                pending = {"relation": relation, "advantage": advantage, "champion_ids": ids,
                           "label": (head["prefix"] + head["label"].strip(" /")).strip(), "parts": []}
        elif pending:
            line = re.sub(r"\[\[([^\]]+)\]\]", lambda m: names.get(lookup.get(normalize(m[1])), m[1]), line)
            pending["parts"].append(line)
    flush()
    return records, parser.anchor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="保存済みHTMLを使わず全ページを再取得")
    args = parser.parse_args()
    champions = json.loads((BASE / "merged_data/all_champions.json").read_text(encoding="utf-8"))
    names = {cid: c["name"] for cid, c in champions.items()}
    CACHE.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

    def fetch(item):
        cid, c = item
        url = c["wiki_info"]["source_url"].split("#")[0]
        cache = CACHE / (cid + ".html")
        try:
            if cache.exists() and not args.refresh:
                html = cache.read_text(encoding="utf-8")
            else:
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 LoLDB/2.7"})
                        with urllib.request.urlopen(req, timeout=20) as response:
                            html = response.read().decode("utf-8")
                        cache.write_text(html, encoding="utf-8")
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(1)
            records, anchor = parse_matchups(html, names)
            return cid, {"status": "extracted" if records else "no_structured_entries", "source_url": url + ("#" + anchor if anchor else ""),
                         "fetched_at": datetime.fromtimestamp(cache.stat().st_mtime, timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
                         "extracted_at": now, "scope": "wiki_general_not_role_specific", "patch_verified": False, "groups": records}
        except Exception as error:
            return cid, {"status": "failed", "source_url": url, "error": str(error), "groups": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        collected = dict(tqdm(pool.map(fetch, champions.items()), total=len(champions), desc="wiki相性欄を集計"))
    (BASE / "data/wiki_matchups.json").write_text(json.dumps(collected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for cid, c in tqdm(champions.items(), desc="相性資料をアプリデータへ同期"):
        c["wiki_matchups"] = collected[cid]
        (BASE / "merged_data" / (cid + ".json")).write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    (BASE / "merged_data/all_champions.json").write_text(json.dumps(champions, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"pages": len(collected), "with_entries": sum(bool(v["groups"]) for v in collected.values()),
               "failed": [cid for cid, v in collected.items() if v["status"] == "failed"],
               "no_structured_entries": [cid for cid, v in collected.items() if v["status"] == "no_structured_entries"],
               "groups": sum(len(v["groups"]) for v in collected.values()),
               "enemy_pairs": sum(len(g["champion_ids"]) for v in collected.values() for g in v["groups"] if g["relation"] == "enemy"),
               "ally_pairs": sum(len(g["champion_ids"]) for v in collected.values() for g in v["groups"] if g["relation"] == "ally")}
    (BASE / "docs/wiki_matchup_collection_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
