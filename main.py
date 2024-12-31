import sys
from ib_async import util
from logger import log
from tui import TUI


if __name__ == "__main__":
    # Uncomment to suppress printing errors to terminal
    #sys.stderr = open(os.devnull, 'w')

    # Allow ib_async's asyncio event loop to run nested and be used as urwid's MainLoop later
    util.patchAsyncio()

    log.info("Starting TUI")
    app = TUI()
    app.start()
