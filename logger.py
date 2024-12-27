import logging
import os
import sys
from datetime import datetime
from logging.handlers import SMTPHandler
from zoneinfo import ZoneInfo


class Logger:
    """Custom HYDRA logger with: system, email, trade, and streaming handlers."""
    _instance = None  # Ensure only one instance of Logger per app
    def __new__(cls, console_height):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, console_height):
        if self._initialized:
            return
        self._initialized = True

        self.logger = logging.getLogger("HYDRA_logger")
        self.logger.setLevel(logging.DEBUG)  # Keep as Debug. Console will always need to show debug messages.

        # Ensure log directory exists
        try:
            os.makedirs("./log", exist_ok=True)
        except Exception as e:
            self.print_and_exit(f"Failed to create log directory: {e}")

        # Formatter with America/New_York timezone
        def format_time(record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, ZoneInfo("America/New_York"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.formatter = logging.Formatter(fmt='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
            self.formatter.formatTime = format_time
        except Exception as e:
            self.print_and_exit(f"Couldn't set formatter: {e}")

        # Setup Handlers
        self.file_handler = self.setup_file_handler()
        self.email_handler = self.setup_email_handler()
        self.trade_handler = self.setup_trade_handler()
        self.console_handler = self.setup_console_handler(console_height)

        # Add Handlers to Logger
        try:
            self.logger.addHandler(self.file_handler)
            self.logger.addHandler(self.email_handler)
            self.logger.addHandler(self.trade_handler)
            self.logger.addHandler(self.console_handler)
        except Exception as e:
            self.print_and_exit(f"Failed to add handlers to logger: {e}")

    def setup_file_handler(self):
        """Sets up the FileHandler for system logs with a custom emit method."""
        try:
            file_handler = logging.FileHandler("./log/hydra.log", encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(self.formatter)
            def emit(record):
                self.file_handler_emit(record)
            file_handler.emit = emit
            return file_handler
        except Exception as e:
            self.print_and_exit(f"Failed to set up file handler: {e}")

    def file_handler_emit(self, record):
        """Custom emit method for file_handler to write logs and trim file size."""
        try:
            log_entry = self.formatter.format(record)
            with open("./log/hydra.log", "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
            # Trim the log file to the last 300 lines
            with open("./log/hydra.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 500:
                with open("./log/hydra.log", "w", encoding="utf-8") as f:
                    f.writelines(lines[-500:])
        except Exception as e:
            self.print_and_exit(f"Failed to write to hydra.log: {e}")

    def setup_email_handler(self):
        """Sets up the SMTPHandler for sending error emails."""
        try:
            email_host = os.getenv("EMAIL_HOST")
            email_port = os.getenv("EMAIL_PORT")
            email_from = os.getenv("EMAIL_FROM")
            email_to = os.getenv("EMAIL_TO")
            email_subject = os.getenv("EMAIL_SUBJECT")
            email_user = os.getenv("EMAIL_USER")
            email_password = os.getenv("EMAIL_PASSWORD")

            if not all([email_host, email_port, email_from, email_to, email_subject, email_user, email_password]):
                self.print_and_exit("Missing one or more environment variables for the email handler.")

            email_handler = SMTPHandler(
                mailhost=(email_host, int(email_port)),
                fromaddr=email_from,
                toaddrs=[email_to],
                subject=email_subject,
                credentials=(email_user, email_password),
                secure=()
            )
            email_handler.setLevel(logging.CRITICAL)
            email_handler.setFormatter(self.formatter)
            return email_handler
        except Exception as e:
            self.print_and_exit(f"Failed to set up email handler: {e}")

    def setup_trade_handler(self):
        """Sets up the TradeHandler for trade-specific logs with a custom emit method."""
        try:
            trade_handler = logging.FileHandler("./log/.gitkeep", encoding="utf-8")
            trade_handler.setLevel(logging.WARNING)
            trade_handler.setFormatter(self.formatter)
            trade_handler.addFilter(self.warning_only_filter)
            def emit(record):
                self.trade_handler_emit(record)
            trade_handler.emit = emit
            return trade_handler
        except Exception as e:
            self.print_and_exit(f"Failed to set up trade handler: {e}")

    def trade_handler_emit(self, record):
        """Custom emit method for trade_handler to write trade-specific logs."""
        try:
            dt = datetime.fromtimestamp(record.created, ZoneInfo("America/New_York"))
            filename = f"./log/trades{dt.year}.log"
            with open(filename, "a", encoding="utf-8") as f:
                f.write(self.formatter.format(record) + "\n")
        except Exception as e:
            self.print_and_exit(f"Failed to emit trade message: {e}")

    def setup_console_handler(self, console_height):
        """Sets up the ConsoleHandler to capture log messages for TUI with a custom emit method."""
        self.console_height = console_height
        self.console_messages = []
        try:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(self.formatter)
            #self.original_streamhandler_emit = console_handler.emit
            def emit(record):
                self.console_handler_emit(record)
            console_handler.emit = emit
            return console_handler
        except Exception as e:
            self.print_and_exit(f"Failed to set up console handler: {e}")

    def console_handler_emit(self, record):
        """Custom emit method for console_handler to capture log messages for TUI."""
        try:
            log_entry = self.formatter.format(record)
            if len(self.console_messages) > self.console_height:
                self.console_messages.pop(0)
            #self.original_streamhandler_emit(record)
            self.console_messages.append(log_entry)
        except Exception as e:
            self.print_and_exit(f"Failed to capture log message: {e}")

    def get_console_messages(self):
        """Allow outside app to access self.console_messages."""
        return self.console_messages

    def warning_only_filter(self, record):
        """Helper ilter to allow ONLY warning level logs."""
        return record.levelno == logging.WARNING

    def OnIBErrorEvent(self, reqId: int, errorCode: int, errorString: str, Contract):
        self.logger.error(f"(TWS) reqId({reqId}) errorCode({errorCode}) {errorString}. Contract:{Contract}")

    def print_and_exit(self, message):
        """Prints an error message to stderr and exits the program."""
        # Configure a basic logger to stderr to ensure the message is printed
        logging.basicConfig(level=logging.ERROR)
        logging.error(message)
        sys.exit(1)
