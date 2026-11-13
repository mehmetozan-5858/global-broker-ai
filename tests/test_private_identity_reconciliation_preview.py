import unittest
from src.private_identity_reconciliation_preview import (
    analyze_collision_rekey,draft_namespaced_identifier,
)

class IdentityReconciliationPreviewTests(unittest.TestCase):
    def test_cross_source_collision_never_automatically_rekeys(self):
        rows=[{'opportunity_id':'123','source':'official-A','lot':'A'},
              {'opportunity_id':'123','source':'official-B','lot':'B'}]
        original=[dict(row) for row in rows]
        result=analyze_collision_rekey(rows)
        self.assertFalse(result['safe_to_apply'])
        self.assertEqual(result['cross_source_groups'],1)
        self.assertEqual(rows,original)
        self.assertNotIn('123',str(result))
    def test_same_source_duplicate_is_not_fixed_by_source_namespace(self):
        result=analyze_collision_rekey([
         {'opportunity_id':'n','source':'official-A'},
         {'opportunity_id':'n','source':'official-A'}])
        self.assertEqual(result['same_source_groups'],1)
        self.assertFalse(result['safe_to_apply'])
    def test_different_sources_and_lots_generate_distinct_preview_only(self):
        a=draft_namespaced_identifier(source_key='a',notice_id='n')
        b=draft_namespaced_identifier(source_key='b',notice_id='n')
        c=draft_namespaced_identifier(source_key='a',notice_id='n',lot_id='2')
        self.assertNotEqual(a,b)
        self.assertNotEqual(a,c)
        self.assertEqual(a,draft_namespaced_identifier(source_key='a',notice_id='n'))
    def test_missing_source_or_notice_blocks_preview(self):
        for source,notice,lot in [('', 'n',None),('s','',None),('s','n','')]:
            self.assertIsNone(draft_namespaced_identifier(source_key=source,notice_id=notice,lot_id=lot))
        self.assertFalse(analyze_collision_rekey([{'opportunity_id':'n'}])['safe_to_apply'])
if __name__=='__main__':
    unittest.main()
