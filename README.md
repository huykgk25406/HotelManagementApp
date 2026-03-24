# HotelManagementApp
Ứng dụng quản lý khách sạn, xây dựng bằng Python và PyQt6.

A hotel management application built with Python and PyQt6.

---
### Giới thiệu

HotelManagementApp là ứng dụng quản lý khách sạn dành cho lễ tân và quản lý, hỗ trợ các nghiệp vụ như quản lý phòng, đặt phòng, nhận/trả phòng, thanh toán, dịch vụ và phân ca nhân viên.
Dữ liệu được lưu trữ cục bộ dưới dạng file JSON.

### Cấu trúc dự án

```
HotelManagementApp/
|-- main.py            # Khởi chạy ứng dụng
|-- gui_Ext.py         # Logic và xử lý giao diện
|-- gui.py             # Giao diện được tạo từ Qt Designer (.ui)
|-- hotel_data.json    # Cơ sở dữ liệu dạng JSON
|-- images/            # Hình ảnh của icon
|-- gui/               # Chứa file giao diện định dạng .ui
```

### Tính năng

- **Đăng nhập / Đăng ký** — Xác thực tài khoản người dùng với kiểm tra định dạng email mật khẩu
- **Quản lý phòng** — Xem danh sách phòng, lọc theo loại và trạng thái (còn trống / hết phòng)
- **Đặt phòng** — Tạo đặt phòng mới, gia hạn ngày trả phòng
- **Nhận / Trả phòng** — Nhận phòng cho khách, trả phòng và cập nhật trạng thái phòng tự động
- **Thanh toán** — Tạo hoá đơn tự động khi trả phòng, theo dõi trạng thái thanh toán (đã / chưa thanh toán)
- **Dịch vụ** — Thêm dịch vụ sử dụng trong thời gian lưu trú (ăn uống, giặt ủi, đưa đón, v.v.)
- **Khách hàng** — Tìm kiếm khách hàng, xem lịch sử đặt phòng và trạng thái thanh toán
- **Nhân viên** — Thêm/xoá nhân viên, phân công ca làm việc theo tuần
- **Lịch ca** — Hiển thị lịch ca làm việc dạng bảng theo ngày trong tuần

### Cách hoạt động

Khi khách nhận phòng, hệ thống tạo một bản ghi **Lưu trú** liên kết với đặt phòng và cập nhật trạng thái phòng thành "hết phòng". Khi trả phòng, hệ thống tạo **Hoá đơn** tổng hợp tiền phòng và tiền dịch vụ. Lễ tân xác nhận thanh toán trực tiếp trên tab Thanh toán.

### Yêu cầu cài đặt

```
pip install PyQt6
```

### Chạy ứng dụng

```
python main.py
```

### Tài khoản mặc định

| Email | Mật khẩu |
|-------|----------|
| admin@hotel.test | admin123 |
| frontdesk@hotel.test | welcome123 |

Dự án hiện vẫn đang trong quá trình phát triển. Một số tính năng có thể chưa hoàn thiện hoặc còn lỗi.
---

### Overview

HotelManagementApp is a hotel management application for both receptionists and managers, supporting room management, bookings, check-in/out, payments, services, and staff scheduling.
All data is stored locally in a JSON file.

### Project Structure

```
HotelManagementApp/
|-- main.py            # App startup
|-- gui_Ext.py         # Logic and UI event handling
|-- gui.py             # UI definitions generated from Qt Designer (.ui)
|-- hotel_data.json    # Local JSON database
|-- images/            # Icon's images
|-- gui/               # Contain .ui files
```

### Features

- **Login / Register** — User authentication with email format and password validation
- **Room Management** — View room list, filter by type and status (available / occupied)
- **Bookings** — Create new bookings, extend check-out dates
- **Check-in / Check-out** — Check guests in and out with automatic room status updates
- **Payments** — Auto-generate invoices on check-out, track payment status (paid / unpaid)
- **Services** — Add in-stay service charges (meals, laundry, transport, etc.)
- **Customers** — Search customers, view booking history and payment status
- **Staff** — Add/remove staff members, assign weekly shift schedules
- **Shift Schedule** — Weekly shift table view by day

### How It Works

When a guest checks in, the system creates a **Stay** record linked to the booking and marks the room as occupied. On check-out, a **Statement** is generated combining room charges and any service usage. The receptionist then confirms payment from the Payment tab.

### Requirements

```
pip install PyQt6
```

### Running the App

```
python main.py
```

### Default Accounts

| Email | Password |
|-------|----------|
| admin@hotel.test | admin123 |
| frontdesk@hotel.test | welcome123 |

This project is still under active development. Some features may be incomplete or contain bugs.
---
