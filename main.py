#!/usr/bin/env python3
# ─────────────────────────────────────────────
#  main.py  –  Application entry point
# ─────────────────────────────────────────────
import sys
from PyQt5.QtWidgets import QApplication
from app.gui import ChatWindow
from app.login import LoginWindow


def start_chat(username):
    global chat_window
    chat_window = ChatWindow(username)
    chat_window.show()


app = QApplication(sys.argv)

login = LoginWindow(start_chat)
login.show()

sys.exit(app.exec_())
