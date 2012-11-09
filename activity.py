# -*- coding: utf-8 -*-

import logging
import olpcgames
import pygame
import gtk

from olpcgames import mesh
from olpcgames import util

from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.graphics.toolbutton import ToolButton
from gettext import gettext as _


class MazeActivity(olpcgames.PyGameActivity):
    game_name = 'game'
    game_title = _('Maze')
    game_size = None    # Let olpcgames pick a nice size for us

    def __init__(self, handle):
        super(MazeActivity, self).__init__(handle)

        # This code was copied from olpcgames.activity.PyGameActivity
        def shared_cb(*args, **kwargs):
            logging.info('shared: %s, %s', args, kwargs)
            try:
                mesh.activity_shared(self)
            except Exception, err:
                logging.error('Failure signaling activity sharing'
                              'to mesh module: %s', util.get_traceback(err))
            else:
                logging.info('mesh activity shared message sent,'
                             ' trying to grab focus')
            try:
                self._pgc.grab_focus()
            except Exception, err:
                logging.warn('Focus failed: %s', err)
            else:
                logging.info('asserting focus')
                assert self._pgc.is_focus(), \
                    'Did not successfully set pygame canvas focus'
            logging.info('callback finished')

        def joined_cb(*args, **kwargs):
            logging.info('joined: %s, %s', args, kwargs)
            mesh.activity_joined(self)
            self._pgc.grab_focus()
        self.connect('shared', shared_cb)
        self.connect('joined', joined_cb)

        if self.get_shared():
            # if set at this point, it means we've already joined (i.e.,
            # launched from Neighborhood)
            joined_cb()

    def build_toolbar(self):
        """Build our Activity toolbar for the Sugar system."""

        toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        separator = gtk.SeparatorToolItem()
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

        separator = gtk.SeparatorToolItem()
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

    def _easier_button_cb(self, button):
        pygame.event.post(olpcgames.eventwrap.Event(
            pygame.USEREVENT, action='easier_button'))

    def _harder_button_cb(self, button):
        pygame.event.post(olpcgames.eventwrap.Event(
            pygame.USEREVENT, action='harder_button'))
