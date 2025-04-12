import urwid
#from datetime import datetime
from zoneinfo import ZoneInfo

#from bots import Bot
from core.ib_client import ib, util, graceful_shutdown
#from ib_async import util
from core.logger import logger, log


class TUI:
    def __init__(self):
        log.info("HYDRA started.")
        self.paused = False
        self.console_messages = []
        self.bots = []
        #self.current_bot = 0

    def start(self):
        """Link ib_async event loop to urwid's MainLoop."""

        # ib_async's built-in asyncio event loop
        self.ib_loop = util.getLoop()

        # Tell urwid the ib loop is an asyncio loop
        self.my_asyncio_loop = urwid.AsyncioEventLoop(loop=self.ib_loop)

        # Init bots
        #self.initialize_bots()

        self.draw_layout()

        # Tell urwid to use the ib asyncio loop as its main loop
        self.loop = urwid.MainLoop(
            self.frame,
            palette=self.palette,
            unhandled_input=self.handle_input,
            event_loop=self.my_asyncio_loop
        )

        #ib.pendingTickersEvent += self.on_pending_tickers

        # Schedule the first refresh immediately
        self.loop.set_alarm_in(0, self.refresh_display)
        self.loop.run()

#     def on_pending_tickers(self, tickers):
#         for t in tickers:
#             if t == 'MES':
#                 self.middle_left_ticker.original_text.set_text(str(tickers[t].last))
#             if t == 'MNQ':
#                 self.middle_left_df.original_text.set_text(str(tickers[t].last))

    def initialize_bots(self):
        self.bots = {0: 'master'}
#         self.bots = {
#                 0: Bot('master', self.bot_callback, client_id=0),
#                 1: Bot('ss_live', self.bot_callback, client_id=1),
#         }
#         for bot in self.bots:
#             self.bots[bot].connect()


    def bot_callback(self, client_id, widget, s):
        if widget == 'time':
            try:
                self.top_text.base_widget.set_text(s)
            except:
                log.error(f"Error updating time: {e}")
                self.top_text.base_widget.set_text("Error retrieving time.")
        if widget == 'ticker':
            try:
                self.middle_left_ticker.base_widget.set_text(s)
            except:
                pass
        if widget == 'bars':
            try:
                self.middle_left_df.base_widget.set_text(s)
            except:
                pass

    def draw_layout(self):
        # UI
        self.palette = [
            ('normal', 'white', 'black'),   # Default text colour
            ('focus', 'black', 'dark red', 'standout'),  # Highlighted widget when focused
        ]

        self.top_text = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        #self.dropdown = [bot.codename for bot in self.bots.values()]
        self.dropdown = ['0', '1', '2']
        self.dropdown_btns = []
        self.selected = [self.dropdown[0]]
        for i in self.dropdown:
            btn = urwid.Button(i)
            def on_click(_button, choice=i):
                self.current_bot = self.get_key_int_from_bot_codename(choice)
                self.selected[0] = choice
                log.debug(f'Selected: #{self.current_bot} "{self.selected[0]}"')
            urwid.connect_signal(btn, 'click', on_click)
            self.dropdown_btns.append(btn)

        self.top_dropdown = urwid.ListBox(urwid.SimpleFocusListWalker(self.dropdown_btns))
        self.top = urwid.LineBox(urwid.Filler(urwid.Columns([('weight', 1, self.top_text), ('weight', 1, self.top_dropdown)], box_columns=[1])))

        self.middle_left_input = urwid.AttrMap(urwid.Edit("Input: ", wrap='clip'), None, 'focus')
        self.middle_left_ticker = urwid.AttrMap(urwid.Text("ML", wrap='clip'), None, 'focus')
        self.middle_left_df = urwid.AttrMap(urwid.Text("ML", wrap='clip'), None, 'focus')
        self.middle_left_pile = urwid.Pile([self.middle_left_input, self.middle_left_ticker, self.middle_left_df])
        self.middle_left = urwid.LineBox(self.middle_left_pile)

        self.middle_right_text = urwid.AttrMap(urwid.Text("MR", wrap='clip'), None, 'focus')
        self.middle_right = urwid.LineBox(self.middle_right_text)

        self.middle = urwid.Filler(urwid.Columns([
                                                    ('weight', 2, self.middle_left),
                                                    ('weight', 1, self.middle_right)
                                                ]),
                                    valign="top")

        self.bottom_text = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.bottom = urwid.LineBox(urwid.ListBox(urwid.SimpleListWalker([self.bottom_text])))

        self.frame = urwid.Pile([
            (3, self.top),              # Fixed height for the top section
            ('weight', 1, self.middle), # Expand self.middle for any remaining screen height
            (9, self.bottom),           # Fixed height for the bottom section
        ])


    def get_key_int_from_bot_codename(self, codename):
        """Return integer key number of self.bots given a codename. Return 0 if none found."""
        return next((key for key, bot in self.bots.items() if codename == bot.codename), 0)

    def refresh_display(self, loop, user_data=None):
        self.console_messages = logger.get_console_messages()
        self.bottom_text.base_widget.set_text("\n".join(self.console_messages))

        # Delete later. Testing TWS error emit
        #con = contract.ContFuture('YM', exchange='CBOT')
        #c = self.ib.qualifyContracts(con)[0]
        #self.ib.reqMktData(c, genericTickList='', snapshot=False, regulatorySnapshot=False)
        #ticker = self.ib.ticker(c)

        #ticker

        ib_time_obj = ib.reqCurrentTime()
        ib_time = str(ib_time_obj.now(ZoneInfo("America/New_York"))) + "  (New York)"
        self.top_text.base_widget.set_text(ib_time)


        #log.debug("beforetime")
        #self.top_text.original_widget.set_text(str(ib.reqCurrentTime().now(ZoneInfo("America/New_York"))) + "  (New York)")
        #log.debug("beforesleep")
        #ib.sleep(0.15)

        #self.bots[0].display_time()

        if not self.paused:
            log.debug("not paused")
            loop.set_alarm_in(0.5, self.refresh_display)
            log.debug("after set alarm")
            #self.loop.draw_screen()


    def handle_input(self, key):
        if isinstance(key, str):
            input_text = self.middle_left_input.base_widget.get_edit_text()
#             if True:  # FIXME: only when edit widget is focused
#                 if key == "enter":
#                     contract_input = self.middle_left_input.base_widget.get_edit_text().upper()

#                     contract_obj = self.bots[self.current_bot].qualify(contract_input)
#                     self.bots[self.current_bot].start_ticker(contract_obj)
#                     self.bots[self.current_bot].start_bars(contract_obj)

            if key.lower() == "q":
#                 for bot in self.bots:
#                     log.debug(f"{bot} stopping")
#                     self.bots[bot].disconnect()
#                     util.sleep(10)
#                     log.debug(f"{bot} stopped")
#                 log.info("All bots stopped. HYDRA stopping.")
                graceful_shutdown()
                raise urwid.ExitMainLoop()
            elif key.lower() == "p":
                if self.paused:
                    self.paused = False
                    log.debug("Refresh unpaused")
                    self.loop.set_alarm_in(0, self.refresh_display)
                else:
                    log.debug("Refresh paused")
                    self.paused = True

tui = TUI()
tui.start()
