from datetime import datetime
from zoneinfo import ZoneInfo

import talib

from logger import logger, log
from ib_async import IB, contract, util


class Bot:

    def __init__(self, codename, report_to_tui, ip='127.0.0.1', port=7498, client_id=0):
        self.codename = codename
        self.callback = report_to_tui
        self.ip = ip
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    def connect(self):
        self.ib.connect(self.ip, self.port, clientId=self.client_id)
        self.ib.errorEvent += logger.OnIBErrorEvent  # catch IB TWS errors

    def disconnect(self):
        log.debug("STOPPING")
        self.ib.cancelTickByTickData(self.ticker.contract, 'Last')
        self.bars.updateEvent -= self.onPendingBars
        self.ib.cancelHistoricalData(self.bars)
        self.ib.sleep(2)
        self.ib.disconnect()
        log.debug(f"{self.codename} disconnected")

    def display_time(self):
        ib_time_obj = self.ib.reqCurrentTime()
        ib_time = str(ib_time_obj.now(ZoneInfo("America/New_York"))) + "  (New York)"
        self.callback(self.client_id, 'time', ib_time)

    def qualify(self, contract_to_qualify: str):
        if contract_to_qualify.upper() in ['ES', 'NQ', 'RTY', 'MES', 'MNQ', 'M2K']:
            c = contract.ContFuture(symbol=contract_to_qualify.upper(), exchange='CME')
            contract_obj = self.ib.qualifyContracts(c)[0]
            return contract_obj

    def start_ticker(self, qualified_contract):
        self.ticker = self.ib.reqTickByTickData(qualified_contract, 'Last')
        self.ib.pendingTickersEvent += self.onPendingTickByTick

    def onPendingTickByTick(self, ticker):
        t = f"[{self.ticker.contract.symbol}] {self.ticker.tickByTicks[0].price:.2f}  x  {self.ticker.tickByTicks[0].size}"
        self.callback(self.client_id, 'ticker', t)

    def stop_ticker(self, qualified_contract):
        self.ib.cancelTickByTickData(qualified_contract, 'Last')

    def start_bars(self, qualified_contract):
        self.bars = self.ib.reqHistoricalData(
                                qualified_contract,
                                endDateTime='',
                                durationStr='49500 S',
                                barSizeSetting='5 mins',
                                whatToShow='TRADES',
                                useRTH=False,
                                formatDate=2,  # 1 for tws local tz, 2 for UTC
                                keepUpToDate=True)
        self.bars.updateEvent += self.onPendingBars

    def onPendingBars(self, bars, hasNewBar):
        df = util.df(bars)
        df['date'] = df['date'].dt.tz_convert("America/New_York")
        df['average'] = df['average'].round(2)
        df['close'] = df['close'].round(3)
        df['MACD-green'] = talib.EMA(df['close'], timeperiod=12) - talib.EMA(df['close'], timeperiod=26).round(6)
        df['MACD-EMA-9-red'] = talib.EMA(df['MACD-green'], timeperiod=9).round(6)
        dftail = df.tail(8)
        self.callback(self.client_id, 'bars', str(dftail))

