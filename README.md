# Hotel Management Module - Odoo 18

Module quản lý khách sạn cho Odoo 18 với đầy đủ tính năng đặt phòng, checkin/checkout, quản lý hóa đơn và báo cáo.

## Cấu trúc thư mục

```
hotel_management/
├── __init__.py                 # File khởi tạo module chính
├── __manifest__.py             # Khai báo thông tin module
│
├── models/                     # Business Logic & Database Models
│   ├── __init__.py
│   ├── room.py                 # Model phòng (F1: Quản lý phòng)
│   ├── room_type.py            # Model loại phòng (F2: Quản lý loại phòng)
│   ├── reservation.py          # Model đặt phòng (F4: Đặt phòng)
│   ├── rental.py               # Model thuê phòng/checkin (F4: Checkin/Checkout)
│   └── invoice.py              # Model hóa đơn (F7: Quản lý hóa đơn)
│
├── views/                      # Giao diện người dùng (XML)
│   ├── room_views.xml          # Views quản lý phòng
│   ├── room_type_views.xml     # Views quản lý loại phòng
│   ├── reservation_views.xml   # Views đặt phòng
│   ├── rental_views.xml        # Views checkin/checkout
│   ├── invoice_views.xml       # Views hóa đơn
│   ├── dashboard_views.xml     # Dashboard trạng thái phòng (F8)
│   ├── report_views.xml        # Views báo cáo thống kê (F9)
│   └── menu_views.xml          # Menu chính của module
│
├── security/                   # Phân quyền & Access Control
│   ├── ir.model.access.csv     # Quyền truy cập models
│   └── security_groups.xml     # Nhóm quyền (Admin, Staff, Customer)
│
├── reports/                    # Báo cáo & In ấn
│   ├── report_invoice_template.xml  # Template in hóa đơn
│   ├── report_revenue.xml           # Báo cáo doanh thu (F9)
│   ├── report_occupancy.xml         # Báo cáo công suất phòng (F9)
│   └── report_actions.xml           # Khai báo report actions
│
├── wizards/                    # Các wizard cho thao tác đặc biệt
│   ├── __init__.py
│   ├── wizard_checkin.py              # Wizard checkin
│   ├── wizard_checkin_views.xml
│   ├── wizard_checkout.py             # Wizard checkout
│   ├── wizard_checkout_views.xml
│   ├── wizard_change_room.py          # Wizard đổi phòng
│   └── wizard_change_room_views.xml
│
├── controllers/                # API Controllers
│   ├── __init__.py
│   ├── portal.py               # Portal cho khách hàng (F3: Tra cứu phòng)
│   └── main.py                 # API endpoints khác
│
├── data/                       # Dữ liệu mẫu & Master data
│   ├── room_type_data.xml      # Dữ liệu loại phòng mặc định
│   └── demo_data.xml           # Dữ liệu demo (optional)
│
└── static/                     # Files tĩnh
    └── description/
        ├── index.html          # Mô tả module
        └── README.md           # Tài liệu module
```

## Mapping với BA Planning

### Models (Database Design)

| Model | File | Mô tả | Chức năng liên quan |
|-------|------|-------|-------------------|
| **hotel.room** | `models/room.py` | Quản lý thông tin phòng | F1: Quản lý phòng |
| **hotel.room.type** | `models/room_type.py` | Quản lý loại phòng | F2: Quản lý loại phòng |
| **hotel.reservation** | `models/reservation.py` | Đặt phòng trước | F4: Đặt phòng |
| **hotel.rental** | `models/rental.py` | Thuê phòng thực tế (checkin) | F4: Checkin/Checkout |
| **hotel.invoice** | `models/invoice.py` | Hóa đơn thanh toán | F7: Quản lý hóa đơn |
| **res.partner** | Odoo standard | Thông tin khách hàng | F5: Quản lý khách hàng |
| **res.users** | Odoo standard | Thông tin nhân viên | F6: Quản lý nhân viên |

### Views theo Chức năng

