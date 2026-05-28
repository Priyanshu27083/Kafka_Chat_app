# ─────────────────────────────────────────────
#  producer.py  –  Kafka message producer
# ─────────────────────────────────────────────

import json
import time
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.config import KAFKA_BOOTSTRAP_SERVERS
from app.db import save_message

logger = logging.getLogger(__name__)


class ChatProducer:
    """
    Wraps KafkaProducer and serialises chat messages to JSON.
    Thread-safe: KafkaProducer is thread-safe by design.
    """

    def __init__(self):
        self._producer: KafkaProducer | None = None

    # ── Connection ─────────────────────────────
    def connect(self) -> bool:
        """Try to connect to Kafka.  Returns True on success."""
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",            # wait for all replicas to ack
                retries=3,
                request_timeout_ms=5_000,
                api_version_auto_timeout_ms=5_000,
            )
            logger.info("KafkaProducer connected.")
            return True
        except NoBrokersAvailable:
            logger.error("No Kafka brokers available.")
            return False
        except Exception as exc:
            logger.error("Producer connect error: %s", exc)
            return False

    # ── Send ───────────────────────────────────
    def send_message(self, topic: str, username: str, message: str) -> bool:
        """
        Publish a chat message.
        Returns True if the send was enqueued successfully.
        """
        if self._producer is None:
            logger.warning("Producer not connected.")
            return False

        payload = {
            "username": username,
            "message": message,
            "timestamp": time.time(),
            "room": topic ,
        }

        

        try:
            future = self._producer.send(topic, value=payload)
            self._producer.flush(timeout=5)  # ensure delivery
            record_meta = future.get(timeout=5)
            # save to MongoDB
            save_message(topic, username, message, payload["timestamp"])
            logger.debug("Sent to %s (partition %s, offset %s)",
                         record_meta.topic, record_meta.partition, record_meta.offset)
            return True
        except KafkaError as exc:
            logger.error("Send error: %s", exc)
            return False

    # ── Cleanup ────────────────────────────────
    def close(self):
        if self._producer:
            self._producer.close()
            self._producer = None
            logger.info("KafkaProducer closed.")

    @property
    def is_connected(self) -> bool:
        return self._producer is not None
