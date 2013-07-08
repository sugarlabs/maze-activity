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

import math
import gtk
import unicodedata

from sugar.graphics import style

class Player:
    def __init__(self, buddy, shape='circle'):
        self.buddy = buddy
        name = buddy.props.nick.decode('utf-8')
        self.nick = unicodedata.normalize('NFC', name)
        colors = buddy.props.color.split(",")
        self.fg = style.Color(colors[0])
        self.bg = style.Color(colors[1])

        # this field is None when the activity is not shared and when
        # the user shared it this field will become to
        # "olpcgames.mesh.my_handle()"
        self.uid = None

        self.shape = shape
        self.hidden = False
        self.bonusplayers = None
        self.reset()

    def draw(self, context, bounds, size):
        rect = gtk.gdk.Rectangle(bounds.x + self.position[0] * size,
                                 bounds.y + self.position[1] * size, size,
                                 size)
        context.save()
        if self.shape == 'circle':
            context.arc(rect.x + size / 2, rect.y + size / 2, size, 0,
                        2 * math.pi)
        elif self.shape == 'square':
            context.rectangle(rect.x, rect.y, size, size)
        elif self.shape == 'triangle':
            context.new_path()
            context.move_to(rect.x, rect.y + size)
            context.line_to(rect.x + size / 2, rect.y)
            context.line_to(rect.x + size, rect.y + size)
            context.close_path()

        context.set_source_rgba(*self.bg.get_rgba())
        context.set_line_width(size / 10.)
        context.fill_preserve()
        context.set_source_rgba(*self.fg.get_rgba())
        context.stroke()
        context.restore()

    def reset(self):
        self.direction = (0, 0)
        self.position = (1, 1)
        self.previous = (1, 1)
        self.elapsed = None

    def animate(self, maze):
        # if the player finished the maze, then don't move
        if maze.map[self.position[0]][self.position[1]] == maze.GOAL:
            self.direction = (0, 0)
        if self.direction == (0, 0):
            return self.position
        if self.canGo(self.direction, maze):
            self.move(self.direction, maze)
            self.keepGoing(self.direction, maze)
        else:
            self.direction = (0, 0)
        return self.position

    def move(self, direction, maze):
        """Move the player in a given direction (deltax,deltay)"""
        newposition = (self.position[0] + direction[0],
                       self.position[1] + direction[1])
        self.previous = self.position
        self.position = newposition

    def canGo(self, direction, maze):
        """Can the player go in this direction without bumping into
           something?
        """
        newposition = (self.position[0] + direction[0],
                       self.position[1] + direction[1])
        return maze.validMove(newposition[0], newposition[1])

    def cameFrom(self, direction):
        """Note the position/direction that we just came from."""
        return self.previous == (self.position[0] + direction[0],
                                 self.position[1] + direction[1])

    def keepGoing(self, curdir, maze):
        """Try to keep going if the direction is obvious.
        This prevents the player from having to use the arrows to navigate
        every single twist and turn of large mazes."""
        # possible directions are fwd, turn left, turn right
        directions = [curdir, (curdir[1], curdir[0]),
                      (- curdir[1], - curdir[0])]
        # remove any that are blocked
        for d in list(directions):
            if not self.canGo(d, maze):
                directions.remove(d)
        # is there only one possible direction?
        if len(directions) == 1:
            self.direction = directions[0]
        else:
            self.direction = (0, 0)

    def bonusPlayers(self):
        if self.bonusplayers is None:
            self.bonusplayers = []
            self.bonusplayers.append(Player(self.buddy, 'square'))
            self.bonusplayers.append(Player(self.buddy, 'triangle'))

            count = 1
            for player in self.bonusplayers:
                player.nick = self.nick + "-%d" % count
                if self.uid is not None:
                    player.uid = self.uid + "-%d" % count
                player.hidden = True
                count += 1

        return self.bonusplayers

    def bonusPlayer(self, uid):
        if uid == self.uid:
            return self
        for bonusplayer in self.bonusPlayers():
            if bonusplayer.uid == uid:
                return bonusplayer
