# ─────────────────────────────────────────────
#  worker.py  –  QThread that drives the consumer
# ─────────────────────────────────────────────
#
#  The GUI NEVER touches Kafka directly.
#  All Kafka I/O lives here, emitted back to the
#  main thread via Qt signals.
#

import logging
from PyQt5.QtCore import QThread, pyqtSignal
from app.consumer import ChatConsumer
from app.config import DEFAULT_TOPIC

logger = logging.getLogger(__name__)


class KafkaWorker(QThread):
    """
    Runs the Kafka consumer loop in a background thread.

    Signals
    -------
    message_received(dict)  – emitted for every incoming chat message
    connection_status(str)  – "connected" | "error" | "disconnected"
    """

    message_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str)

    def __init__(self, topic: str = DEFAULT_TOPIC, parent=None):
        super().__init__(parent)
        self.topic = topic
        self._consumer = ChatConsumer(topic)
        self._active = True

    # ── QThread entry point ────────────────────
    def run(self):
        """Called automatically by QThread.start()."""
        logger.info("KafkaWorker thread started.")

        # Try to connect
        ok = self._consumer.connect()
        if not ok:
            self.connection_status.emit("error")
            logger.error("Consumer failed to connect – worker exiting.")
            return

        self.connection_status.emit("connected")

        # Main consume loop
        try:
            for msg in self._consumer.poll_messages():
                if not self._active:
                    break
                # Emit to GUI (crosses thread boundary safely via Qt queued connection)
                self.message_received.emit(msg)
        except Exception as exc:
            logger.error("Worker loop exception: %s", exc)
            self.connection_status.emit("error")
        finally:
            self._consumer.close()
            self.connection_status.emit("disconnected")
            logger.info("KafkaWorker thread finished.")

    # ── Control ────────────────────────────────
    def stop(self):
        """Request a graceful shutdown."""
        self._active = False
        self._consumer.stop()

    def switch_topic(self, new_topic: str):
        """Hot-swap the subscribed topic."""
        self.topic = new_topic
        self._consumer.change_topic(new_topic)
