import os

from ib_async import Future, IB, util
from core.event_manager import event_manager


util.patchAsyncio()
ib = IB()
ib.connect(os.getenv('IB_HOST'), os.getenv('IB_PORT'), clientId=0)


mes = Future('MES', '20250620')
mnq = Future('MNQ', '20250620')

contracts = {'MNQ': ib.qualifyContracts(mnq)[0],
             'MES': ib.qualifyContracts(mes)[0],
            }

# tickers = {}
# for c in contracts:
#     ib.reqMktData(contracts[c], '233', False, False, [])
#     # https://ib-insync.readthedocs.io/api.html#ib_insync.ib.IB.reqMktData
#     tickers[c] = ib.ticker(contracts[c])
#     ib.sleep(1.0)

def graceful_shutdown():
    for c in contracts:
        ib.cancelMktData(contracts[c])
    ib.sleep(0.2)
    ib.disconnect()

#from pprint import pprint
#pprint(tickers['MES'].last)
#ib.disconnect()
#input("PAUSE")

