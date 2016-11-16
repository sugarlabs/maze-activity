#
#   sensors.py, Copyright (C) 2014-2016 One Laptop per Child
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import subprocess

from gi.repository import GObject
from gi.repository import Gtk


class Accelerometer():

    DEVICE = '/sys/devices/platform/lis3lv02d/position'

    def read_position(self):
        """
        return [x, y, z] values or [0, 0, 0] if no accelerometer is available
        """
        try:
            fh = open(self.DEVICE)
            string = fh.read()
            xyz = string[1:-2].split(',')
            fh.close()
            return int(xyz[0]), int(xyz[1]), int(xyz[2])
        except:
            return 0, 0, 0


class EbookModeDetector(GObject.GObject):

    DEVICE = '/dev/input/event4'

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, ([bool])), }

    def __init__(self):
        GObject.GObject.__init__(self)

        try:
            self._fp = open(self.DEVICE, 'rb')
        except IOError:
            self._ebook_mode = False
            return

        def _io_in_cb(fp, condition):
            data = fp.read(16)
            if data == '':
                return False
            if ord(data[10]) == 1:  # SW_TABLET_MODE
                mode = (ord(data[12]) == 1)
                if mode != self._ebook_mode:
                    self._ebook_mode = mode
                    self.emit('changed', self._ebook_mode)
            return True

        self._sid = GObject.io_add_watch(self._fp, GObject.IO_IN, _io_in_cb)

        self._ebook_mode = self._get_initial_value()

    def get_ebook_mode(self):
        return self._ebook_mode

    def _get_initial_value(self):
        try:
            output = subprocess.call(['evtest', '--query', self.DEVICE,
                                      'EV_SW', 'SW_TABLET_MODE'])
            # 10 is ebook_mode, 0 is normal
            return (output == 10)
        except:
            return False


def test():
    window = Gtk.Window(title='test sensors')
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                  spacing=20, border_width=20)
    window.add(box)
    ebookmode_label = Gtk.Label()
    box.add(ebookmode_label)
    accelerometer_label = Gtk.Label()
    box.add(accelerometer_label)
    window.connect('destroy', Gtk.main_quit)
    window.connect('key-press-event', Gtk.main_quit)

    def _changed_cb(ebookdetector, ebook_mode):
        if ebook_mode:
            ebookmode_label.set_label('ebook mode')
        else:
            ebookmode_label.set_label('laptop mode')

    ebookdetector = EbookModeDetector()
    _changed_cb(ebookdetector, ebookdetector.get_ebook_mode())
    ebookdetector.connect('changed', _changed_cb)

    def _timeout_cb():
        pos = accelerometer.read_position()
        accelerometer_label.set_label('accelerometer %s' % repr(pos))
        return True

    accelerometer = Accelerometer()
    _timeout_cb()
    GObject.timeout_add(100, _timeout_cb)

    window.show_all()
    Gtk.main()

if __name__ == '__main__':
    test()
