"""v0.6.36: horários das mensagens, rolagem preservada, botão de versão e Linux/macOS."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mesh_analyzer.database import Database, now_ms
from mesh_analyzer.transports import LIVE_CLOCK_SKEW_MS, PacketIngestor, message_timestamp

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
WORKFLOW=(ROOT/".github"/"workflows"/"windows.yml").read_text(encoding="utf-8")


class MessageTimestamps(unittest.TestCase):
    def test_live_skew_uses_local_reception_time(self):
        received=1_800_000_000_000
        self.assertEqual(message_timestamp(received-180_000,received),received)
        self.assertEqual(message_timestamp(received+120_000,received),received)

    def test_history_and_future_are_not_invented(self):
        received=1_800_000_000_000
        old=received-LIVE_CLOCK_SKEW_MS-60_000
        self.assertEqual(message_timestamp(old,received),old)
        self.assertEqual(message_timestamp(received+LIVE_CLOCK_SKEW_MS+60_000,received),received)

    def test_radio_clock_is_persisted_for_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Database(Path(tmp)/"m.sqlite3")
            try:
                ingest=PacketIngestor(db)
                radio_s=int(now_ms()/1000)-180
                ingest.handle(1,{"from":0x1234,"to":0xffffffff,"id":77,"rxTime":radio_s,"channel":0,
                                 "decoded":{"portnum":"TEXT_MESSAGE_APP","text":"oi"}})
                row=db.message_rows()[0]
                self.assertEqual(row["radio_time_ms"],radio_s*1000)
                self.assertLess(abs(row["timestamp_ms"]-now_ms()),5000)
            finally:
                db.close()

    def test_ui_has_distinct_labels_and_future_guard(self):
        label=HTML[HTML.index("function messageTimeLabel("):HTML.index("function messageTimeHtml(")]
        self.assertIn("horário à frente do relógio deste computador",label)
        self.assertIn("function refreshMessageTimes(",HTML)
        self.assertIn("relógio do rádio: ",HTML)


class ChatScroll(unittest.TestCase):
    def test_refresh_does_not_force_scroll(self):
        chat=HTML[HTML.index("function renderChat("):HTML.index("const choices=txRadioSources();",HTML.index("function renderChat("))]
        self.assertIn("if(signature===chatRenderSignature){refreshMessageTimes();}",chat)
        self.assertIn("if(switched||atBottom){box.scrollTop=box.scrollHeight;",chat)
        self.assertIn("$('bubblesNewMessages').hidden=false;",chat)
        self.assertNotIn("$('bubbles').scrollTop=$('bubbles').scrollHeight;",chat)
        self.assertIn('id="bubblesNewMessages"',HTML)


class UpdateButton(unittest.TestCase):
    def test_label_has_no_version_number(self):
        state=HTML[HTML.index("function updateVersionState(info){"):HTML.index("btn.textContent=label;")]
        self.assertIn("label='Nova Versão'",state)
        self.assertIn("label='Atualizado'",state)
        self.assertNotIn("'NOVA VERSÃO v'",state)
        self.assertNotIn("' · ATUALIZADO'",state)

    def test_direct_update_only_on_windows(self):
        from mesh_analyzer.app import ReleaseMonitor
        db=mock.Mock();db.system_settings.return_value={"update_minutes":15}
        with mock.patch("mesh_analyzer.app.os.name","posix"):
            self.assertFalse(ReleaseMonitor(db).status()["direct_update"])
        self.assertIn("monitorState.direct_update===false",HTML)


class Platforms(unittest.TestCase):
    def test_linux_and_macos_packages_published_without_source_zip(self):
        for name in ("Linux-x64.tar.gz","macOS-arm64.dmg","macOS-x64.dmg"):
            self.assertIn(name,WORKFLOW)
        self.assertIn("needs: [package-win10-win11, package-linux, package-macos]",WORKFLOW)
        self.assertNotIn("Codigo-Fonte",WORKFLOW)
        self.assertIn("NSBluetoothAlwaysUsageDescription",WORKFLOW)
        self.assertTrue((ROOT/"linux"/"instalar.sh").is_file())


if __name__=="__main__":
    unittest.main()
