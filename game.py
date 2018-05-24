# -*- coding: utf-8 -*-

# Maze.activity
# A simple multi-player maze game for the XO laptop.
# http://wiki.laptop.org/go/Maze
#
# Special thanks to Brendan Donohoe for the icon.
#
# Copyright (C) 2007  Joshua Minor
# This file is part of Maze.activity
#
#     Maze.activity is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Maze.activity is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with Maze.activity.  If not, see <http://www.gnu.org/licenses/>.


import sys
import time
from math import pi
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
import cairo

import logging
from gettext import gettext as _

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.toolbutton import ToolButton

from maze import Maze, Rectangle
from player import Player
import sensors


class MazeGame(Gtk.DrawingArea):
    """Maze game controller.
    This class handles all of the game logic, event loop, mulitplayer, etc."""

    # Munsell color values http://wiki.laptop.org/go/Munsell
    EMPTY_COLOR = (203.0 / 255.0, 203.0 / 255.0, 203.0 / 255.0)
    SOLID_COLOR = (28.0 / 255.0, 28.0 / 255.0, 28.0 / 255.0)
    GOAL_COLOR = (0x00, 0xff, 0x00)

    def __init__(self, activity, owner, state=None):
        super(MazeGame, self).__init__()
        # note what time it was when we first launched
        self.game_start_time = time.time()

        # the activity is used to communicate with other players
        self._activity = activity

        # keep a list of all local players
        self.localplayers = []

        # start with just one player
        player = Player(owner)
        self.localplayers.append(player)
        # plus some bonus players (all hidden to start with)
        self.localplayers.extend(player.bonusPlayers())

        # keep a dictionary of all remote players, indexed by handle
        self.remoteplayers = {}
        # keep a list of all players, local and remote,
        self.allplayers = [] + self.localplayers

        screen = Gdk.Screen.get_default()
        self.aspectRatio = float(screen.width()) / screen.height()

        # start with a small maze using a seed that will be different
        # each time you play
        if state is None:
            state = {'seed': int(time.time()),
                     'width': int(9 * self.aspectRatio),
                     'height': 9}

        if 'finish_time' in state and state['finish_time'] is not None:
            # the maze was alread played, reset it to start a new one
            state['seed'] = int(time.time())

        logging.debug('Starting the game with: %s', state)
        self.maze = Maze(state['seed'], state['width'], state['height'])
        self._ebook_mode_detector = sensors.EbookModeDetector()
        self._finish_window = None
        self.reset()

        self.frame = 0
        self._show_trail = True
        self._cached_surface = None

        # support arrow keys, game pad arrows and game pad buttons
        # each set maps to a local player index and a direction
        self.arrowkeys = {
            # real key:     (localplayer index, ideal key)
            'Up': (0, 'Up'),
            'Down': (0, 'Down'),
            'Left': (0, 'Left'),
            'Right': (0, 'Right'),
            'KP_Up': (1, 'Up'),
            'KP_Down': (1, 'Down'),
            'KP_Left': (1, 'Left'),
            'KP_Right': (1, 'Right'),
            'KP_Page_Up': (2, 'Up'),
            'KP_Page_Down': (2, 'Down'),
            'KP_Home': (2, 'Left'),
            'KP_End': (2, 'Right')
        }

        Gdk.Screen.get_default().connect('size-changed',
                                         self.__configure_cb)
        self.connect('draw', self.__draw_cb)
        self.connect('size-allocate', self.__size_allocate_cb)
        self.connect('event', self.__event_cb)

        self.set_events(
            Gdk.EventMask.EXPOSURE_MASK | Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.BUTTON_MOTION_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.POINTER_MOTION_HINT_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.TOUCH_MASK)
        self.set_can_focus(True)
        self.grab_focus()
        self._accelerometer = sensors.Accelerometer()
        self._read_accelerator_id = None
        if self._ebook_mode_detector.get_ebook_mode():
            self._activity.show_accelerator_alert()
            self._start_accelerometer()
        self._ebook_mode_detector.connect('changed',
                                          self._ebook_mode_changed_cb)

    def __configure_cb(self, event):
        ''' Screen size has changed '''
        width = Gdk.Screen.get_default().width()
        height = Gdk.Screen.get_default().height() - style.GRID_CELL_SIZE
        self.aspectRatio = width / height

        self._activity.busy()
        if width < height:
            if self.maze.width < self.maze.height:
                self.maze = Maze(self.maze.seed + 1, self.maze.width,
                                 self.maze.height)
            else:
                self.maze = Maze(self.maze.seed + 1, self.maze.height,
                                 self.maze.width)
        else:
            if self.maze.width > self.maze.height:
                self.maze = Maze(self.maze.seed + 1, self.maze.width,
                                 self.maze.height)
            else:
                self.maze = Maze(self.maze.seed + 1, self.maze.height,
                                 self.maze.width)
        if len(self.remoteplayers) > 0:
            self.game_start_time -= 10
            self._send_maze()
        self._activity.unbusy()
        self.reset()

    def game_running_time(self, newelapsed=None):
        return int(time.time() - self.game_start_time)

    def reset(self):
        """Reset the game state.  Everyone starts in the top-left.
        The goal starts in the bottom-right corner."""
        self.running = True
        self.level_start_time = time.time()
        self.finish_time = None
        for player in self.allplayers:
            player.reset()
        self._dirty_points = []
        self.maze.map[self.maze.width - 2][self.maze.height - 2] = \
            self.maze.GOAL

        # force size recalcuation
        self._recalculate_sizes(self.get_allocation())

        self.queue_draw()
        self.mouse_in_use = 0
        if self._ebook_mode_detector.get_ebook_mode():
            self._start_accelerometer()
        self.close_finish_window()
        self.grab_focus()

    def __size_allocate_cb(self, widget, allocation):
        self._recalculate_sizes(allocation)

    def _recalculate_sizes(self, allocation):
        self._width = allocation.width
        self._height = allocation.height
        # compute the size of the tiles given the screen size, etc.
        self.tileSize = min(self._width / self.maze.width,
                            self._height / self.maze.height)
        self.bounds = Rectangle((self._width - self.tileSize *
                                 self.maze.width) / 2,
                                (self._height - self.tileSize *
                                 self.maze.height) / 2,
                                self.tileSize * self.maze.width,
                                self.tileSize * self.maze.height)
        self.outline = int(self.tileSize / 5)
        self._cached_surface = None
        self._dirty_rect = self.maze.bounds

    def __draw_cb(self, widget, ctx):
        """Draw the current state of the game.
        This makes use of the dirty rectangle to reduce CPU load."""

        if self._cached_surface is None:
            self._cached_surface = ctx.get_target().create_similar(
                cairo.CONTENT_COLOR_ALPHA, self._width, self._height)
            self._ctx = cairo.Context(self._cached_surface)

        if self._dirty_rect is None and len(self._dirty_points) == 0:
            ctx.set_source_surface(self._cached_surface)
            ctx.paint()
            return

        def drawPoint(x, y):
            rect = Rectangle(self.bounds.x + x * self.tileSize,
                             self.bounds.y + y * self.tileSize,
                             self.tileSize, self.tileSize)
            tile = self.maze.map[x][y]
            background_color = self.EMPTY_COLOR
            if tile == self.maze.EMPTY:
                background_color = self.EMPTY_COLOR
            elif tile == self.maze.SOLID:
                background_color = self.SOLID_COLOR
            elif tile == self.maze.GOAL:
                background_color = self.GOAL_COLOR
            self._ctx.save()
            self._ctx.set_source_rgb(*background_color)
            self._ctx.rectangle(*rect.get_bounds())
            self._ctx.fill()

            if self._show_trail:
                if tile == self.maze.SEEN:
                    radius = self.tileSize / 3 - self.outline
                    center = self.tileSize / 2
                    self._ctx.set_source_rgba(
                        *self.localplayers[0].bg.get_rgba())
                    self._ctx.arc(rect.x + center, rect.y + center, radius, 0,
                                  2 * pi)
                    self._ctx.fill()
            self._ctx.restore()

        # re-draw the dirty rectangle
        if self._dirty_rect is not None:

            # background
            self._ctx.save()
            self._ctx.rectangle(0, 0, self._width, self._height)
            self._ctx.set_source_rgb(*self.SOLID_COLOR)
            self._ctx.fill()
            self._ctx.restore()

            # compute the area that needs to be redrawn
            left = max(0, self._dirty_rect.x)
            right = min(self.maze.width,
                        self._dirty_rect.x + self._dirty_rect.width)
            top = max(0, self._dirty_rect.y)
            bottom = min(self.maze.height,
                         self._dirty_rect.y + self._dirty_rect.height)

            # loop over the dirty rect and draw
            for x in range(left, right):
                for y in range(top, bottom):
                    drawPoint(x, y)

        # re-draw the dirty points
        for x, y in self._dirty_points:
            drawPoint(x, y)

        main_player = self.localplayers[0]
        # draw all players
        for player in self.allplayers:
            if not player.hidden and player != main_player:
                player.draw(self._ctx, self.bounds, self.tileSize)
        # draw last the main player
        main_player.draw(self._ctx, self.bounds, self.tileSize)

        ctx.set_source_surface(self._cached_surface)
        ctx.paint()

        # clear the dirty rect so nothing will be drawn until there is a change
        self._dirty_rect = None
        self._dirty_points = []

    def set_show_trail(self, show_trail):
        if self._show_trail != show_trail:
            self._show_trail = show_trail
            self._dirty_rect = self.maze.bounds
            self.queue_draw()
            return True
        else:
            return False

    def _mark_point_dirty(self, pt):
        """Mark a single point that needs to be redrawn."""
        self._dirty_points.append(pt)

    def _ebook_mode_changed_cb(self, detector, ebook_mode):
        if ebook_mode:
            GObject.idle_add(self._activity.show_accelerator_alert)
            if self._read_accelerator_id is None:
                self._start_accelerometer()
        else:
            self._read_accelerator_id = None

    def _read_accelerometer(self):
        x, y, z = self._accelerometer.read_position()

        debug_msg = "x %s, y %s, z %s | " % (x, y, z)

        TRIGGER = 100
        if abs(x) < TRIGGER:
            x = 0
        if abs(y) < TRIGGER:
            y = 0

        player = self.localplayers[0]
        player.hidden = False
        if abs(x) > abs(y):
            if x > 0:
                # RIGHT
                player.direction = (1, 0)
            if x < 0:
                # LEFT
                player.direction = (-1, 0)
            value = abs(x)
        else:
            if y < 0:
                # UP
                player.direction = (0, -1)
            if y > 0:
                # DOWN
                player.direction = (0, 1)
            value = abs(y)
        if x == 0 and y == 0:
            player.direction = (0, 0)

        debug_msg = debug_msg + "direction %s %s | " % (player.direction)

        self.player_walk(player, False)

        if self._ebook_mode_detector.get_ebook_mode() and \
                player.elapsed is None:
            # next_read depend on inclination
            next_read = 200 - int(100 * (float(value - TRIGGER) / 500))
            # minimal time is 50 ms
            next_read = max(50, next_read)
            self._start_accelerometer(delay=next_read)

            debug_msg = debug_msg + "next_read %s" % next_read

        logging.debug('accelerometer read %s', debug_msg)

        return False

    def _start_accelerometer(self, delay=200):
        self._read_accelerator_id = GObject.timeout_add(
            delay, self._read_accelerometer)

    def __event_cb(self, widget, event):

        if event.type in (Gdk.EventType.TOUCH_BEGIN,
                          Gdk.EventType.TOUCH_CANCEL, Gdk.EventType.TOUCH_END,
                          Gdk.EventType.BUTTON_PRESS,
                          Gdk.EventType.BUTTON_RELEASE):
            x = int(event.get_coords()[1])
            y = int(event.get_coords()[2])

            # logging.error('event x %d y %d type %s', x, y, event.type)
            if event.type in (Gdk.EventType.TOUCH_BEGIN,
                              Gdk.EventType.BUTTON_PRESS):
                self.prev_mouse_pos = (x, y)
            elif event.type in (Gdk.EventType.TOUCH_END,
                                Gdk.EventType.BUTTON_RELEASE):

                new_mouse_pos = (x, y)
                mouse_movement = (new_mouse_pos[0] - self.prev_mouse_pos[0],
                                  new_mouse_pos[1] - self.prev_mouse_pos[1])

                if ((abs(mouse_movement[0]) > 10) or
                        (abs(mouse_movement[1]) > 10)):
                    player = self.localplayers[0]
                    player.hidden = False
                    # x movement larger
                    if abs(mouse_movement[0]) > abs(mouse_movement[1]):
                        if mouse_movement[0] > 0:
                            # RIGHT
                            player.direction = (1, 0)
                        else:
                            # LEFT
                            player.direction = (-1, 0)
                    else:
                        if mouse_movement[1] < 0:
                            # UP
                            player.direction = (0, -1)
                        else:
                            # DOWN
                            player.direction = (0, 1)

                    if len(self.remoteplayers) > 0 and \
                            player == self.localplayers[0]:
                        self._send_move(player)
                    self.player_walk(player)

    def key_press_cb(self, widget, event):
        if isinstance(widget.get_toplevel().get_focus(), Gtk.Entry):
            return False
        key_name = Gdk.keyval_name(event.keyval)
        if key_name in ('plus', 'equal'):
            self.harder()
        elif key_name == 'minus':
            self.easier()
        elif key_name in self.arrowkeys:
            playernum, direction = self.arrowkeys[key_name]
            player = self.localplayers[playernum]
            player.hidden = False

            if direction == 'Up':
                player.direction = (0, -1)
            elif direction == 'Down':
                player.direction = (0, 1)
            elif direction == 'Left':
                player.direction = (-1, 0)
            elif direction == 'Right':
                player.direction = (1, 0)

            if len(self.remoteplayers) > 0 and \
                    player == self.localplayers[0]:
                self._send_move(player)
            self.player_walk(player)

    def player_walk(self, player, change_direction=True):
        oldposition = player.position
        newposition = player.animate(self.maze, change_direction)
        if oldposition != newposition:
            self._mark_point_dirty(oldposition)
            self._mark_point_dirty(newposition)
            if player in self.localplayers:
                self.maze.map[player.previous[0]][player.previous[1]] = \
                    self.maze.SEEN
                if self.maze.map[newposition[0]][newposition[1]] == \
                        self.maze.GOAL:
                    self.finish(player)
            self.queue_draw()
            if change_direction:
                GObject.timeout_add(100, self.player_walk, player)
            else:
                # if we have peers and the player is the main local player
                if len(self.remoteplayers) > 0 and \
                        player == self.localplayers[0]:
                    self._activity.broadcast_msg(
                        "step:%d,%d,%d,%d" %
                        (player.position[0], player.position[1],
                         player.direction[0], player.direction[1]))

    def buddy_joined(self, buddy):
        if buddy:
            logging.debug("Join: %s - %s", buddy.props.nick,
                          buddy.props.color)
            player = Player(buddy)
            player.uid = buddy.get_key()
            self.remoteplayers[buddy.get_key()] = player
            self.allplayers.append(player)
            self.allplayers.extend(player.bonusPlayers())
            self._mark_point_dirty(player.position)

    def _send_move(self, player):
        self._activity.broadcast_msg(
            "move:%d,%d,%d,%d" %
            (player.position[0], player.position[1],
             player.direction[0], player.direction[1]))

    def _send_maze(self):
        self._activity.broadcast_msg(
            "maze:%d,%d,%d,%d" %
            (self.game_running_time(), self.maze.seed, self.maze.width,
             self.maze.height))

    def _handle_req_maze(self, player):
        # tell them which maze we are playing, so they can sync up
        self._send_maze()
        # only the first player collaborate
        player = self.localplayers[0]
        if not player.hidden:
            self._send_move(player)

    def buddy_left(self, buddy):
        logging.debug('buddy left %s %s', buddy.__class__, dir(buddy))
        if buddy.get_key() in self.remoteplayers:
            player = self.remoteplayers[buddy.get_key()]
            logging.debug("Leave: %s", player.nick)
            self._mark_point_dirty(player.position)
            self.allplayers.remove(player)
            for bonusplayer in player.bonusPlayers():
                self._mark_point_dirty(bonusplayer.position)
                self.allplayers.remove(bonusplayer)
            del self.remoteplayers[buddy.get_key()]

    def msg_received(self, buddy, message):
        logging.debug('msg received %s', message)
        key, message = message.split('|')
        if message.startswith('maze'):
            self.handleMessage(None, message)
            return

        if key in self.remoteplayers:
            player = self.remoteplayers[key]
            try:
                self.handleMessage(player, message)
            except BaseException:
                logging.error("Error handling message: %s\n%s",
                              message, sys.exc_info())
        else:
            logging.error("Message from unknown buddy %s", key)

    def handleMessage(self, player, message):
        """Handle a message from a player.
            We try to be forward compatible with new versions of Maze by
            allowing messages to have extra stuff at the end and ignoring
            unrecognized messages.

            We allow some messages to contain a different nick than the
            message's source player to support bonus players on that
            player's XO.

            The valid messages are:

            req_maze
                Request to please send me the maze.  Reply is maze:.

            maze: running_time, seed, width, height
                A player has a differen maze.
                The one that has been running the longest will force all other
                players to use that maze.
                This way new players will join the existing game properly.

            move: x, y, dx, dy
                A player's at x, y is now moving in direction dx, dy

            step: x, y, dx, dy
                A player move using the accelerator, move a single step

            show_trail: True/False

            finish: elapsed
                A player has finished the maze
        """
        logging.debug('message: %s', message)

        # ignore messages from myself
        if player in self.localplayers:
            return
        if message == "req_maze":
            self._handle_req_maze(player)
        elif message.startswith("move:"):
            # a player has moved
            x, y, dx, dy = message[5:].split(",")[:5]

            self._mark_point_dirty(player.position)
            player.position = (int(x), int(y))
            player.direction = (int(dx), int(dy))
            self._mark_point_dirty(player.position)
            self.player_walk(player)
        elif message.startswith("step:"):
            # a player has moved using the accelerometer
            x, y, dx, dy = message[5:].split(",")[:5]

            self._mark_point_dirty(player.position)
            player.position = (int(x), int(y))
            player.direction = (int(dx), int(dy))
            self._mark_point_dirty(player.position)
            self.player_walk(player, False)
        elif message.startswith("maze:"):
            # someone has a different maze than us
            self._activity.update_alert('Connected', 'Maze shared!')
            running_time, seed, width, height = map(lambda x: int(x),
                                                    message[5:].split(",")[:4])
            if self.maze.seed == seed:
                logging.debug('Same seed, don\'t reload Maze')
                return
            # is that maze older than the one we're already playing?
            # note that we use elapsed time instead of absolute time because
            # people's clocks are often set to something totally wrong
            if self.game_running_time() < running_time:
                # make note of the earlier time that the game really
                # started (before we joined)
                self.game_start_time = time.time() - running_time
                # use the new seed
                self._activity.busy()
                self.maze = Maze(seed, width, height)
                self._activity.unbusy()
                self.reset()
        elif message.startswith("finish:"):
            # someone finished the maze
            elapsed = message[7:]
            player.elapsed = float(elapsed)

            self.show_finish_window()
        elif message.startswith("show_trail:"):
            show_trail = message.endswith('True')
            self._activity.show_trail_button.set_active(show_trail)
        else:
            # it was something I don't recognize...
            logging.debug("Message from %s: %s", player.nick, message)

    def harder(self):
        """Make a new maze that is harder than the current one."""
        # both width and height must be odd
        newHeight = self.maze.height + 2
        if newHeight > 125:
            newHeight = 125
        newWidth = int(newHeight * self.aspectRatio)
        if newWidth % 2 == 0:
            newWidth -= 1
        self._restart(newWidth, newHeight)

    def easier(self):
        """Make a new maze that is easier than the current one."""
        # both width and height must be odd
        newHeight = max(self.maze.height - 2, 9)
        newWidth = int(newHeight * self.aspectRatio)
        if newWidth % 2 == 0:
            newWidth -= 1
        self._restart(newWidth, newHeight)

    def _restart(self, newWidth, newHeight):
        self._activity.busy()
        self.maze = Maze(self.maze.seed + 1, newWidth, newHeight)
        self.reset()
        # tell everyone which maze we are playing, so they can sync up
        if len(self.remoteplayers) > 0:
            # but fudge it a little so that we can be sure they'll use our maze
            self.game_start_time -= 10
            self._send_maze()
        self._activity.unbusy()

    def finish(self, player):
        self.finish_time = time.time()
        player.elapsed = self.finish_time - self.level_start_time
        self.queue_draw()
        if len(self.remoteplayers) > 0 and \
                player == self.localplayers[0]:
            self._activity.broadcast_msg("finish:%.2f" % player.elapsed)
        winner = True
        for players in self.allplayers:
            if players.elapsed is not None and player.elapsed > \
                    players.elapsed:
                winner = False
        if winner:
            player.victories += 1

        self.show_finish_window()

    def show_finish_window(self):
        all_finished = True
        for player in self.allplayers:
            if not player.hidden and player.elapsed is None:
                all_finished = False

        if all_finished:
            parent_xid = self.get_toplevel().get_window()
            self._finish_window = FinishWindow(self, parent_xid)

    def close_finish_window(self):
        if self._finish_window is not None:
            self._finish_window.destroy()
            self._finish_window = None


