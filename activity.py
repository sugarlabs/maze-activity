# -*- coding: utf-8 -*-

import logging
import json

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('TelepathyGLib', '0.12')

from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import TelepathyGLib

from sugar3.activity import activity
from sugar3.presence.presenceservice import PresenceService
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.alert import ErrorAlert
from sugar3.graphics.alert import NotifyAlert
from sugar3 import profile
from gettext import gettext as _

from textchannel import TextChannelWrapper
import game


class MazeActivity(activity.Activity):

    def __init__(self, handle):
        """Set up the Maze activity."""
        activity.Activity.__init__(self, handle)
        self._busy_count = 0
        self._unbusy_idle_sid = None

        if 'state' in self.metadata:
            self.state = json.loads(self.metadata['state'])
        else:
            self.state = None

        self.build_toolbar()

        self.pservice = PresenceService()
        self.owner = self.pservice.get_owner()

        self.game = game.MazeGame(self)
        self.set_canvas(self.game)
        self.game.show()
        self.connect("key_press_event", self.game.key_press_cb)

        self.text_channel = None
        self.my_key = profile.get_pubkey()
        self._alert = None

        if self.shared_activity:
            # we are joining the activity
            self._add_alert(_('Joining a maze'), _('Connecting...'))
            self.connect('joined', self._joined_cb)
            if self.get_shared():
                # we have already joined
                self._joined_cb()
        else:
            # we are creating the activity
            self.connect('shared', self._shared_cb)

    def busy(self):
        if self._busy_count == 0:
            if self._unbusy_idle_sid is not None:
                GLib.source_remove(self._unbusy_idle_sid)
                self._unbusy_idle_sid = None
            self._old_cursor = self.get_window().get_cursor()
            self._set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self._busy_count += 1

    def unbusy(self):
        self._unbusy_idle_sid = GLib.idle_add(self._unbusy_idle_cb)

    def _unbusy_idle_cb(self):
        self._unbusy_idle_sid = None
        self._busy_count -= 1
        if self._busy_count == 0:
            self._set_cursor(self._old_cursor)

    def _set_cursor(self, cursor):
        self.get_window().set_cursor(cursor)
        Gdk.flush()

    def build_toolbar(self):
        """Build our Activity toolbar for the Sugar system."""

        toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        separator = Gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        easier_button = ToolButton('create-easier')
        easier_button.set_tooltip(_('Easier level'))
        easier_button.connect('clicked', self._easier_button_cb)
        toolbar_box.toolbar.insert(easier_button, -1)

        harder_button = ToolButton('create-harder')
        harder_button.set_tooltip(_('Harder level'))
        harder_button.connect('clicked', self._harder_button_cb)
        toolbar_box.toolbar.insert(harder_button, -1)

        self._risk_button = ToggleToolButton('make-risk')
        self._risk_button.set_tooltip(_('Make risk'))
        if self.state and 'risk' in self.state:
            self._risk_button.set_active(self.state['risk'])
        self._risk_button.connect('toggled', self._make_risk_button_cb)
        toolbar_box.toolbar.insert(self._risk_button, -1)

        separator = Gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        self.show_trail_button = ToggleToolButton('show-trail')
        self.show_trail_button.set_tooltip(_('Show trail'))
        self.show_trail_button.set_active(True)
        self.show_trail_button.connect('toggled', self._toggled_show_trail_cb)
        toolbar_box.toolbar.insert(self.show_trail_button, -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_size_request(0, -1)
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show_all()

        return toolbar_box

    def disable_risk(self):
        self._risk_button.set_sensitive(False)

    def set_risk(self, risk):
        self._risk_button.disconnect_by_func(self._make_risk_button_cb)
        self._risk_button.set_active(risk)
        self._risk_button.connect('toggled', self._make_risk_button_cb)

    def _make_risk_button_cb(self, button):
        self.game.set_risk(int(button.get_active()))

    def _easier_button_cb(self, button):
        self.game.easier()

    def _harder_button_cb(self, button):
        self.game.harder()

    def _toggled_show_trail_cb(self, button):
        if self.game.set_show_trail(button.get_active()):
            self.broadcast_msg('show_trail:%s' % str(button.get_active()))

    def _shared_cb(self, activity):
        logging.debug('Maze was shared')
        self._add_alert(_('Sharing'), _('This maze is shared.'))
        self._setup()

    def _joined_cb(self, activity):
        """Joined a shared activity."""
        if not self.shared_activity:
            return
        logging.debug('Joined a shared chat')
        for buddy in self.shared_activity.get_joined_buddies():
            self._buddy_already_exists(buddy)
        self._setup()
        # request maze data
        self.broadcast_msg('req_maze')

    def _setup(self):
        CHANNEL = TelepathyGLib.IFACE_CHANNEL
        self.text_channel = TextChannelWrapper(
            self.shared_activity.telepathy_text_chan[CHANNEL],
            self.shared_activity.telepathy_conn, self.pservice)
        self.text_channel.set_received_callback(self._received_cb)
        self.shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self.shared_activity.connect('buddy-left', self._buddy_left_cb)

    def _received_cb(self, buddy, text):
        if buddy == self.owner:
            return
        self.game.msg_received(buddy, text)

    def _add_alert(self, title, text=None):
        self.grab_focus()
        self._alert = ErrorAlert()
        self._alert.props.title = title
        self._alert.props.msg = text
        self.add_alert(self._alert)
        self._alert.connect('response', self._alert_cancel_cb)
        self._alert.show()

    def _alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)
        self._alert = None

    def update_alert(self, title, text=None):
        if self._alert is not None:
            self._alert.props.title = title
            self._alert.props.msg = text

    def show_accelerator_alert(self):
        self.grab_focus()
        self._alert = NotifyAlert()
        self._alert.props.title = _('Tablet mode detected.')
        self._alert.props.msg = _('Hold your XO flat and tilt to play!')
        self.add_alert(self._alert)
        self._alert.connect('response', self._alert_cancel_cb)
        self._alert.show()

    def _buddy_joined_cb(self, activity, buddy):
        """Show a buddy who joined"""
        logging.debug('buddy joined')
        if buddy == self.owner:
            logging.debug('its me, exit!')
            return
        self.game.buddy_joined(buddy)

    def _buddy_left_cb(self, activity, buddy):
        self.game.buddy_left(buddy)

    def _buddy_already_exists(self, buddy):
        """Show a buddy already in the chat."""
        if buddy == self.owner:
            return
        self.game.buddy_joined(buddy)

    def broadcast_msg(self, message):
        if self.text_channel:
            # FIXME: can't identify the sender at the other end,
            # add the pubkey to the text message
            self.text_channel.send('%s|%s' % (self.my_key, message))

    def write_file(self, file_path):
        logging.debug('Saving the state of the game...')
        data = {'seed': self.game.maze.seed,
                'width': self.game.maze.width,
                'height': self.game.maze.height,
                'finish_time': self.game.finish_time,
                'risk': self.game.maze.risk}

        logging.debug('Saving data: %s', data)
        self.metadata['state'] = json.dumps(data)

    def can_close(self):
        self.game.close_finish_window()
        return True

    def read_file(self, file_path):
        pass
