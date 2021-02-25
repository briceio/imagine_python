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

