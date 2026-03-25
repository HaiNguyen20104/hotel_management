# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HotelRoomType(models.Model):
    """Model quản lý loại phòng khách sạn (F2: Quản lý loại phòng)

    Các loại phòng ví dụ: Standard, Deluxe, VIP, Family, Suite...
    Mỗi loại phòng có giá cơ bản, số người tối đa và tiện nghi riêng.
    """
    _name = 'hotel.room.type'
    _description = 'Hotel Room Type'
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(
        string='Tên loại phòng',
        required=True,
        translate=True,
        help='Ví dụ: Standard, Deluxe, VIP, Family, Suite'
    )

    code = fields.Char(
        string='Mã loại phòng',
        required=True,
        copy=False,
        help='Mã định danh duy nhất cho loại phòng. Ví dụ: STD, DLX, VIP'
    )

    sequence = fields.Integer(
        string='Thứ tự',
        default=10,
        help='Dùng để sắp xếp thứ tự hiển thị'
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True,
        help='Bỏ tích để ẩn loại phòng này khỏi hệ thống'
    )

    # Pricing Information (F2: Khai báo giá cơ bản)
    base_price = fields.Float(
        string='Giá cơ bản (theo ngày)',
        required=True,
        digits='Product Price',
        help='Giá thuê phòng theo ngày (24 giờ)'
    )

    hourly_price = fields.Float(
        string='Giá theo giờ',
        digits='Product Price',
        help='Giá thuê phòng theo giờ (nếu cho thuê theo giờ)'
    )

    # Capacity (F2: Số người tối đa)
    max_capacity = fields.Integer(
        string='Số người tối đa',
        required=True,
        default=2,
        help='Số lượng người tối đa có thể ở trong phòng'
    )

    # Amenities & Description (F2: Tiện nghi)
    amenities = fields.Html(
        string='Tiện nghi',
        help='Danh sách tiện nghi của loại phòng này. Ví dụ: TV, Minibar, Wifi, Điều hòa...'
    )

    description = fields.Text(
        string='Mô tả',
        translate=True,
        help='Mô tả chi tiết về loại phòng'
    )

    # Room Size
    room_size = fields.Float(
        string='Diện tích (m²)',
        help='Diện tích phòng'
    )

    # Bed Configuration
    bed_type = fields.Selection([
        ('single', 'Giường đơn'),
        ('double', 'Giường đôi'),
        ('twin', 'Hai giường đơn'),
        ('queen', 'Giường Queen'),
        ('king', 'Giường King'),
    ], string='Loại giường')

    # Relations
    room_ids = fields.One2many(
        'hotel.room',
        'room_type_id',
        string='Các phòng',
        help='Danh sách phòng thuộc loại này'
    )

    # Computed Fields
    room_count = fields.Integer(
        string='Số lượng phòng',
        compute='_compute_room_count',
        store=True
    )

    available_room_count = fields.Integer(
        string='Phòng trống',
        compute='_compute_available_room_count'
    )

    # Company (Multi-company support)
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    # Constraints
    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)', 'Mã loại phòng phải là duy nhất trong công ty!'),
        ('base_price_positive', 'check(base_price >= 0)', 'Giá cơ bản phải lớn hơn hoặc bằng 0!'),
        ('hourly_price_positive', 'check(hourly_price >= 0)', 'Giá theo giờ phải lớn hơn hoặc bằng 0!'),
        ('max_capacity_positive', 'check(max_capacity > 0)', 'Số người tối đa phải lớn hơn 0!'),
    ]

    # Computed Methods
    @api.depends('room_ids')
    def _compute_room_count(self):
        """Tính tổng số phòng thuộc loại này"""
        for record in self:
            record.room_count = len(record.room_ids)

    def _compute_available_room_count(self):
        """Tính số phòng trống hiện tại (F3: Tra cứu phòng trống)"""
        for record in self:
            record.available_room_count = self.env['hotel.room'].search_count([
                ('room_type_id', '=', record.id),
                ('state', '=', 'available')
            ])

    # Validation Methods
    @api.constrains('max_capacity', 'room_size')
    def _check_capacity_and_size(self):
        """Kiểm tra số người tối đa hợp lý với diện tích phòng"""
        for record in self:
            if record.room_size and record.max_capacity:
                # Mỗi người cần ít nhất 5m² (có thể điều chỉnh theo quy định)
                min_size_per_person = 5
                if record.room_size < (record.max_capacity * min_size_per_person):
                    raise ValidationError(
                        f'Diện tích phòng {record.room_size}m² quá nhỏ cho {record.max_capacity} người. '
                        f'Khuyến nghị tối thiểu {record.max_capacity * min_size_per_person}m²!'
                    )

    # CRUD Override Methods
    @api.model
    def create(self, vals):
        """Override create để tự động tạo code nếu chưa có"""
        if not vals.get('code'):
            # Tự động tạo code từ name
            vals['code'] = vals.get('name', '').upper()[:3]
        return super(HotelRoomType, self).create(vals)

    def write(self, vals):
        """Override write để kiểm tra khi thay đổi giá"""
        # Nếu thay đổi giá, có thể cần cảnh báo
        if 'base_price' in vals or 'hourly_price' in vals:
            # Log hoặc notify về thay đổi giá
            pass
        return super(HotelRoomType, self).write(vals)

    def unlink(self):
        """Override unlink để kiểm tra trước khi xóa"""
        for record in self:
            if record.room_ids:
                raise ValidationError(
                    f'Không thể xóa loại phòng "{record.name}" vì vẫn còn {record.room_count} phòng thuộc loại này! '
                    'Vui lòng xóa hoặc chuyển các phòng sang loại khác trước.'
                )
        return super(HotelRoomType, self).unlink()

    # Business Methods
    def action_view_rooms(self):
        """Action để xem danh sách phòng thuộc loại này"""
        self.ensure_one()
        return {
            'name': f'Phòng {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'view_mode': 'tree,form,kanban',
            'domain': [('room_type_id', '=', self.id)],
            'context': {'default_room_type_id': self.id}
        }

    def get_available_rooms(self, checkin_date=None, checkout_date=None):
        """Lấy danh sách phòng trống theo loại phòng này (F3: Tra cứu phòng trống)

        Args:
            checkin_date: Ngày checkin (datetime)
            checkout_date: Ngày checkout (datetime)

        Returns:
            recordset: Danh sách phòng trống
        """
        self.ensure_one()
        domain = [
            ('room_type_id', '=', self.id),
            ('state', '=', 'available')
        ]

        if checkin_date and checkout_date:
            # TODO: Kiểm tra phòng không có booking trùng ngày
            # Sẽ implement sau khi có model reservation
            pass

        return self.env['hotel.room'].search(domain)
