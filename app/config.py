# ─────────────────────────────────────────────
#  config.py  –  Central configuration
# ─────────────────────────────────────────────

# Kafka broker address (change if remote)
KAFKA_BOOTSTRAP_SERVERS = ["127.0.0.1:9092"]

# Default chat topic
DEFAULT_TOPIC = "chat-room"

# Available chat rooms
CHAT_ROOMS = ["chat-room", "tech-talk", "random", "announcements"]

# Consumer group id (unique per app instance is fine for chat)
import uuid
CONSUMER_GROUP_ID = f"chat-consumer-{uuid.uuid4().hex[:8]}"

# How long (ms) the consumer poll blocks before yielding
CONSUMER_POLL_TIMEOUT_MS = 200

# ── Palette (used in gui.py as reference) ──────
PURPLE_PRIMARY   = "#7C5CBF"
PURPLE_DARK      = "#0E0B1A"
PURPLE_MID       = "#1A1230"
PURPLE_LIGHT     = "#9B7FD4"
PURPLE_ACCENT    = "#BFA3F5"
BUBBLE_SENT      = "#6B44B8"
BUBBLE_RECV      = "#211840"
TEXT_MAIN        = "#EDE9FF"
TEXT_DIM         = "#8B7FAB"
