import tkinter as tk
import unittest
from achievement_extractor.gui import App

class GuiTests(unittest.TestCase):
    def test_independent_window_and_partial_catalog_can_be_reviewed(self):
        root=tk.Tk();root.withdraw()
        try:
            app=App(root)
            app.result={'entries':[{'source_id':'OWN_FIRST','title':'OWN_FIRST','description':'','hidden':False,'icon':'','review':['title','description'],'selected':True,'evidence':[]}],'warnings':[]}
            app.refresh();root.update_idletasks()
            self.assertEqual(len(app.table.get_children()),1)
            app.table.selection_set('0');app.toggle()
            self.assertFalse(app.result['entries'][0]['selected'])
            self.assertIn('descrição',app.table.item('0','values')[-1])
            self.assertIn('0.3.0',root.title())
        finally:root.destroy()

    def test_persistent_official_mode_cannot_include_an_unconfirmed_row(self):
        root=tk.Tk();root.withdraw()
        try:
            app=App(root);self.assertTrue(app.official_only.get())
            app.result={'entries':[dict(source_id=i,title=i,description='',hidden=False,icon='',
                review=[],selected=True,evidence=[])for i in ('OFFICIAL','LOCAL_ONLY')],
                'official_lookup':{'appid':'123','matched_ids':['OFFICIAL']},'warnings':[]}
            app.refresh();self.assertFalse(app.result['entries'][1]['selected'])
            app.table.selection_set('1');app.toggle();self.assertFalse(app.result['entries'][1]['selected'])
            app.official_only.set(False);app.table.selection_set('1');app.toggle();self.assertTrue(app.result['entries'][1]['selected'])
            app.official_only.set(True);app.official_mode_changed();self.assertFalse(app.result['entries'][1]['selected'])
        finally:root.destroy()

if __name__=='__main__':unittest.main()
