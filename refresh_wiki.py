"""公式一覧から参照URLを再生成し、wikiの考察・対策を再取得する。"""
import json
import argparse
import html as html_module
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

from tqdm import tqdm

BASE = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
ALIASES = {"MonkeyKing": "wukong", "Renata": "renata"}


def wiki_url_map():
    req = urllib.request.Request("https://www.loljp-wiki.jp/wiki/?Champion", headers={"User-Agent": "Mozilla/5.0 LoLDB/2.6"})
    with urllib.request.urlopen(req, timeout=15) as response:
        html = response.read().decode("utf-8")
    result = {}
    for link in re.findall(r'href="([^\"]+)"', html):
        if not link.startswith("./?Champion/") or "#" in link:
            continue
        page = urllib.parse.unquote_plus(html_module.unescape(link).split("?", 1)[1])
        key = re.sub(r"[^a-z0-9]", "", page.split("/", 1)[1].lower())
        result[key] = "https://www.loljp-wiki.jp/wiki/?" + urllib.parse.quote(page, safe="/")
    if len(result) < 160:
        raise ValueError("wiki索引のチャンピオンリンクが不足しています")
    return result


class WikiSections(HTMLParser):
    """ナビゲーションを除外し、本文の見出し単位でテキストを収集する。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.heading = None
        self.heading_parts = []
        self.current = None
        self.sections = {}
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "body":
            self.in_body = True
        if not self.in_body:
            return
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("h2", "h3", "h4"):
            self.heading = tag
            self.heading_parts = []
        if tag in ("p", "li", "br", "tr", "div") and self.current:
            self.sections[self.current].append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag == self.heading:
            self.current = re.sub(r"\s+", " ", "".join(self.heading_parts)).strip()
            self.sections.setdefault(self.current, [])
            self.heading = None
        if tag in ("p", "li", "tr", "div") and self.current:
            self.sections[self.current].append(" ")

    def handle_data(self, data):
        if not self.in_body or self.skip:
            return
        if self.heading:
            self.heading_parts.append(data)
        elif self.current:
            self.sections[self.current].append(data)


def parse_wiki(html):
    parser = WikiSections()
    parser.feed(html)
    selected = {}
    for heading, parts in parser.sections.items():
        if any(term in heading for term in ("考察", "相性・対策", "立ち回り")):
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            if len(text) >= 30:
                selected[heading] = text[:120]
    if not selected:
        raise ValueError("考察・対策の本文が見つかりません（未作成・構造変更の可能性）")
    return selected


def fetch_wiki(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 LoLDB/2.6"})
    with urllib.request.urlopen(req, timeout=15) as response:
        html = response.read().decode("utf-8")
        final_url = response.url
    return {"source_url": final_url, "fetched_at": datetime.now(JST).isoformat(timespec="seconds"),
            "status": "success", "sections": parse_wiki(html),
            "patch_verified": False}


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-failed", action="store_true", help="直前に失敗したwikiだけ再取得")
    args = parser.parse_args()
    from merge_data import find_strategy_file
    wiki_urls = wiki_url_map()
    report_path = BASE / "docs/wiki_refresh_report.json"
    previous = {r["champion_id"]: r for r in json.loads(report_path.read_text(encoding="utf-8"))} if args.retry_failed and report_path.exists() else {}
    md_path = BASE / "docs/LoL_URL_list.md"
    old = md_path.read_text(encoding="utf-8")
    checked = set(re.findall(r"^- \[x\].*?\(([^)]+)\)", old, re.M))
    records = []
    lines = ["参照元：Riot Data Dragonの公式チャンピオン一覧", "wiki取得成功はOP.GGのチェックとは別にdocs/wiki_refresh_report.jsonで管理する。", ""]
    for path in sorted((BASE / "champions_data").glob("*.json")):
        champ = json.loads(path.read_text(encoding="utf-8"))
        cid = champ["id"]
        slug = ALIASES.get(cid, cid.lower())
        prior_slug = "renataglasc" if cid == "Renata" else slug
        mark = "x" if prior_slug in checked else " "
        wiki_key = {"MonkeyKing": "wukong", "Renata": "renataglasc", "Nunu": "nunuwillump"}.get(cid, cid.lower())
        wiki = wiki_urls.get(wiki_key)
        if not wiki:
            raise ValueError(f"wiki索引に対応URLがありません: {cid}")
        lines.extend([f"- [{mark}] {champ['name']} ({slug})", f"  OP.GG: https://www.op.gg/champions/{slug}/build", f"  wiki: {wiki}"])
        records.append((cid, champ["name"], slug, wiki))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"URLリストを公式一覧の{len(records)}体で再生成しました。", flush=True)
    report = []
    for cid, name, slug, url in tqdm(records, desc="wiki再取得", unit="体"):
        result = {"champion_id": cid, "name": name, "source_url": url}
        try:
            if previous.get(cid, {}).get("status") == "success":
                result = previous[cid]
            else:
                result.update(fetch_wiki(url))
        except Exception as error:
            result.update(status="failed", error=str(error))
        target = find_strategy_file(str(BASE / "strategy_data"), cid)
        if target:
            path = Path(target)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["name"] = name
            data["wiki_info"] = result
            # 取得失敗を汎用文で成功に見せず、wiki原文抜粋は出典付きの独立欄に保持する。
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report.append(result)
        if previous.get(cid, {}).get("status") != "success":
            time.sleep(0.3)
    (BASE / "docs/wiki_refresh_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    successes = sum(r["status"] == "success" for r in report)
    print(f"wiki再取得: 成功{successes}件、失敗{len(report)-successes}件", flush=True)


if __name__ == "__main__":
    run()
