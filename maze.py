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

import random
import logging


class Rectangle:

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_bounds(self):
        return (self.x, self.y, self.width, self.height)


class Maze:
    SOLID = 0
    EMPTY = 1
    SEEN = 2
    GOAL = 3
    HOLE = 4

    def __init__(self, seed, width, height, hole=False):
        # use the seed given to us to make a pseudo-random number generator
        # we will use that to generate the maze, so that other players can
        # generate the exact same maze given the same seed.
        logging.debug("Generating maze: seed %d, width %d, height %d", seed,
                      width, height)
        self.seed = seed
        self.generator = random.Random(seed)
        self.width, self.height = width, height
        self.map = []
        self.bounds = Rectangle(0, 0, width, height)
        for x in range(0, width):
            self.map.append([self.SOLID] * self.height)

        startx = self.generator.randrange(1, width, 2)
        starty = self.generator.randrange(1, height, 2)
        self.dig(startx, starty)
        if(hole is True):
            self._generate_holes()

        for row in self.map:
            logging.debug(row)

    def _generate_holes(self):
        if self.width <= 15:
            max_holes = 0
        else:
            max_holes = int(self.width / 7) - 1

        holes = 0
        while holes != max_holes:
            x = self.generator.randrange(1, self.width, 1)
            y = self.generator.randrange(1, self.height, 1)

            if(self.validHole(x, y)):
                self.map[x][y] = self.HOLE
                holes += 1

    def _check_point_in_rectangle(self, rectangle, x, y):
        if x < rectangle.x or y < rectangle.y:
            return False
        if x >= rectangle.x + rectangle.width or \
                y >= rectangle.y + rectangle.height:
            return False
        return True

    def validHole(self, x, y):
        if x > 1 and y > 1 and x < self.width - 2 and y < self.height - 2 \
                and self.map[x][y] != self.SOLID:
            left = (self.map[x - 1][y] != self.SOLID)
            right = (self.map[x + 1][y] != self.SOLID)
            up = (self.map[x][y + 1] != self.SOLID)
            down = (self.map[x][y - 1] != self.SOLID)

            return (left and right and not (up or down)) or \
                (up and down and not (left or right))
        return False

    def validMove(self, x, y):
        return self._check_point_in_rectangle(self.bounds, x, y) and \
            self.map[x][y] != self.SOLID

    def validDig(self, x, y):
        return self._check_point_in_rectangle(self.bounds, x, y) and \
            self.map[x][y] == self.SOLID

    def validDigDirections(self, x, y):
        directions = []
        if self.validDig(x, y - 2):
            directions.append((0, -1))
        if self.validDig(x + 2, y):
            directions.append((1, 0))
        if self.validDig(x, y + 2):
            directions.append((0, 1))
        if self.validDig(x - 2, y):
            directions.append((-1, 0))
        return directions

    def digRecursively(self, x, y):
        """This works great, except for python's lame limit on
           recursion depth.
        """
        self.map[x][y] = self.EMPTY
        directions = self.validDigDirections(x, y)
        while len(directions) > 0:
            direction = self.generator.choice(directions)
            self.map[x + direction[0]][y + direction[1]] = self.EMPTY
            self.dig(x + direction[0] * 2, y + direction[1] * 2)
            directions = self.validDigDirections(x, y)

    def dig(self, x, y):
        stack = [(x, y)]
        while len(stack) > 0:
            x, y = stack[-1]
            self.map[x][y] = self.EMPTY
            directions = self.validDigDirections(x, y)
            if len(directions) > 0:
                direction = self.generator.choice(directions)
                self.map[x + direction[0]][y + direction[1]] = self.EMPTY
                stack.append((x + direction[0] * 2, y + direction[1] * 2))
            else:
                stack.pop()
