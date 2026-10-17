import unittest
from scripts.retain_latest_release import removal_plan


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.latest = {'id':21, 'tag_name':'v0.6.21', 'draft':False, 'prerelease':False,
            'assets':[{'name':name, 'state':'uploaded', 'size':12} for name in (
                'PT2VHF-Mesh-Analyzer-v0.6.21-Setup-Win11-x64.exe',
                'PT2VHF-Mesh-Analyzer-v0.6.21-Portable-Win11-x64.exe', 'SHA256SUMS.txt')]}

    def test_only_older_published_stable_releases_are_removed(self):
        releases=[self.latest, {'id':20,'tag_name':'v0.6.20'},
            {'id':19,'tag_name':'v0.6.19','draft':True},
            {'id':18,'tag_name':'v0.6.18','prerelease':True},
            {'id':17,'tag_name':'experiment'}]
        self.assertEqual([x['id'] for x in removal_plan(self.latest,releases,'v0.6.21')],[20])

    def test_incomplete_latest_preserves_all_previous_downloads(self):
        self.latest['assets'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):
            removal_plan(self.latest,[{'id':20,'tag_name':'v0.6.20'}],'v0.6.21')

    def test_newer_release_or_wrong_build_prevents_deletion(self):
        with self.assertRaises(ValueError):
            removal_plan(self.latest,[{'id':22,'tag_name':'v0.6.22'}],'v0.6.21')
        with self.assertRaises(ValueError):
            removal_plan(self.latest,[],'v0.6.20')

    def test_same_release_id_is_never_deleted(self):
        self.assertEqual(removal_plan(self.latest,[{'id':21,'tag_name':'v0.6.20'}],'v0.6.21'),[])
