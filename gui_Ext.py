import re
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from PyQt6 import QtWidgets, QtCore

from gui import (Ui_MainWindow, Ui_PassEmail, Ui_PassMoi,
                 Ui_ThemKhach, Ui_ThemNV, Ui_ThemNgay,
                 Ui_GiaCa, Ui_LichSu, Ui_CheckIn)


def _now():
    return datetime.now().isoformat()


# status constants

class Role:
    MANAGER = "Lễ tân"
    RECEPTIONIST = "Lễ tân"

class RoomStatus:
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"

class BookingStatus:
    RESERVED = "reserved"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"

class PaymentStatus:
    UNPAID = "unpaid"
    PAID = "paid"

class ShiftStatus:
    ASSIGNED = "assigned"
    HANDED_OVER = "handed_over"
    CLOSED = "closed"

# dataclasses

@dataclass
class Room:
    id: int
    room_number: str
    room_type: str
    view_type: str
    price_per_day: float
    status: str = RoomStatus.AVAILABLE

@dataclass
class Customer:
    id: int
    full_name: str
    phone: str
    email: str
    national_id: str

@dataclass
class Booking:
    id: int
    customer_id: int
    room_id: int
    check_in_day: str
    check_out_day: str
    status: str = BookingStatus.RESERVED
    extend_count: int = 0

@dataclass
class Stay:
    id: int
    booking_id: int
    room_id: int
    checked_in_at: str = None
    checked_out_at: str = None
    active: bool = True

    def __post_init__(self):
        if self.checked_in_at is None:
            self.checked_in_at = _now()

@dataclass
class ServiceItem:
    id: int
    name: str
    price_per_unit: float
    category: str

@dataclass
class ServiceUsage:
    id: int
    stay_id: int
    service_item_id: int
    quantity: int
    note: str
    created_at: str | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = _now()

@dataclass
class Statement:
    id: int
    stay_id: int
    room_amount: int
    service_amount: int
    total_amount: int
    status: str = PaymentStatus.UNPAID
    created_at: str = None
    paid_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = _now()

@dataclass
class Staff(Customer):
    position: str = Role.MANAGER
    active: bool = True

@dataclass
class UserAccount:
    id: int
    username: str
    email: str
    password: str
    role: str
    active: bool = True

@dataclass
class ShiftRecord:
    id: int
    staff_id: int
    weekday: int
    shift_slot: str
    status: str = ShiftStatus.ASSIGNED
    note: str = ""
    closed_at: str = None


# data layer

