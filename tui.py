import urwid

from bots import Bot
from ib_async import util
from logger import logger, log


class TUI:
    def __init__(self):
        self.paused = False
        self.console_messages = []
        self.bots = []

        log.info("HYDRA started.")
        #self.initialize_bots()

        # UI
        self.palette = [
            ('normal', 'white', 'black'),   # Default text colour
            ('focus', 'black', 'dark red', 'standout'),  # Highlighted widget when focused
        ]

        self.top_text = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.dropdown = ['manual', '1', '2']
        self.dropdown_btns = []
        self.selected = [self.dropdown[0]]
        for i in self.dropdown:
            btn = urwid.Button(i)
            def on_click(_button, choice=i):
                self.selected[0] = choice
                log.debug(f"Selected: {self.selected[0]}")
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

    def start(self):
        """Begin running event loop."""
        # Setup Event Loops
        self.ib_loop = util.getLoop()  # ib_async's built-in asyncio event loop
        self.my_asyncio_loop = urwid.AsyncioEventLoop(loop=self.ib_loop)  # Tell urwid the ib loop is an asyncio loop
        self.loop = urwid.MainLoop(  # Tell urwid to use the ib asyncio loop as its main loop
            self.frame,
            palette=self.palette,
            unhandled_input=self.handle_input,
            event_loop=self.my_asyncio_loop
        )

        self.initialize_bots()
        # Schedule the first refresh immediately
        self.loop.set_alarm_in(0, self.refresh_display)
        self.loop.run()

    def initialize_bots(self):
        self.bots = {
                0: Bot('master', self.bot_callback, client_id=0),
                1: Bot('ss_live', self.bot_callback, client_id=1),
        }
        for bot in self.bots:
            self.bots[bot].connect()


    def bot_callback(self, client_id, widget, s):
        if widget == 'time':
            try:
                self.top_text.base_widget.set_text(s)
            except:
                log.error(f"Error updating time: {e}")
                self.top_text.base_widget.set_text("Error retrieving time.")
        if widget == 'ticker':
            try:
                self.middle_left_ticker.base_widget_set_text(s)
            except:
                pass
        if widget == 'bars':
            try:
                self.middle_left_df.base_widget.set_text(s)
            except:
                pass

    def handle_input(self, key):
        if isinstance(key, str):
            input_text = self.middle_left_input.base_widget.get_edit_text()
            if True:  # FIXME: only when edit widget is focused
                if key == "enter":
                    contract_input = self.middle_left_input.base_widget.get_edit_text().upper()
    
                    contract_obj = self.current_bot.qualify(contract_input)
                    self.current_bot.start_ticker(contract_obj)
                    self.current_bot.start_bars(contract_obj)


            if key.lower() == "q":
                for bot in bots:
                    bot.disconnect()
                log.info("All bots stopped. HYDRA stopping.")
                raise urwid.ExitMainLoop()
            elif key.lower() == "p":
                if self.paused:
                    self.paused = False
                    log.debug("Refresh unpaused")
                    self.loop.set_alarm_in(0, self.refresh_display)
                else:
                    log.debug("Refresh paused")
                    self.paused = True

    def refresh_display(self, loop, user_data=None):
        self.console_messages = logger.get_console_messages()
        self.bottom_text.base_widget.set_text("\n".join(self.console_messages))

        # Delete later. Testing TWS error emit
        #con = contract.ContFuture('YM', exchange='CBOT')
        #c = self.ib.qualifyContracts(con)[0]
        #self.ib.reqMktData(c, genericTickList='', snapshot=False, regulatorySnapshot=False)
        #ticker = self.ib.ticker(c)
        #self.ib.sleep(0.5)
        #ticker
        self.bots[0].display_time()

        if not self.paused:
            loop.set_alarm_in(0.1, self.refresh_display)
        self.loop.draw_screen()

