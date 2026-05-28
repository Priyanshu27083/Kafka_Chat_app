from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt


class LoginWindow(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(300, 200)

        self.on_login = on_login

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Enter Username")
        title.setAlignment(Qt.AlignCenter)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Username")

        btn = QPushButton("Enter Chat")
        btn.clicked.connect(self.handle_login)

        layout.addWidget(title)
        layout.addWidget(self.input)
        layout.addWidget(btn)

    def handle_login(self):
        username = self.input.text().strip()
        if username:
            self.on_login(username)
            self.close()