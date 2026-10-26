import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from port_station.gui import App

class IntegrationTests(unittest.TestCase):
    def test_embedded_extractor_prefills_and_applies_without_changing_theme_or_adapter(self):
        root=tk.Tk();root.withdraw()
        try:
            app=App(root);app.var('game_dir').set(str(Path(tempfile.gettempdir())));app.var('executable').set('Own.exe')
            style=ttk.Style(root);color=style.lookup('TFrame','background')
            app.extract_achievements();child=app.extractor
            self.assertEqual(child.folder.get(),str(Path(tempfile.gettempdir()).resolve()))
            self.assertEqual(child.exe.get(),'Own.exe')
            self.assertEqual(style.lookup('TFrame','background'),color)
            with tempfile.TemporaryDirectory()as td:
                child.output.set(str(Path(td)/'new-catalog'));child.appid.set('123')
                child.result={'entries':[dict(source_id='OWN_FIRST',title='Primeira',description='Official',hidden=False,
                    icon='',selected=True,evidence=[],review=[])], 'official_lookup':{'appid':'123','matched_ids':['OWN_FIRST']},'warnings':[]}
                with patch('achievement_extractor.gui.messagebox.showerror')as error:child.apply();error.assert_not_called()
                self.assertEqual(app.project['achievements'][0]['id'],'OWN_FIRST')
                self.assertEqual(app.project['achievements'][0]['description'],'Official')
                self.assertEqual(app.var('adapter').get(),'none')
                self.assertTrue((Path(td)/'new-catalog/achievements.json').is_file())
            child.close()
        finally:root.destroy()

if __name__=='__main__':unittest.main()
