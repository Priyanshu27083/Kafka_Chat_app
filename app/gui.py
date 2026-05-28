# ─────────────────────────────────────────────
#  gui.py  –  Main application window
# ─────────────────────────────────────────────

import time
import datetime
import logging

from PyQt5.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                           QTimer, pyqtSlot, QSize)
from PyQt5.QtGui import (QColor, QFont, QFontDatabase, QPalette,
                          QLinearGradient, QIcon, QPixmap, QPainter,
                          QTextOption)
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QFrame, QComboBox, QGraphicsDropShadowEffect,
    QSizePolicy, QSpacerItem, QTextEdit, QApplication,
)

from app.config import CHAT_ROOMS, BUBBLE_SENT, BUBBLE_RECV
from app.worker import KafkaWorker
from app.producer import ChatProducer
from app.db import load_messages
from app.summarizer import summarize_chat
from PyQt5.QtWidgets import QMessageBox
from app.analytics import get_analytics

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  Colour tokens
# ══════════════════════════════════════════════
C = {
    "bg_deep":    "#080612",
    "bg_panel":   "#100D20",
    "bg_card":    "#181330",
    "border":     "#2D2450",
    "purple_hi":  "#7B5EA7",
    "purple_btn": "#6B44B8",
    "purple_glow":"#9B7FD4",
    "accent":     "#C4AAFF",
    "sent":       "#5C35A8",
    "recv":       "#1E1840",
    "text":       "#EDE9FF",
    "text_dim":   "#7A6FAA",
    "green":      "#4DFFB4",
    "yellow":     "#FFD166",
    "red":        "#FF6B8A",
}

# ══════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════
def fmt_time(ts: float) -> str:
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M")


def shadow(blur=20, color="#6B44B8", alpha=120) -> QGraphicsDropShadowEffect:
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    c = QColor(color)
    c.setAlpha(alpha)
    eff.setColor(c)
    eff.setOffset(0, 4)
    return eff


