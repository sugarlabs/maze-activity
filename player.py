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
import unicodedata

from sugar3.graphics import style

from maze import Rectangle


class Player:
    def __init__(self, buddy, look='centre'):
        self.buddy = buddy
        name = buddy.props.nick
        self.nick = unicodedata.normalize('NFC', name)
        colors = buddy.props.color.split(",")
        self.fg = style.Color(colors[0])
        self.bg = style.Color(colors[1])
        self.victories = 0

        # this field is None when the activity is not shared and when
        # the user shared it this field will become to
        # "olpcgames.mesh.my_handle()"
        self.uid = None

        self.look = look
        self.hidden = False
        self.bonusplayers = None
        self.reset()
        self.falling = 0

    def draw(self, ctx, bounds, size, hole_color):
        line_width = size / 32.
        rect = Rectangle(bounds.x + self.position[0] * size,
                         bounds.y + self.position[1] * size, size,
                         size)

        ctx.save()

        # centre of face
        cx = rect.x + size / 2
        cy = rect.y + size / 2

        bg = {
            'centre': self.bg.get_rgba(),
            'left': [0.45, 0.45, 0.45, 1.],
            'right': [0.55, 0.55, 0.55, 1.]
        }
        fg = {
            'centre': self.fg.get_rgba(),
            'left': [1., 1., 1., 1.],
            'right': [0., 0., 0., 1.]
        }
        if self.falling > 20:
            fg = {
                'centre': hole_color,
                'left': [0.45, 0.45, 0.45, 1.],
                'right': [0.55, 0.55, 0.55, 1.]
            }
            size = self.falling

        # a background filled circle with foreground border
        ctx.arc(cx, cy, (size / 2 - line_width), 0, 2 * math.pi)
        ctx.set_source_rgba(*bg[self.look])
        ctx.set_line_width(line_width)
        ctx.fill_preserve()
        ctx.set_source_rgba(*fg[self.look])
        ctx.stroke()

        # two eyes
        for ex in [cx - 0.20 * size, cx + 0.20 * size]:
            # conjunctiva
            er = 0.14 * size
            ey = cy - 0.05 * size
            ctx.arc(ex, ey, er, 0, 2 * math.pi)
            ctx.set_source_rgba(1., 1., 1., 1.)
            ctx.fill()
            # iris, pupil
            er = 0.04 * size
            if self.look == 'left':
                ex -= 0.04 * size
            elif self.look == 'right':
                ex += 0.04 * size
            else:
                ey += 0.02 * size
            ctx.arc(ex, ey, er, 0, 2 * math.pi)
            ctx.set_source_rgba(0., 0., 0., 1.)
            ctx.fill()

        # mouth
        (lx, ly) = (cx - 0.25 * size, cy + 0.15 * size)  # left corner
        (bx, by) = (cx, cy + 0.25 * size)  # weak control
        (rx, ry) = (cx + 0.25 * size, cy + 0.15 * size)  # right corner
        (tx, ty) = (cx, cy + 0.50 * size)  # strong control
        ctx.set_source_rgba(1., 1., 1., 1.)
        ctx.curve_to(lx, ly, bx, by, rx, ry)  # upper lip
        ctx.curve_to(rx, ry, tx, ty, lx, ly)  # lower lip
        ctx.fill_preserve()
        ctx.stroke()

        ctx.restore()

    def reset(self):
        self.direction = (0, 0)
        self.position = (1, 1)
        self.previous = (1, 1)
        self.elapsed = None
        if self.look != 'centre':
            self.hidden = True

    def animate(self, maze, size, change_direction=True):
        # if player is falling
        if self.falling > 0:
            self.falling -= max(1, int(size / 6))
            if self.falling <= 20:
                self.falling = 0
                self.reset()
            return (True, self.position)

        # if the player finished the maze, then don't move
        if maze.map[self.position[0]][self.position[1]] == maze.GOAL:
            self.direction = (0, 0)
            return (False, self.position)

        if maze.map[self.position[0]][self.position[1]] == \
                maze.HOLE or (maze.map[self.position[0]][self.position[1]] ==
                              maze.PASSED and self.falling > 0):
            self.direction = (0, 0)
            return (True, self.position)

        if self.canGo(self.direction, maze):
            self.move(self.direction, maze)
            if change_direction:
                self.keepGoing(self.direction, maze)
            return (True, self.position)

        self.direction = (0, 0)
        return (False, self.position)

    def move(self, direction, maze):
        """Move the player in a given direction (deltax,deltay)"""
        newposition = (self.position[0] + direction[0],
                       self.position[1] + direction[1])
        self.previous = self.position
        self.position = newposition

    def fallThroughHole(self, tile_size):
        self.falling = tile_size

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
            self.bonusplayers.append(Player(self.buddy, 'left'))
            self.bonusplayers.append(Player(self.buddy, 'right'))

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
