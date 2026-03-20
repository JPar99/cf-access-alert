"""Graceful shutdown — handle SIGTERM/SIGINT to save state before exiting."""

import logging
import signal

log = logging.getLogger("cf-access-alert")


class GracefulShutdown:
    """Handle SIGTERM/SIGINT to allow clean exit."""

    def __init__(self):
        self.should_exit = False
        signal.signal(signal.SIGTERM, self._handler)
        signal.signal(signal.SIGINT, self._handler)

    def _handler(self, signum, frame):
        signame = signal.Signals(signum).name
        log.info("Received %s — shutting down gracefully", signame)
        self.should_exit = True
