"""Implement Pygame's font interface using Pango for international support

Depends on:

    pygtk (to get the pango context)
    pycairo (for the pango rendering context)
    python-pango (obviously)
    pygame (obviously)
"""
import pango
import logging
import cairo
import pangocairo
import pygame.rect, pygame.image
import gtk
import struct
from pygame import surface

log = logging.getLogger( 'pangofont' )
#log.setLevel( logging.DEBUG )

# Install myself on top of pygame.font
def install():
    """Replace Pygame's font module with this module"""
    log.info( 'installing' )
    from olpcgames import pangofont
    import pygame
    pygame.font = pangofont
    import sys
    sys.modules["pygame.font"] = pangofont

class PangoFont(object):
    """Base class for a pygame.font.Font-like object drawn by Pango."""
    def __init__(self, family=None, size=None, bold=False, italic=False, fd=None):
        """If you know what pango.FontDescription (fd) you want, pass it in as
        'fd'.  Otherwise, specify any number of family, size, bold, or italic,
        and we will try to match something up for you."""

        # Always set the FontDescription (FIXME - only set it if the user wants
        # to change something?)
        if fd is None:
            fd = pango.FontDescription()
            if family is not None:
                fd.set_family(family)
            if size is not None:
                fd.set_size(size*1000)

            if bold:
                fd.set_weight(pango.WEIGHT_BOLD)
            if italic:
                fd.set_style(pango.STYLE_OBLIQUE)

        self.fd = fd

    def render(self, text, antialias=True, color=(255,255,255), background=None ):
        """Render the font onto a new Surface and return it.
        We ignore 'antialias' and use system settings.
        
        text -- (unicode) string with the text to render
        antialias -- attempt to antialias the text or not
        color -- three or four-tuple of 0-255 values specifying rendering 
            colour for the text 
        background -- three or four-tuple of 0-255 values specifying rendering 
            colour for the background, or None for trasparent background
        
        returns a pygame image instance
        """
        log.info( 'render: %r, antialias = %s, color=%s, background=%s', text, antialias, color, background )

        # create layout
        layout = pango.Layout(gtk.gdk.pango_context_get())
        layout.set_font_description(self.fd)
        layout.set_text(text)

        # determine pixel size
        (logical, ink) = layout.get_pixel_extents()
        ink = pygame.rect.Rect(ink)

        # Create a new Cairo ImageSurface
        csrf = cairo.ImageSurface(cairo.FORMAT_ARGB32, ink.w, ink.h)
        cctx = pangocairo.CairoContext(cairo.Context(csrf))

        # Mangle the colors on little-endian machines. The reason for this 
        # is that Cairo writes native-endian 32-bit ARGB values whereas
        # Pygame expects endian-independent values in whatever format. So we
        # tell our users not to expect transparency here (avoiding the A issue)
        # and we swizzle all the colors around.
        big_endian = struct.pack( '=i', 1 ) == struct.pack( '>i', 1 )
        if hasattr(csrf,'get_data'):
            swap = True
        else:
            swap = False
        log.debug( 'big_endian: %s   swap: %s', big_endian, swap )
        def mangle_color(color):
            """Mange a colour depending on endian-ness, and swap-necessity
            
            This implementation has only been tested on an AMD64
            machine with a get_data implementation (rather than 
            a get_data_as_rgba implementation).
            """
            r,g,b = color[:3]
            if len(color) > 3:
                a = color[3]
            else:
                a = 255.0
            if swap and not big_endian:
                return map(_fixColorBase, (b,g,r,a) )
            return map(_fixColorBase, (r,g,b,a) )

        # render onto it
        if background is not None:
            background = mangle_color( background )
            cctx.set_source_rgba(*background)
            cctx.paint()
        
        log.debug( 'incoming color: %s', color )
        color = mangle_color( color )
        log.debug( '  translated color: %s', color )

        cctx.new_path()
        cctx.layout_path(layout)
        cctx.set_source_rgba(*color)
        cctx.fill()

        # Create and return a new Pygame Image derived from the Cairo Surface
        if big_endian:
            # You see, in big-endian-world, we can just use the RGB values
            format = "ARGB"
        else:
            # But with little endian, we've already swapped R and B in 
            # mangle_color, so now just move the A
            format = "RGBA"
        if hasattr(csrf,'get_data'):
            data = csrf.get_data()
        else:
            # XXX little-endian here, check on a big-endian machine 
            data = csrf.get_data_as_rgba()
            format = 'RGBA' # XXX wrong, what's with all the silly swapping!
        try:
            data = str(data)
            return pygame.image.fromstring(data, (ink.w,ink.h), format)
        except ValueError, err:
            err.args += (len(data), ink.w*ink.h*4,format )
            raise

