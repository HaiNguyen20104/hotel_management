# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HotelRoom(models.Model):
    """Model quản lý phòng khách sạn (F1: Quản lý phòng)

    Quản lý thông tin chi tiết từng phòng trong khách sạn,
    bao gồm trạng thái, giá cả, và khả năng đặt phòng.
    """
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _order = 'floor, room_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information (F1: Thông tin phòng)
    name = fields.Char(
        string='Tên phòng',
        required=True,
        tracking=True,
        help='Tên hiển thị của phòng'
    )

    code = fields.Char(
        string='Mã phòng',
        required=True,
        copy=False,
        tracking=True,
        help='Mã định danh duy nhất cho phòng. Ví dụ: R101, R201'
    )

    room_number = fields.Char(
        string='Số phòng',
        required=True,
        tracking=True,
        help='Số phòng hiển thị cho khách. Ví dụ: 101, 201, A01'
    )

    # Room Type (F1: Loại phòng)
    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Loại phòng',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Loại phòng (Standard, Deluxe, VIP...)'
    )

    # Floor (F1: Tầng)
    floor = fields.Integer(
        string='Tầng',
        required=True,
        default=1,
        tracking=True,
        help='Số tầng của phòng'
    )

    # Capacity (F1: Số người)
    capacity = fields.Integer(
        string='Số người',
        compute='_compute_capacity',
        store=True,
        help='Số người tối đa (lấy từ loại phòng, có thể override)'
    )

    capacity_override = fields.Integer(
        string='Override số người',
        help='Ghi đè số người tối đa cho phòng này (nếu khác với loại phòng)'
    )

    # Pricing (F1: Giá thuê theo ngày/giờ)
    daily_price = fields.Float(
        string='Giá theo ngày',
        compute='_compute_daily_price',
        store=True,
        digits='Product Price',
        tracking=True,
        help='Giá thuê theo ngày (lấy từ loại phòng, có thể override)'
    )

    daily_price_override = fields.Float(
        string='Override giá ngày',
        digits='Product Price',
        help='Ghi đè giá thuê theo ngày cho phòng này'
    )

    hourly_price = fields.Float(
        string='Giá theo giờ',
        compute='_compute_hourly_price',
        store=True,
        digits='Product Price',
        help='Giá thuê theo giờ (lấy từ loại phòng, có thể override)'
    )

    hourly_price_override = fields.Float(
        string='Override giá giờ',
        digits='Product Price',
        help='Ghi đè giá thuê theo giờ cho phòng này'
    )

    # State (F1: Trạng thái phòng)
    state = fields.Selection([
        ('available', 'Phòng trống'),
        ('reserved', 'Đã đặt'),
        ('occupied', 'Đang sử dụng'),
        ('maintenance', 'Bảo trì'),
        ('cleaning', 'Đang dọn dẹp'),
    ], string='Trạng thái',
        default='available',
        required=True,
        tracking=True,
        help='Trạng thái hiện tại của phòng'
    )

    # Description & Notes (F1: Mô tả, ghi chú)
    description = fields.Text(
        string='Mô tả',
        help='Mô tả chi tiết về phòng'
    )

    notes = fields.Text(
        string='Ghi chú',
        tracking=True,
        help='Ghi chú nội bộ về phòng'
    )

    # Location Details
    building = fields.Char(
        string='Tòa nhà',
        help='Tên tòa nhà (nếu khách sạn có nhiều tòa)'
    )

    view_type = fields.Selection([
        ('sea', 'Hướng biển'),
        ('mountain', 'Hướng núi'),
        ('city', 'Hướng thành phố'),
        ('garden', 'Hướng vườn'),
        ('pool', 'Hướng hồ bơi'),
        ('inside', 'Trong khuôn viên'),
    ], string='Hướng nhìn')

    # Status
    active = fields.Boolean(
        string='Hoạt động',
        default=True,
        help='Bỏ tích để ẩn phòng này khỏi hệ thống'
    )

    # Relations
    reservation_ids = fields.One2many(
        'hotel.reservation',
        'room_id',
        string='Các đặt phòng',
        help='Lịch sử đặt phòng'
    )

    rental_ids = fields.One2many(
        'hotel.rental',
        'room_id',
        string='Các lần thuê',
        help='Lịch sử thuê phòng'
    )

    # Current Rental (F4: Checkin/Checkout)
    current_rental_id = fields.Many2one(
        'hotel.rental',
        string='Đang thuê',
        compute='_compute_current_rental',
        help='Thông tin thuê phòng hiện tại'
    )

    current_guest_id = fields.Many2one(
        'res.partner',
        string='Khách hiện tại',
        compute='_compute_current_rental',
        help='Khách đang ở phòng'
    )

    # Computed Fields
    is_available = fields.Boolean(
        string='Khả dụng',
        compute='_compute_is_available',
        search='_search_is_available',
        help='Phòng có sẵn để đặt không'
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    # Constraints
    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)',
         'Mã phòng phải là duy nhất!'),
        ('room_number_unique', 'unique(room_number, floor, building, company_id)',
         'Số phòng đã tồn tại trên tầng này!'),
        ('floor_positive', 'check(floor > 0)',
         'Số tầng phải lớn hơn 0!'),
    ]

    # Computed Methods
    @api.depends('room_type_id.max_capacity', 'capacity_override')
    def _compute_capacity(self):
        """Tính số người tối đa (lấy từ room_type hoặc override)"""
        for record in self:
            if record.capacity_override:
                record.capacity = record.capacity_override
            else:
                record.capacity = record.room_type_id.max_capacity if record.room_type_id else 2

    @api.depends('room_type_id.base_price', 'daily_price_override')
    def _compute_daily_price(self):
        """Tính giá theo ngày (lấy từ room_type hoặc override)"""
        for record in self:
            if record.daily_price_override:
                record.daily_price = record.daily_price_override
            else:
                record.daily_price = record.room_type_id.base_price if record.room_type_id else 0.0

    @api.depends('room_type_id.hourly_price', 'hourly_price_override')
    def _compute_hourly_price(self):
        """Tính giá theo giờ (lấy từ room_type hoặc override)"""
        for record in self:
            if record.hourly_price_override:
                record.hourly_price = record.hourly_price_override
            else:
                record.hourly_price = record.room_type_id.hourly_price if record.room_type_id else 0.0

    def _compute_current_rental(self):
        """Tìm thông tin thuê phòng hiện tại"""
        for record in self:
            current_rental = self.env['hotel.rental'].search([
                ('room_id', '=', record.id),
                ('state', '=', 'ongoing')
            ], limit=1)

            record.current_rental_id = current_rental
            record.current_guest_id = current_rental.guest_id if current_rental else False

    @api.depends('state')
    def _compute_is_available(self):
        """Kiểm tra phòng có khả dụng không (F3: Tra cứu phòng trống)"""
        for record in self:
            record.is_available = record.state == 'available'

    def _search_is_available(self, operator, value):
        """Search domain cho is_available field"""
        if operator == '=' and value:
            return [('state', '=', 'available')]
        elif operator == '=' and not value:
            return [('state', '!=', 'available')]
        return []

    # Validation Methods
    @api.constrains('capacity_override', 'room_type_id')
    def _check_capacity_override(self):
        """Kiểm tra capacity_override không vượt quá giới hạn"""
        for record in self:
            if record.capacity_override:
                max_allowed = record.room_type_id.max_capacity * 1.5  # Cho phép tối đa 150%
                if record.capacity_override > max_allowed:
                    raise ValidationError(
                        f'Số người override ({record.capacity_override}) vượt quá giới hạn '
                        f'cho phép ({int(max_allowed)})!'
                    )

    # CRUD Override
    @api.model
    def create(self, vals):
        """Override create để tự động tạo code và name"""
        if not vals.get('code'):
            # Tự động tạo code: R + floor + room_number
            floor = vals.get('floor', 1)
            room_number = vals.get('room_number', '000')
            vals['code'] = f"R{floor}{room_number}"

        if not vals.get('name'):
            # Tự động tạo name
            vals['name'] = f"Phòng {vals.get('room_number', '')}"

        return super(HotelRoom, self).create(vals)

    def write(self, vals):
        """Override write để kiểm tra trạng thái trước khi cập nhật"""
        # Không cho phép thay đổi một số field khi phòng đang occupied
        if 'room_type_id' in vals or 'room_number' in vals:
            for record in self:
                if record.state == 'occupied':
                    raise UserError(
                        'Không thể thay đổi loại phòng hoặc số phòng '
                        'khi phòng đang được sử dụng!'
                    )

        return super(HotelRoom, self).write(vals)

    def unlink(self):
        """Override unlink để kiểm tra trước khi xóa"""
        for record in self:
            if record.state == 'occupied':
                raise UserError(
                    f'Không thể xóa phòng "{record.name}" đang được sử dụng!'
                )

            if record.reservation_ids or record.rental_ids:
                raise UserError(
                    f'Không thể xóa phòng "{record.name}" vì có lịch sử đặt phòng/thuê phòng! '
                    'Vui lòng archive thay vì xóa.'
                )

        return super(HotelRoom, self).unlink()

    # Business Methods (F1: CRUD phòng)
    def action_set_available(self):
        """Đặt phòng về trạng thái Available"""
        for record in self:
            if record.state == 'occupied' and record.current_rental_id:
                raise UserError('Phòng đang được sử dụng! Vui lòng checkout trước.')
            record.state = 'available'

    def action_set_maintenance(self):
        """Đặt phòng vào trạng thái Maintenance"""
        for record in self:
            if record.state == 'occupied':
                raise UserError('Không thể bảo trì phòng đang có khách!')
            record.state = 'maintenance'

    def action_set_cleaning(self):
        """Đặt phòng vào trạng thái Cleaning"""
        self.write({'state': 'cleaning'})

    def action_view_reservations(self):
        """Xem lịch sử đặt phòng"""
        self.ensure_one()
        return {
            'name': f'Đặt phòng - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form,calendar',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id}
        }

    def action_view_rentals(self):
        """Xem lịch sử thuê phòng"""
        self.ensure_one()
        return {
            'name': f'Lịch sử thuê - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.rental',
            'view_mode': 'tree,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id}
        }

    # F3: Tra cứu phòng trống
    @api.model
    def search_available_rooms(self, checkin_date, checkout_date, room_type_id=None,
                              min_capacity=None, max_price=None):
        """Tìm phòng trống theo điều kiện (F3: Tra cứu phòng trống)

        Args:
            checkin_date (datetime): Ngày checkin
            checkout_date (datetime): Ngày checkout
            room_type_id (int): ID loại phòng (optional)
            min_capacity (int): Số người tối thiểu (optional)
            max_price (float): Giá tối đa (optional)

        Returns:
            recordset: Danh sách phòng trống
        """
        domain = [('state', '=', 'available')]

        if room_type_id:
            domain.append(('room_type_id', '=', room_type_id))

        if min_capacity:
            domain.append(('capacity', '>=', min_capacity))

        if max_price:
            domain.append(('daily_price', '<=', max_price))

        available_rooms = self.search(domain)

        # Lọc phòng không có conflict với reservation/rental
        if checkin_date and checkout_date:
            conflicting_rooms = self.env['hotel.reservation'].search([
                ('checkin_date', '<', checkout_date),
                ('checkout_date', '>', checkin_date),
                ('state', 'in', ['confirmed', 'checked_in'])
            ]).mapped('room_id')

            available_rooms = available_rooms - conflicting_rooms

        return available_rooms

    def check_availability(self, checkin_date, checkout_date):
        """Kiểm tra phòng có trống trong khoảng thời gian không

        Args:
            checkin_date (datetime): Ngày checkin
            checkout_date (datetime): Ngày checkout

        Returns:
            bool: True nếu phòng trống
        """
        self.ensure_one()

        if self.state != 'available':
            return False

        # Kiểm tra conflict với reservation
        conflict = self.env['hotel.reservation'].search([
            ('room_id', '=', self.id),
            ('checkin_date', '<', checkout_date),
            ('checkout_date', '>', checkin_date),
            ('state', 'in', ['confirmed', 'checked_in'])
        ], limit=1)

        return not conflict

    def get_availability_calendar(self, month, year):
        """Lấy lịch trống của phòng theo tháng (F3: Xem lịch trống)

        Args:
            month (int): Tháng (1-12)
            year (int): Năm

        Returns:
            dict: Calendar data
        """
        self.ensure_one()
        # TODO: Implement calendar view logic
        return {
            'room_id': self.id,
            'room_name': self.name,
            'month': month,
            'year': year,
            'availability': []
        }
