"""Module for progress status indicator.

Attributes:
    MSG_CHARS_COLOR_SUBLIME: chars for using in colorsublime-like progress
    MSG_READY_COLOR_SUBLIME: ready message in colorsublime-like progress
    MSG_CHARS_MOON (str): chars for using in moon-like progress
    MSG_READY_MOON (str): ready message in moon-like progress
"""

import sublime

MSG_CHARS_MOON = u'🌑🌒🌓🌔🌕🌖🌗🌘'
MSG_READY_MOON = u'✔'
MSG_CHARS_COLOR_SUBLIME = u'⣾⣽⣻⢿⡿⣟⣯⣷'
MSG_READY_COLOR_SUBLIME = '     READY      '


class BaseProgressStatus(object):
    """A base class for progress status."""

    MSG_TAG = '000_ECC'
    MSG_MASK = ' | {msg} |'
    PROGRESS_MASK = 'ECC: [{progress}]'
    FULL_MASK = PROGRESS_MASK + MSG_MASK

    def __init__(self):
        """Initialize progress status."""
        self.showing = False
        self.msg_chars = None
        self.msg_ready = None

    @staticmethod
    def set_status(message):
        """Set status message for the current view."""
        view = sublime.active_window().active_view()
        view.set_status(BaseProgressStatus.MSG_TAG, message)

    def erase_status(self):
        """Erase status message for the current view."""
        self.showing = False
        view = sublime.active_window().active_view()
        view.erase_status(BaseProgressStatus.MSG_TAG)

    def show_as_ready(self):
        """Show ready state."""
        if not self.showing:
            return
        BaseProgressStatus.set_status(
            BaseProgressStatus.PROGRESS_MASK.format(progress=self.msg_ready))

    def update_progress(self, message=''):
        """Abstract method. Generate next message."""
        raise NotImplementedError("abstract method is called")


class MoonProgressStatus(BaseProgressStatus):
    """Progress status that shows phases of the moon."""

    def __init__(self):
        """Init moon progress status."""
        super().__init__()
        self.idx = 0
        self.msg_chars = MSG_CHARS_MOON
        self.msg_ready = MSG_READY_MOON

    def update_progress(self, message):
        """Show next moon phase and a custom message."""
        if not self.showing:
            return
        chars = self.msg_chars
        mod = len(chars)
        self.idx = (self.idx + 1) % mod
        BaseProgressStatus.set_status(
            BaseProgressStatus.FULL_MASK.format(
                progress=chars[self.idx], msg=message))


class ColorSublimeProgressStatus(BaseProgressStatus):
    """Progress status that shows phases of the moon."""

    def __init__(self):
        """Init color sublime like progress status."""
        super().__init__()
        self.msg_chars = MSG_CHARS_COLOR_SUBLIME
        self.msg_ready = MSG_READY_COLOR_SUBLIME

    def update_progress(self, message):
        """Show next random progress indicator and a custom message."""
        if not self.showing:
            return
        from random import sample
        mod = len(self.msg_chars)
        rands = [self.msg_chars[x % mod] for x in sample(range(100), 10)]
        BaseProgressStatus.set_status(
            BaseProgressStatus.FULL_MASK.format(
                progress=''.join(rands), msg=message))


class NoneSublimeProgressStatus(BaseProgressStatus):
    """Progress status that does nothing."""

    def __init__(self):
        """Init color sublime like progress status."""
        super().__init__()
        self.showing = False

    def show_as_ready(self):
        """Empty implementation."""
        pass

    def update_progress(self, message):
        """Empty implementation."""
        pass
