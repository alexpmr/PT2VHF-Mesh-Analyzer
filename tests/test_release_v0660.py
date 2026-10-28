"""v0.6.60: aviso do site oficial sempre na abertura, sem atrapalhar o aviso de versão nova."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


class OfficialSiteNotice(unittest.TestCase):
    def notice_js(self):
        return HTML[HTML.index("const OFFICIAL_NOTICE_TRANSLATIONS="):HTML.index("function notify(")]

    def test_shown_on_every_start_without_opt_out(self):
        js=self.notice_js()
        self.assertNotIn("localStorage",js)
        self.assertNotIn("sessionStorage",js)
        box=HTML[HTML.index('<div id="officialSiteNotice"'):HTML.index("</div>",HTML.index('id="officialSiteNoticeClose"'))]
        self.assertNotIn('type="checkbox"',box)
        self.assertIn('href="https://www.pt2vhf.com/mesh"',box)
        self.assertIn("document.addEventListener('pywebviewready',scheduleOfficialSiteNotice,{once:true});",js)

    def test_update_prompt_waits_for_notice(self):
        prompt=HTML[HTML.index("function maybePromptUpdate(info){"):HTML.index("function showUpdateDialog(")]
        self.assertIn("officialSiteNoticeOpen()){setTimeout(()=>maybePromptUpdate(monitorState),5000);return;}",prompt)
        # Em sequência: ao fechar o aviso, o aviso de versão nova abre na hora.
        self.assertIn("function closeOfficialSiteNotice(){$('officialSiteNotice').classList.remove('open');maybePromptUpdate(monitorState);}",HTML)
        self.assertIn("function officialSiteNoticeOpen(){return $('officialSiteNotice').classList.contains('open');}",HTML)

    def test_version(self):
        from mesh_analyzer import __version__
        self.assertEqual(__version__,"0.6.60")
        self.assertEqual((ROOT/"VERSION").read_text().strip(),"0.6.60")


if __name__=="__main__":
    unittest.main()