class SysFont(PangoFont):
    """Construct a PangoFont from a font description (name), size in pixels,
    bold, and italic designation. Similar to SysFont from Pygame."""
    def __init__(self, name, size, bold=False, italic=False):
        fd = pango.FontDescription(name)
        fd.set_absolute_size(size*pango.SCALE)
        if bold:
            fd.set_weight(pango.WEIGHT_BOLD)
        if italic:
            fd.set_style(pango.STYLE_OBLIQUE)
        super(SysFont, self).__init__(fd=fd)

# originally defined a new class, no reason for that...
NotImplemented = NotImplementedError

class Font(PangoFont):
    """Abstract class, do not use"""
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("PangoFont doesn't support Font directly, use SysFont or .fontByDesc")

def match_font(name,bold=False,italic=False):
    """Stub, does not work, use fontByDesc instead"""
    raise NotImplementedError("PangoFont doesn't support match_font directly, use SysFont or .fontByDesc")

def fontByDesc(desc="",bold=False,italic=False):
    """Constructs a FontDescription from the given string representation.
The format of the string representation is:

  "[FAMILY-LIST] [STYLE-OPTIONS] [SIZE]"

where FAMILY-LIST is a comma separated list of families optionally terminated by a comma, STYLE_OPTIONS is a whitespace separated list of words where each WORD describes one of style, variant, weight, or stretch, and SIZE is an decimal number (size in points). For example the following are all valid string representations:

  "sans bold 12"
  "serif,monospace bold italic condensed 16"
  "normal 10"

The commonly available font families are: Normal, Sans, Serif and Monospace. The available styles are:
Normal	the font is upright.
Oblique	the font is slanted, but in a roman style.
Italic	the font is slanted in an italic style.

The available weights are:
Ultra-Light	the ultralight weight (= 200)
Light	the light weight (=300)
Normal	the default weight (= 400)
Bold	the bold weight (= 700)
Ultra-Bold	the ultra-bold weight (= 800)
Heavy	the heavy weight (= 900)

The available variants are:
Normal	
Small-Caps	

The available stretch styles are:
Ultra-Condensed	the smallest width
Extra-Condensed	
Condensed	
Semi-Condensed	
Normal	the normal width
Semi-Expanded	
Expanded	
Extra-Expanded	
Ultra-Expanded	the widest width
    """
    fd = pango.FontDescription(name)
    if bold:
        fd.set_weight(pango.WEIGHT_BOLD)
    if italic:
        fd.set_style(pango.STYLE_OBLIQUE)
    return PangoFont(fd=fd)

def get_init():
    """Return boolean indicating whether we are initialised
    
    Always returns True 
    """
    return True

def init():
    """Initialise the module (null operation)"""
    pass

def quit():
    """De-initialise the module (null operation)"""
    pass

def get_default_font():
    """Return default-font specification to be passed to e.g. fontByDesc"""
    return "sans"

def get_fonts():
    """Return the set of all fonts available (currently just 3 generic types)"""
    return ["sans","serif","monospace"]


def stdcolor(color):
    """Produce a 4-element 0.0-1.0 color value from input"""
    def fixlen(color):
        if len(color) == 3:
            return tuple(color) + (255,)
        elif len(color) == 4:
            return color
        else:
            raise TypeError("What sort of color is this: %s" % (color,))
    return [_fixColorBase(x) for x in fixlen(color)]
def _fixColorBase( v ):
    """Return a properly clamped colour in floating-point space"""
    return max((0,min((v,255.0))))/255.0

if __name__ == "__main__":
    # Simple testing code...
    logging.basicConfig()
    from pygame import image,display, event, sprite
    import pygame
    import pygame.event
    def main():
        display.init()
        maxX,maxY = display.list_modes()[0] 
        screen = display.set_mode( (maxX/2, maxY/2 ) )
        background = pygame.Surface(screen.get_size())
        background = background.convert()
        background.fill((255, 255,255))
        
        screen.blit(background, (0, 0))
        display.flip()
        
        clock = pygame.time.Clock()
        
        font = PangoFont( size=30, family='monospace' )
        text1 = font.render( 'red', color=(255,0,0) , background=(255,255,255,0) )
        text2 = font.render( 'green', color=(0,255,0)  )
        text3 = font.render( 'blue', color=(0,0,255)  )
        text4 = font.render( 'blue-trans', color=(0,0,255,128)  )
        text5 = font.render( 'cyan-trans', color=(0,255,255,128)  )
        while 1:
            clock.tick( 60 )
            for event in pygame.event.get():
                log.debug( 'event: %s', event )
                if event.type == pygame.QUIT:
                    return True
            screen.blit( text1, (20,20 ))
            screen.blit( text2, (20,80 ))
            screen.blit( text3, (20,140 ))
            screen.blit( text4, (200,20 ))
            screen.blit( text5, (200,80 ))
            display.flip()
    main()
    
