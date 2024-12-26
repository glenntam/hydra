import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import urwid
from dotenv import load_dotenv
from ib_async import IB, contract, util

from logger import Logger


class TUI:
    def __init__(self):
        # Custom Logger
        self.console_height = 7
        self.logger_instance = Logger(console_height=self.console_height)
        self.log = self.logger_instance.logger
        self.console_messages = []
        sys.stderr = open(os.devnull, 'w')  # supress printing errors, just log them

        # IB
        self.ib = IB()
        self.ib.connect('127.0.0.1', 7497, clientId=0)
        self.log.info("HYDRA started. Connected to IB().")
        self.ib.errorEvent += self.logger_instance.OnIBErrorEvent  # catch IB TWS errors
        self.selected_contract = None

        # UI
        self.top_text = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.top = urwid.LineBox(self.top_text)

        self.middle_left_text = urwid.AttrMap(urwid.Text("ML", wrap='clip'), None, 'focus')
        self.middle_left_input = urwid.AttrMap(urwid.Edit("Input: ", wrap='clip'), None, 'focus')
        self.middle_left_pile = urwid.Pile([self.middle_left_text, self.middle_left_input])
        self.middle_left = urwid.LineBox(self.middle_left_pile)

        self.middle_right_text = urwid.AttrMap(urwid.Text("MR", wrap='clip'), None, 'focus')
        self.middle_right = urwid.LineBox(self.middle_right_text)
        self.middle = urwid.Filler(urwid.Columns([self.middle_left, self.middle_right]), valign="top")

        self.bottom_text = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.bottom = urwid.LineBox(urwid.ListBox(urwid.SimpleListWalker([self.bottom_text])))

        self.frame = urwid.Pile([
            (3, self.top),              # Fixed height for the top section
            ('weight', 1, self.middle), # Expand self.middle for any remaining screen height
            (9, self.bottom),           # Fixed height for the bottom section
        ])

        palette = [
            ('normal', 'white', 'black'),   # Default text colour
            ('focus', 'black', 'dark red', 'standout'),  # Highlighted widget when focused
        ]
        self.focused_widget = None

        # Setup Event Loops
        self.ib_loop = util.getLoop()  # ib_async's built-in asyncio event loop
        self.my_asyncio_loop = urwid.AsyncioEventLoop(loop=self.ib_loop)  # Tell urwid the ib loop is an asyncio loop
        self.loop = urwid.MainLoop(  # Tell urwid to use the ib asyncio loop as its main loop
            self.frame,
            palette=palette,
            unhandled_input=self.handle_input,
            event_loop=self.my_asyncio_loop
        )

        # Schedule the first refresh immediately
        self.loop.set_alarm_in(0, self.refresh_display)
        self.loop.run()

    def handle_input(self, key):
        if isinstance(key, str):
            input_text = self.middle_left_input.base_widget.get_edit_text()
            self.middle_left_text.base_widget.set_text(input_text)
            if key.lower() == "q":
                self.log.debug("Disconnecting...")
                self.ib.disconnect()
                raise urwid.ExitMainLoop()

    def refresh_display(self, loop, user_data=None):

        self.console_messages = self.logger_instance.get_console_messages()
        self.bottom_text.base_widget.set_text("\n".join(self.console_messages))

        # Delete later. Testing TWS error emit
        #con = contract.ContFuture('YM', exchange='CBOT')
        #c = self.ib.qualifyContracts(con)[0]
        #self.ib.reqMktData(c, genericTickList='', snapshot=False, regulatorySnapshot=False)
        #ticker = self.ib.ticker(c)
        #self.ib.sleep(0.5)
        #ticker
        try:
            ib_time_obj = self.ib.reqCurrentTime()
            ib_time = str(ib_time_obj.now(ZoneInfo("America/New_York"))) + "  (New York)"
            self.top_text.base_widget.set_text(ib_time)
            #self.log.debug(f"Time updated: {ib_time}")
        except Exception as e:
            self.log.error(f"Error updating time: {e}")
            self.top_text.base_widget.set_text("Error retrieving time.")
        loop.set_alarm_in(0.2, self.refresh_display)


if __name__ == "__main__":
    load_dotenv()
    util.patchAsyncio()  # Allow ib_async's asyncio event loop to run nested within urwid's MainLoop
    app = TUI()
