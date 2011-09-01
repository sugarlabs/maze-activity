import olpcgames
from gettext import gettext as _



class MazeActivity(olpcgames.PyGameActivity):
    game_name = 'game'
    game_title = _('Maze')
    game_size = None    # let olpcgames pick a nice size for us
