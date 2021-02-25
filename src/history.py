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

    def snapshot(self, description, rollback):
        self.snapshots.insert(0, Snapshot(description, rollback))

    def rollback(self, index):
        print("Rollbacking to: %d" % index)

        while index >= 0:
            snapshot = self.snapshots[0]
            snapshot.rollback()
            self.snapshots.remove(0)
            index -= 1
