import olpcgames
import pygame
from sugar.graphics.toolbutton import ToolButton
from gettext import gettext as _

class MazeActivity(olpcgames.PyGameActivity):
    game_name = 'game'
    game_title = 'Maze'
    game_size = None    # let olpcgames pick a nice size for us

    def build_toolbar( self ):
        """Build our Activity toolbar for the Sugar system."""
        toolbar = super( MazeActivity, self ).build_toolbar()
        
        # Add buttons that will make the maze harder or easier
        toolbar.harder = ToolButton('activity-harder')
        toolbar.harder.set_tooltip(_('Harder'))
        toolbar.harder.connect('clicked', self._harder_cb)
        toolbar.insert(toolbar.harder, 2)
        toolbar.harder.show()
        
        toolbar.easier = ToolButton('activity-easier')
        toolbar.easier.set_tooltip(_('Easier'))
        toolbar.easier.connect('clicked', self._easier_cb)
        toolbar.insert(toolbar.easier, 2)
        toolbar.easier.show()
        
        return toolbar

    def _harder_cb(self, button):
        pygame.event.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action='harder'))
        
    def _easier_cb(self, button):
        pygame.event.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action='easier'))