| Chức năng | File Views | Mô tả |
|-----------|-----------|-------|
| **F1: Quản lý phòng** | `views/room_views.xml` | CRUD phòng, danh sách, form chi tiết |
| **F2: Quản lý loại phòng** | `views/room_type_views.xml` | CRUD loại phòng, cấu hình giá |
| **F3: Tra cứu phòng trống** | `controllers/portal.py` | API tra cứu phòng, lọc theo ngày/giá |
| **F4: Đặt phòng** | `views/reservation_views.xml`, `views/rental_views.xml` | Tạo đặt phòng, checkin, checkout |
| **F5: Quản lý khách hàng** | Odoo Contact standard | Extend res.partner views |
| **F6: Quản lý nhân viên** | Odoo HR/Users standard | Phân quyền qua security groups |
| **F7: Quản lý hóa đơn** | `views/invoice_views.xml` | CRUD hóa đơn, in hóa đơn |
| **F8: Theo dõi trạng thái** | `views/dashboard_views.xml` | Dashboard, kanban, calendar views |
| **F9: Thống kê báo cáo** | `views/report_views.xml`, `reports/` | Biểu đồ, báo cáo doanh thu, excel |

### Security Groups (F6: Phân quyền)

Định nghĩa trong `security/security_groups.xml`:

1. **Hotel Manager (Admin)**: Toàn quyền
2. **Hotel Staff**: CRUD phòng, đặt phòng, checkin/checkout
3. **Hotel Customer**: Xem phòng trống, đặt phòng (thông qua portal)

## Thông tin Models chi tiết

### hotel.room (Room)
- Mã phòng, tên phòng, số phòng
- Loại phòng (Many2one -> hotel.room.type)
- Tầng, số người
- Giá thuê theo ngày/giờ
- Trạng thái (available, occupied, maintenance, reserved)
- Mô tả, ghi chú

### hotel.room.type (RoomType)
- Tên loại phòng (Standard, Deluxe, VIP, Family)
- Giá cơ bản
- Số người tối đa
- Tiện nghi
- Mô tả

### hotel.reservation (Reservation)
- Mã đặt phòng
- Khách hàng (Many2one -> res.partner)
- Phòng (Many2one -> hotel.room)
- Ngày giờ nhận phòng dự kiến
- Ngày giờ trả phòng dự kiến
- Trạng thái (draft, confirmed, cancelled, checked_in)
- Tiền cọc

### hotel.rental (Rental)
- Mã thuê phòng
- Reservation (Many2one -> hotel.reservation)
- Khách hàng, phòng
- Ngày giờ checkin thực tế
- Ngày giờ checkout dự kiến
- Ngày giờ checkout thực tế
- Số người ở thực tế
- Trạng thái (ongoing, completed, cancelled)

### hotel.invoice (Invoice)
- Mã hóa đơn
- Rental (Many2one -> hotel.rental)
- Khách hàng
- Đơn giá
- Số ngày/giờ thuê
- Phụ thu (điện nước, dịch vụ)
- Tổng tiền
- Trạng thái thanh toán

## Ghi chú triển khai

1. **Tự động cập nhật trạng thái phòng**:
   - Khi checkin -> room.state = 'occupied'
   - Khi checkout -> room.state = 'available'
   - Cronjob kiểm tra và nhắc nhở checkin/checkout (F8)

2. **Tính toán giá tự động**:
   - Giá phòng từ room_type
   - Override được ở từng room
   - Tính phụ thu tự động

3. **Portal cho khách hàng**:
   - Tra cứu phòng trống (F3)
   - Đặt phòng online
   - Xem lịch sử thuê

4. **Báo cáo thống kê** (F9):
   - Dashboard tổng quan
   - Báo cáo doanh thu theo thời gian/phòng
   - Thống kê công suất phòng
   - Export Excel

## Next Steps

1. ✅ Tạo cấu trúc thư mục
2. ⏳ Viết models (room, room_type, reservation, rental, invoice)
3. ⏳ Viết views (form, tree, kanban, calendar)
4. ⏳ Cấu hình security (groups, access rights)
5. ⏳ Viết wizards (checkin, checkout, change_room)
6. ⏳ Viết controllers (API tra cứu phòng)
7. ⏳ Viết reports (templates, actions)
8. ⏳ Test & Debug
