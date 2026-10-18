"""Favorite and node-list regressions for the v0.6.33 Meshtastic UI."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mesh_analyzer.database import Database
from mesh_analyzer.transports import SourceManager

HTML=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


class LocalNode:
    def __init__(self):self.calls=[]
    def setFavorite(self,num):self.calls.append(("set",num))
    def removeFavorite(self,num):self.calls.append(("remove",num))


class FavoriteRadioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.temp.name)/"mesh.db")
        self.db.upsert_node(42,1,timestamp_ms=1730000000000,long_name="Nó de teste")
        self.source=self.db.source
        self.db.source=lambda sid:{"id":sid,"enabled":True,"kind":"serial"}
        self.sources=SourceManager(self.db)
        self.local=LocalNode()
        self.iface=SimpleNamespace(localNode=self.local,nodesByNum={42:{"num":42,"isFavorite":False}})
        self.sources._interfaces[1]=self.iface
        self.sources._states[1]={"status":"connected"}
    def tearDown(self):
        self.db.source=self.source
        self.db._db.close()
        self.temp.cleanup()

    def test_favorite_command_does_not_fabricate_confirmation(self):
        res=self.sources.set_favorite(1,42,True)
        self.assertTrue(res["success"])
        self.assertFalse(res["confirmed"])
        self.assertEqual(res["status"],"awaiting_nodedb")
        self.assertEqual(self.local.calls,[("set",42)])
        self.assertEqual(self.db.node_rows()[0]["favorite_source_ids"],[])
        self.iface.nodesByNum[42]["isFavorite"]=True
        self.sources.sync_favorites_from_radio(1)
        self.assertEqual(self.db.node_rows()[0]["favorite_source_ids"],[1])
        self.assertEqual(self.sources.set_favorite(1,42,True)["status"],"confirmed")

    def test_unfavorite_updates_only_after_radio_reports(self):
        self.iface.nodesByNum[42]["isFavorite"]=True
        self.sources.sync_favorites_from_radio(1)
        res=self.sources.set_favorite(1,42,False)
        self.assertFalse(res["confirmed"])
        self.assertEqual(self.db.node_rows()[0]["favorite_source_ids"],[1])
        self.assertEqual(self.local.calls[-1],("remove",42))
        self.iface.nodesByNum[42]["isFavorite"]=False
        self.sources.sync_favorites_from_radio(1)
        self.assertEqual(self.db.node_rows()[0]["favorite_source_ids"],[])
        self.assertEqual(self.db.node_rows()[0]["favorite_known_source_ids"],[1])

    def test_missing_radio_unsupported_and_invalid_input(self):
        with self.assertRaises(ValueError):
            self.sources.set_favorite(1,42,1)
        with self.assertRaises(ValueError):
            self.sources.set_favorite(1,0,True)
        self.sources._states[1]["status"]="disconnected"
        with self.assertRaisesRegex(RuntimeError,"desconectado"):
            self.sources.set_favorite(1,42,True)
        self.sources._states[1]["status"]="connected"
        self.iface.localNode=object()
        with self.assertRaisesRegex(RuntimeError,"não oferece"):
            self.sources.set_favorite(1,42,True)
        self.db.source=lambda sid:{"id":sid,"enabled":True,"kind":"mqtt"}
        with self.assertRaisesRegex(ValueError,"local"):
            self.sources.set_favorite(1,42,True)

    def test_no_radio_favorites_fabricated_without_explicit_flag(self):
        self.iface.nodesByNum[42].pop("isFavorite")
        self.sources.sync_favorites_from_radio(1)
        self.assertEqual(self.db.node_rows()[0]["favorite_known_source_ids"],[])

    def test_favorites_are_visible_and_actionable_in_nodes(self):
        for marker in (
            'data-favorite-toggle', "function favoriteRadio()", "function favoriteNodeState(",
            "async function setFavoriteForNode(", "/api/nodes/favorite",
            "case 'favorite':await setFavoriteForNode",
            "Favoritar no rádio", "Desfavoritar no rádio",
            "favorite_source_ids", "favorite_known_source_ids",
        ):
            self.assertIn(marker,HTML)
        self.assertIn("ev.stopPropagation()",HTML)
        self.assertIn("Aguardando confirmação do NodeDB",HTML)
