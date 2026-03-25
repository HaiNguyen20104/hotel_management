# Cấu trúc Module Hotel Management

## 📁 Tổng quan cấu trúc thư mục

```
hotel_management/
│
├── 📄 __init__.py                          # Module initialization
├── 📄 __manifest__.py                      # Module manifest (metadata, dependencies)
├── 📄 README.md                            # Tài liệu chi tiết module
│
├── 📂 models/                              # BUSINESS LOGIC & DATABASE
│   ├── __init__.py
│   ├── room.py                             # ✓ F1: Quản lý phòng
│   ├── room_type.py                        # ✓ F2: Quản lý loại phòng
│   ├── reservation.py                      # ✓ F4: Đặt phòng
│   ├── rental.py                           # ✓ F4: Checkin/Checkout
│   └── invoice.py                          # ✓ F7: Quản lý hóa đơn
│
├── 📂 views/                               # USER INTERFACE (XML)
│   ├── menu_views.xml                      # Menu chính module
│   ├── room_views.xml                      # ✓ F1: CRUD phòng
│   ├── room_type_views.xml                 # ✓ F2: CRUD loại phòng
│   ├── reservation_views.xml               # ✓ F4: Đặt phòng, hủy phòng
│   ├── rental_views.xml                    # ✓ F4: Checkin, checkout, đổi phòng
│   ├── invoice_views.xml                   # ✓ F7: CRUD hóa đơn, in hóa đơn
│   ├── dashboard_views.xml                 # ✓ F8: Dashboard trạng thái phòng
│   └── report_views.xml                    # ✓ F9: Views báo cáo thống kê
│
├── 📂 security/                            # ACCESS CONTROL
│   ├── ir.model.access.csv                 # ✓ F6: Access rights cho models
│   └── security_groups.xml                 # ✓ F6: Groups (Admin, Staff, Customer)
│
├── 📂 wizards/                             # TRANSIENT MODELS (Popup actions)
│   ├── __init__.py
│   ├── wizard_checkin.py                   # ✓ F4: Wizard checkin
│   ├── wizard_checkin_views.xml
│   ├── wizard_checkout.py                  # ✓ F4: Wizard checkout
│   ├── wizard_checkout_views.xml
│   ├── wizard_change_room.py               # ✓ F4: Wizard đổi phòng
│   └── wizard_change_room_views.xml
│
├── 📂 reports/                             # REPORTS & PRINTING
│   ├── report_actions.xml                  # ✓ F9: Khai báo report actions
│   ├── report_invoice_template.xml         # ✓ F7: Template in hóa đơn
│   ├── report_revenue.xml                  # ✓ F9: Báo cáo doanh thu
│   └── report_occupancy.xml                # ✓ F9: Báo cáo công suất phòng
│
├── 📂 controllers/                         # WEB CONTROLLERS (API, Portal)
│   ├── __init__.py
│   ├── portal.py                           # ✓ F3: Portal khách hàng, tra cứu phòng
│   └── main.py                             # API endpoints khác
│
├── 📂 data/                                # MASTER DATA & DEMO
│   ├── room_type_data.xml                  # Dữ liệu loại phòng mặc định
│   └── demo_data.xml                       # Dữ liệu demo (optional)
│
└── 📂 static/                              # STATIC FILES
    └── description/
        ├── index.html                      # Module description HTML
        ├── README.md                       # Module info
        └── icon.png                        # Module icon (128x128)
```

## 🗄️ Database Schema (Models Relationship)

```
┌─────────────────┐
│   res.partner   │ (Odoo Standard - Khách hàng)
│   (Customer)    │
└────────┬────────┘
         │ Many2one
         ▼
┌─────────────────────────┐         ┌──────────────────┐
│  hotel.reservation      │────────▶│  hotel.room      │
│  (Đặt phòng)            │Many2one │  (Phòng)         │
│  - Mã đặt phòng         │         │  - Mã phòng      │
│  - Khách hàng           │         │  - Số phòng      │
│  - Phòng                │         │  - Trạng thái    │
│  - Ngày nhận/trả dự kiến│         └────────┬─────────┘
│  - Tiền cọc             │                  │ Many2one
│  - Trạng thái           │                  ▼
└─────────┬───────────────┘         ┌──────────────────┐
          │ One2many                │ hotel.room.type  │
          ▼                         │ (Loại phòng)     │
┌─────────────────────────┐         │ - Tên loại       │
│  hotel.rental           │────────▶│ - Giá cơ bản     │
│  (Thuê phòng)           │Many2one │ - Số người max   │
│  - Mã thuê              │         │ - Tiện nghi      │
│  - Reservation          │         └──────────────────┘
│  - Checkin thực tế      │
│  - Checkout thực tế     │
│  - Số người ở           │
└─────────┬───────────────┘
          │ One2many
          ▼
┌─────────────────────────┐
│  hotel.invoice          │
│  (Hóa đơn)              │
│  - Mã hóa đơn           │
│  - Rental               │
│  - Đơn giá              │
│  - Phụ thu              │
│  - Tổng tiền            │
│  - Trạng thái TT        │
└─────────────────────────┘

┌─────────────────┐
│   res.users     │ (Odoo Standard - Nhân viên)
│   (Staff/Admin) │
└─────────────────┘
```

## 🔐 Security Groups Hierarchy

```
hotel_group_admin (Hotel Manager)
    └── Toàn quyền: CRUD all models, reports, settings

hotel_group_staff (Hotel Staff)
    └── CRUD: Room, RoomType, Reservation, Rental, Invoice
    └── View: Dashboard, Reports

hotel_group_customer (Hotel Customer - Portal)
    └── View: Available rooms
    └── Create: Own reservations
    └── View: Own reservations & invoices
```