# ══════════════════════════════════════════════
#  Message Bubble Widget
# ══════════════════════════════════════════════
class MessageBubble(QFrame):
    """
    A single chat bubble.  Sent messages sit on the right,
    received messages on the left.
    """

    def __init__(self, username: str, message: str, ts: float,
                 is_self: bool, parent=None):
        super().__init__(parent)
        self.is_self = is_self
        self._build(username, message, ts)

    def _build(self, username, message, ts):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)
        outer.setSpacing(0)

        # ── bubble frame ──────────────────────
        bubble = QFrame()
        bubble.setMaximumWidth(480)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if self.is_self:
            bg = C["sent"]
            border_col = "#8B6FD4"
            radius = "18px 18px 4px 18px"
        else:
            bg = C["recv"]
            border_col = C["border"]
            radius = "18px 18px 18px 4px"

        bubble.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border_col};
                border-radius: {radius};
                padding: 10px 14px 8px 14px;
            }}
        """)

        blay = QVBoxLayout(bubble)
        blay.setSpacing(3)
        blay.setContentsMargins(0, 0, 0, 0)

        # username + time row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        uname = QLabel(username)
        uname.setFont(QFont("Segoe UI", 9, QFont.Bold))
        if self.is_self:
            uname.setStyleSheet(f"color: {C['accent']}; background: transparent;")
        else:
            uname.setStyleSheet(f"color: {C['purple_glow']}; background: transparent;")

        ts_label = QLabel(fmt_time(ts))
        ts_label.setFont(QFont("Segoe UI", 8))
        ts_label.setStyleSheet(f"color: {C['text_dim']}; background: transparent;")

        meta_row.addWidget(uname)
        meta_row.addStretch()
        meta_row.addWidget(ts_label)

        # message text
        msg_label = QLabel(message)
        msg_label.setFont(QFont("Segoe UI", 11))
        msg_label.setStyleSheet(f"color: {C['text']}; background: transparent;")
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        blay.addLayout(meta_row)
        blay.addWidget(msg_label)

        eff = shadow(16, "#6B44B8" if self.is_self else "#000000", 80)
        bubble.setGraphicsEffect(eff)

        if self.is_self:
            outer.addStretch()
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addStretch()


# ══════════════════════════════════════════════
#  Status Pill
# ══════════════════════════════════════════════
class StatusPill(QLabel):
    STATES = {
        "waiting":      ("🟡", "Waiting",    C["yellow"]),
        "connected":    ("🟢", "Connected",  C["green"]),
        "error":        ("🔴", "Kafka Offline", C["red"]),
        "disconnected": ("🔴", "Disconnected", C["red"]),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_state("waiting")
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet(f"""
            QLabel {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                padding: 3px 12px;
                color: {C['text']};
            }}
        """)

    def set_state(self, state: str):
        icon, label, color = self.STATES.get(state, self.STATES["waiting"])
        self.setText(f"{icon}  {label}")
        self.setStyleSheet(f"""
            QLabel {{
                background: {C['bg_card']};
                border: 1px solid {color};
                border-radius: 10px;
                padding: 3px 12px;
                color: {color};
                font-weight: bold;
            }}
        """)


# ══════════════════════════════════════════════
#  Send Button
# ══════════════════════════════════════════════
SEND_STYLE = f"""
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #7B5EA7, stop:1 #4B2D8F);
    color: {C['text']};
    border: none;
    border-radius: 22px;
    padding: 0 28px;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #9B7EC7, stop:1 #6B4DAF);
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #5B3E87, stop:1 #3B1D6F);
    padding-top: 2px;
}}
"""


# ══════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════
class ChatWindow(QMainWindow):

    def __init__(self,username):
        super().__init__()
        self.setWindowTitle("⚡ KafkaChat")
        self.setMinimumSize(820, 640)
        self.resize(940, 720)

        self._username = username
        self._current_room = CHAT_ROOMS[0]
        self._producer = ChatProducer()
        self._worker: KafkaWorker | None = None
        self._typing_timer = QTimer(self)
        self._typing_timer.setSingleShot(True)
        self._typing_timer.timeout.connect(self._stop_typing_indicator)
        self._other_typing = False

        self._apply_palette()
        self._build_ui()
        self._start_kafka()

    def _show_summary(self):
        summary = summarize_chat(self._current_room)
        QMessageBox.information(
            self,
            "Chat Summary",
            summary
    )
        
    #Analytics
    def _print_analytics(self):
        data = get_analytics(self._current_room)
        
        print("\n" + "="*40)
        print(f"📊 Analytics (Room: {self._current_room})")
        print("="*40)
        print(data)
        print("="*40 + "\n")

    # ── App-wide palette ───────────────────────
    def _apply_palette(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {C['bg_deep']};
                color: {C['text']};
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }}
            QScrollBar:vertical {{
                background: {C['bg_panel']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['purple_hi']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QComboBox {{
                background: {C['bg_card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {C['bg_card']};
                color: {C['text']};
                selection-background-color: {C['sent']};
                border: 1px solid {C['border']};
            }}
            QLineEdit {{
                background: {C['bg_card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 12px;
                selection-background-color: {C['sent']};
            }}
            QLineEdit:focus {{
                border: 1px solid {C['purple_hi']};
            }}
        """)

    # ── Build UI ───────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.setCentralWidget(root)

        # ── Header bar ─────────────────────────
        root_lay.addWidget(self._make_header())

        # ── Body (sidebar + chat) ──────────────
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._make_sidebar())
        body.addWidget(self._make_chat_panel(), 1)
        root_lay.addLayout(body, 1)

    # ── Header ─────────────────────────────────
    def _make_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1A0F35, stop:1 #0E0B1A);
                border-bottom: 1px solid {C['border']};
            }}
        """)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 0, 20, 0)

        # Logo / title
        logo = QLabel("⚡")
        logo.setFont(QFont("Segoe UI", 20))
        logo.setStyleSheet("background: transparent;")

        title = QLabel("KafkaChat")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"""
            background: transparent;
            color: {C['accent']};
            letter-spacing: 2px;
        """)

        subtitle = QLabel("Real-time · Apache Kafka")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet(f"background: transparent; color: {C['text_dim']};")

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        lay.addWidget(logo)
        lay.addSpacing(10)
        lay.addLayout(title_col)
        lay.addStretch()

        # Status pill
        self.status_pill = StatusPill()
        lay.addWidget(self.status_pill)

        return header

    # ── Sidebar ────────────────────────────────
    def _make_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(220)

        sidebar.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_panel']};
                border-right: 1px solid {C['border']};
            }}
        """)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(14, 20, 14, 20)
        lay.setSpacing(16)

        # ── User section ───────────────────────
        user_card = self._make_card()
        user_lay = QVBoxLayout(user_card)
        user_lay.setSpacing(6)

        lbl_user = QLabel("YOUR NAME")
        lbl_user.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl_user.setStyleSheet(f"color: {C['text_dim']}; background: transparent; letter-spacing: 1px;")

        self.username_input = QLineEdit("Guest")
        self.username_input.setPlaceholderText("Enter username…")
        self.username_input.setMaxLength(24)
        self.username_input.setText(self._username)
        self.username_input.textChanged.connect(self._on_username_changed)

        user_lay.addWidget(lbl_user)
        user_lay.addWidget(self.username_input)
        lay.addWidget(user_card)

        # ── Room section ───────────────────────
        room_card = self._make_card()
        room_lay = QVBoxLayout(room_card)
        room_lay.setSpacing(6)

        lbl_room = QLabel("CHAT ROOM")
        lbl_room.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl_room.setStyleSheet(f"color: {C['text_dim']}; background: transparent; letter-spacing: 1px;")

        self.room_combo = QComboBox()
        for r in CHAT_ROOMS:
            self.room_combo.addItem(f"# {r}")
        self.room_combo.currentIndexChanged.connect(self._on_room_changed)

        room_lay.addWidget(lbl_room)
        room_lay.addWidget(self.room_combo)
        lay.addWidget(room_card)

        # ── Tips card ──────────────────────────
        tips_card = self._make_card()
        tips_lay = QVBoxLayout(tips_card)
        tips_lay.setSpacing(4)

        tip_title = QLabel("💡 TIPS")
        tip_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        tip_title.setStyleSheet(f"color: {C['text_dim']}; background: transparent; letter-spacing: 1px;")
        tips_lay.addWidget(tip_title)

        tips = [
            "Open multiple windows\nto simulate users.",
            "Press Enter to send.",
            "Switch rooms live.",
        ]
        for t in tips:
            tl = QLabel(t)
            tl.setFont(QFont("Segoe UI", 9))
            tl.setStyleSheet(f"color: {C['text_dim']}; background: transparent;")
            tl.setWordWrap(True)
            tips_lay.addWidget(tl)

        lay.addWidget(tips_card)
        lay.addStretch()

        # ── Kafka info ─────────────────────────
        kafka_lbl = QLabel("Apache Kafka 3.x")
        kafka_lbl.setFont(QFont("Segoe UI", 8))
        kafka_lbl.setAlignment(Qt.AlignCenter)
        kafka_lbl.setStyleSheet(f"color: {C['text_dim']}; background: transparent;")
        lay.addWidget(kafka_lbl)

        return sidebar

    def _make_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                padding: 4px;
            }}
        """)
        return card

    # ── Chat panel ─────────────────────────────
    def _make_chat_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background: {C['bg_deep']};")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Chat room label bar
        self.room_label_bar = QFrame()
        self.room_label_bar.setFixedHeight(40)
        self.room_label_bar.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_panel']};
                border-bottom: 1px solid {C['border']};
            }}
        """)
        rbl = QHBoxLayout(self.room_label_bar)
        rbl.setContentsMargins(20, 0, 20, 0)
        self.room_name_lbl = QLabel(f"# {CHAT_ROOMS[0]}")
        self.room_name_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.room_name_lbl.setStyleSheet(f"color: {C['accent']}; background: transparent;")

        self.typing_lbl = QLabel("")
        self.typing_lbl.setFont(QFont("Segoe UI", 9))
        self.typing_lbl.setStyleSheet(f"color: {C['text_dim']}; background: transparent;")

        rbl.addWidget(self.room_name_lbl)
        rbl.addStretch()
        rbl.addWidget(self.typing_lbl)
        lay.addWidget(self.room_label_bar)

        # ── Scroll area (message bubbles) ──────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)

        self.messages_widget = QWidget()
        self.messages_widget.setStyleSheet(f"background: transparent;")
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(0, 12, 0, 12)
        self.messages_layout.setSpacing(2)
        self.messages_layout.addStretch()   # push bubbles to bottom

        self.scroll_area.setWidget(self.messages_widget)
        lay.addWidget(self.scroll_area, 1)

        # ── Input bar ──────────────────────────
        lay.addWidget(self._make_input_bar())
        return panel

    def _make_input_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_panel']};
                border-top: 1px solid {C['border']};
            }}
        """)
        self.summary_btn = QPushButton("🧠 Summary")
        self.summary_btn.clicked.connect(self._show_summary)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)
        lay.addWidget(self.summary_btn)

        # Emoji button
        emoji_btn = QPushButton("😊")
        emoji_btn.setFixedSize(44, 44)
        emoji_btn.setFont(QFont("Segoe UI", 16))
        emoji_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 22px;
            }}
            QPushButton:hover {{ background: {C['recv']}; }}
        """)
        emoji_btn.clicked.connect(self._insert_emoji)

        # Message input
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type a message…  (Enter to send)")
        self.msg_input.setFixedHeight(44)
        self.msg_input.setFont(QFont("Segoe UI", 12))
        self.msg_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C['bg_card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 22px;
                padding: 0 18px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C['purple_hi']};
            }}
        """)
        self.msg_input.returnPressed.connect(self._send_message)
        self.msg_input.textChanged.connect(self._on_typing)

        # Send button
        self.send_btn = QPushButton("Send ➤")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.send_btn.setStyleSheet(SEND_STYLE)
        self.send_btn.setGraphicsEffect(shadow(20, C["purple_btn"], 160))
        self.send_btn.clicked.connect(self._send_message)

        lay.addWidget(emoji_btn)
        lay.addWidget(self.msg_input, 1)
        lay.addWidget(self.send_btn)
        return bar

    # ── Kafka lifecycle ────────────────────────
    def _start_kafka(self):
        self.status_pill.set_state("waiting")

        # Producer
        ok = self._producer.connect()
        if not ok:
            self.status_pill.set_state("error")

        # Worker (consumer in QThread)
        self._worker = KafkaWorker(self._current_room)
        self._worker.message_received.connect(self._on_message_received)
        self._worker.connection_status.connect(self._on_connection_status)
        self._worker.start()

    def _stop_kafka(self):
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
        self._producer.close()

    # ── Slots / signal handlers ────────────────
    @pyqtSlot(dict)
    def _on_message_received(self, data: dict):
        """Called in the main thread via queued connection."""
        uname = data.get("username", "Unknown")
        msg   = data.get("message", "")
        ts    = data.get("timestamp", time.time())
        is_self = (uname == self._username)

        # Show typing indicator briefly for others
        if not is_self:
            self.typing_lbl.setText(f"{uname} sent a message")
            QTimer.singleShot(2000, lambda: self.typing_lbl.setText(""))

        room = data.get("room")
        if room == self._current_room:
            self._add_bubble(uname, msg, ts, is_self)
        self._print_analytics()

    @pyqtSlot(str)
    def _on_connection_status(self, status: str):
        self.status_pill.set_state(status)
        if status == "error":
            self._add_system_msg("⚠️  Could not connect to Kafka. Is the broker running?")
        elif status == "connected":
            self._add_system_msg(f"✅  Connected to Kafka · Room: #{self._current_room}")
        elif status == "disconnected":
            self._add_system_msg("🔌  Disconnected from Kafka.")

    def _on_username_changed(self, text: str):
        self._username = text.strip() or "Guest"
        with open("user.txt", "w") as f:
            f.write(self._username)

    def _on_room_changed(self, idx: int):
        room = CHAT_ROOMS[idx]
        self._current_room = room
        self.room_name_lbl.setText(f"# {room}")
        # switch Kafka topic
        if self._worker:
            self._worker.switch_topic(room)
            
        # clear UI
        for i in reversed(range(self.messages_layout.count() - 1)):
            widget = self.messages_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 🔥 Load from MongoDB
        messages = load_messages(room)
        for msg in messages:
            uname = msg["username"]
            text = msg["message"]
            ts = msg["timestamp"]
            is_self = (uname == self._username)
            self._add_bubble(uname, text, ts, is_self)
                
            
        self._add_system_msg(f"📌  Switched to room: #{room}")
        self._print_analytics()

    def _on_typing(self, text: str):
        # (typing indicator for *self* would need extra Kafka msg – skipped for clarity)
        pass

    def _send_message(self):
        msg = self.msg_input.text().strip()
        if not msg:
            return

        uname = self._username
        ok = self._producer.send_message(self._current_room, uname, msg)

        if not ok:
            self._add_system_msg("❌  Failed to send (Kafka unreachable).")
            return

        self.msg_input.clear()
        self.msg_input.setFocus()

    def _insert_emoji(self):
        """Cycle through a few quick emojis."""
        emojis = ["😊", "👍", "🔥", "💜", "🎉", "🤔", "😂", "❤️"]
        import random
        self.msg_input.insert(random.choice(emojis))
        self.msg_input.setFocus()

    # ── UI helpers ─────────────────────────────
    def _add_bubble(self, username, message, ts, is_self):
        bubble = MessageBubble(username, message, ts, is_self)
        # Insert before the trailing stretch (last item)
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, bubble)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _add_system_msg(self, text: str):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"""
            color: {C['text_dim']};
            background: transparent;
            padding: 6px 0;
        """)
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, lbl)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _stop_typing_indicator(self):
        self._other_typing = False
        self.typing_lbl.setText("")

    # ── Window close ──────────────────────────
    def closeEvent(self, event):
        self._stop_kafka()
        event.accept()
