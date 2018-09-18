import logging

import gi
gi.require_version('TelepathyGLib', '0.12')

from gi.repository import TelepathyGLib


class TextChannelWrapper(object):
    """Wrap a telepathy Text Channel to make
    usage simpler."""

    def __init__(self, text_chan, conn, pservice):
        """Connect to the text channel"""
        self._activity_cb = None
        self._activity_close_cb = None
        self._text_chan = text_chan
        self._conn = conn
        self._pservice = pservice
        self._logger = logging.getLogger(
            'minichat-activity.TextChannelWrapper')
        self._signal_matches = []
        m = self._text_chan[TelepathyGLib.IFACE_CHANNEL].\
            connect_to_signal(
            'Closed', self._closed_cb)
        self._signal_matches.append(m)

    def send(self, text):
        """Send text over the Telepathy text channel."""
        # XXX Implement CHANNEL_TEXT_MESSAGE_TYPE_ACTION
        if self._text_chan is not None:
            self._text_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT].Send(
                TelepathyGLib.ChannelTextMessageType.NORMAL, text)

    def close(self):
        """Close the text channel."""
        self._logger.debug('Closing text channel')
        try:
            self._text_chan[TelepathyGLib.IFACE_CHANNEL].Close()
        except BaseException:
            self._logger.debug('Channel disappeared!')
            self._closed_cb()

    def _closed_cb(self):
        """Clean up text channel."""
        self._logger.debug('Text channel closed.')
        for match in self._signal_matches:
            match.remove()
        self._signal_matches = []
        self._text_chan = None
        if self._activity_close_cb is not None:
            self._activity_close_cb()

    def set_received_callback(self, callback):
        """Connect the function callback to the signal.

        callback -- callback function taking buddy
        and text args
        """
        if self._text_chan is None:
            return
        self._activity_cb = callback
        m = self._text_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT].\
            connect_to_signal(
            'Received', self._received_cb)
        self._signal_matches.append(m)

    def handle_pending_messages(self):
        """Get pending messages and show them as
        received."""
        for id, timestamp, sender, type, flags, text \
                in self._text_chan[
                    TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT
                ].ListPendingMessages(
                    False):
            self._received_cb(id, timestamp, sender, type, flags, text)

    def _received_cb(self, id, timestamp, sender, type, flags, text):
        """Handle received text from the text channel.

        Converts sender to a Buddy.
        Calls self._activity_cb which is a callback
        to the activity.
        """
        if self._activity_cb:
            buddy = self._get_buddy(sender)
            self._activity_cb(buddy, text)
            self._text_chan[
                TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT
            ].AcknowledgePendingMessages([id])
        else:
            self._logger.debug(
                'Throwing received message on the floor'
                ' since there is no callback connected. See '
                'set_received_callback')

    def set_closed_callback(self, callback):
        """Connect a callback for when the text channel
        is closed.

        callback -- callback function taking no args

        """
        self._activity_close_cb = callback

    def _get_buddy(self, cs_handle):
        """Get a Buddy from a (possibly channel-specific)
        handle."""
        # XXX This will be made redundant once Presence
        # Service provides buddy resolution
        # Get the Telepathy Connection
        tp_name, tp_path = \
            self._pservice.get_preferred_connection()
        conn = TelepathyGLib.Connection.new(
            TelepathyGLib.DBusDaemon.dup(), tp_name, tp_path)
        group = self._text_chan[TelepathyGLib.IFACE_CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        if my_csh == cs_handle:
            handle = conn.GetSelfHandle()
        elif group.GetGroupFlags() & \
                TelepathyGLib.ChannelGroupFlags.CHANNEL_SPECIFIC_HANDLES:
            handle = group.GetHandleOwners([cs_handle])[0]
        else:
            handle = cs_handle

            # XXX: deal with failure to get the handle owner
            assert handle != 0

        return self._pservice.get_buddy_by_telepathy_handle(
            tp_name, tp_path, handle)
