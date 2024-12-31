import os
from datetime import datetime
from zoneinfo import ZoneInfo

import talib
import urwid
from ib_async import IB, contract, util

from logger import logger, log


class TUI:
    def __init__(self):
        self.paused = False
        self.console_messages = []

        # IB
        self.ib = IB()
        self.ib.connect('127.0.0.1', 7498, clientId=0)
        log.info("HYDRA started. Connected to IB().")
        self.ib.errorEvent += logger.OnIBErrorEvent  # catch IB TWS errors
        self.ib.pendingTickersEvent += self.onPendingTickByTick

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

        # Schedule the first refresh immediately
        self.loop.set_alarm_in(0, self.refresh_display)
        self.loop.run()

    def onPendingTickByTick(self, ticker):
        try:
            t = f"[{self.ticker.contract.symbol}] {self.ticker.tickByTicks[0].price:.2f}  x  {self.ticker.tickByTicks[0].size}"
            self.middle_left_ticker.base_widget.set_text(t)
        except:
            pass

    def onPendingBars(self, bars, hasNewBar):
        df = util.df(bars)
        df['date'] = df['date'].dt.tz_convert("America/New_York")
        df['average'] = df['average'].round(2)
        df['close'] = df['close'].round(3)
        df['MACD-green'] = talib.EMA(df['close'], timeperiod=12) - talib.EMA(df['close'], timeperiod=26).round(6)
        df['MACD-EMA-9-red'] = talib.EMA(df['MACD-green'], timeperiod=9).round(6)
        dftail = df.tail(8)
        self.middle_left_df.base_widget.set_text(str(dftail))

    def handle_input(self, key):
        if isinstance(key, str):
            input_text = self.middle_left_input.base_widget.get_edit_text()
            if True:  # FIXME: only when edit widget is focused
                if key == "enter":
                    contract_input = self.middle_left_input.base_widget.get_edit_text().upper()
                    if contract_input in ['ES', 'NQ', 'RTY', 'MES', 'MNQ', 'M2K']:
                        con = contract.ContFuture(symbol=contract_input, exchange='CME')
                        self.contract = self.ib.qualifyContracts(con)[0]
                        self.ticker = self.ib.reqTickByTickData(self.contract, 'Last')
                        self.bars = self.ib.reqHistoricalData(
                                self.contract,
                                endDateTime='',
                                durationStr='49500 S',
                                barSizeSetting='5 mins',
                                whatToShow='TRADES',
                                useRTH=False,
                                formatDate=2,  # 1 for tws local tz, 2 for UTC
                                keepUpToDate=True)
                        self.bars.updateEvent += self.onPendingBars
                        #self.middle_left_df.base_widget.set_text(str(util.df(self.bars)))


            if key.lower() == "q":
                log.info("Disconnecting IB(). HYDRA stopping.")
                try:
                    self.ib.cancelTickByTickData(self.ticker.contract, 'Last')
                except:
                    pass
                try:
                    self.bars.updateEvent -= self.onPendingBars
                    self.ib.cancelHistoricalData(self.bars)
                except:
                    pass
                self.ib.sleep(2)
                self.ib.disconnect()
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
        try:
            ib_time_obj = self.ib.reqCurrentTime()
            ib_time = str(ib_time_obj.now(ZoneInfo("America/New_York"))) + "  (New York)"
            self.top_text.base_widget.set_text(ib_time)
            #log.debug(f"Time updated: {ib_time}")
        except Exception as e:
            log.error(f"Error updating time: {e}")
            self.top_text.base_widget.set_text("Error retrieving time.")
        if not self.paused:
            loop.set_alarm_in(0.1, self.refresh_display)
        self.loop.draw_screen()

