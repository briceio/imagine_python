# gtk_extensions.py
#
# Copyright 2021 Brice MARTIN
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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
