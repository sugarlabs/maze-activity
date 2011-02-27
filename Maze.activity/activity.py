import olpcgames
from gettext import gettext as _



class MazeActivity(olpcgames.PyGameActivity):
    game_name = 'maze'
    game_title = _('Maze')
    game_size = None    # let olpcgames pick a nice size for us
