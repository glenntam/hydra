# from ib_async import *
# import time

# ib = IB()
# ib.connect('127.0.0.1', 7497, clientId=0)



import asyncio
from datetime import date

from ib_async import IB, Forex, util, ContFuture

bars = None
prev_bars = None
async def load(end):
    print(f"Loading {end}")
    global bars
    bars = await ib.reqHistoricalDataAsync(
        contract, endDateTime='', durationStr="49500 S", barSizeSetting="5 mins",
        whatToShow="TRADES", useRTH=False, formatDate=2, keepUpToDate=False)
    global prev_bars
    prev_bars = bars
    print(bars)


async def main():
    tasks = [asyncio.create_task(load(1)),
             asyncio.create_task(load(2))]
    await asyncio.gather(*tasks)
    print('All done')


if __name__ == "__main__":
    #util.patchAsyncio()
    ib = IB()
    ib.connect(host='127.0.0.1', port=7497, clientId=1)
    #contract = Forex("GBPUSD", 'IDEALPRO')
    contract = ContFuture('MES', 'CME')
    ib.qualifyContracts(contract)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


# def onTicker(ticker):
#     print(ticker.bid)

# cons = ['ES', 'NQ', 'RTY', 'MES', 'MNQ', 'M2K']
# for c in cons:
#     contract = ContFuture(symbol=c, exchange='CME')
#     contract = ib.qualifyContracts(contract)
#     print(contract)


# con = ContFuture('YM', exchange='CBOT')
# c = ib.qualifyContracts(con)[0]
# ib.reqMktData(c, genericTickList='', snapshot=False, regulatorySnapshot=False)
# ticker = ib.ticker(c)
# ib.sleep(0.5)
# ticker

