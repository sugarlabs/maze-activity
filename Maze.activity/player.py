from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor

class Player:
    def __init__(self, buddy):
        self.nick = buddy.props.nick
        colors = buddy.props.color.split(",")
        def string2Color(str):
            return (int(str[1:3],16), int(str[3:5],16), int(str[5:7],16))
        self.colors = map(string2Color, colors)
        self.reset()

    def reset(self):
        self.direction = (0,0)
        self.position = (1,1)
        self.previous = (1,1)
        self.elapsed = None
    
    def animate(self, maze):
        # if the player finished the maze, then don't move
        if self.elapsed is not None:
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

