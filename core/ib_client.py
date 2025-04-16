import os

from ib_async import Contract, Future, IB, util
from core.event_manager import event_manager


util.patchAsyncio()
ib = IB()
ib.connect(os.getenv('IB_HOST'), os.getenv('IB_PORT'), clientId=0)

state = {}

# Contracts and Tickers
state['assets'] = ['MESM5', 'MNQM5']
contracts = {}
for asset in state['assets']:
    if asset.startswith(('MES', 'ES', 'MNQ', 'NQ', 'MYM', 'YM', 'M2K', 'RTY', 'CL', 'GC')):
        contract = Future(localSymbol=asset, exchange='CME', currency='USD')
        qualified = ib.qualifyContracts(contract)
        contracts[asset] = qualified[0]
    else:
        raise Exception("Qualify asset class manually:")
        # Fill manually
        #contract = Stock(localSymbol=asset, exchange='', currency='USD')
    qualified = ib.qualifyContracts(contract)
    contracts[asset] = qualified[0]

tickers = {}
for c in contracts:
    ib.reqMktData(contracts[c], '233', False, False, [])
    # https://ib-insync.readthedocs.io/api.html#ib_insync.ib.IB.reqMktData
    tickers[c] = ib.ticker(contracts[c])
ib.sleep(1.0)

# Positions

def update_state():
    try:
        ib.sleep(0.1)
        state['system_time'] = ib.reqCurrentTime()
        state['account_summary'] = ib.accountSummary()
        state['mes_last'] = tickers['MESM5'].last
        state['mnq_last'] = tickers['MNQM5'].last
        state['portfolio'] = ib.portfolio()
        state['positions'] = ib.positions()
        state['debug'] = populate_pos_data()
        #populate_pos_data()
    except RuntimeError as e:
        if "Event loop stopped before Future completed" in str(e):
            pass  # Event loop is already stopping, ignore this error.
        else:
            raise  # For any other runtime error, re-raise.
    except ConnectionError as e:
        if "Not connected" in str(e):
            pass  # Keep retrying anyway
        else:
            raise

ib.pendingTickersEvent += update_state

def populate_pos_data():
    pos = ib.portfolio()
    data = []
    current_owned = []
    for p in pos:
        row = []
        row.append(p.contract.localSymbol)
        current_owned.append(p.contract.localSymbol)
        row.append(str(p.position))
        row.append(str(round((p.averageCost / float(multiplier)), 2)))
        row.append(str(round(p.marketPrice, 2)))
        row.append(str(int(round(p.unrealizedPNL, 0))))
        row.append(str(int(round(p.realizedPNL, 0))))
        data.append(row)
    for asset in state['assets']:
        if asset not in current_owned:
            data.append([asset, '0', '0.00', 'FIXME', '0', '0'])

    # sort alphabetically, except the header
    sorted_rows = sorted(data, key=lambda sublist: sublist[0])
    pos_data = [['localSymbol', 'position', 'averageCost', 'marketPrice', 'unrealizedPNL', 'realizedPNL']]
    for each_row in sorted_rows:
        pos_data.append(each_row)
    return pos_data

def graceful_shutdown():
        ib.pendingTickersEvent -= update_state
        for c in contracts:
            ib.cancelMktData(contracts[c])
        ib.sleep(0.5)
        ib.disconnect()