## 📊 Mapping BA Planning → Implementation

| STT | Chức năng | Tác nhân | Implementation | Files liên quan |
|-----|-----------|----------|----------------|-----------------|
| **F1** | Quản lý phòng | Staff | Model + Views | `models/room.py`<br>`views/room_views.xml` |
| **F2** | Quản lý loại phòng | Staff | Model + Views | `models/room_type.py`<br>`views/room_type_views.xml` |
| **F3** | Tra cứu phòng trống | All | Controller + Portal | `controllers/portal.py`<br>Computed fields in models |
| **F4** | Đặt phòng | Staff, Customer | Models + Views + Wizards | `models/reservation.py`<br>`models/rental.py`<br>`wizards/wizard_*.py` |
| **F5** | Quản lý khách hàng | Admin | Extend res.partner | Odoo standard + custom fields |
| **F6** | Quản lý nhân viên | Admin | Security groups | `security/security_groups.xml`<br>`security/ir.model.access.csv` |
| **F7** | Quản lý hóa đơn | Admin | Model + Views + Report | `models/invoice.py`<br>`views/invoice_views.xml`<br>`reports/report_invoice_template.xml` |
| **F8** | Theo dõi trạng thái | All | Dashboard + Cron | `views/dashboard_views.xml`<br>Kanban/Calendar views<br>Cron job (in models) |
| **F9** | Thống kê báo cáo | Admin | Reports + Charts | `views/report_views.xml`<br>`reports/report_revenue.xml`<br>`reports/report_occupancy.xml` |

## 🔄 Workflow Chính

### 1. Workflow Đặt phòng → Checkin → Checkout → Hóa đơn

```
[Customer/Staff]
      │
      ▼
┌─────────────────┐
│ Tạo Reservation │  (reservation.py)
│  - Chọn phòng   │
│  - Chọn ngày    │
│  - Đặt cọc      │
└────────┬────────┘
         │ state = 'confirmed'
         ▼
┌─────────────────┐
│ Wizard Checkin  │  (wizard_checkin.py)
│  - Xác nhận     │
│  - Tạo Rental   │
└────────┬────────┘
         │ Room.state = 'occupied'
         ▼
┌─────────────────┐
│ Rental (Ongoing)│  (rental.py)
│  - Cập nhật     │
│    số người ở   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Wizard Checkout │  (wizard_checkout.py)
│  - Tính tiền    │
│  - Tạo Invoice  │
└────────┬────────┘
         │ Room.state = 'available'
         ▼
┌─────────────────┐
│ Invoice         │  (invoice.py)
│  - Thanh toán   │
│  - In hóa đơn   │
└─────────────────┘
```

### 2. Workflow Tra cứu phòng trống (F3)

```
[Customer Portal]
      │
      ▼
┌──────────────────────┐
│ portal.py            │
│ - Input: checkin_date│
│          checkout_date
│          room_type   │
│          max_price   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Search Domain        │
│ - state = available  │
│ - no conflict dates  │
│ - price <= max_price │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Return: List of      │
│         Available    │
│         Rooms        │
└──────────────────────┘
```

## 📝 Checklist Implementation

### Phase 1: Core Models ✅
- [x] Tạo cấu trúc thư mục
- [ ] Implement `room.py`
- [ ] Implement `room_type.py`
- [ ] Implement `reservation.py`
- [ ] Implement `rental.py`
- [ ] Implement `invoice.py`

### Phase 2: Views & UI
- [ ] Views cho Room (tree, form, kanban)
- [ ] Views cho RoomType
- [ ] Views cho Reservation (form, calendar)
- [ ] Views cho Rental (form, tree)
- [ ] Views cho Invoice (form, tree)
- [ ] Dashboard (kanban, graph, pivot)
- [ ] Menu structure

### Phase 3: Security
- [ ] Define security groups
- [ ] Set access rights (ir.model.access.csv)
- [ ] Record rules (if needed)

### Phase 4: Wizards & Actions
- [ ] Wizard Checkin
- [ ] Wizard Checkout
- [ ] Wizard Change Room
- [ ] Actions & buttons

### Phase 5: Reports
- [ ] Report Invoice Template
- [ ] Report Revenue Analysis
- [ ] Report Room Occupancy
- [ ] Export Excel functions

### Phase 6: Controllers & Portal
- [ ] Portal controller (room search)
- [ ] API endpoints
- [ ] Customer portal views

### Phase 7: Data & Demo
- [ ] Master data: Room types
- [ ] Demo data: Rooms, Reservations

### Phase 8: Advanced Features
- [ ] Cronjob: Auto update room status
- [ ] Cronjob: Send reminder emails
- [ ] Automated pricing rules
- [ ] Integration with payment gateway (optional)

## 🚀 Quick Start

1. **Copy module vào addons_path**:
   ```bash
   cp -r hotel_management /path/to/odoo/custome_addons/
   ```

2. **Update Odoo apps list**:
   - Apps → Update Apps List

3. **Install module**:
   - Apps → Search "Hotel Management" → Install

4. **Setup initial data**:
   - Hotel → Configuration → Room Types
   - Hotel → Rooms → Create rooms

5. **Start using**:
   - Hotel → Reservations → Create new reservation
   - Hotel → Dashboard → View room status

## 📞 Support

Tài liệu chi tiết: Xem `README.md`
