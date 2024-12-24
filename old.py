import logging
import os
from datetime import datetime
from logging.handlers import SMTPHandler, TimedRotatingFileHandler
from zoneinfo import ZoneInfo

import urwid
from dotenv import load_dotenv
from ib_async import IB, util


class TUI:
    def __init__(self):
        self.setup_loggers()

        # Initialize UI Components
        self.top_text = urwid.Text("Waiting for time...")
        self.top = urwid.LineBox(urwid.Filler(self.top_text))

        self.middle_left_text = urwid.Text("ML")
        self.middle_left = urwid.LineBox(urwid.Filler(self.middle_left_text))

        self.middle_right_text = urwid.Text("MR")
        self.middle_right = urwid.LineBox(urwid.Filler(self.middle_right_text))

        self.middle = urwid.Filler(urwid.Columns([self.middle_left, self.middle_right]))

        self.bottom_text = urwid.Text(" " * 80)  # Initialize with empty space for 7 rows
        self.bottom = urwid.LineBox(urwid.Filler(self.bottom_text, valign="top"))

        self.frame = urwid.Pile([self.top, self.middle, self.bottom])

        # Connect to Interactive Brokers (IB)
        self.ib = IB()
        self.ib.connect('127.0.0.1', 7497, clientId=0)
        self.logger.debug("Connected to IB()")

        # Setup Event Loops
        self.ib_loop = util.getLoop()  # ib_async's built-in asyncio event loop
        self.my_asyncio_loop = urwid.AsyncioEventLoop(loop=self.ib_loop)  # Integrate with urwid
        self.loop = urwid.MainLoop(
            self.frame,
            unhandled_input=self.handle_input,
            event_loop=self.my_asyncio_loop
        )

        # Schedule the first refresh
        self.loop.set_alarm_in(0, self.refresh_display)
        self.loop.run()

    def setup_loggers(self):
        self.logger = logging.getLogger("TUI_Logger")
        self.logger.setLevel(logging.DEBUG)  # Changed from NOTSET to DEBUG

        # Ensure log directory exists
        os.makedirs("./log", exist_ok=True)

        # Formatter with America/New_York timezone
        self.formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s')

        def format_time(record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, ZoneInfo("America/New_York"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        self.formatter.formatTime = format_time

        # File Handler for General Logs
        self.file_handler = logging.FileHandler("./log/hydra.log")
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(self.formatter)
        self.file_handler.emit = self.file_handler_emit
        self.logger.addHandler(self.file_handler)

        # Email Handler for Critical Alerts (Currently Disabled)
        try:
            email_host = os.getenv("EMAIL_HOST")
            email_port = int(os.getenv("EMAIL_PORT"))
            email_from = os.getenv("EMAIL_FROM")
            email_to = os.getenv("EMAIL_TO")
            email_subject = os.getenv("EMAIL_SUBJECT")
            email_user = os.getenv("EMAIL_USER")
            email_password = os.getenv("EMAIL_PASSWORD")

            if all([email_host, email_port, email_from, email_to, email_subject, email_user, email_password]):
                self.email_handler = SMTPHandler(
                    mailhost=(email_host, email_port),
                    fromaddr=email_from,
                    toaddrs=[email_to],
                    subject=email_subject,
                    credentials=(email_user, email_password),
                    secure=()
                )
                self.email_handler.setLevel(logging.INFO)
                self.email_handler.setFormatter(self.formatter)
                self.logger.addHandler(self.email_handler)
            else:
                self.logger.warning("Email handler not configured due to missing environment variables.")
        except Exception as e:
            self.logger.error(f"Failed to set up email handler: {e}")

        # Console Handler to Capture Log Messages for TUI
        self.log_messages = []  # To store the last 7 log messages
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(logging.DEBUG)
        self.console_handler.setFormatter(self.formatter)
        self.console_handler.emit = self.console_handler_emit
        self.logger.addHandler(self.console_handler)

        # Trade Handler for Warning and Above
        self.trade_handler = logging.FileHandler("./log/trades.YYYY.log")
        self.trade_handler.setLevel(logging.WARNING)
        self.trade_handler.setFormatter(self.formatter)

        def warning_filter(record):
            return record.levelno >= logging.WARNING

        self.trade_handler.addFilter(warning_filter)
        self.trade_handler.emit = self.trade_handler_emit
        self.logger.addHandler(self.trade_handler)

        self.logger.debug("Logger setup complete.")

    def file_handler_emit(self, record):
        try:
            log_entry = self.formatter.format(record)
            with open(self.file_handler.baseFilename, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
            # Trim the log file to the last 200 lines
            with open(self.file_handler.baseFilename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 200:
                with open(self.file_handler.baseFilename, "w", encoding="utf-8") as f:
                    f.writelines(lines[-200:])
        except Exception as e:
            # If logging fails, print to stderr
            print(f"Failed to write to log file: {e}")

    def trade_handler_emit(self, record):
        try:
            dt = datetime.fromtimestamp(record.created, ZoneInfo("America/New_York"))
            filename = f"./log/trades{dt.year}.log"
            with open(filename, "a", encoding="utf-8") as f:
                f.write(self.formatter.format(record) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write trade log: {e}")

    def console_handler_emit(self, record):
        try:
            log_entry = self.formatter.format(record)
            self.log_messages.append(log_entry)
            if len(self.log_messages) > 7:
                self.log_messages.pop(0)
        except Exception as e:
            # If capturing log messages fails, print to stderr
            print(f"Failed to capture log message: {e}")

    def handle_input(self, key):
        if key.lower() == "q":
            self.logger.debug("Disconnecting...")
            self.ib.disconnect()
            raise urwid.ExitMainLoop()

    def refresh_display(self, loop, user_data=None):
        # Update time display
        try:
            # Assuming reqCurrentTime returns an object with a 'now' attribute that is a datetime
            ib_time_obj = self.ib.reqCurrentTime()
            # Wait for the result (since ib_async uses asyncio)
            ib_time = str(ib_time_obj.now(ZoneInfo("America/New_York"))) + "  (New York)"
            self.top_text.set_text(ib_time)
            self.logger.debug(f"Time updated: {ib_time}")
        except Exception as e:
            self.logger.error(f"Error updating time: {e}")
            self.top_text.set_text("Error retrieving time.")

        # Update bottom_text with the last 7 log messages
        if hasattr(self, 'log_messages'):
            # Ensure there are always 7 lines
            log_display = self.log_messages[-8:]
            while len(log_display) < 8:
                log_display.insert(0, " ")
            # Join the last 7 messages, most recent at the bottom
            display_text = "\n".join(log_display)
            self.bottom_text.set_text(display_text)

        # Schedule the next refresh
        loop.set_alarm_in(0.5, self.refresh_display)  # Adjust the interval as needed

if __name__ == "__main__":
    load_dotenv()
    util.patchAsyncio()  # Allow ib_async's asyncio event loop to run nested within urwid's MainLoop
    try:
        app = TUI()
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Application failed to start: {e}")

