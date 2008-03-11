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

from olpcgames.util import get_bundle_path
bundlepath = get_bundle_path()
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor
import pygame
import re, os

class Player:
    def __init__(self, buddy, shape='circle'):
        self.buddy = buddy
        self.nick = buddy.props.nick
        colors = buddy.props.color.split(",")
        def string2Color(str):
            return (int(str[1:3],16), int(str[3:5],16), int(str[5:7],16))
        self.colors = map(string2Color, colors)
        self.shape = shape
        self.hidden = False
        self.bonusplayers = None
        self.reset()

    def draw(self, screen, bounds, size):
        rect = pygame.Rect(bounds.x+self.position[0]*size, bounds.y+self.position[1]*size, size, size)
        border = size / 10.
        center = rect.inflate(-border*2, -border*2)
        fg, bg = self.colors
        if self.shape == 'circle':
            pygame.draw.ellipse(screen, fg, rect, 0)
            pygame.draw.ellipse(screen, bg, center, 0)
        elif self.shape == 'square':
            pygame.draw.rect(screen, fg, rect, 0)
            pygame.draw.rect(screen, bg, center, 0)
        elif self.shape == 'triangle':
            rect = rect.inflate(-1,-1)
            pts = [rect.bottomleft, rect.midtop, rect.bottomright]
            pygame.draw.polygon(screen, fg, pts, 0)
            pts = [(pts[0][0]+border*1.394, pts[0][1]-border),
                   (pts[1][0],              pts[1][1]+border*2.236),
                   (pts[2][0]-border*1.394, pts[2][1]-border)]
            pygame.draw.polygon(screen, bg, pts, 0)

    def reset(self):
        self.direction = (0,0)
        self.position = (1,1)
        self.previous = (1,1)
        self.elapsed = None
    
    def animate(self, maze):
        # if the player finished the maze, then don't move
        if maze.map[self.position[0]][self.position[1]] == maze.GOAL:
            self.direction=(0,0)
        if self.direction == (0,0):
            return self.position
        if self.canGo(self.direction, maze):
            self.move(self.direction, maze)
            self.keepGoing(self.direction, maze)
        else:
            self.direction = (0,0)
        return self.position
    
    def move(self, direction, maze):
        """Move the player in a given direction (deltax,deltay)"""
        newposition = (self.position[0]+direction[0], self.position[1]+direction[1])
        self.previous = self.position
        self.position = newposition

    def canGo(self, direction, maze):
        """Can the player go in this direction without bumping into something?"""
        newposition = (self.position[0]+direction[0], self.position[1]+direction[1])
        return maze.validMove(newposition[0], newposition[1])

    def cameFrom(self, direction):
        """Note the position/direction that we just came from."""
        return self.previous == (self.position[0]+direction[0], self.position[1]+direction[1])

    def keepGoing(self, curdir, maze):
        """Try to keep going if the direction is obvious.
        This prevents the player from having to use the arrows to navigate
        every single twist and turn of large mazes."""
        # possible directions are fwd, turn left, turn right
        directions = [curdir, (curdir[1],curdir[0]), (-curdir[1],-curdir[0])]
        # remove any that are blocked
        for d in list(directions):
            if not self.canGo(d, maze):
                directions.remove(d)
        # is there only one possible direction?
        if len(directions) == 1:
       	    self.direction = directions[0]
        else:
            self.direction = (0,0)

    def bonusPlayers(self):
        if self.bonusplayers is None:
            self.bonusplayers = []
            self.bonusplayers.append(Player(self.buddy,'square'))
            self.bonusplayers.append(Player(self.buddy,'triangle'))

            count = 2
            for player in self.bonusplayers:
                player.nick = self.nick + "-%d" % count
                player.hidden = True
                count += 1

        return self.bonusplayers

    def bonusPlayer(self, nick):
        if nick == self.nick:
            return self
        for bonusplayer in self.bonusPlayers():
            if bonusplayer.nick == nick:
                return bonusplayer

