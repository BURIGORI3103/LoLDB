"""wiki本文と偽の成功を区別する回帰テスト。"""
import unittest
from refresh_wiki import parse_wiki


class WikiTests(unittest.TestCase):
    def test_real_section_and_navigation(self):
        html = '<h2>考察</h2>ナビゲーション<div id="body"><h2>考察</h2><p>' + '本文の立ち回り説明。' * 8 + '</p><h2>コメント</h2>コメントは除外'
        result = parse_wiki(html)
        self.assertIn('考察', result)
        self.assertNotIn('ナビゲーション', result['考察'])
        self.assertNotIn('コメント', result['考察'])

    def test_parked_or_missing_page_is_failure(self):
        for html in ('<title>loljp-wiki.tk</title>', '<div id="body"><h2>編集</h2>新規作成</div>'):
            with self.assertRaises(ValueError):
                parse_wiki(html)