class FinishWindow(Gtk.Window):

    def __init__(self, game, parent_xid):
        Gtk.Window.__init__(self)
        self._game = game
        self._parent_window_xid = parent_xid

        self.set_border_width(style.LINE_WIDTH)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.connect('realize', self.__realize_cb)
        self.connect('key-press-event', self.__key_press_event_cb)

        grid = Gtk.Grid()
        grid.set_row_spacing(0)
        grid.set_border_width(style.DEFAULT_SPACING)
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        title = Gtk.Label()

        title_font_size = style.FONT_SIZE * 3
        text_font_size = style.FONT_SIZE * 2

        title.set_markup('<span font="%d" color="white">%s</span>' %
                         (title_font_size, _('Maze solved!')))
        grid.add(title)

        players_grid = Gtk.Grid()
        players_grid.set_column_spacing(style.DEFAULT_PADDING * 3)
        players_grid.set_row_spacing(style.DEFAULT_PADDING)
        players_grid.set_border_width(style.DEFAULT_SPACING)
        row = 0
        all_players = self._game.allplayers
        all_players.sort(lambda a, b: cmp(a.elapsed, b.elapsed))
        for player in all_players:
            if not player.hidden:
                players_grid.attach(
                    Icon(icon_name='stopwatch',
                         pixel_size=style.MEDIUM_ICON_SIZE,
                         xo_color=XoColor(player.buddy.props.color)),
                    0, row, 1, 1)

                time = Gtk.Label()
                if player.elapsed > 60:
                    minutes = int(player.elapsed / 60)
                    seconds = player.elapsed - minutes * 60
                    elapsed = "%d:%2.2f" % (minutes, seconds)
                else:
                    elapsed = "%3.2f" % player.elapsed

                time.set_markup('<span font="%d" color="%s">%s</span>' %
                                (text_font_size, player.fg.get_html(),
                                 elapsed))
                players_grid.attach(time, 1, row, 1, 1)

                name = Gtk.Label()
                name.set_markup('<span font="%d" color="%s">%s</span>' %
                                (text_font_size, player.fg.get_html(),
                                 player.nick))
                name.set_halign(Gtk.Align.START)
                players_grid.attach(name, 2, row, 1, 1)

                players_grid.attach(
                    Icon(icon_name='trophy',
                         pixel_size=style.MEDIUM_ICON_SIZE,
                         xo_color=XoColor(player.buddy.props.color)),
                    3, row, 1, 1)

                points = Gtk.Label()
                points.set_markup('<span font="%d" color="%s">%d</span>' %
                                  (text_font_size, player.fg.get_html(),
                                   player.victories))
                players_grid.attach(points, 4, row, 1, 1)

                row += 1

        grid.add(players_grid)

        ask = Gtk.Label()
        ask.set_markup('<span font="%d" color="white">%s</span>' %
                       (text_font_size, _('Play again?')))
        grid.add(ask)

        buttons_grid = Gtk.Grid()
        buttons_grid.set_row_spacing(0)
        buttons_grid.set_border_width(style.DEFAULT_SPACING)
        buttons_grid.set_orientation(Gtk.Orientation.HORIZONTAL)

        easier_button = ToolButton('create-easier')
        easier_button.connect('clicked', self._easier_button_cb)
        buttons_grid.add(easier_button)

        harder_button = ToolButton('create-harder')
        harder_button.connect('clicked', self._harder_button_cb)
        buttons_grid.add(harder_button)
        buttons_grid.set_halign(Gtk.Align.CENTER)
        grid.add(buttons_grid)

        self.add(grid)

        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_TOOLBAR_GREY.get_gdk_color())

        self.show_all()

    def __realize_cb(self, widget):
        self.get_window().set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_decorations(Gdk.WMDecoration.BORDER)
        self.get_window().set_transient_for(self._parent_window_xid)

    def _easier_button_cb(self, button):
        GObject.idle_add(self._game.easier)

    def _harder_button_cb(self, button):
        GObject.idle_add(self._game.harder)

    def __key_press_event_cb(self, window, event):
        if event.keyval == Gdk.KEY_Escape:
            GObject.idle_add(self._game.close_finish_window)
        elif event.keyval == Gdk.KEY_q and \
                event.state & Gdk.ModifierType.CONTROL_MASK != 0:
            self._game._activity.close()
