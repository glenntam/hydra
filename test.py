from ib_async import *
import time

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=0)

# def onTicker(ticker):
#     print(ticker.bid)

# contract = ContFuture('MNQ')
# contract = ib.qualifyContracts(contract)[0]
# ticker = ib.reqMktData(contract)
# ticker.updateEvent += onTicker


# while True:
#     ib.sleep(0.03)


# def onScanData(scanData):
#     print(scanData[0])
#     print(len(scanData))

# sub = ScannerSubscription(
#     instrument='FUT.US',
#     scanCode='TOP_PERC_GAIN')
#scandata = ib.reqscannersubscription(sub)
#scandata.updateevent += onscandata
#ib.sleep(60)
#ib.cancelscannersubscription(scandata)

while True:
    print(ib.reqCurrentTime().isoformat(), end='\r')
    #util.sleep(0.2)

