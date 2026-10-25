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
            self.assertIn('0.1.0',root.title())
        finally:root.destroy()

if __name__=='__main__':unittest.main()
