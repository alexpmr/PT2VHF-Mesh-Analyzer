"""Regression tests for persistent UI settings and conservative analytics."""
import tempfile
import unittest
from pathlib import Path

from mesh_analyzer.database import Database,now_ms
from mesh_analyzer.analytics import calculate


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"mesh.sqlite3"
        self.db=Database(self.path)
    def tearDown(self):
        self.db.close();self.tmp.cleanup()

    def test_map_preferences_persist_across_reopen(self):
        settings={"mapWindow":"7d","mapMinObservations":"3","mapRfColor":"#ffe100",
                  "mapShowLinksSetting":False,"soundTheme":"arcade"}
        received=self.db.save_ui_preferences(settings)
        self.assertEqual(received["mapWindow"],"7d")
        self.assertFalse(received["mapShowLinksSetting"])
        self.db.close()
        self.db=Database(self.path)
        self.assertEqual(self.db.ui_preferences()["mapMinObservations"],"3")
        self.assertEqual(self.db.ui_preferences()["mapRfColor"],"#ffe100")

    def test_map_rejects_bad_colors_and_sizes(self):
        cases=[{"mapRfColor":"javascript:alert(1)"},{"mapMinObservations":-4},
               {"mapWindow":"6 months"},{"mapType":"http://attacker.test"},
               {"mapBrightness":500},{"unknown":"bad"}]
        for data in cases:
            with self.subTest(data=data),self.assertRaises(ValueError):
                self.db.save_ui_preferences(data)
        self.assertEqual(self.db.ui_preferences(),{})

    def test_traceroutes_not_in_direct_rf_ranking(self):
        now=now_ms()
        self.db.upsert_node(100,1,timestamp_ms=now,latitude=-15.7,longitude=-47.8)
        self.db.upsert_node(200,1,timestamp_ms=now,latitude=-15.8,longitude=-47.9)
        self.db.add_link(1,100,200,now,"observed_route_unverified_rf")
        result=calculate(self.db,{"period":"all"})
        self.assertEqual(result["direct_rf_rank"],[])
        self.assertEqual(result["counts"]["confirmed_direct_rf"],None)
        self.assertEqual(result["counts"]["tx_observations"],None)


if __name__=="__main__":unittest.main()
