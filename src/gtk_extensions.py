from gi.repository import Gtk

class Menu(Gtk.Menu):

    def add_entry(self, label, action, stock_id=None):
        if stock_id == None:
            mitem = Gtk.MenuItem(label)
        else:
            mimage = Gtk.Image()
            mimage.set_from_stock(stock_id, Gtk.IconSize.MENU)
            mitem = Gtk.ImageMenuItem(label, image=mimage)

        mitem.connect("activate", action)
        self.append(mitem)

    def add_separator(self):
        self.append(Gtk.SeparatorMenuItem())
