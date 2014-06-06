import threading
import subprocess

from gi.repository import GObject

GObject.threads_init()


class Accelerometer():

    ACCELEROMETER_DEVICE = '/sys/devices/platform/lis3lv02d/position'

    def read():
        """
        return x, y, z values or None if no accelerometer is available
        """
        try:
            fh = open(ACCELEROMETER_DEVICE)
            string = fh.read()
            xyz = string[1:-2].split(',')
            x = float(xyz[0]) / (64 * 18)
            y = float(xyz[1]) / (64 * 18)
            z = float(xyz[2]) / (64 * 18)
            fh.close()
            return x, y, z
        except:
            return None

class EbookModeDetector(GObject.GObject):

    EBOOK_DEVICE = '/dev/input/event4'

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, ([bool])), }

    def __init__(self):
        GObject.GObject.__init__(self)
        self._ebook_mode = self._get_initial_value()
        self._start_reading()

    def get_ebook_mode(self):
        return self._ebook_mode

    def _get_initial_value(self):
        output = subprocess.call(['evtest', '--query', self.EBOOK_DEVICE,
                                  'EV_SW', 'SW_TABLET_MODE'])
        # 10 is ebook_mode, 0 is normal
        return (output == 10)
        logging.error('Initial state %s', (output == 10))

    def _start_reading(self):
        thread = threading.Thread(target=self._read)
        thread.daemon = True
        thread.start()

    def _read(self):
        fd = open(self.EBOOK_DEVICE, 'rb')
        for x in range(12):
            fd.read(1)
        self._report_change(ord(fd.read(1)))

    def _report_change(self, value):
        self._ebook_mode = (value == 1)
        self.emit('changed', self._ebook_mode)
        # restart
        GObject.idle_add(self._start_reading)

# Move to tests

import logging
from gi.repository import Gtk


def log_ebook_mode(detector, ebook_mode):
    logging.error('Ebook mode %s', ebook_mode)


def quit(win, detector):
    Gtk.main_quit()


def main():
    win = Gtk.Window()
    win.set_default_size(450, 550)
    label = Gtk.Label('Put your xo in ebook mode nd in notebook mode')
    win.add(label)
    win.show_all()
    ebookdetector = EbookModeDetector()
    ebookdetector.connect('changed', log_ebook_mode)
    win.connect('destroy', quit, ebookdetector)
    Gtk.main()

if __name__ == '__main__':
    main()