class Data:
    def __init__(self, file_path="hotel_data.json"):
        self.file_path = file_path
        self._default_data()
        self.load_all()

    def _default_data(self):
        self.data = {
            "users": [], "rooms": [], "customers": [], "bookings": [],
            "stays": [], "service_items": [], "service_usages": [],
            "statements": [], "staffs": [], "shifts": [],
            "settings": {"room_types": [], "booking_sources": [], "shift_slots": []},
            "counters": {
                "users": 1, "rooms": 1, "customers": 1, "bookings": 1,
                "stays": 1, "service_items": 1, "service_usages": 1,
                "statements": 1, "staffs": 1, "shifts": 1,
            },
        }

    def next_id(self, table):
        val = self.data["counters"][table]
        self.data["counters"][table] += 1
        return val

    def load_all(self):
        if not os.path.exists(self.file_path):
            self.save_all()
            return
        with open(self.file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            self.data = loaded

    def save_all(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


# services

class AuthService:
    def __init__(self, data):
        self.data = data

    def register(self, username, email, password, role=Role.RECEPTIONIST):
        for u in self.data.data["users"]:
            if u["email"].lower() == email.lower():
                raise ValueError("Email đã tồn tại")
        user = UserAccount(self.data.next_id("users"), username, email, password, role)
        self.data.data["users"].append(user.__dict__)
        self.data.save_all()
        return user

    def login(self, email, password):
        for u in self.data.data["users"]:
            if u["email"].lower() == email.lower() and u["password"] == password:
                if not u.get("active", True):
                    raise ValueError("Tài khoản đã bị vô hiệu hoá")
                return u
        raise ValueError("Email hoặc mật khẩu không đúng")

    def request_password_reset(self, email):
        return any(u["email"].lower() == email.lower() for u in self.data.data["users"])

    def reset_password(self, email, new_password):
        for u in self.data.data["users"]:
            if u["email"].lower() == email.lower():
                u["password"] = new_password
                self.data.save_all()
                return True
        return False


class RoomService:
    def __init__(self, data):
        self.data = data

    def create_room(self, room_number, room_type, view_type, price_per_day):
        for r in self.data.data["rooms"]:
            if r["room_number"] == room_number:
                raise ValueError("Số phòng đã tồn tại")
        room = Room(self.data.next_id("rooms"), room_number, room_type, view_type, price_per_day)
        self.data.data["rooms"].append(room.__dict__)
        self.data.save_all()
        return room

    def list_rooms(self, room_type=None, status=None, keyword=""):
        rooms = self.data.data["rooms"]
        if room_type:
            rooms = [r for r in rooms if r["room_type"].lower() == room_type.lower()]
        if status:
            rooms = [r for r in rooms if r["status"] == status]
        if keyword:
            rooms = [r for r in rooms if keyword.lower() in r["room_number"].lower()]
        return rooms

    def get_room(self, room_id):
        for r in self.data.data["rooms"]:
            if r["id"] == room_id:
                return r
        raise ValueError("Không tìm thấy phòng")


class CustomerService:
    def __init__(self, data):
        self.data = data

    def add_customer(self, full_name, phone, email, national_id):
        c = Customer(self.data.next_id("customers"), full_name, phone, email, national_id)
        self.data.data["customers"].append(c.__dict__)
        self.data.save_all()
        return c

    def search_customer(self, keyword=""):
        key = keyword.lower()
        if not key:
            return self.data.data["customers"]
        return [c for c in self.data.data["customers"]
                if key in c["full_name"].lower() or key in c["phone"].lower()
                or key in c["email"].lower() or key in c["national_id"].lower()]

    def get_customer(self, customer_id):
        for c in self.data.data["customers"]:
            if c["id"] == customer_id:
                return c
        raise ValueError("Không tìm thấy khách hàng")


class BookingService:
    def __init__(self, data, room_service, customer_service):
        self.data = data
        self.rooms = room_service
        self.customers = customer_service

    def create_booking(self, customer_id, room_id, check_in_day, check_out_day):
        self.customers.get_customer(customer_id)
        room = self.rooms.get_room(room_id)
        if room["status"] != RoomStatus.AVAILABLE:
            raise ValueError("Phòng hiện không còn trống")
        b = Booking(self.data.next_id("bookings"), customer_id, room_id,
                    check_in_day, check_out_day)
        self.data.data["bookings"].append(b.__dict__)
        self.data.save_all()
        return b

    def get_booking(self, booking_id):
        for b in self.data.data["bookings"]:
            if b["id"] == booking_id:
                return b
        raise ValueError("Không tìm thấy đặt phòng")

    def list_bookings(self):
        return self.data.data["bookings"]

    def extend_booking(self, booking_id, extra_days):
        b = self.get_booking(booking_id)
        old_out = date.fromisoformat(b["check_out_day"])
        b["check_out_day"] = (old_out + timedelta(days=extra_days)).isoformat()
        b["extend_count"] = b.get("extend_count", 0) + 1
        self.data.save_all()
        return b

    def room_history(self, room_id):
        return [b for b in self.data.data["bookings"] if b["room_id"] == room_id]


class StayService:
    def __init__(self, data, booking_service, room_service):
        self.data = data
        self.bookings = booking_service
        self.rooms = room_service

    def check_in(self, booking_id):
        b = self.bookings.get_booking(booking_id)
        if b["status"] != BookingStatus.RESERVED:
            raise ValueError("Đặt phòng chưa ở trạng thái chờ nhận")
        room = self.rooms.get_room(b["room_id"])
        if room["status"] != RoomStatus.AVAILABLE:
            raise ValueError("Phòng hiện không còn trống")
        stay = Stay(self.data.next_id("stays"), booking_id, b["room_id"], _now(), None, True)
        self.data.data["stays"].append(stay.__dict__)
        b["status"] = BookingStatus.CHECKED_IN
        room["status"] = RoomStatus.OCCUPIED
        self.data.save_all()
        return stay

    def check_out(self, stay_id):
        stay = self.get_stay(stay_id)
        if not stay.get("active", True):
            raise ValueError("Khách đã trả phòng trước đó")
        stay["active"] = False
        stay["checked_out_at"] = _now()
        b = self.bookings.get_booking(stay["booking_id"])
        b["status"] = BookingStatus.CHECKED_OUT
        self.rooms.get_room(stay["room_id"])["status"] = RoomStatus.AVAILABLE
        self.data.save_all()
        return stay

    def get_stay(self, stay_id):
        for s in self.data.data["stays"]:
            if s["id"] == stay_id:
                return s
        raise ValueError("Không tìm thấy lượt lưu trú")

    def list_active_stays(self):
        return [s for s in self.data.data["stays"] if s.get("active", True)]



class ServiceUsageService:
    def __init__(self, data):
        self.data = data

    def create_service_item(self, name, price_per_unit, category):
        item = ServiceItem(self.data.next_id("service_items"), name, price_per_unit, category)
        self.data.data["service_items"].append(item.__dict__)
        self.data.save_all()
        return item

    def add_service_usage(self, stay_id, service_item_id, quantity=1, note=""):
        usage = ServiceUsage(self.data.next_id("service_usages"), stay_id,
                             service_item_id, quantity, note)
        self.data.data["service_usages"].append(usage.__dict__)
        self.data.save_all()
        return usage

    def calculate_service_total(self, stay_id):
        items = {i["id"]: i for i in self.data.data["service_items"]}
        return sum(
            items[u["service_item_id"]]["price_per_unit"] * u["quantity"]
            for u in self.data.data["service_usages"]
            if u["stay_id"] == stay_id and u["service_item_id"] in items
        )


class PaymentService:
    def __init__(self, data, booking_service, service_usage_service, room_service):
        self.data = data
        self.bookings = booking_service
        self.services = service_usage_service
        self.rooms = room_service

    def generate_statement(self, stay_id):
        stay = next((s for s in self.data.data["stays"] if s["id"] == stay_id), None)
        if not stay:
            raise ValueError("Không tìm thấy lượt lưu trú")
        # remove any existing unpaid statement for this stay to avoid duplicates
        self.data.data["statements"] = [
            s for s in self.data.data["statements"]
            if not (s.get("stay_id") == stay_id and s.get("status") == "unpaid")
        ]
        b = self.bookings.get_booking(stay["booking_id"])
        room = self.rooms.get_room(b["room_id"])
        try:
            nights = max(1, (date.fromisoformat(b["check_out_day"]) -
                             date.fromisoformat(b["check_in_day"])).days)
        except Exception:
            nights = 1
        room_amount = nights * room["price_per_day"]
        service_amount = self.services.calculate_service_total(stay_id)
        st = Statement(self.data.next_id("statements"), stay_id,
                       room_amount, service_amount, room_amount + service_amount)
        self.data.data["statements"].append(st.__dict__)
        self.data.save_all()
        return st

    def mark_paid(self, statement_id):
        for s in self.data.data["statements"]:
            if s["id"] == statement_id:
                s["status"] = PaymentStatus.PAID
                s["paid_at"] = _now()
                self.data.save_all()
                return s
        raise ValueError("Không tìm thấy hoá đơn")


class StaffService:
    def __init__(self, data):
        self.data = data

    def add_staff(self, full_name, phone, email, national_id, position="Lễ tân"):
        s = Staff(self.data.next_id("staffs"), full_name, phone, email, national_id, position)
        self.data.data["staffs"].append(s.__dict__)
        self.data.save_all()
        return s

    def list_staff(self):
        return self.data.data["staffs"]

    def assign_shift(self, staff_id, weekday, shift_slot):
        shift = ShiftRecord(self.data.next_id("shifts"), staff_id, weekday, shift_slot)
        self.data.data["shifts"].append(shift.__dict__)
        self.data.save_all()
        return shift

    def handover_shift(self, shift_id, note=""):
        for s in self.data.data["shifts"]:
            if s["id"] == shift_id:
                s["status"] = ShiftStatus.HANDED_OVER
                s["note"] = note
                self.data.save_all()
                return s
        raise ValueError("Không tìm thấy ca làm việc")

    def close_shift(self, shift_id):
        for s in self.data.data["shifts"]:
            if s["id"] == shift_id:
                s["status"] = ShiftStatus.CLOSED
                s["closed_at"] = _now()
                self.data.save_all()
                return s
        raise ValueError("Không tìm thấy ca làm việc")

    def weekly_schedule(self):
        schedule = {}
        for s in self.data.data["shifts"]:
            schedule.setdefault(s["weekday"], []).append(s)
        return schedule

# main window

class HotelApp(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # data layer
        self.db = Data()
        self.auth = AuthService(self.db)
        self.rooms = RoomService(self.db)
        self.customers = CustomerService(self.db)
        self.bookings = BookingService(self.db, self.rooms, self.customers)
        self.stays = StayService(self.db, self.bookings, self.rooms)
        self.services = ServiceUsageService(self.db)
        self.payments = PaymentService(self.db, self.bookings, self.services, self.rooms)
        self.staff = StaffService(self.db)

        self.customers_cache = []
        self.dynamic_checkout_rows = {}

        self.setup_connections()
        self.on_startup()

    def setup_connections(self):
        ui = self.ui

        # auth
        ui.btnSignIn.clicked.connect(self.handle_sign_in)
        ui.btnSignUp.clicked.connect(self.handle_sign_up)
        ui.lblSignInGoSignUp.mousePressEvent = lambda e: self.show_page(ui.pgSignUp) # mousePressEvent always passes a QMouseEvent, must accept it even if unused
        ui.lblSignUpGoSignIn.mousePressEvent = lambda e: self.show_page(ui.pgSignIn)
        ui.lblSignInForgotPassword.mousePressEvent = lambda e: self.forgot_password_dialog()

        # nav
        ui.btnNavRoom.clicked.connect( lambda: self.show_page(ui.pgRoom))
        ui.btnNavBooking.clicked.connect( lambda: self.show_page(ui.pgBooking))
        ui.btnNavCustomer.clicked.connect( lambda: self.show_page(ui.pgCustomer))
        ui.btnNavCheckInOut.clicked.connect(lambda: self.show_page(ui.pgCheckInOut))
        ui.btnNavPayment.clicked.connect( lambda: self.show_page(ui.pgPayment))
        ui.btnNavEmployee.clicked.connect( lambda: self.show_page(ui.pgEmployee))
        ui.btnNavService.clicked.connect(
            lambda: (self.show_page(ui.pgService), self.load_service_rooms()))
        ui.btnNavLogout.clicked.connect(self.handle_logout)

        # rooms
        ui.leRoomSearch.returnPressed.connect(self.load_rooms)
        ui.scrollRoomListContents.mouseDoubleClickEvent = lambda e: self.on_room_double_click(e)
        ui.cbRoomType.currentIndexChanged.connect(lambda _: self.load_rooms()) # currentIndexChanged always passes the new index, must accept it even if unused
        ui.cbRoomStatus.currentIndexChanged.connect(lambda _: self.load_rooms())

        # customers
        ui.leCustomerSearch.returnPressed.connect(self.load_customers)
        ui.tbtnCustomerSearch.clicked.connect(self.load_customers)
        ui.tbtnCustomerAdd.clicked.connect(self.add_customer_dialog)

        # booking extend wired dynamically in load_bookings via cloning

        # check-out row 1 wired here, rest cloned dynamically in load_checkinout
        for i in range(1, 3):
            btn = getattr(ui, f"btnCheckOutRow{i}", None)
            if btn:
                btn.clicked.connect(lambda checked, idx=i: self.do_checkout(idx))

        # payments
        for i in range(1, 5):
            btn = getattr(ui, f"btnPaymentDownloadRow{i}", None)
            if btn:
                btn.clicked.connect(lambda checked, idx=i: self.mark_payment_paid(idx))

        # service
        ui.cbServiceSelectRoom.currentIndexChanged.connect(self.on_service_room_changed)
        for i in range(1, 9):
            btn = getattr(ui, f"btnServiceRow{i}Add", None)
            if btn:
                btn.clicked.connect(lambda checked, idx=i: self.add_service_item(idx))
        ui.btnServiceConfirm.clicked.connect(self.delete_last_service)

        # employee
        ui.btnEmployeeAdd.clicked.connect(self.add_employee_dialog)
        for i in range(1, 10):
            btn_assign = getattr(ui, f"btnEmployeeRow{i}Assign", None)
            if btn_assign:
                btn_assign.clicked.connect(lambda checked, idx=i: self.assign_shift_dialog(idx))
            btn_delete = getattr(ui, f"btnEmployeeRow{i}Delete", None)
            if btn_delete:
                btn_delete.clicked.connect(lambda checked, idx=i: self.delete_employee(idx))
        ui.btnEmployeeRowDelete.clicked.connect(self.delete_selected_shift)

    def on_startup(self):
        self.show_page(self.ui.pgSignIn)
        self.set_nav_enabled(False)
        self.set_user_info_visible(False)
        self.ui.textEdit.setText("")
        self.set_text("leServiceRoom", "")
        self.update_service_totals(0.0)
        self.ui.btnCheckOutRow1.setVisible(False)
        # center align all booking row1 template fields
        for w in (self.ui.leBookingRow1Id, self.ui.leBookingRow1Name,
                  self.ui.leBookingRow1Room, self.ui.leBookingRow1CheckIn,
                  self.ui.leBookingRow1CheckOut):
            w.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.ui.lblCheckInOutRow1Room.setText("")
        self.ui.lblCheckInOutRow1Status.setText("")
        self.ui.leCheckInOutRow1Time.setText("")
        for name in ("btnCustomerViewRow1", "btnCustomerViewRow2"):
            w = self.get_widget(name)
            if w:
                w.setVisible(False)

        self.reload_all()

    # utility

    def show_page(self, page):
        self.ui.stkMain.setCurrentWidget(page)

    def show_info(self, title, msg):
        QtWidgets.QMessageBox.information(self, title, msg)

    def show_error(self, title, msg):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def confirm(self, message):
        return QtWidgets.QMessageBox.question(
            self, "Xác nhận", message,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        ) == QtWidgets.QMessageBox.StandardButton.Yes

    def get_widget(self, name):
        return getattr(self.ui, name, None)

    def set_text(self, name, value):
        w = self.get_widget(name)
        if w:
            w.setText(str(value))

    def fmt_time(self, dt_str):
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str).strftime("%H:%M")
        except Exception:
            return dt_str

    def fmt_datetime(self, dt_str):
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return dt_str

    def set_nav_enabled(self, enabled):
        for btn in [self.ui.btnNavRoom, self.ui.btnNavBooking, self.ui.btnNavCustomer,
                    self.ui.btnNavCheckInOut, self.ui.btnNavPayment, self.ui.btnNavService,
                    self.ui.btnNavEmployee, self.ui.btnNavSettings, self.ui.btnNavLogout]:
            btn.setEnabled(enabled)
        self.ui.btnNavLogout.setVisible(enabled)

    def set_user_info_visible(self, visible):
        for name in ("lblAppLogo", "lblNavUsername", "lblNavEmail"):
            w = self.get_widget(name)
            if w:
                w.setVisible(visible)

    def reload_all(self):
        self.load_rooms()
        self.load_bookings()
        self.load_customers()
        self.load_checkinout()
        self.load_payments()
        self.load_staff()
        self.load_schedule()
        self.load_service_rooms()

    # auth

    def handle_sign_in(self):
        email = self.ui.leSignInEmail.text().strip()
        password = self.ui.leSignInPassword.text().strip()
        if not email or not password:
            return self.show_error("Thiếu thông tin", "Vui lòng nhập email và mật khẩu.")
        try:
            user = self.auth.login(email, password)
        except ValueError as e:
            return self.show_error("Đăng nhập thất bại", str(e))
        self.db.data["last_login"] = {"email": email, "password": password}
        self.db.save_all()
        self.set_text("lblNavUsername", user.get("role", ""))
        email = user.get("email", "")
        self.set_text("lblNavEmail", email.replace("@", "\n@") if "@" in email else email)
        self.set_text("lblAppLogo", user.get("username", "?")[0].upper())
        self.set_user_info_visible(True)
        self.set_nav_enabled(True)
        self.show_page(self.ui.pgRoom)
        self.reload_all()

    def handle_sign_up(self):
        username = self.ui.leSignUpUsername.text().strip()
        email = self.ui.leSignUpEmail.text().strip()
        password = self.ui.leSignUpPassword.text().strip()
        confirm = self.ui.leSignUpConfirmPassword.text().strip()
        if not all([username, email, password, confirm]):
            return self.show_error("Thiếu thông tin", "Vui lòng nhập đầy đủ thông tin.")
        if not any(c.isalpha() for c in username):
            return self.show_error("Tên đăng nhập", "Tên đăng nhập phải chứa chữ cái.")
        parts = email.split("@")
        if (len(parts) != 2 or not parts[0] or not parts[1]
                or ".." in email or parts[1].startswith(".")
                or "." not in parts[1] or parts[1].endswith(".")):
            return self.show_error("Email", "Email không hợp lệ.")
        if len(password) < 6:
            return self.show_error("Mật khẩu", "Mật khẩu phải có ít nhất 6 ký tự.")
        if password != confirm:
            return self.show_error("Mật khẩu", "Mật khẩu xác nhận không khớp.")
        if not self.confirm(f"Đăng ký tài khoản với email '{email}'?"):
            return
        try:
            self.auth.register(username, email, password)
        except ValueError as e:
            return self.show_error("Đăng ký thất bại", str(e))
        self.show_info("Thành công", "Đăng ký thành công. Bạn có thể đăng nhập.")
        self.show_page(self.ui.pgSignIn)

    def handle_logout(self):
        if not self.confirm("Bạn có chắc muốn đăng xuất?"):
            return
        self.set_nav_enabled(False)
        self.set_user_info_visible(False)
        self.ui.leSignInEmail.clear()
        self.ui.leSignInPassword.clear()
        self.show_page(self.ui.pgSignIn)

    def forgot_password_dialog(self):
        dialog = QtWidgets.QDialog(self)
        ui = Ui_PassEmail()
        ui.setupUi(dialog)
        ui.leEmail.setPlaceholderText("Value")

        def do_reset():
            email = ui.leEmail.text().strip()
            if not email:
                return self.show_error("Thiếu thông tin", "Vui lòng nhập email.")
            if not self.auth.request_password_reset(email):
                return self.show_error("Không tìm thấy", "Email không tồn tại.")
            dialog.accept()
            self.new_password_dialog(email)

        ui.btnConfirm.clicked.connect(do_reset)
        ui.btnCancel.clicked.connect(dialog.reject)
        dialog.exec()

    def new_password_dialog(self, email):
        dialog = QtWidgets.QDialog(self)
        ui = Ui_PassMoi()
        ui.setupUi(dialog)

        def confirm():
            new_pw = ui.leNewPassword.text().strip()
            confirm_pw = ui.leConfirmPassword.text().strip()
            if not new_pw:
                return self.show_error("Thiếu thông tin", "Vui lòng nhập mật khẩu mới.")
            if new_pw != confirm_pw:
                return self.show_error("Mật khẩu", "Mật khẩu xác nhận không khớp.")
            self.auth.reset_password(email, new_pw)
            self.show_info("Thành công", "Đã đặt lại mật khẩu.")
            dialog.accept()

        ui.btnConfirm.clicked.connect(confirm)
        dialog.exec()

    # rooms

    def load_rooms(self):
        self.db.load_all()
        keyword = self.ui.leRoomSearch.text().strip()
        type_text = self.ui.cbRoomType.currentText()
        status_text = self.ui.cbRoomStatus.currentText()
        status_map = {
            "Còn phòng": RoomStatus.AVAILABLE,
            "Hết phòng": RoomStatus.OCCUPIED,
        }
        rooms = self.rooms.list_rooms(
            None if type_text in ("Loại phòng", "") else type_text,
            status_map.get(status_text),
            keyword,
        )

        layout = self.ui.vboxRoomList
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if not rooms:
            self.ui.frmRoomRow1.setVisible(False)
            layout.addStretch()
            return

        self.ui.frmRoomRow1.setMaximumHeight(50)
        self.ui.frmRoomRow1.setVisible(True)
        self.fill_room_widgets(
            self.ui.lblRoomRow1Number, self.ui.lblRoomRow1View,
            self.ui.lblRoomRow1Price, self.ui.lblRoomRow1Type,
            self.ui.leRoomRow1Status, rooms[0]
        )
        for room in rooms[1:]:
            self.clone_room_row(room)
        layout.addStretch()

    def clone_room_row(self, room):
        tmpl = self.ui.frmRoomRow1
        frm = QtWidgets.QFrame(self.ui.scrollRoomListContents)
        frm.setMinimumSize(tmpl.minimumSize())
        frm.setMaximumHeight(50)
        frm.setStyleSheet(tmpl.styleSheet())
        frm.setFrameShape(tmpl.frameShape())
        frm.setFrameShadow(tmpl.frameShadow())
        def lbl(src):
            w = QtWidgets.QLabel(frm)
            w.setGeometry(src.geometry())
            w.setStyleSheet(src.styleSheet())
            return w
        lbl_number = lbl(self.ui.lblRoomRow1Number)
        lbl_view = lbl(self.ui.lblRoomRow1View)
        lbl_price = lbl(self.ui.lblRoomRow1Price)
        lbl_type = lbl(self.ui.lblRoomRow1Type)
        lbl_type.setMinimumWidth(60)
        le_status = QtWidgets.QLineEdit(frm)
        le_status.setGeometry(self.ui.leRoomRow1Status.geometry())
        le_status.setStyleSheet(self.ui.leRoomRow1Status.styleSheet())
        le_status.setReadOnly(True)
        self.ui.vboxRoomList.addWidget(frm)
        self.fill_room_widgets(lbl_number, lbl_view, lbl_price, lbl_type, le_status, room)

    def fill_room_widgets(self, lbl_number, lbl_view, lbl_price, lbl_type, le_status, room):
        lbl_number.setText(f"Phòng {room['room_number']}")
        lbl_view.setText(f"View {room.get('view_type', '')}")
        lbl_price.setText(f"${int(room.get('price_per_day', 0))} / ngày")
        lbl_type.setText(room.get("room_type", ""))
        lbl_type.setMinimumWidth(60)
        le_status.setText({
            RoomStatus.AVAILABLE: "Còn phòng",
            RoomStatus.OCCUPIED: "Hết phòng",
        }.get(room.get("status", ""), room.get("status", "")))

    def on_room_double_click(self, event):
        # find which room row was clicked by y position
        y = event.pos().y()
        layout = self.ui.vboxRoomList
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item or not item.widget():
                continue
            frm = item.widget()
            if frm.y() <= y <= frm.y() + frm.height():
                # find number label in this frame
                for child in frm.children():
                    if isinstance(child, QtWidgets.QLabel) and child.text().startswith("Phòng"):
                        room_number = child.text().replace("Phòng ", "").strip()
                        room = next((r for r in self.db.data["rooms"]
                                     if r["room_number"] == room_number), None)
                        if room:
                            self.checkin_dialog(room)
                        return

    def validate_customer_fields(self, name, phone, email, nid):
        if not any(c.isalpha() for c in name):
            return "Họ tên phải chứa chữ cái."
        p = phone.strip()
        if p.startswith("+"):
            p = p[1:]
        if p.startswith("-") or p.startswith(" "):
            return "Số điện thoại không hợp lệ."
        if not p.replace("-", "").isdigit():
            return "Số điện thoại không hợp lệ."
        phone_digits = p.replace("-", "")
        if not (7 <= len(phone_digits) <= 15):
            return "Số điện thoại không hợp lệ."
        parts = email.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1] or ".." in email or parts[1].startswith(".") or "." not in parts[1] or parts[1].endswith("."):
            return "Email không hợp lệ."
        if not nid.isalnum() or not (9 <= len(nid) <= 12):
            return "Số ID/CCCD không hợp lệ (9-12 ký tự, chỉ chữ và số)."
        return None

    def checkin_dialog(self, room):
        self.db.load_all()
        if room.get("status") != RoomStatus.AVAILABLE:
            return self.show_error("Nhận phòng", f"Phòng {room['room_number']} hiện không trống.")
        dialog = QtWidgets.QDialog(self)
        ui = Ui_CheckIn()
        ui.setupUi(dialog)
        ui.lblRoomInfo.setText(f"Phòng {room['room_number']} · {room.get('room_type','')} · ${int(room.get('price_per_day', 0))}/ngày")

        def submit():
            name = ui.leFullName.text().strip()
            phone = ui.lePhone.text().strip()
            email = ui.leEmail.text().strip()
            nid = ui.leNationalId.text().strip()
            checkout = ui.leCheckOut.text().strip()
            if not all([name, phone, email, nid, checkout]):
                return self.show_error("Thiếu thông tin", "Vui lòng nhập đầy đủ thông tin.")
            err = self.validate_customer_fields(name, phone, email, nid)
            if err:
                return self.show_error("Lỗi", err)
            try:
                checkout_date = datetime.fromisoformat(checkout).date()
            except ValueError:
                return self.show_error("Lỗi", "Ngày trả phòng không hợp lệ. Dùng định dạng YYYY-MM-DD.")
            if checkout_date <= date.today():
                return self.show_error("Lỗi", "Ngày trả phòng phải sau ngày hôm nay.")
            if not self.confirm(f"Nhận phòng cho khách '{name}' vào phòng {room['room_number']}?"):
                return
            try:
                existing = next((c for c in self.db.data["customers"] if c["national_id"] == nid), None)
                if existing:
                    class _C: pass
                    customer = _C()
                    customer.id = existing["id"]
                else:
                    customer = self.customers.add_customer(name, phone, email, nid)
                today = _now()[:10] # YYYY-MM-DD from _now()
                booking = self.bookings.create_booking(customer.id, room["id"], today, checkout)
                self.stays.check_in(booking.id)
                self.reload_all()
                self.show_info("Nhận phòng", f"Đã nhận phòng cho khách '{name}' vào phòng {room['room_number']}.")
                dialog.accept()
            except ValueError as e:
                self.show_error("Lỗi", str(e))

        ui.btnConfirm.clicked.connect(submit)
        ui.btnCancel.clicked.connect(dialog.reject)
        dialog.exec()

    # bookings

    def load_bookings(self):
        self.db.load_all()
        bookings = self.db.data["bookings"]

        layout = self.ui.vboxBookingList
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if not bookings:
            self.ui.frmBookingRow1.setVisible(False)
            return

        self.ui.frmBookingRow1.setMaximumHeight(40)
        self.ui.frmBookingRow1.setVisible(True)
        self.fill_booking_widgets(
            self.ui.leBookingRow1Id, self.ui.leBookingRow1Name,
            self.ui.leBookingRow1Room, self.ui.leBookingRow1CheckIn,
            self.ui.leBookingRow1CheckOut, self.ui.btnBookingRow1Extend,
            bookings[0], 1
        )
        for i, booking in enumerate(bookings[1:], start=2):
            row = self.clone_booking_row(i)
            self.fill_booking_widgets(*row, booking, i)
        self.ui.vboxBookingList.addStretch()

    def clone_booking_row(self, booking_idx):
        tmpl = self.ui.frmBookingRow1
        frm = QtWidgets.QFrame(self.ui.scrollBookingListContents)
        frm.setMinimumSize(tmpl.minimumSize())
        frm.setMaximumHeight(40)
        frm.setStyleSheet(tmpl.styleSheet())
        frm.setFrameShape(tmpl.frameShape())
        frm.setFrameShadow(tmpl.frameShadow())
        def le(src):
            w = QtWidgets.QLineEdit(frm)
            w.setGeometry(src.geometry())
            w.setStyleSheet(src.styleSheet())
            w.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            w.setReadOnly(True)
            return w
        le_id = le(self.ui.leBookingRow1Id)
        le_name = le(self.ui.leBookingRow1Name)
        le_room = le(self.ui.leBookingRow1Room)
        le_checkin = le(self.ui.leBookingRow1CheckIn)
        le_checkout= le(self.ui.leBookingRow1CheckOut)
        btn = QtWidgets.QPushButton(frm)
        btn.setGeometry(self.ui.btnBookingRow1Extend.geometry())
        btn.setStyleSheet(self.ui.btnBookingRow1Extend.styleSheet())
        btn.setText(self.ui.btnBookingRow1Extend.text())
        self.ui.vboxBookingList.addWidget(frm)
        return le_id, le_name, le_room, le_checkin, le_checkout, btn

    def fill_booking_widgets(self, le_id, le_name, le_room, le_checkin, le_checkout, btn, booking, idx):
        try:
            customer = self.customers.get_customer(booking["customer_id"])
            room = self.rooms.get_room(booking["room_id"])
        except ValueError:
            return
        le_id.setText(str(booking["id"]))
        le_name.setText(customer.get("full_name", ""))
        le_room.setText(room.get("room_number", ""))
        le_checkin.setText(booking.get("check_in_day", ""))
        le_checkout.setText(booking.get("check_out_day", ""))
        for w in (le_id, le_name, le_room, le_checkin, le_checkout):
            w.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            
        # wire extend button (template or cloned)
        try: btn.clicked.disconnect()
        except: pass
        btn.clicked.connect(lambda checked, bid=booking["id"]: self.extend_booking(bid))

    def extend_booking(self, booking_id):
        self.db.load_all()
        booking = next((b for b in self.db.data["bookings"] if b["id"] == booking_id), None)
        if not booking:
            return

        dialog = QtWidgets.QDialog(self)
        ui = Ui_ThemNgay()
        ui.setupUi(dialog)

        def submit():
            try:
                days = int(ui.leDays.text().strip())
            except ValueError:
                return self.show_error("Lỗi", "Vui lòng nhập số ngày hợp lệ.")
            if days <= 0:
                return self.show_error("Lỗi", "Số ngày gia hạn phải lớn hơn 0.")
            if not self.confirm(f"Gia hạn đặt phòng #{booking['id']} thêm {days} ngày?"):
                return
            try:
                self.bookings.extend_booking(booking["id"], days)
                self.load_bookings()
                dialog.accept()
            except ValueError as e:
                self.show_error("Gia hạn thất bại", str(e))

        ui.btnConfirm.clicked.connect(submit)
        ui.btnCancel.clicked.connect(dialog.reject)
        dialog.exec()

    # customers

    def load_customers(self):
        self.db.load_all()
        keyword = self.ui.leCustomerSearch.text().strip()
        self.customers_cache = self.customers.search_customer(keyword)
        table = self.ui.tblCustomerList
        table.setRowCount(len(self.customers_cache))
        for r, c in enumerate(self.customers_cache):
            table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(c.get("id", ""))))
            table.setItem(r, 1, QtWidgets.QTableWidgetItem(c.get("full_name", "")))
            table.setItem(r, 2, QtWidgets.QTableWidgetItem(c.get("phone", "")))
            table.setItem(r, 3, QtWidgets.QTableWidgetItem(c.get("email", "")))
            table.setItem(r, 4, QtWidgets.QTableWidgetItem(c.get("national_id", "")))
            btn = QtWidgets.QPushButton("Xem")
            btn.setStyleSheet("QPushButton { border:none; color:#2563EB; }"
                              "QPushButton:hover { text-decoration:underline; }")
            btn.clicked.connect(lambda checked, idx=r: self.show_customer_detail(idx))
            table.setCellWidget(r, 5, btn)

    def show_customer_detail(self, idx):
        if idx >= len(self.customers_cache):
            return
        c = self.customers_cache[idx]
        bookings = [b for b in self.db.data["bookings"] if b["customer_id"] == c.get("id")]

        dialog = QtWidgets.QDialog(self)
        ui = Ui_LichSu()
        ui.setupUi(dialog)
        dialog.setWindowTitle(c.get("full_name", ""))
        ui.lblCustomerName.setText(c.get("full_name", ""))

        if bookings:
            b = bookings[-1]
            room = self.rooms.get_room(b["room_id"])
            ui.lblRoomValue.setText(room.get("room_number", ""))
            ui.lblCheckInValue.setText(b.get("check_in_day", ""))
            ui.lblTypeValue.setText(room.get("room_type", ""))
            ui.lblCheckOutValue.setText(b.get("check_out_day", ""))
            # resolve payment status from statements via the booking's stay
            stay = next((s for s in self.db.data["stays"] if s["booking_id"] == b["id"]), None)
            if stay:
                stmt = next((st for st in self.db.data["statements"] if st["stay_id"] == stay["id"]), None)
                raw_payment = stmt["status"] if stmt else PaymentStatus.UNPAID
            else:
                raw_payment = PaymentStatus.UNPAID
            payment_label = {"paid": "Đã thanh toán", "unpaid": "Chưa thanh toán"}.get(raw_payment, raw_payment)
            ui.lblPaymentValue.setText(payment_label)
            ui.lblPriceValue.setText(f"${room.get('price_per_day', 0):.2f}")

        ui.btnConfirm.clicked.connect(dialog.accept)
        dialog.exec()

    def add_customer_dialog(self):
        dialog = QtWidgets.QDialog(self)
        ui = Ui_ThemKhach()
        ui.setupUi(dialog)

        def submit():
            name = ui.leFullName.text().strip()
            phone = ui.lePhone.text().strip()
            email = ui.leEmail.text().strip()
            nid = ui.leNationalId.text().strip()
            if not all([name, phone, email, nid]):
                return self.show_error("Thiếu thông tin", "Vui lòng nhập đầy đủ thông tin.")
            err = self.validate_customer_fields(name, phone, email, nid)
            if err:
                return self.show_error("Lỗi", err)
            if not self.confirm(f"Thêm khách hàng '{name}'?"):
                return
            self.customers.add_customer(name, phone, email, nid)
            self.load_customers()
            self.show_info("Thành công", f"Đã thêm khách hàng '{name}'.")
            dialog.accept()

        ui.btnConfirm.clicked.connect(submit)
        dialog.exec()

    # check in / out

    def load_checkinout(self):
        self.db.load_all()
        stays = [s for s in self.db.data["stays"] if s.get("active")]

        layout = self.ui.vboxCheckInOutList
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.dynamic_checkout_rows = {}

        if stays:
            self.ui.frmCheckInOutRow1.setVisible(True)
            self.fill_checkinout_row(
                self.ui.lblCheckInOutRow1Room,
                self.ui.lblCheckInOutRow1Status,
                self.ui.leCheckInOutRow1Time,
                self.ui.btnCheckOutRow1,
                stays[0], 1
            )
        else:
            self.ui.frmCheckInOutRow1.setVisible(False)
            self.ui.btnCheckOutRow1.setVisible(False)

        for i, stay in enumerate(stays[1:], start=2):
            frm, lbl_room, lbl_status, le_time, btn = self.clone_checkinout_row(i)
            self.dynamic_checkout_rows[i] = (lbl_room, lbl_status, le_time, btn)
            self.fill_checkinout_row(lbl_room, lbl_status, le_time, btn, stay, i)

    def clone_checkinout_row(self, checkout_idx):
        tmpl = self.ui.frmCheckInOutRow1
        frm = QtWidgets.QFrame(self.ui.scrollCheckInOutListContents)
        frm.setMinimumSize(tmpl.minimumSize())
        frm.setMaximumSize(tmpl.maximumSize())
        frm.setStyleSheet(tmpl.styleSheet())
        frm.setFrameShape(tmpl.frameShape())
        frm.setFrameShadow(tmpl.frameShadow())
        info_w = QtWidgets.QWidget(frm)
        info_w.setGeometry(self.ui.vboxCheckInOutRow1Info.geometry())
        info_layout = QtWidgets.QVBoxLayout(info_w)
        info_layout.setContentsMargins(0, 0, 0, 0)
        lbl_room = QtWidgets.QLabel()
        lbl_room.setFont(self.ui.lblCheckInOutRow1Room.font())
        lbl_room.setAlignment(self.ui.lblCheckInOutRow1Room.alignment())
        lbl_status = QtWidgets.QLabel()
        lbl_status.setStyleSheet(self.ui.lblCheckInOutRow1Status.styleSheet())
        lbl_status.setAlignment(self.ui.lblCheckInOutRow1Status.alignment())
        info_layout.addWidget(lbl_room)
        info_layout.addWidget(lbl_status)
        le_time = QtWidgets.QLineEdit(frm)
        le_time.setGeometry(self.ui.leCheckInOutRow1Time.geometry())
        le_time.setFont(self.ui.leCheckInOutRow1Time.font())
        le_time.setStyleSheet(self.ui.leCheckInOutRow1Time.styleSheet())
        le_time.setReadOnly(True)
        btn = QtWidgets.QPushButton("Check out", frm)
        btn.setGeometry(self.ui.btnCheckOutRow1.geometry())
        btn.setFont(self.ui.btnCheckOutRow1.font())
        btn.setStyleSheet(self.ui.btnCheckOutRow1.styleSheet())
        btn.setVisible(False)
        btn.clicked.connect(lambda checked, i=checkout_idx: self.do_checkout(i))
        self.ui.vboxCheckInOutList.addWidget(frm)
        return frm, lbl_room, lbl_status, le_time, btn

    def fill_checkinout_row(self, lbl_room, lbl_status, le_time, btn, stay, checkout_idx):
        data = self.db.data
        booking = next((b for b in data["bookings"] if b["id"] == stay["booking_id"]), {})
        room = next((r for r in data["rooms"] if r["id"] == stay["room_id"]), {})
        lbl_room.setText(f"Room {room.get('room_number', '')}")
        lbl_status.setText("Check in")
        le_time.setText(self.fmt_datetime(stay.get("checked_in_at")))
        if btn is self.ui.btnCheckOutRow1:
            try: btn.clicked.disconnect()
            except: pass
            btn.clicked.connect(lambda checked, i=checkout_idx: self.do_checkout(i))
        btn.setVisible(True)

    def do_checkout(self, idx):
        self.db.load_all()
        stays = [s for s in self.db.data["stays"] if s.get("active")]
        if idx - 1 >= len(stays):
            return
        stay = stays[idx - 1]
        data = self.db.data
        booking = next((b for b in data["bookings"] if b["id"] == stay["booking_id"]), {})
        room = next((r for r in data["rooms"] if r["id"] == stay["room_id"]), {})
        customer = next((c for c in data["customers"] if c["id"] == booking.get("customer_id")), {})
        if not self.confirm(
            f"Check out phòng {room.get('room_number', '')}?\n"
            f"Khách: {customer.get('full_name', '')}\n"
            f"Check in: {self.fmt_datetime(stay.get('checked_in_at'))}"
        ):
            return
        try:
            self.stays.check_out(stay["id"])
            self.db.load_all() # reload after check_out saved
            # remove any old unpaid statement and regenerate with latest services
            self.db.data["statements"] = [
                s for s in self.db.data["statements"]
                if not (s.get("stay_id") == stay["id"] and s.get("status") == PaymentStatus.UNPAID)
            ]
            self.db.save_all()
            self.payments.generate_statement(stay["id"])
        except ValueError as e:
            return self.show_error("Check out thất bại", str(e))
        self.show_info("Check out", f"Phòng {room.get('room_number', '')} đã check out thành công.")
        self.load_checkinout()
        self.load_rooms()
        self.load_payments()

    # payments

    def load_payments(self):
        self.db.load_all()
        data = self.db.data
        table = self.ui.tblPaymentList
        # hide old overlay buttons
        for i in range(1, 5):
            btn = self.get_widget(f"btnPaymentDownloadRow{i}")
            if btn:
                btn.setVisible(False)
        table.setRowCount(len(data["statements"]))
        table.verticalHeader().setDefaultSectionSize(44)
        table.verticalHeader().setVisible(False)
        for r, st in enumerate(data["statements"]):
            stay = next((s for s in data["stays"] if s["id"] == st["stay_id"]), {})
            booking = next((b for b in data["bookings"] if b["id"] == stay.get("booking_id")), {})
            customer = next((c for c in data["customers"] if c["id"] == booking.get("customer_id")), {})
            status = "Đã thanh toán" if st.get("status") == PaymentStatus.PAID else "Chưa thanh toán"
            table.setItem(r, 0, QtWidgets.QTableWidgetItem(customer.get("full_name", f"Stay #{st.get('stay_id','')}")))
            table.setItem(r, 1, QtWidgets.QTableWidgetItem(f"${st.get('total_amount', 0):.2f}"))
            table.setItem(r, 2, QtWidgets.QTableWidgetItem(status))
            btn = QtWidgets.QPushButton()
            btn.setStyleSheet("QPushButton { background-color:transparent; border:1px; }")
            btn.setText("")
            icon = self.ui.btnPaymentDownloadRow1.icon()
            btn.setIcon(icon)
            btn.setIconSize(self.ui.btnPaymentDownloadRow1.iconSize())
            btn.clicked.connect(lambda checked, sid=st["id"]: self.pay_by_statement_id(sid))
            table.setCellWidget(r, 3, btn)

    def mark_payment_paid(self, idx):
        self.db.load_all()
        unpaid = [s for s in self.db.data["statements"] if s.get("status") == PaymentStatus.UNPAID]
        if idx - 1 >= len(unpaid):
            self.show_info("Thanh toán", "Không có hoá đơn chưa thanh toán ở vị trí này.")
            return
        self.pay_by_statement_id(unpaid[idx - 1]["id"])

    def pay_by_statement_id(self, statement_id):
        self.db.load_all()
        st = next((s for s in self.db.data["statements"] if s["id"] == statement_id), None)
        if not st or st.get("status") == PaymentStatus.PAID:
            self.show_info("Thanh toán", "Hoá đơn đã được thanh toán.")
            return
        stay = next((s for s in self.db.data["stays"] if s["id"] == st.get("stay_id")), None)
        if stay and stay.get("active"):
            return self.show_error("Thanh toán", "Khách chưa check out. Không thể thanh toán.")
        if not self.confirm(
            f"Xác nhận thanh toán hoá đơn #{st['id']}?\n"
            f"Tổng tiền: ${st.get('total_amount', 0):.2f}"
        ):
            return
        try:
            self.payments.mark_paid(st["id"])
            self.show_info("Thanh toán", "Thanh toán thành công!")
            self.load_payments()
        except ValueError as e:
            self.show_error("Lỗi", str(e))

    # staff

    def load_staff(self):
        self.db.load_all()
        staffs = self.db.data["staffs"]
        for i in range(1, 10):
            self.set_staff_row(i, staffs[i - 1] if i - 1 < len(staffs) else None)

    def add_employee_dialog(self):
        dialog = QtWidgets.QDialog(self)
        ui = Ui_ThemNV()
        ui.setupUi(dialog)

        def submit():
            name = ui.leFullName.text().strip()
            phone = ui.lePhone.text().strip()
            email = ui.leEmail.text().strip()
            nid = ui.leNationalId.text().strip()
            pos = ui.cbPosition.currentText()
            if not all([name, phone, email, nid]) or pos == "Chưa chọn":
                return self.show_error("Thiếu thông tin", "Vui lòng nhập đầy đủ thông tin.")
            err = self.validate_customer_fields(name, phone, email, nid)
            if err:
                return self.show_error("Lỗi", err)
            if not self.confirm(f"Thêm nhân viên '{name}'?"):
                return
            self.staff.add_staff(name, phone, email, nid, position=pos)
            self.load_staff()
            self.show_info("Thành công", f"Đã thêm nhân viên '{name}'.")
            dialog.accept()

        ui.btnConfirm.clicked.connect(submit)
        dialog.exec()

    def delete_employee(self, idx):
        self.db.load_all()
        staffs = self.db.data["staffs"]
        if idx - 1 >= len(staffs):
            return
        staff = staffs[idx - 1]
        if not self.confirm(f"Xoá nhân viên '{staff.get('full_name', '')}'?"):
            return
        self.db.data["staffs"] = [s for s in staffs if s["id"] != staff["id"]]
        self.db.save_all()
        self.load_staff()
        self.show_info("Thành công", f"Đã xoá nhân viên '{staff.get('full_name', '')}'.")

    def assign_shift_dialog(self, idx):
        self.db.load_all()
        staffs = self.db.data["staffs"]
        if idx - 1 >= len(staffs):
            return
        s = staffs[idx - 1]

        dialog = QtWidgets.QDialog(self)
        ui = Ui_GiaCa()
        ui.setupUi(dialog)
        dialog.setWindowTitle(f"Giao ca - {s.get('full_name', '')}")

        def submit():
            if ui.cbWeekday.currentText() == "không" or ui.cbShiftSlot.currentText() == "không":
                return self.show_error("Thiếu thông tin", "Vui lòng chọn thứ và ca.")
            weekday = ui.cbWeekday.currentIndex() - 1
            slot_index = ui.cbShiftSlot.currentIndex() - 1
            if not self.confirm(f"Giao ca '{ui.cbShiftSlot.currentText()}' ngày '{ui.cbWeekday.currentText()}' cho {s.get('full_name', '')}?"):
                return
            # remove existing shift for this staff before assigning new one
            self.db.data["shifts"] = [sh for sh in self.db.data["shifts"] if sh["staff_id"] != s["id"]]
            self.db.save_all()
            self.staff.assign_shift(s["id"], weekday, slot_index)
            self.load_schedule()
            self.load_staff()
            self.show_info("Thành công", "Đã giao ca.")
            dialog.accept()

        ui.btnConfirm.clicked.connect(submit)
        dialog.exec()

    def load_schedule(self):
        self.db.load_all()
        data = self.db.data
        staffs = {s["id"]: s for s in data["staffs"]}
        tbl = self.ui.tblEmployeeSchedule

        for r in range(tbl.rowCount()):
            for c in range(tbl.columnCount()):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(""))

        for shift in data["shifts"]:
            row = shift.get("shift_slot")
            col = shift.get("weekday")
            if not isinstance(row, int) or not isinstance(col, int):
                continue
            if row < 0 or row >= tbl.rowCount() or col < 0 or col >= tbl.columnCount():
                continue
            name = staffs.get(shift["staff_id"], {}).get("full_name", "?")
            existing = tbl.item(row, col)
            current = existing.text() if existing and existing.text() else ""
            tbl.setItem(row, col, QtWidgets.QTableWidgetItem(
                f"{current}\n{name}".strip() if current else name))

    def delete_selected_shift(self):
        tbl = self.ui.tblEmployeeSchedule
        item = tbl.currentItem()
        if not item or not item.text().strip():
            return self.show_error("Xoá ca", "Vui lòng chọn một ô có ca làm việc.")
        row = tbl.currentRow()
        col = tbl.currentColumn()
        if not self.confirm("Xoá tất cả ca trong ô này?"):
            return
        self.db.load_all()
        self.db.data["shifts"] = [
            s for s in self.db.data["shifts"]
            if not (s.get("shift_slot") == row and s.get("weekday") == col)
        ]
        self.db.save_all()
        self.load_schedule()
        self.load_staff()

    def set_staff_row(self, idx, staff):
        slot_names = ["Ca sáng", "Ca chiều", "Ca đêm 1", "Ca đêm 2"]
        day_names = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]

        lbl_ca = self.get_widget(f"leEmployeeRow{idx}Ca")
        lbl_shift = self.get_widget(f"leEmployeeRow{idx}Shift")

        if staff is None:
            for f in ("Name", "Position", "Phone", "Email", "CCCD"):
                self.set_text(f"leEmployeeRow{idx}{f}", "")
            if lbl_ca: lbl_ca.setVisible(False)
            if lbl_shift: lbl_shift.setVisible(False)
            return

        self.set_text(f"leEmployeeRow{idx}Name", staff.get("full_name", ""))
        self.set_text(f"leEmployeeRow{idx}Position", staff.get("position", ""))
        w = self.get_widget(f"leEmployeeRow{idx}Position")
        if w:
            w.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.set_text(f"leEmployeeRow{idx}Phone", staff.get("phone", ""))
        self.set_text(f"leEmployeeRow{idx}Email", staff.get("email", ""))
        self.set_text(f"leEmployeeRow{idx}CCCD", staff.get("national_id", ""))

        shifts = self.db.data.get("shifts", [])
        my_shift = next((s for s in shifts if s["staff_id"] == staff["id"]), None)
        if my_shift:
            slot = my_shift.get("shift_slot")
            day = my_shift.get("weekday")
            slot_text = slot_names[slot] if isinstance(slot, int) and slot < len(slot_names) else ""
            day_text = day_names[day] if isinstance(day, int) and day < len(day_names) else ""
            if lbl_ca:
                lbl_ca.setText("Ca:")
                lbl_ca.setVisible(True)
            if lbl_shift:
                lbl_shift.setText(f"{slot_text} {day_text}".strip())
                lbl_shift.setVisible(True)
        else:
            if lbl_ca: lbl_ca.setVisible(False)
            if lbl_shift: lbl_shift.setVisible(False)

    # service

    def load_service_rooms(self):
        self.db.load_all()
        cb = self.ui.cbServiceSelectRoom
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("Chọn phòng", None)
        data = self.db.data
        for booking in data["bookings"]:
            if booking["status"] != BookingStatus.CHECKED_IN:
                continue
            room = next((r for r in data["rooms"] if r["id"] == booking["room_id"]), None)
            if not room:
                continue
            stay = next((s for s in data["stays"]
                         if s["booking_id"] == booking["id"] and s.get("active")), None)
            cb.addItem(f"Room {room['room_number']}", stay["id"] if stay else None)
        cb.blockSignals(False)
        self.ui.textEdit.setText("")
        self.set_text("leServiceRoom", "")
        self.update_service_totals(0.0)

    def on_service_room_changed(self):
        stay_id = self.ui.cbServiceSelectRoom.currentData()
        room_txt = self.ui.cbServiceSelectRoom.currentText() if stay_id else ""
        self.set_text("leServiceRoom", room_txt)
        self.ui.textEdit.setText("")
        self.update_service_totals(0.0)
        if stay_id:
            self.load_service_detail()

    def load_service_detail(self):
        self.db.load_all()
        self.ui.textEdit.setText("")
        stay_id = self.ui.cbServiceSelectRoom.currentData()
        if not stay_id:
            self.update_service_totals(0.0)
            return
        data = self.db.data
        items = {i["id"]: i for i in data["service_items"]}
        usages = [u for u in data["service_usages"] if u["stay_id"] == stay_id]
        # stack same items together
        totals = {}
        for u in usages:
            if u["service_item_id"] not in items:
                continue
            name = items[u["service_item_id"]]["name"]
            totals[name] = totals.get(name, 0) + u["quantity"]
        lines = "\n".join(f"{name}  x{qty}" for name, qty in totals.items())
        self.ui.textEdit.setPlainText(lines)
        total = sum(
            items[u["service_item_id"]]["price_per_unit"] * u["quantity"]
            for u in usages if u["service_item_id"] in items
        )
        self.update_service_totals(total)

    def update_service_totals(self, total):
        tax = total * 0.015
        self.set_text("leServiceDetailPriceExTax", f"${total:.2f}")
        self.set_text("leServiceDetailTaxAmount", f"${tax:.2f}")
        self.set_text("leServiceTotal", f"${total + tax:.2f}")

    def add_service_item(self, row_idx):
        stay_id = self.ui.cbServiceSelectRoom.currentData()
        if not stay_id:
            return self.show_error("Dịch vụ", "Vui lòng chọn phòng trước.")
        name_w = self.get_widget(f"lblServiceRow{row_idx}Name")
        price_w = self.get_widget(f"lblServiceRow{row_idx}Price")
        if not name_w:
            return
        service_name = name_w.text().strip()
        price_text = price_w.text().strip() if price_w else "0"
        if not service_name:
            return
        try:
            price = float(price_text.replace("$", "").replace(",", ""))
        except ValueError:
            price = 0.0
        self.db.load_all()
        items = self.db.data.get("service_items", [])
        item_id = next((i["id"] for i in items if i["name"] == service_name), None)
        if item_id is None:
            item_id = self.services.create_service_item(service_name, price, "service").id
        self.services.add_service_usage(stay_id, item_id, 1, "")
        self.load_service_detail()

    def delete_last_service(self):
        stay_id = self.ui.cbServiceSelectRoom.currentData()
        if not stay_id:
            return
        self.db.load_all()
        usages = [u for u in self.db.data["service_usages"] if u["stay_id"] == stay_id]
        if not usages:
            return
        last = usages[-1]
        items = {i["id"]: i for i in self.db.data["service_items"]}
        name = items.get(last["service_item_id"], {}).get("name", f"ID {last['service_item_id']}")
        if not self.confirm(f"Xoá dịch vụ '{name}' vừa thêm?"):
            return
        self.db.data["service_usages"] = [
            u for u in self.db.data["service_usages"] if u["id"] != last["id"]
        ]
        self.db.save_all()
        self.load_service_detail()