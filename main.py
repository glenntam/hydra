import os
import sys
from zoneinfo import ZoneInfo

import urwid
from dotenv import load_dotenv; load_dotenv()

#from core.event_manager import event_manager
from core.ib_client import ib, util, state, update_state, graceful_shutdown
from core.logger import logger, log


class TUI:
    def __init__(self):
        ib.errorEvent += logger.OnIBErrorEvent  # Catch IB TWS errors
        log.info("HYDRA started.")
        self.paused = False
        self.console_messages = []
        self.bots = []

    def draw_initial_layout(self):
        """Draw the initial boxes and text fields for the frame."""
        # Color scheme
        self.palette = [
            ('normal', 'white', 'black'),   # Default text colour
            ('focus', 'black', 'dark red', 'standout'),  # Highlighted widget when focused
        ]

        # Boxes and Text fields
        self.top_time = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.top_mes = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.top_mnq = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.top_net_liquidation = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')

        self.pos_local_symbol = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.pos_position = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.pos_average_cost = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        self.pos_cost = urwid.AttrMap(urwid.Text("", wrap='clip'), None, 'focus')
        #
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

        self.top = urwid.LineBox(urwid.Filler(urwid.Columns([
                                                                ('weight', 8, self.top_time),
                                                                ('weight', 4, self.top_mes),
                                                                ('weight', 4, self.top_mnq),
                                                                ('weight', 4, self.top_net_liquidation),
                                                                ('weight', 1, self.top_dropdown)
                                                            ], box_columns=[4])))

        self.middle_left_input = urwid.AttrMap(urwid.Edit("Input: ", wrap='clip'), None, 'focus')
        self.middle_left_ticker = urwid.AttrMap(urwid.Text("ML", wrap='clip'), None, 'focus')
        self.debug = urwid.AttrMap(urwid.Text(""), 'normal', 'focus')
        self.debug2 = urwid.AttrMap(urwid.Text(""), 'normal', 'focus')
        self.middle_left_pile = urwid.Pile([self.middle_left_input, self.middle_left_ticker, self.debug, self.debug2])
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

    def bind_async_loop(self):
        """Link ib_async event loop to urwid's MainLoop."""
        # ib_async's built-in asyncio event loop
        self.ib_loop = util.getLoop()
        # Tell urwid the ib loop is an asyncio loop
        self.my_asyncio_loop = urwid.AsyncioEventLoop(loop=self.ib_loop)
        # Init bots
        #self.initialize_bots()
        # Tell urwid to use the ib asyncio loop as its main loop
        self.loop = urwid.MainLoop(
            self.frame,
            palette=self.palette,
            unhandled_input=self.handle_input,
            event_loop=self.my_asyncio_loop
        )
        # Schedule the first refresh when loop runs
        self.loop.set_alarm_in(0, self.refresh_display)

    def start(self):
        self.loop.run()

    def refresh_display(self, loop, user_data=None):
        if not self.paused:
            update_state()

            self.console_messages = logger.get_console_messages()
            self.bottom_text.base_widget.set_text("\n".join(self.console_messages))

            ib_time = str(state['system_time'].now(ZoneInfo("America/New_York"))) + "  (New York)"
            self.top_time.base_widget.set_text(ib_time)

            self.top_mes.base_widget.set_text(str(state['mes_last']))
            self.top_mnq.base_widget.set_text(str(state['mnq_last']))

            net_liquidity_header = str(state['account_summary'][88].tag + ': ')
            net_liquidity_value = str('{:,}'.format(int(state['account_summary'][88].value.split('.')[0])))
            self.top_net_liquidation.base_widget.set_text(net_liquidity_header + net_liquidity_value)

            self.debug.base_widget.set_text(str(state['debug']))

            loop.set_alarm_in(0, self.refresh_display)

    def initialize_bots(self):
        """Initialize the bots in a dict."""
        self.bots = {0: 'master'}
        #self.bots = {
        #        0: Bot('master', self.bot_callback, client_id=0),
        #        1: Bot('ss_live', self.bot_callback, client_id=1),
        #}
        #for bot in self.bots:
        #    self.bots[bot].connect()

    def bot_callback(self, client_id, widget, s):
        if widget == 'time':
            try:
                self.top_time.base_widget.set_text(s)
            except:
                log.error(f"Error updating time: {e}")
                self.top_time.base_widget.set_text("Error retrieving time.")
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

    def get_key_int_from_bot_codename(self, codename):
        """Return integer key number of self.bots given a codename. Return 0 if none found."""
        return next((key for key, bot in self.bots.items() if codename == bot.codename), 0)

    def handle_input(self, key):
        if isinstance(key, str):
            input_text = self.middle_left_input.base_widget.get_edit_text()
            #if true:  # fixme: only when edit widget is focused
            #    if key == "enter":
            #        contract_input = self.middle_left_input.base_widget.get_edit_text().upper()

            #        contract_obj = self.bots[self.current_bot].qualify(contract_input)
            #        self.bots[self.current_bot].start_ticker(contract_obj)
            #        self.bots[self.current_bot].start_bars(contract_obj)
            if key.lower() == "q":
                self.paused = True
                graceful_shutdown()
                raise urwid.ExitMainLoop()
            if key.lower() == "esc":
                self.loop.screen.clear()
                self.loop.draw_screen()
            elif key.lower() == "p":
                if self.paused:
                    self.paused = False
                    log.debug("refresh unpaused")
                    self.loop.set_alarm_in(0, self.refresh_display)
                else:
                    log.debug("refresh paused")
                    self.paused = True


if __name__ == "__main__":
    app = TUI()
    app.draw_initial_layout()
    app.bind_async_loop()
    app.start()
