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

import logging

from sugar3.presence import presenceservice
from sugar3.graphics.style import GRID_CELL_SIZE

presenceService = presenceservice.get_instance()

from maze import Maze, Rectangle
from player import Player


class MazeGame(Gtk.DrawingArea):
    """Maze game controller.
    This class handles all of the game logic, event loop, mulitplayer, etc."""

    # Munsell color values http://wiki.laptop.org/go/Munsell
    EMPTY_COLOR = (203.0 / 255.0, 203.0 / 255.0, 203.0 / 255.0)
    SOLID_COLOR = (28.0 / 255.0, 28.0 / 255.0,  28.0 / 255.0)
    TRAIL_COLOR = (1.0, 1.0, 1.0)
    GOAL_COLOR = (0x00, 0xff, 0x00)
    WIN_COLOR = (0xff, 0xff, 0x00)

    def __init__(self, state=None):
        super(MazeGame, self).__init__()
        # note what time it was when we first launched
        self.game_start_time = time.time()

        xoOwner = presenceService.get_owner()
        # keep a list of all local players
        self.localplayers = []

        # start with just one player
        player = Player(xoOwner)
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

        logging.debug('Starting the game with: %s', state)
        self.maze = Maze(**state)
        self.reset()

        self.frame = 0

        # self.font = pygame.font.Font(None, 30)

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

    def __configure_cb(self, event):
        ''' Screen size has changed '''
        width = Gdk.Screen.get_default().width()
        height = Gdk.Screen.get_default().height() - GRID_CELL_SIZE
        self.aspectRatio = width / height

        if width < height:
            if self.maze.width < self.maze.height:
                self.maze = Maze(self.maze.seed, self.maze.width,
                                 self.maze.height)
            else:
                self.maze = Maze(self.maze.seed, self.maze.height,
                                 self.maze.width)
        else:
            if self.maze.width > self.maze.height:
                self.maze = Maze(self.maze.seed, self.maze.width,
                                 self.maze.height)
            else:
                self.maze = Maze(self.maze.seed, self.maze.height,
                                 self.maze.width)
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
        self.dirtyRect = self.maze.bounds
        self.dirtyPoints = []
        self.maze.map[self.maze.width - 2][self.maze.height - 2] = \
            self.maze.GOAL

        # clear and mark the whole screen as dirty
        # TODO
        # self.screen.fill((0, 0, 0))
        self.queue_draw()
        self.mouse_in_use = 0

    def __draw_cb(self, widget, ctx):
        """Draw the current state of the game.
        This makes use of the dirty rectangle to reduce CPU load."""
        # TODO
        # if self.dirtyRect is None and len(self.dirtyPoints) == 0:
        #    return

        # compute the size of the tiles given the screen size, etc.
        allocation = self.get_allocation()

        ctx.rectangle(0, 0, allocation.width, allocation.height)
        ctx.set_source_rgb(*self.SOLID_COLOR)
        ctx.fill()

        self.tileSize = min(allocation.width / self.maze.width,
                            allocation.height / self.maze.height)
        self.bounds = Rectangle((allocation.width - self.tileSize *
                                 self.maze.width) / 2,
                                (allocation.height - self.tileSize *
                                 self.maze.height) / 2,
                                self.tileSize * self.maze.width,
                                self.tileSize * self.maze.height)
        self.outline = int(self.tileSize / 5)

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
            ctx.save()
            ctx.set_source_rgb(*background_color)
            ctx.rectangle(*rect.get_bounds())
            ctx.fill()

            if tile == self.maze.SEEN:
                ctx.set_source_rgb(*self.TRAIL_COLOR)
                radius = self.tileSize / 2 - self.outline
                center = self.tileSize / 2
                ctx.arc(rect.x + center, rect.y + center, radius, 0, 2 * pi)
                ctx.fill()
            ctx.restore()

        # re-draw the dirty rectangle
        if self.dirtyRect is not None:
            # compute the area that needs to be redrawn
            left = max(0, self.dirtyRect.x)
            right = min(self.maze.width,
                        self.dirtyRect.x + self.dirtyRect.width)
            top = max(0, self.dirtyRect.y)
            bottom = min(self.maze.height,
                         self.dirtyRect.y + self.dirtyRect.height)

            # loop over the dirty rect and draw
            for x in range(left, right):
                for y in range(top, bottom):
                    drawPoint(x, y)

        # re-draw the dirty points
        # for x, y in self.dirtyPoints:
        #    drawPoint(x, y)

        # draw all players
        for player in self.allplayers:
            if not player.hidden:
                player.draw(ctx, self.bounds, self.tileSize)

        # draw the elapsed time for each player that has finished
        # TODO
        """
        finishedPlayers = filter(lambda p: p.elapsed is not None,
                                 self.allplayers)
        finishedPlayers.sort(lambda a, b: cmp(a.elapsed, b.elapsed))
        y = 0
        for player in finishedPlayers:
            fg, bg = player.colors
            text = "%3.2f - %s" % (player.elapsed, player.nick)
            textimg = self.font.render(text, 1, fg)
            textwidth, textheight = self.font.size(text)
            rect = pygame.Rect(8, y + 4, textwidth, textheight)
            bigrect = rect.inflate(16, 8)
            pygame.draw.rect(self.screen, bg, bigrect, 0)
            pygame.draw.rect(self.screen, fg, bigrect, 2)
            self.screen.blit(textimg, rect)

            y += bigrect.height + 4
        """
        # clear the dirty rect so nothing will be drawn until there is a change
        # TODO
        # self.dirtyRect = None
        # self.dirtyPoints = []

    def markRectDirty(self, rect):
        """Mark an area that needs to be redrawn.  This lets us
        play really big mazes without needing to re-draw the whole
        thing each frame."""
        if self.dirtyRect is None:
            self.dirtyRect = rect
        else:
            self.dirtyRect.union_ip(rect)

    def markPointDirty(self, pt):
        """Mark a single point that needs to be redrawn."""
        self.dirtyPoints.append(pt)

    def __event_cb(self, widget, event):
        pass
        """
        if event.type in (
                Gdk.EventType.TOUCH_BEGIN,
                Gdk.EventType.TOUCH_CANCEL, Gdk.EventType.TOUCH_END,
                Gdk.EventType.TOUCH_UPDATE, Gdk.EventType.BUTTON_PRESS,
                Gdk.EventType.BUTTON_RELEASE, Gdk.EventType.MOTION_NOTIFY):
            x = event.touch.x
            y = event.touch.y
            seq = str(event.touch.sequence)
            updated_positions = False
            # save a copy of the old touches
        """

    def key_press_cb(self, widget, event):
        key_name = Gdk.keyval_name(event.keyval)
        logging.error('key %s presssed', key_name)
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

            if len(self.remoteplayers) > 0:
                mesh.broadcast("move:%s,%d,%d,%d,%d" %
                               (player.uid,
                                player.position[0],
                                player.position[1],
                                player.direction[0],
                                player.direction[1]))
            self.player_walk(player)

    def player_walk(self, player):
        oldposition = player.position
        newposition = player.animate(self.maze)
        if oldposition != newposition:
            self.markPointDirty(oldposition)
            self.markPointDirty(newposition)
            if player in self.localplayers:
                self.maze.map[player.previous[0]][player.previous[1]] = \
                    self.maze.SEEN
                if self.maze.map[newposition[0]][newposition[1]] == \
                        self.maze.GOAL:
                    self.finish(player)
            self.queue_draw()
            GObject.timeout_add(200, self.player_walk, player)
        """
        finish_delay = min(2 * len(self.allplayers), 6)
        if self.finish_time is not None and \
           time.time() > self.finish_time + finish_delay:
            self.harder()
        """

    def processEvent(self, event):
        """Process a single pygame event.  This includes keystrokes
        as well as multiplayer events from the mesh."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_in_use = 1
            self.prev_mouse_pos = pygame.mouse.get_pos()

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.mouse_in_use:
                new_mouse_pos = pygame.mouse.get_pos()
                mouse_movement = (new_mouse_pos[0] - self.prev_mouse_pos[0],
                                  new_mouse_pos[1] - self.prev_mouse_pos[1])

                if ((abs(mouse_movement[0]) > 10) or
                        (abs(mouse_movement[1]) > 10)):
                    player = self.localplayers[0]
                    player.hidden = False
                    # x movement larger
                    if abs(mouse_movement[0]) > abs(mouse_movement[1]):
                        # direction == pygame.K_RIGHT
                        if mouse_movement[0] > 0:
                            player.direction = (1, 0)
                        else:
                            # direction == pygame.K_LEFT
                            player.direction = (-1, 0)
                    else:
                        if mouse_movement[1] < 0:
                            # direction == pygame.K_UP
                            player.direction = (0, -1)
                        else:                     # direction == pygame.K_DOWN
                            player.direction = (0, 1)

                    if len(self.remoteplayers) > 0:
                        mesh.broadcast("move:%s,%d,%d,%d,%d" %
                                       (player.nick,
                                        player.position[0],
                                        player.position[1],
                                        player.direction[0],
                                        player.direction[1]))

            self.mouse_in_use = 0

        elif event.type == mesh.CONNECT:
            logging.debug("Connected to the mesh")

        elif event.type == mesh.PARTICIPANT_ADD:
            logging.debug('mesh.PARTICIPANT_ADD')

            def withBuddy(buddy):
                if event.handle == mesh.my_handle():
                    logging.debug("Me: %s - %s", buddy.props.nick,
                                  buddy.props.color)
                    # README: this is a workaround to use an unique
                    # identifier instead the nick of the buddy
                    # http://dev.laptop.org/ticket/10750
                    count = ''
                    for i, player in enumerate(self.localplayers):
                        if i > 0:
                            count = '-%d' % i
                        player.uid = mesh.my_handle() + count
                else:
                    logging.debug("Join: %s - %s", buddy.props.nick,
                                  buddy.props.color)
                    player = Player(buddy)
                    player.uid = event.handle
                    self.remoteplayers[event.handle] = player
                    self.allplayers.append(player)
                    self.allplayers.extend(player.bonusPlayers())
                    self.markPointDirty(player.position)
                    # send a test message to the new player
                    mesh.broadcast("Welcome %s" % player.nick)
                    # tell them which maze we are playing, so they can sync up
                    mesh.send_to(event.handle, "maze:%d,%d,%d,%d" %
                                 (self.game_running_time(),
                                  self.maze.seed,
                                  self.maze.width, self.maze.height))
                    for player in self.localplayers:
                        if not player.hidden:
                            mesh.send_to(event.handle,
                                         "move:%s,%d,%d,%d,%d" %
                                         (player.uid,
                                          player.position[0],
                                          player.position[1],
                                          player.direction[0],
                                          player.direction[1]))

            mesh.lookup_buddy(event.handle, callback=withBuddy)
        elif event.type == mesh.PARTICIPANT_REMOVE:
            logging.debug('mesh.PARTICIPANT_REMOVE')
            if event.handle in self.remoteplayers:
                player = self.remoteplayers[event.handle]
                logging.debug("Leave: %s", player.nick)
                self.markPointDirty(player.position)
                self.allplayers.remove(player)
                for bonusplayer in player.bonusPlayers():
                    self.markPointDirty(bonusplayer.position)
                    self.allplayers.remove(bonusplayer)
                del self.remoteplayers[event.handle]
        elif event.type == mesh.MESSAGE_UNI or \
                event.type == mesh.MESSAGE_MULTI:
            logging.debug('mesh.MESSAGE_UNI or mesh.MESSAGE_MULTI')
            if event.handle == mesh.my_handle():
                # ignore messages from ourself
                pass
            elif event.handle in self.remoteplayers:
                player = self.remoteplayers[event.handle]
                try:
                    self.handleMessage(player, event.content)
                except:
                    logging.debug("Error handling message: %s\n%s",
                                  event, sys.exc_info())
            else:
                logging.debug("Message from unknown buddy?")
        else:
            logging.debug('Unknown event: %r', event)

    def handleMessage(self, player, message):
        """Handle a message from a player on the mesh.
            We try to be forward compatible with new versions of Maze by
            allowing messages to have extra stuff at the end and ignoring
            unrecognized messages.

            We allow some messages to contain a different nick than the
            message's source player to support bonus players on that
            player's XO.

            The valid messages are:

            maze: running_time, seed, width, height
                A player has a differen maze.
                The one that has been running the longest will force all other
                players to use that maze.
                This way new players will join the existing game properly.

            move: nick, x, y, dx, dy
                A player's at x, y is now moving in direction dx, dy

            finish: nick, elapsed
                A player has finished the maze
        """
        logging.debug('mesh message: %s', message)

        # ignore messages from myself
        if player in self.localplayers:
            return
        if message.startswith("move:"):
            # a player has moved
            uid, x, y, dx, dy = message[5:].split(",")[:5]

            # README: this function (player.bonusPlayer) sometimes
            # returns None and the activity doesn't move the players.
            # This is because the name sent to the server is the
            # child's name but it returns something like this:
            #  * 6be01ff2bcfaa58eeacc7f10a57b77b65470d413@jabber.sugarlabs.org
            # So, we have set remote users with this kind of name but
            # we receive the reald child's name in the mesh message

            player = player.bonusPlayer(uid)
            player.hidden = False

            self.markPointDirty(player.position)
            player.position = (int(x), int(y))
            player.direction = (int(dx), int(dy))
            self.markPointDirty(player.position)
        elif message.startswith("maze:"):
            # someone has a different maze than us
            running_time, seed, width, height = map(lambda x: int(x),
                                                    message[5:].split(",")[:4])
            # is that maze older than the one we're already playing?
            # note that we use elapsed time instead of absolute time because
            # people's clocks are often set to something totally wrong
            if self.game_running_time() < running_time:
                # make note of the earlier time that the game really
                # started (before we joined)
                self.game_start_time = time.time() - running_time
                # use the new seed
                self.maze = Maze(seed, width, height)
                self.reset()
        elif message.startswith("finish:"):
            # someone finished the maze
            uid, elapsed = message[7:].split(",")[:2]
            player = player.bonusPlayer(uid)
            player.elapsed = float(elapsed)
            self.markPointDirty(player.position)
        else:
            # it was something I don't recognize...
            logging.debug("Message from %s: %s", player.nick, message)

    def harder(self):
        """Make a new maze that is harder than the current one."""
        # both width and height must be odd
        newHeight = self.maze.height + 2
        newWidth = int(newHeight * self.aspectRatio)
        if newWidth % 2 == 0:
            newWidth -= 1
        self.maze = Maze(self.maze.seed + 1, newWidth, newHeight)
        self.reset()
        # tell everyone which maze we are playing, so they can sync up
        if len(self.remoteplayers) > 0:
            # but fudge it a little so that we can be sure they'll use our maze
            self.game_start_time -= 10
            mesh.broadcast("maze:%d,%d,%d,%d" %
                           (self.game_running_time(), self.maze.seed,
                            self.maze.width, self.maze.height))

    def easier(self):
        """Make a new maze that is easier than the current one."""
        # both width and height must be odd
        newHeight = max(self.maze.height - 2, 5)
        newWidth = int(newHeight * self.aspectRatio)
        if newWidth % 2 == 0:
            newWidth -= 1
        self.maze = Maze(self.maze.seed + 1, newWidth, newHeight)
        self.reset()
        # tell everyone which maze we are playing, so they can sync up
        if len(self.remoteplayers) > 0:
            # but fudge it a little so that we can be sure they'll use our maze
            self.game_start_time -= 10
            mesh.broadcast("maze:%d,%d,%d,%d" %
                           (self.game_running_time(), self.maze.seed,
                            self.maze.width, self.maze.height))

    def finish(self, player):
        self.finish_time = time.time()
        player.elapsed = self.finish_time - self.level_start_time
        if len(self.remoteplayers) > 0:
            mesh.broadcast("finish:%s,%.2f" % (player.nick, player.elapsed))
