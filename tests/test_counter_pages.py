"""対面一覧の勝率の方向、件数上限、ページ取り違えを検証する。"""
import unittest

from refresh_matchup_stats import parse_counter_page
from build_comprehensive_matchups import _enrich_measured_entry


class CounterPageTests(unittest.TestCase):
    def setUp(self):
        self.champions = {"Garen": {"name": "ガレン", "name_en": "Garen"}}
        rows = []
        for i in range(20):
            cid = f"Opponent{i}"
            self.champions[cid] = {"name": f"対面{i}", "name_en": cid}
            rows.append(f'<li><div><img src="/champion/{cid}.png"></div>'
                        f'<div><strong>{40+i}%</strong></div><div>1,234</div></li>')
        self.html = '<h1>Garen Counters for Top, Patch 16.21</h1><ul>' + ''.join(rows) + '</ul>'

    def parse(self, html=None, role="TOP", patch="16.21.1"):
        return parse_counter_page(html or self.html, "Garen", role, patch, self.champions, "https://www.op.gg/")

    def test_top_seven_preserve_player_winrate_and_games(self):
        matchups, available = self.parse()
        self.assertEqual(available, 20)
        self.assertEqual([m['winrate_num'] for m in matchups['favorable']], [59, 58, 57, 56, 55, 54, 53])
        self.assertEqual([m['winrate_num'] for m in matchups['unfavorable']], [40, 41, 42, 43, 44, 45, 46])
        self.assertEqual(matchups['favorable'][0]['games'], 1234)
        self.assertFalse(matchups['favorable'][0]['is_estimated'])

    def test_rejects_wrong_champion_role_patch_or_empty_page(self):
        for kwargs in ({'role': 'MID'}, {'patch': '16.22.1'},
                       {'html': self.html.replace('Garen Counters', 'Jax Counters')},
                       {'html': '<h1>Garen Counters for Top, Patch 16.21</h1>'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.parse(**kwargs)

    def test_shortage_is_not_filled_with_estimates(self):
        html = '<h1>Garen Counters for Top, Patch 16.21</h1>' + self.html.split('<li>')[1].split('</li>')[0]
        matchups, available = self.parse(html.replace('<div>', '<li><div>', 1) + '</li>')
        self.assertEqual(available, 1)
        self.assertEqual(len(matchups['unfavorable']), 1)
        self.assertEqual(matchups['favorable'], [])

    def test_explicit_insufficient_sample_is_empty(self):
        matchups, available = self.parse('<h1>Garen Counters for Top, Patch 16.21</h1><p>Sample size is not large enough.</p>')
        self.assertEqual(available, 0)
        self.assertEqual(matchups, {'favorable': [], 'unfavorable': []})

    def test_normalization_can_repeat_without_reason_evidence(self):
        matchups, _ = self.parse()
        entry = matchups['favorable'][0]
        first = _enrich_measured_entry(entry, 'fav', 'TOP', '16.21.1')
        second = _enrich_measured_entry(first, 'fav', 'TOP', '16.21.1')
        self.assertEqual(first, second)
        self.assertEqual(second['games'], 1234)
        self.assertEqual(second['source_url'], 'https://www.op.gg/')
