# history.py
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


from gi.repository import Gio, GLib, GObject

class Snapshot(GObject.GObject):

    description = GObject.Property(type=str)

    def __init__(self, description, rollback):
        GObject.GObject.__init__(self)

        self.description = description
        self.rollback = rollback

class History(GObject.GObject):

    def __init__(self):
        GObject.GObject.__init__(self)

        # snapshots
        self.snapshots = Gio.ListStore()

        # rollbacking
        self._rollbacking = False

    def snapshot(self, description, rollback):
        if not self._rollbacking:
            self.snapshots.insert(0, Snapshot(description, rollback))

    def undo(self):
        self.rollback(0)

    def rollback(self, index):
        self._rollbacking = True

        while index >= 0 and len(self.snapshots) >= 1:
            snapshot = self.snapshots[0]
            snapshot.rollback()
            self.snapshots.remove(0)
            index -= 1

        self._rollbacking = False

