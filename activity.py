import gtk
import olpcgames
import pygame

from sugar.graphics.toolbutton import ToolButton
from gettext import gettext as _


class MazeActivity(olpcgames.PyGameActivity):
    game_name = 'game'
    game_title = _('Maze')
    game_size = None    # let olpcgames pick a nice size for us

    def build_toolbar(self):
        """Build our Activity toolbar for the Sugar system."""
        toolbar = super(MazeActivity, self).build_toolbar()

        separator = gtk.SeparatorToolItem()
        separator.set_expand(True)
        separator.set_draw(False)
        toolbar.insert(separator, 0)

        harder_button = ToolButton('create-harder')
        harder_button.set_tooltip(_('Harder level'))
        harder_button.connect('clicked', self._harder_button_cb)
        toolbar.insert(harder_button, 2)
        harder_button.show()

        easier_button = ToolButton('create-easier')
        easier_button.set_tooltip(_('Easier level'))
        easier_button.connect('clicked', self._easier_button_cb)
        toolbar.insert(easier_button, 2)
        easier_button.show()

        return toolbar

    def _easier_button_cb(self, button):
        pygame.event.post(olpcgames.eventwrap.Event(
            pygame.USEREVENT, action='easier_button'))

    def _harder_button_cb(self, button):
        pygame.event.post(olpcgames.eventwrap.Event(
            pygame.USEREVENT, action='harder_button'))
