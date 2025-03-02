from bot import Bot


class BotManager:
    def __init__(self, tui=None):
        self.bots = []
        # Storing a reference to TUI (optional, but useful if bots need to send messages back)
        self.tui = tui

    def add_bot(self, bot):
        self.bots.append(bot)

    def get_bot_by_name(self, name):
        for bot in self.bots:
            if bot.name == name:
                return bot
        return None

    def remove_bot_by_name(self, name):
        bot = self.get_bot_by_name(name)
        if bot:
            self.bots.remove(bot)

    def run_all_bots(self):
        for bot in self.bots:
            bot.run()

    def send_message_to_bot(self, bot_name, message):
        """
        Relay a TUI/user message to the specified Bot.
        """
        bot = self.get_bot_by_name(bot_name)
        if bot:
            bot.on_message(message)

    def handle_brokerage_update(self, update_data):
        """
        Forward any brokerage/ib_insync streaming updates to all bots,
        or selectively to those who need it.
        """
        for bot in self.bots:
            bot.on_brokerage_update(update_data)

    def on_bot_message(self, bot_name, message):
        """
        Bot calls this to relay a response back up to the TUI.
        Only works if TUI was passed in on initialization.
        """
        if self.tui:
            self.tui.display_bot_message(bot_name, message)

