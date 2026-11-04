"""正規化、再統合、配布射影と監査後の全件整合性を検証する。"""
import copy
import json
import re
import unittest
from pathlib import Path

from audit_normalization import (canonical_item_ids, is_finished_item, normalize_champion,
                                 normalize_runes, plain_text, project_for_display, rsc_item_groups)

BASE = Path(__file__).resolve().parent.parent


class NormalizationTests(unittest.TestCase):
    def test_plain_text_preserves_breaks_and_removes_executable_content(self):
        self.assertEqual(plain_text('A<br><magicDamage>B</magicDamage><script>bad()</script>&amp;C'), 'A\nB&C')

    def test_transform_is_kept_but_material_and_mode_clone_are_not(self):
        raw = {'3070': {'maps': {'11': True}, 'into': ['3003']},
               '3003': {'maps': {'11': True}, 'from': ['3070']},
               '3040': {'maps': {'11': True}, 'inStore': False, 'specialRecipe': 3003},
               '323040': {'maps': {'11': True}, 'from': ['3070']}}
        allowed = canonical_item_ids(raw)
        self.assertNotIn('323040', allowed)
        self.assertIn('3040', allowed)
        self.assertFalse(is_finished_item('3070', raw, allowed))
        self.assertTrue(is_finished_item('3003', raw, allowed))
        self.assertTrue(is_finished_item('3040', raw, allowed))

    def test_row_references_stay_inside_their_group(self):
        stream = '1:["$","tr","boots_0",{"children":"$L2"}]\n2:{"metaType":"item","metaId":3006}\n3:{"metaType":"item","metaId":3070}'
        self.assertEqual(rsc_item_groups(stream, 'boots'), [['3006']])

    def test_conflicting_rune_parents_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_runes({'primary': {'keystone_name':'a'}, 'secondary': {'choices':['a','b']}}, {'a':'栄華','b':'魔道'})

    def test_normalization_is_idempotent_and_preserves_statistics(self):
        champ = {'id':'Cassiopeia', 'roles':['MID'], 'patch':'16.21.1', 'build':{'boots':[{'item_id':'3020'}]},
                 'matchups':{'favorable':[{'winrate':53.2,'games':150}]},
                 'gameplay_notes':{'laning':'【序盤】 【序盤】 本文'}, 'role_data':{'MID':{'build':{'boots':[]}}}}
        once = normalize_champion(champ, {})
        self.assertEqual(once, normalize_champion(once, {}))
        self.assertEqual(once['matchups'], champ['matchups'])
        self.assertEqual(once['gameplay_notes']['laning'], '本文')
        self.assertEqual(champ['build']['boots'], [{'item_id':'3020'}])


class CompleteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.champs = json.loads((BASE/'merged_data/all_champions.json').read_text(encoding='utf-8'))
        cls.items = json.loads((BASE/'merged_data/all_items.json').read_text(encoding='utf-8'))
        cls.parents = json.loads((BASE/'data/rune_reference.json').read_text(encoding='utf-8'))['parents']

    def test_all_rune_paths_match_the_actual_choices(self):
        for cid, champ in self.champs.items():
            for role, data in [('primary',champ), *champ['role_data'].items()]:
                expected = normalize_runes(data['runes'], self.parents)
                self.assertEqual(data['runes'], expected, (cid,role))

    def test_all_build_references_exist_and_core_is_finished(self):
        for cid, champ in self.champs.items():
            for role, data in [('primary',champ), *champ['role_data'].items()]:
                for key in ('starter','boots','core','situational'):
                    for item in data['build'].get(key,[]):
                        self.assertIn(item['item_id'],self.items,(cid,role,key,item))
                for item in data['build']['core']:
                    self.assertTrue(is_finished_item(item['item_id'],self.items,set(self.items)),(cid,role,item))

    def test_individuals_and_descriptions_match_master(self):
        for cid, champ in self.champs.items():
            self.assertEqual(champ,json.loads((BASE/'merged_data'/f'{cid}.json').read_text(encoding='utf-8')),cid)
            for skill in champ['abilities']+champ['spells']:
                self.assertNotRegex(skill['description'],r'<[^>]+>')
            for data in [champ,*champ['role_data'].values()]:
                for text in data.get('gameplay_notes',{}).values():
                    self.assertFalse(text.startswith('【'),cid)
                for pattern in data.get('build_patterns',[]):
                    self.assertRegex(pattern['name'],r'^\[(AD|AP|TANK|HYBRID)\] ')

    def test_three_new_roles_have_evidence_and_no_invented_levels(self):
        for cid,role in [('Lux','ADC'),('Sion','MID'),('Tristana','MID')]:
            data=self.champs[cid]['role_data'][role]
            for key in ('gameplay_notes','combos','skill_order','skill_matrix'):
                self.assertTrue(data[key])
                self.assertTrue(data['guidance_sources'][key]['source_url'].startswith('https://'))
            self.assertEqual(sorted(level for values in data['skill_matrix'].values() for level in values),list(range(1,16)))

    def test_display_projection_keeps_all_role_data_and_skills(self):
        before=copy.deepcopy(self.champs)
        result=project_for_display(self.champs)
        self.assertEqual(before,self.champs)
        for cid,champ in result.items():
            self.assertEqual(champ['abilities'],before[cid]['abilities'])
            self.assertEqual(champ['spells'],before[cid]['spells'])
            for role,rd in champ['role_data'].items():
                restored={**champ.get('common_role_data',{}),**rd}
                for key in ('build','runes','matchups','combos','gameplay_notes','skill_order','skill_matrix'):
                    self.assertEqual(restored.get(key),before[cid]['role_data'][role].get(key),(cid,role,key))

    def test_remerge_preserves_current_statistics_and_guidance(self):
        from merge_data import merge_record, find_strategy_file
        for cid, previous in self.champs.items():
            base=json.loads((BASE/'champions_data'/f'{cid}.json').read_text(encoding='utf-8'))
            strategy=json.loads(Path(find_strategy_file(str(BASE/'strategy_data'),cid)).read_text(encoding='utf-8'))
            actual=merge_record(base,strategy,previous)
            for role,rd in previous['role_data'].items():
                for field in ('matchups','combos','gameplay_notes','skill_order','skill_matrix'):
                    self.assertEqual(actual['role_data'][role].get(field),rd.get(field),(cid,role,field))


if __name__ == '__main__':
    unittest.main()
