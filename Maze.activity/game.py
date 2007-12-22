# Maze.activity
# A simple multi-player maze game for the XO laptop.
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
#     Foobar is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with Foobar.  If not, see <http://www.gnu.org/licenses/>.


import sys
import os
import time

import pygame
import olpcgames

import olpcgames.pausescreen as pausescreen
import olpcgames.mesh as mesh
from olpcgames.util import get_bundle_path
from sugar.presence import presenceservice

bundlepath = get_bundle_path()
presenceService = presenceservice.get_instance()

# # MakeBot on OS X - useful for prototyping with pygame
# # http://stratolab.com/misc/makebot/
# sys.path.append("/Applications/MakeBot-1.4/site-packages")
# import pygame
# pygame.init()
# bundlepath = ""
# canvas_size = (1200,825)

from maze import Maze
from player import Player

class MazeGame:
    """Maze game controller.
    This class handles all of the game logic, event loop, mulitplayer, etc."""
    
    # Munsell color values http://wiki.laptop.org/go/Munsell
    N10	 = (255, 255, 255)
    N9p5 = (243, 243, 243)
    N9	 = (232, 232, 232)
    N8	 = (203, 203, 203)
    N7	 = (179, 179, 179)
    N6	 = (150, 150, 150)
    N5	 = (124, 124, 124)
    N4	 = ( 97,  97,  97)
    N3	 = ( 70,  70,  70)
    N2	 = ( 48,  48,  48)
    N1	 = ( 28,  28,  28)
    N0	 = (  0,   0,   0)
    EMPTY_COLOR = N8
    SOLID_COLOR = N1
    TRAIL_COLOR = N10
    GOAL_COLOR  = (0x00, 0xff, 0x00)
    WIN_COLOR   = (0xff, 0xff, 0x00)

    def __init__(self, screen):
        xoOwner = presenceService.get_owner()
        self.localplayer = Player(xoOwner)
        # keep a list of active players, starting empty
        self.players = {'xoOwner':self.localplayer}
        
        self.screen = screen
        canvas_size = screen.get_size()
        self.aspectRatio = canvas_size[0] / float(canvas_size[1])
        
        # start with a small maze
        self.start_time = time.time()
        self.maze = Maze(int(self.start_time), int(9*self.aspectRatio), 9)
        self.reset()
        self.frame = 0
        
        self.font = pygame.font.Font(None, 30)
        
        # support arrow keys, game pad arrows and game pad buttons
        self.upkeys = (pygame.K_UP, pygame.K_KP8, pygame.K_KP9)
        self.downkeys = (pygame.K_DOWN, pygame.K_KP2, pygame.K_KP3)
        self.leftkeys = (pygame.K_LEFT, pygame.K_KP4, pygame.K_KP7)
        self.rightkeys = (pygame.K_RIGHT, pygame.K_KP6, pygame.K_KP1)
        self.allkeys = self.upkeys + self.downkeys + self.leftkeys + self.rightkeys

    def reset(self):
        """Reset the game state.  Everyone starts in the top-left.
        The goal starts in the bottom-right corner."""
        self.running = True
        self.start_time = time.time()
        self.finish_time = None
        for player in self.players.values():
            player.reset()
        self.goal = (self.maze.width-2, self.maze.height-2)
        self.dirtyRect = None
        
        # clear and mark the whole screen as dirty
        self.screen.fill((0,0,0))
        self.markRectDirty(pygame.Rect(0,0,99999,99999))

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
        rect = pygame.Rect(pt[0], pt[1], 1, 1)
        self.markRectDirty(rect)
        
    def processEvent(self, event):
        """Process a single pygame event.  This includes keystrokes
        as well as multiplayer events from the mesh."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                self.harder()
            elif event.key == pygame.K_MINUS:
                self.easier()
            elif event.key in self.upkeys:
                self.localplayer.direction=(0,-1)
                if len(self.players)>1:
                    mesh.broadcast("move:%d,%d,%d,%d" % (self.localplayer.position[0], self.localplayer.position[1], self.localplayer.direction[0], self.localplayer.direction[1]))
            elif event.key in self.downkeys:
                self.localplayer.direction=(0,1)
                if len(self.players)>1:
                    mesh.broadcast("move:%d,%d,%d,%d" % (self.localplayer.position[0], self.localplayer.position[1], self.localplayer.direction[0], self.localplayer.direction[1]))
            elif event.key in self.leftkeys:
                self.localplayer.direction=(-1,0)
                if len(self.players)>1:
                    mesh.broadcast("move:%d,%d,%d,%d" % (self.localplayer.position[0], self.localplayer.position[1], self.localplayer.direction[0], self.localplayer.direction[1]))
            elif event.key in self.rightkeys:
                self.localplayer.direction=(1,0)
                if len(self.players)>1:
                    mesh.broadcast("move:%d,%d,%d,%d" % (self.localplayer.position[0], self.localplayer.position[1], self.localplayer.direction[0], self.localplayer.direction[1]))
        elif event.type == pygame.KEYUP:
            pass
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pass
        elif event.type == mesh.CONNECT:
            print "Connected to the mesh."
        elif event.type == mesh.PARTICIPANT_ADD:
            buddy = mesh.get_buddy(event.handle)
            if event.handle == mesh.my_handle():
                print "Me:", buddy.props.nick, buddy.props.color
                del self.players['xoOwner']
                self.players[event.handle] = self.localplayer
            else:
                print "Join:", buddy.props.nick, buddy.props.color
                player = Player(buddy)
                self.players[event.handle] = player
                self.markPointDirty(player.position)
                # send a test message to the new player
                mesh.broadcast("Welcome %s" % player.nick)
                # tell them which maze we are playing, so they can sync up
                mesh.send_to(event.handle, "maze:%d,%d,%d" % (self.maze.seed, self.maze.width, self.maze.height))
        elif event.type == mesh.PARTICIPANT_REMOVE:
            if self.players.has_key(event.handle):
                player = self.players[event.handle]
                print "Leave:", player.nick
                self.markPointDirty(player.position)
                del self.players[event.handle]
        elif event.type == mesh.MESSAGE_UNI or event.type == mesh.MESSAGE_MULTI:
            buddy = mesh.get_buddy(event.handle)
            #print "Message from %s / %s: %s" % (buddy.props.nick, event.handle, event.content)
            if self.players.has_key(event.handle):
                player = self.players[event.handle]
                self.handleMessage(player, event.content)
            else:
                print "Message from unknown buddy?"
        else:
            print "Unknown event:", event

    def handleMessage(self, player, message):
        """Handle a message from a player on the mesh.  The messages are:
            maze:seed,width,height
                A player has a differen maze.
                The one with the lowest seed # will force all other players to use that maze.
            position:x,y
                A player has moved to x,y
        """
        # ignore messages from myself
        if player == self.localplayer:
            return
        if message.startswith("move:"):
            # a player has moved
            x,y,dx,dy = message[5:].split(",")
            self.markPointDirty(player.position)
            player.position = (int(x),int(y))
            player.direction = (int(dx),int(dy))
            self.markPointDirty(player.position)
        elif message.startswith("maze:"):
            # someone has a different maze than us
            seed,width,height = map(lambda x: int(x), message[5:].split(","))
            # is that a different maze than the one we're already playing?
            if self.maze.seed>seed: # or self.maze.width!=width or self.maze.height!=height:
                # use the smaller seed, so the players who are already playing
                # won't have their maps yanked out from under them when someone new joins.
                self.maze = Maze(seed, width, height)
                self.reset()
        elif message.startswith("finish:"):
            # someone finished the maze
            elapsed = float(message[7:])
            player.elapsed = elapsed
            self.markPointDirty(player.position)
        else:
            # it was something I don't recognize...
            print "Message from %s: %s" % (player.nick, message)
            pass

    def arrowKeysPressed(self):
        keys = pygame.key.get_pressed()
        for key in self.allkeys:
            if keys[key]:
                return True
        return False

    def run(self):
        """Run the main loop of the game."""
        # lets draw once before we enter the event loop
        self.draw()
        pygame.display.flip()
        clock = pygame.time.Clock()
        
        while self.running:
            self.frame += 1
            # process all queued events
            for event in pausescreen.get_events(sleep_timeout=30):
                self.processEvent(event)
            
            self.animate()
            self.draw()
            
            pygame.display.flip()
            # don't animate faster than about 20 frames per second
            # this keeps the speed reasonable and limits cpu usage
            clock.tick(20)

    def harder(self):
        """Make a new maze that is harder than the current one."""
        # both width and height must be odd
        newHeight = self.maze.height+2
        newWidth = int(newHeight * self.aspectRatio)
        if newWidth % 2 == 0:
            newWidth -= 1
        # use a smaller seed, so that other players will use this maze also
        self.maze = Maze(self.maze.seed-1, newWidth, newHeight)
        self.reset()
        # tell everyone which maze we are playing, so they can sync up
        if len(self.players)>1:
            mesh.broadcast("maze:%d,%d,%d" % (self.maze.seed, self.maze.width, self.maze.height))
        
    def easier(self):
        """Make a new maze that is easier than the current one."""
        # both width and height must be odd
        newHeight = max(self.maze.height-2, 5)
        newWidth = int(newHeight * self.aspectRatio)
        if newWidth % 2 == 0:
            newWidth -= 1
        # use a smaller seed, so that other players will use this maze also
        self.maze = Maze(self.maze.seed-1, newWidth, newHeight)
        self.reset()
        # tell everyone which maze we are playing, so they can sync up
        if len(self.players)>1:
            mesh.broadcast("maze:%d,%d,%d" % (self.maze.seed, self.maze.width, self.maze.height))

    def animate(self):
        """Animate one frame of action."""
        
        for player in self.players.values():
            oldposition = player.position
            newposition = player.animate(self.maze)
            if oldposition != newposition:
                self.markPointDirty(oldposition)
                self.markPointDirty(newposition)
                if player == self.localplayer:
                    self.maze.map[player.previous[0]][player.previous[1]] = self.maze.SEEN
                    if newposition == self.goal:
                        self.finish()
                        
        if self.finish_time is not None and time.time() > self.finish_time+5:
            self.harder()
    
    def finish(self):
        self.finish_time = time.time()
        self.localplayer.elapsed = self.finish_time - self.start_time
        if len(self.players)>1:
            mesh.broadcast("finish:%.2f" % (self.localplayer.elapsed))
    
    def draw(self):
        """Draw the current state of the game.
        This makes use of the dirty rectangle to reduce CPU load."""
        if self.dirtyRect is None:
            return
        
        # compute the size of the tiles given the screen size, etc.
        size = self.screen.get_size()
        self.tileSize = min(size[0] / self.maze.width, size[1] / self.maze.height)
        self.offsetX = (size[0] - self.tileSize * self.maze.width)/2
        self.offsetY = (size[1] - self.tileSize * self.maze.height)/2
        self.outline = int(self.tileSize/5)
        
        # compute the area that needs to be redrawn
        left = max(0, self.dirtyRect.left)
        right = min(self.maze.width, self.dirtyRect.right)
        top = max(0, self.dirtyRect.top)
        bottom = min(self.maze.height, self.dirtyRect.bottom)
        
        # loop over the dirty rect and draw
        for x in range(left, right):
            for y in range(top, bottom):
                rect = pygame.Rect(self.offsetX + x*self.tileSize, self.offsetY + y*self.tileSize, self.tileSize, self.tileSize)
                if self.maze.map[x][y] == self.maze.EMPTY:
                    pygame.draw.rect(self.screen, self.EMPTY_COLOR, rect, 0)
                elif self.maze.map[x][y] == self.maze.SOLID:
                    pygame.draw.rect(self.screen, self.SOLID_COLOR, rect, 0)
                elif self.maze.map[x][y] == self.maze.SEEN:
                    pygame.draw.rect(self.screen, self.EMPTY_COLOR, rect, 0)
                    dot = rect.inflate(-self.outline*2, -self.outline*2)
                    pygame.draw.ellipse(self.screen, self.TRAIL_COLOR, dot, 0)
                else:
                    pygame.draw.rect(self.screen, (0xff, 0x00, 0xff), rect, 0)
        
        # draw the goal
        rect = self.offsetX+self.goal[0]*self.tileSize, self.offsetY+self.goal[1]*self.tileSize, self.tileSize, self.tileSize
        pygame.draw.rect(self.screen, self.GOAL_COLOR, rect, 0)

        # draw all remote players
        remotePlayers = list(self.players.values())
        remotePlayers.remove(self.localplayer)
        for player in remotePlayers:
            self.drawPlayer(player)

        # draw the local player last so he/she will show up on top
        self.drawPlayer(self.localplayer)

        # draw the elapsed time for each player that has finished
        finishedPlayers = filter(lambda p: p.elapsed is not None, self.players.values())
        finishedPlayers.sort(lambda a,b: cmp(a.elapsed,b.elapsed))
        y = 0
        for player in finishedPlayers:
            fg, bg = player.colors
            text = "%3.2f - %s" % (player.elapsed, player.nick)
            textimg = self.font.render(text, 1, fg)
            textwidth, textheight = self.font.size(text)
            rect = pygame.Rect(8, y+4, textwidth, textheight)
            bigrect = rect.inflate(16,8)
            pygame.draw.rect(self.screen, bg, bigrect, 0)
            pygame.draw.rect(self.screen, fg, bigrect, 2)
            self.screen.blit(textimg, rect)
            
            y += bigrect.height + 4

        # clear the dirty rect so nothing will be drawn until there is a change
        self.dirtyRect = None

    def drawPlayer(self, player):
        fg, bg = player.colors
        posX, posY = player.position
        rect = pygame.Rect(self.offsetX+posX*self.tileSize,
                           self.offsetY+posY*self.tileSize,
                           self.tileSize, self.tileSize)
        pygame.draw.ellipse(self.screen, fg, rect, 0)
        dot = rect.inflate(-self.outline, -self.outline)
        pygame.draw.ellipse(self.screen, bg, dot, 0)

def main():
    """Run a game of Maze."""
    #canvas_size = 1024,768-75
    #screen = pygame.display.set_mode(canvas_size)

    # ask pygame how big the screen is, leaving a little room for the toolbar
    toolbarheight = 75
    pygame.display.init()
    maxX,maxY = pygame.display.list_modes()[0]
    screen = pygame.display.set_mode( ( maxX, maxY-toolbarheight ) )

    game = MazeGame(screen)
    game.run()

if __name__ == '__main__':
    main()

