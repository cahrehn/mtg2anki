"""Timestamped logging to stdout, and optionally to a file."""

from datetime import datetime


def make_logger(log_file=None):
    """Return a log function. Writes to log_file too when one is given."""

    def log_message(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {message}"
        print(log_entry, flush=True)
        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a") as f:
                f.write(log_entry + "\n")

    return log_message
