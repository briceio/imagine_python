# accelerator.py
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


from gi.repository import Gdk
from threading import Thread
from gi.repository import GLib, Gtk
from time import sleep, time

__all__ = ['Accelerator']

class Key:
    def __init__(self, key, mod):
        self.key = key
        self.mod = mod

class Action:
    def __init__(self, action, wait_timeout):
        self.action = action
        self.wait_timeout = wait_timeout

class Accelerator:

    INSTANCIATED = False
    ACTIVATION_TIMEOUT = 1.0

    def __init__(self, activation_timeout=1.0):
        self.activation_timeout = activation_timeout
        self.global_context = {}
        self.contexts = {}
        self.commands = {}
        self.buffer = []
        self.disable()
        self._current_context = None

        print("Acceleration activation timeout: %f" % self.activation_timeout)

        # check singleton
        if Accelerator.INSTANCIATED:
            print("There is already an Accelerator in the app!")
        Accelerator.INSTANCIATED = True

        # init
        self.action_pending = False

        # start the accelerator
        self.running = True
        self.thread = Thread(target=self._thread, args=())
        self.thread.start()

    EXCLUDED_KEYVALS = [Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R]

    def key_handler(self, window, event):

        def register_event():
            if event.type == Gdk.EventType.KEY_PRESS and not event.keyval in Accelerator.EXCLUDED_KEYVALS:
                self.buffer.append(Key(event.keyval, event.state))

        if not self.enabled: return

        #print("Accelerator command: %s" % Gtk.accelerator_name_with_keycode(None, event.keyval, event.hardware_keycode, event.state))

        # get current focused widget
        widget = window.get_focus();
        if isinstance(widget, (Gtk.Entry, Gtk.TextView)):
            return # skip

        if not self.action_pending:
            self.action_pending = True
            self.buffer = []

        if self.action_pending:
            self.last_action_time = time()
            register_event()
            return self._process_buffer()

        return False

    def stop(self):
        self.running = False # to stop the thread

    def _thread(self):
        print("Accelerator thread started.")

        while (self.running):
            # disable action if too much time spent
            if self.action_pending:
                delta = time() - self.last_action_time
                if delta >= self.activation_timeout:
                    self._process_buffer(True)
                    self.buffer = []
                    self.action_pending = False

            sleep(0.25)

        print("Accelerator thread killed successfully.")

    def _process_buffer(self, timeout=False):

        # merge global & current active contexts
        # to be replaced with A | B in Python 3.9+ (A |= B)
        contexts = self.global_context.copy()
        if self._current_context != None:
            contexts.update(self._current_context)

        for _, (command, action) in enumerate(contexts.items()):

            # parse command
            codes = command.split(",")

            if len(self.buffer) == len(codes):
                valid = True
                for event, accelerator in zip(self.buffer, codes):
                    key, mod = Gtk.accelerator_parse(accelerator)

                    if key != event.key or mod != event.mod:
                        valid = False
                        continue

                if valid:
                    self._execute_action(command, action, timeout) # process commands tirggered on timeout expiration
                    return True

        return False

    def _execute_action(self, command, action: Action, timeout):
        if (not action.wait_timeout or (action.wait_timeout and timeout)) and callable(action.action):
            #print("Acceleration action triggered: %s" % command)
            self.action_pending = False
            self.buffer = []
            GLib.idle_add(lambda: action.action())

    def add(self, context, command, action, wait_timeout=False):
        a = Action(action, wait_timeout)
        if context == None:
            self.global_context[command] = a
        else:
            self.contexts.setdefault(context, {})[command] = a

    def set_context(self, context):
        if self.contexts.__contains__(context):
            self._current_context = self.contexts[context]
        else:
            print("Unknown accelerator context: %s" % context)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.buffer = []
        self.action_pending = False
        self.enabled = False
