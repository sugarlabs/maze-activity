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
from pygame import Rect

class Maze:
    SOLID = 0
    EMPTY = 1
    SEEN = 2
    GOAL = 3
    
    def __init__(self, seed, width, height):
        # use the seed given to us to make a pseudo-random number generator
        # we will use that to generate the maze, so that other players can
        # generate the exact same maze given the same seed.
        print "Generating maze:%d,%d,%d" % (seed, width, height)
        self.seed = seed
        self.generator = random.Random(seed)
        self.width, self.height = width, height
        self.map = []
        self.bounds = Rect(0,0,width,height)

        for x in range(0, width):
            self.map.append([self.SOLID] * self.height)

        startx = self.generator.randrange(1,width,2)
        starty = self.generator.randrange(1,height,2)
        self.dig(startx,starty)

    def validMove(self, x, y):
        return self.bounds.collidepoint(x,y) and self.map[x][y]!=self.SOLID

    def validDig(self, x, y):
        return self.bounds.collidepoint(x,y) and self.map[x][y]==self.SOLID
  
    def validDigDirections(self, x, y):
        directions = []
        if self.validDig(x,y-2):
            directions.append((0,-1))
        if self.validDig(x+2,y):
            directions.append((1,0))
        if self.validDig(x,y+2):
            directions.append((0,1))
        if self.validDig(x-2,y):
            directions.append((-1,0))
        return directions

    def fill(self, color):
        for y in range(0, height):
            for x in range(0, width):
                self.map[x][y] = color

    def digRecursively(self, x, y):
        """This works great, except for python's lame limit on recursion depth."""
        self.map[x][y] = self.EMPTY
        directions = self.validDigDirections(x,y)
        while len(directions) > 0:
            direction = self.generator.choice(directions)
            self.map[x+direction[0]][y+direction[1]] = self.EMPTY
            self.dig(x+direction[0]*2, y+direction[1]*2)
            directions = self.validDigDirections(x,y)

    def dig(self, x, y):
        stack = [(x,y)]
        while len(stack) > 0:
            x, y = stack[-1]
            self.map[x][y] = self.EMPTY
            directions = self.validDigDirections(x,y)
            if len(directions) > 0:
                direction = self.generator.choice(directions)
                self.map[x+direction[0]][y+direction[1]] = self.EMPTY
                stack.append((x+direction[0]*2, y+direction[1]*2))
            else:
                stack.pop()
