import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import urwid
from dotenv import load_dotenv
from ib_async import IB, util

from logger import Logger

class TUI:
    def __init__(self):
        # Custom Logger
        self.logger_instance = Logger()
        self.log = self.logger_instance.logger

        # UI
        self.top_text = urwid.Text("Waiting for time...")
        self.top = urwid.LineBox(urwid.Filler(self.top_text))

        self.middle_left_text = urwid.Text("ML")
        self.middle_left = urwid.LineBox(urwid.Filler(self.middle_left_text))

        self.middle_right_text = urwid.Text("MR")
        self.middle_right = urwid.LineBox(urwid.Filler(self.middle_right_text))

        self.middle = urwid.Filler(urwid.Columns([self.middle_left, self.middle_right]))

        self.bottom_text = urwid.Text(" " * 80)  # Initialize with empty space for 7 rows
        self.bottom = urwid.LineBox(urwid.Filler(self.bottom_text, valign="top"))

        self.frame = urwid.Pile([self.top, self.middle, self.bottom])

        # IB
        self.ib = IB()
        self.ib.connect('127.0.0.1', 7497, clientId=0)
        self.log.debug("Connected to IB()")

        # Setup Event Loops
        self.ib_loop = util.getLoop()  # ib_async's built-in asyncio event loop
        self.my_asyncio_loop = urwid.AsyncioEventLoop(loop=self.ib_loop)  # Tell urwid the ib loop is an asyncio loop
        self.loop = urwid.MainLoop(  # Tell urwid to use the ib asyncio loop as its main loop
            self.frame,
            unhandled_input=self.handle_input,
            event_loop=self.my_asyncio_loop
        )

        # Schedule the first refresh
        self.loop.set_alarm_in(0, self.refresh_display)
        self.loop.run()

    def handle_input(self, key):
        if key.lower() == "q":
            self.log.debug("Disconnecting...")
            self.ib.disconnect()
            raise urwid.ExitMainLoop()

    def refresh_display(self, loop, user_data=None):
        # Update time display

        # Update bottom_text with the last 7 log messages
#         log_messages = []
#         for handler in self.log.handlers:
#             if isinstance(handler, logging.StreamHandler):
#                 log_messages = getattr(handler, 'log_messages', [])
#                 break
        console_messages = self.logger_instance.get_console_messages()
        # Ensure there are always 7 lines
        console_display = console_messages[-7:]
        while len(console_display) < 7:
            console_display.insert(0, " ")
        # Join the last 7 messages, most recent at the bottom
        sometext = "\n".join(console_display)
        self.bottom_text.set_text(sometext)

        try:
            ib_time_obj = self.ib.reqCurrentTime()
            ib_time = str(ib_time_obj.now(ZoneInfo("America/New_York"))) + "  (New York)"
            self.top_text.set_text(ib_time)
            self.log.info(f"Time updated: {ib_time}")
        except Exception as e:
            self.log.error(f"Error updating time: {e}")
            self.top_text.set_text("Error retrieving time.")
        # Schedule the next refresh
        loop.set_alarm_in(0.5, self.refresh_display)  # Adjust the interval as needed

if __name__ == "__main__":
    load_dotenv()  # Load environment variables for the entire application
    util.patchAsyncio()  # Allow ib_async's asyncio event loop to run nested within urwid's MainLoop
    try:
        app = TUI()
    except Exception as e:
        # If TUI initialization fails, set up basic logging to stderr
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger("TUI_Logger").error(f"Application failed to start: {e}")

