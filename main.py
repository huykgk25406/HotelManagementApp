from PyQt6 import QtWidgets

from gui_Ext import HotelApp


def main():
    app = QtWidgets.QApplication([])
    window = HotelApp()
    window.show()
    auto_login(window)
    app.exec()


def auto_login(window):
    window.db.load_all()
    last = window.db.data.get("last_login", {})
    email = last.get("email", "")
    password = last.get("password", "")
    if not email or not password:
        return
    window.ui.leSignInEmail.setText(email)
    window.ui.leSignInPassword.setText(password)


if __name__ == "__main__":
    main()