"""v0.6.33: chat UX and About regressions, radio-sourced favorite cache."""
import tempfile
import unittest
from pathlib import Path

from mesh_analyzer.database import Database

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


class MessagingAndAbout(unittest.TestCase):
    def test_about_contact_matches_reference_and_preserves_help(self):
        start=HTML.index('<section class="view" id="viewAbout">')
        end=HTML.index('<section class="view" id="viewHelp">',start)
        banner=HTML[start:end]
        for literal in (
            'DÚVIDAS, DIFICULDADES OU SUGESTÕES?',
            'Fale comigo',
            'Se precisar de ajuda para configurar o programa, encontrou algum problema',
            'entre em contato.',
            'Alex',
            'href="https://wa.me/5561984023634"',
            'WhatsApp: 61 98402-3634',
            'href="mailto:alexpmr@gmail.com"'
        ):
            self.assertIn(literal,banner)
        self.assertIn("about:'/sobre'",HTML)
        self.assertIn("['/ajuda','help']",HTML)
        self.assertIn('data-view="help">Ajuda</button>',HTML)

    def test_emojis_reply_retry_and_rate_limits(self):
        for literal in ('id="messageEmojiPicker"','id="messageEmojiButton"',
                        'id="messageByteCount"', 'id="messageReplyAction"',
                        'id="messageRetryAction"', 'function replyText(',
                        'function sendChatMessage(', 'messageBytes(text)',
                        "new TextEncoder().encode", "bytes>220",
                        "['failed','rejected','timeout']", 'confirm(\'Reenviar mensagem?'):
            self.assertIn(literal,HTML)
        self.assertIn("['nodeinfo','NodeInfo']",HTML)

    def test_pinned_primary_and_favorites_only_from_real_radio_flags(self):
        self.assertIn('id="contactPinned"',HTML)
        self.assertIn('contactMarkup(\'channel:0\')',HTML)
        # v0.6.38 (#157): lista única de favoritos do aplicativo.
        self.assertIn("nodes.filter(n=>n.favorite)",HTML)
        self.assertIn("★ Favoritos",HTML)

    def test_favorite_cache_is_source_scoped_and_only_accepts_bools(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Database(Path(folder)/"state.sqlite3")
            try:
                db.upsert_node(42,1,timestamp_ms=1730000000000,long_name="Nodo 42")
                self.assertEqual(db.node_rows()[0]["favorite_source_ids"],[])
                self.assertFalse(db.set_node_favorite_from_radio(1,42,None))
                self.assertFalse(db.set_node_favorite_from_radio(1,42,1))
                self.assertTrue(db.set_node_favorite_from_radio(1,42,True))
                self.assertEqual(db.node_rows()[0]["favorite_source_ids"],[1])
                self.assertTrue(db.set_node_favorite_from_radio(2,42,True))
                self.assertEqual(set(db.node_rows()[0]["favorite_source_ids"]),{1,2})
                db.set_node_favorite_from_radio(1,42,False)
                self.assertEqual(db.node_rows()[0]["favorite_source_ids"],[2])
                db._db.close()
                reopened=Database(Path(folder)/"state.sqlite3")
                try:self.assertEqual(reopened.node_rows()[0]["favorite_source_ids"],[2])
                finally:reopened._db.close()
            finally:
                try:db._db.close()
                except Exception:pass
