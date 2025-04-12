import os
import sys
from collections import defaultdict

from dotenv import load_dotenv; load_dotenv()
from core.event_manager import event_manager
from core.ib_client import ib, Future
from core.logger import logger, log
from tui2 import tui





class Hydra2:
    def __init__(self):
        log.info("Starting HYDRA")
        # Uncomment to suppress printing errors to terminal
        #sys.stderr = open(os.devnull, 'w')

        # Allow ib_async's asyncio event loop to run nested and be used as urwid's MainLoop later
        #util.patchAsyncio()






#     def execute_trade(self, bot_id, action, order_type, contract, amt, price):
#         #execute trade on ib.
#         #pass confirmation to bot (and save to db)
#         #convey to TUI?
#         if order_type == 'LMT':
#             if action == 'BUY':
#                 order = LimitOrder('BUY', amt, price)
#             elif action == 'SELL':
#                 order = LimitOrder('SELL', amt, price)
#         elif order_type == 'MKT':
#             if action == 'BUY':
#                 order = MarketOrder('BUY', amt)
#             elif action == 'SELL':
#                 order = MarketOrder('SELL', amt)
#         else:
#             pass
#         trade = self.ib.placeOrder(self.contracts[contract], order)



    def start(self):
        #self.ib.connect(os.getenv('IB_HOST'), os.getenv("IB_PORT"), clientId=0)
        #self.ib.connect('127.0.0.1', 7498, clientId=0)
        self.ib.errorEvent += logger.OnIBErrorEvent  # Catch IB TWS errors
        #self.tui.initialize_bots()



#     def initialize__bots(self):
#         self.bots = {
#                 0: Bot(bot_id=0, codename='master', event_manager=self.event_manager),
#                 1: Bot(bot_id=1, codename='ss_live', event_manager=self.event.manager),
#         }

#     def graceful_stop(self):
#         #TODO: More stuff
#         self.ib.disconnect()
#         self.tui.stop()





#     def bot_callback(self, bot_id, action, message):
#         """All individual bots will call this when they need to send a message to Hydra/TUI.

#         It's up to this func to decide what to do to TUI based on this info"""
#         if action == 'time':
#             try:
#                 self.tui.top_text.base_widget.set_text(s)
#             except:
#                 log.error(f"Error updating time: {e}")
#                 self.tui.top_text.base_widget.set_text("Error retrieving time.")
#         if action == 'ticker':
#             try:
#                 self.tui.middle_left_ticker.base_widget.set_text(s)
#             except:
#                 pass
#         if actions == 'bars':
#             try:
#                 self.tui.middle_left_df.base_widget.set_text(s)
#             except:
#                 pass



#     def get_bot_codename_list(self):
#         return [bot.codename for bot in self.bots.values()]

#     def get_key_int_from_bot_codename(self, codename: str):
#         """Return integer key number of self.bots given a codename. Return 0 if none found."""
#         return next((key for key, bot in self.bots.items() if codename == bot.codename), 0)


# if __name__ == "__main__":
#     app = Hydra()
#     app.start()
