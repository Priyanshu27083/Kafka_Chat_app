# ─────────────────────────────────────────────
#  consumer.py  –  Kafka message consumer
# ─────────────────────────────────────────────

import json
import logging
from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    CONSUMER_GROUP_ID,
    CONSUMER_POLL_TIMEOUT_MS,
)

logger = logging.getLogger(__name__)


class ChatConsumer:
    """
    Wraps KafkaConsumer.  Designed to be driven from a QThread (worker.py).
    NOT thread-safe: one consumer per thread.
    """

    def __init__(self, topic: str):
        self.topic = topic
        self._consumer: KafkaConsumer | None = None
        self._running = False

    def safe_deserializer(self,b):
        try:
            return json.loads(b.decode("utf-8"))
        except:
            return {"username": "Unknown", "message": b.decode("utf-8")}
    
    # ── Connection ─────────────────────────────
    def connect(self) -> bool:
        """Subscribe to the topic.  Returns True on success."""
        try:
            self._consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=self.safe_deserializer,
                consumer_timeout_ms=CONSUMER_POLL_TIMEOUT_MS,
                api_version_auto_timeout_ms=5_000,
                request_timeout_ms=20000,
            )
            self._running = True
            logger.info("KafkaConsumer subscribed to '%s'.", self.topic)
            return True
        except NoBrokersAvailable:
            logger.error("No Kafka brokers available.")
            return False
        except Exception as exc:
            logger.error("Consumer connect error: %s", exc)
            return False

    # ── Poll ───────────────────────────────────
    def poll_messages(self):
        """
        Generator that yields one decoded message dict at a time.
        Stops when self._running is False.
        Caller must handle StopIteration.
        """
        if self._consumer is None:
            return

        while self._running:
            try:
                # KafkaConsumer is itself iterable; consumer_timeout_ms
                # makes it raise StopIteration after silence → we loop again.
                for msg in self._consumer:
                    if not self._running:
                        break
                    data = msg.value          # already decoded by value_deserializer
                    if isinstance(data, dict):
                        yield data
            except StopIteration:
                # poll window elapsed, no new messages – continue looping
                continue
            except KafkaError as exc:
                logger.error("Consumer poll error: %s", exc)
                break

    # ── Cleanup ────────────────────────────────
    def stop(self):
        self._running = False

    def close(self):
        self._running = False
        if self._consumer:
            self._consumer.close()
            self._consumer = None
            logger.info("KafkaConsumer closed.")

    def change_topic(self, new_topic: str) -> bool:
        """Re-subscribe to a different topic without recreating the consumer."""
        if self._consumer is None:
            return False
        try:
            self.topic = new_topic
            self._consumer.unsubscribe()
            self._consumer.subscribe([new_topic])
            logger.info("Consumer switched to topic '%s'.", new_topic)
            return True
        except Exception as exc:
            logger.error("Topic switch error: %s", exc)
            return False
