# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import re


class HotelUser(models.Model):
    """
    Model quản lý người dùng khách sạn - Extends res.partner
    (F5: Quản lý khách hàng, F6: Quản lý nhân viên)
    """
    _inherit = 'res.partner'

    # Hotel-specific fields
    hotel_code = fields.Char(
        string='Mã KS',
        copy=False,
        readonly=True,
        help='Mã khách hàng/nhân viên trong hệ thống khách sạn'
    )

    identity_card = fields.Char(
        string='CCCD/CMND',
        tracking=True,
        help='Căn cước công dân hoặc chứng minh nhân dân'
    )

    nationality = fields.Many2one(
        'res.country',
        string='Quốc tịch',
        default=lambda self: self.env.ref('base.vn', raise_if_not_found=False),
        tracking=True
    )

    birth_date = fields.Date(
        string='Ngày sinh',
        tracking=True
    )

    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác'),
    ], string='Giới tính')

    # Hotel role
    is_hotel_customer = fields.Boolean(
        string='Là khách hàng KS',
        default=False,
        help='Đánh dấu partner này là khách hàng khách sạn'
    )

    is_hotel_employee = fields.Boolean(
        string='Là nhân viên KS',
        default=False,
        help='Đánh dấu partner này là nhân viên khách sạn'
    )

    # Employee-specific fields (F6)
    employee_position = fields.Selection([
        ('receptionist', 'Lễ tân'),
        ('manager', 'Quản lý'),
        ('staff', 'Nhân viên'),
        ('admin', 'Quản trị viên'),
        ('housekeeping', 'Buồng phòng'),
        ('maintenance', 'Bảo trì'),
    ], string='Chức vụ', tracking=True)

    employee_state = fields.Selection([
        ('active', 'Đang làm việc'),
        ('on_leave', 'Nghỉ phép'),
        ('inactive', 'Ngừng làm việc'),
    ], string='Trạng thái NV', default='active', tracking=True)

    hire_date = fields.Date(
        string='Ngày vào làm',
        tracking=True
    )

    system_user_id = fields.Many2one(
        'res.users',
        string='Tài khoản hệ thống',
        help='Liên kết với tài khoản đăng nhập Odoo (cho nhân viên)',
        tracking=True
    )

    # Relations - History (F5: Xem lịch sử thuê)
    reservation_ids = fields.One2many(
        'hotel.reservation',
        'guest_id',
        string='Lịch sử đặt phòng'
    )

    reservation_count = fields.Integer(
        string='Số lần đặt',
        compute='_compute_hotel_statistics',
        store=True
    )

    rental_ids = fields.One2many(
        'hotel.rental',
        'guest_id',
        string='Lịch sử thuê'
    )

    rental_count = fields.Integer(
        string='Số lần thuê',
        compute='_compute_hotel_statistics',
        store=True
    )

    invoice_ids = fields.One2many(
        'hotel.invoice',
        'customer_id',
        string='Hóa đơn'
    )

    invoice_count = fields.Integer(
        string='Số hóa đơn',
        compute='_compute_hotel_statistics',
        store=True
    )

    # Customer statistics
    total_spent = fields.Float(
        string='Tổng chi tiêu',
        compute='_compute_total_spent',
        store=True,
        digits='Product Price',
        help='Tổng tiền đã chi tiêu tại khách sạn'
    )

    is_vip_customer = fields.Boolean(
        string='Khách VIP',
        compute='_compute_is_vip_customer',
        store=True,
        help='Khách VIP: Tổng chi tiêu > 10M hoặc đặt > 5 lần'
    )

    age = fields.Integer(
        string='Tuổi',
        compute='_compute_age'
    )

    hotel_notes = fields.Text(
        string='Ghi chú KS',
        help='Ghi chú riêng cho khách sạn'
    )

    _sql_constraints = [
        ('identity_card_unique', 'unique(identity_card)', 'Số CCCD/CMND đã tồn tại trong hệ thống!'),
    ]

    @api.depends('reservation_ids', 'rental_ids', 'invoice_ids')
    def _compute_hotel_statistics(self):
        for record in self:
            record.reservation_count = len(record.reservation_ids)
            record.rental_count = len(record.rental_ids)
            record.invoice_count = len(record.invoice_ids)

    @api.depends('invoice_ids', 'invoice_ids.total_amount', 'invoice_ids.state')
    def _compute_total_spent(self):
        for record in self:
            paid_invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'paid')
            record.total_spent = sum(paid_invoices.mapped('total_amount'))

    @api.depends('total_spent', 'reservation_count')
    def _compute_is_vip_customer(self):
        """Khách VIP: Tổng chi tiêu > 10M hoặc đặt > 5 lần"""
        for record in self:
            if record.is_hotel_customer:
                record.is_vip_customer = (record.total_spent > 10000000 or record.reservation_count > 5)
            else:
                record.is_vip_customer = False

    @api.depends('birth_date')
    def _compute_age(self):
        today = fields.Date.today()
        for record in self:
            if record.birth_date:
                record.age = today.year - record.birth_date.year - (
                    (today.month, today.day) < (record.birth_date.month, record.birth_date.day)
                )
            else:
                record.age = 0

    @api.constrains('identity_card')
    def _check_identity_card_format(self):
        """Validate identity card format (CMND: 9 số, CCCD: 12 số)"""
        for record in self:
            if record.identity_card:
                clean_id = record.identity_card.replace(' ', '').replace('-', '')
                if not clean_id.isdigit():
                    raise ValidationError('CCCD/CMND chỉ được chứa chữ số!')
                if len(clean_id) not in [9, 12]:
                    raise ValidationError('CCCD/CMND không hợp lệ: CMND có 9 số, CCCD có 12 số!')

    @api.constrains('is_hotel_employee', 'employee_position')
    def _check_employee_position(self):
        """Employee must have position"""
        for record in self:
            if record.is_hotel_employee and not record.employee_position:
                raise ValidationError('Nhân viên phải có chức vụ!')

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """Check valid birth date"""
        today = fields.Date.today()
        for record in self:
            if record.birth_date:
                if record.birth_date > today:
                    raise ValidationError('Ngày sinh không thể là tương lai!')

                age = today.year - record.birth_date.year
                if age < 0 or age > 150:
                    raise ValidationError('Ngày sinh không hợp lệ!')

                if record.is_hotel_employee and age < 18:
                    raise ValidationError('Nhân viên phải từ 18 tuổi trở lên!')

    @api.constrains('phone')
    def _check_phone_format(self):
        """Validate phone format (Vietnam phone number)"""
        phone_regex = r'^(0|\+84)[0-9]{9,10}$'
        for record in self:
            if record.phone:
                clean_phone = record.phone.replace(' ', '').replace('-', '').replace('.', '')
                if not re.match(phone_regex, clean_phone):
                    raise ValidationError(
                        f'Số điện thoại không hợp lệ: {record.phone}. '
                        'Vui lòng nhập số điện thoại Việt Nam (VD: 0901234567 hoặc +84901234567)'
                    )

    @api.onchange('is_hotel_customer')
    def _onchange_is_hotel_customer(self):
        """Auto-generate customer code"""
        if self.is_hotel_customer and not self.hotel_code:
            self.hotel_code = 'Sẽ tự động tạo khi lưu'

    @api.onchange('is_hotel_employee')
    def _onchange_is_hotel_employee(self):
        """Set default employee state and generate code"""
        if self.is_hotel_employee:
            if not self.employee_state:
                self.employee_state = 'active'
            if not self.hotel_code:
                self.hotel_code = 'Sẽ tự động tạo khi lưu'
        else:
            self.employee_position = False
            self.employee_state = False
            self.hire_date = False

    @api.onchange('system_user_id')
    def _onchange_system_user_id(self):
        """Auto-fill info from res.users"""
        if self.system_user_id:
            if not self.email:
                self.email = self.system_user_id.email
            if not self.phone:
                self.phone = self.system_user_id.phone

    @api.model
    def create(self, vals):
        """Auto-generate hotel_code based on role"""
        if vals.get('is_hotel_customer') or vals.get('is_hotel_employee'):
            if not vals.get('hotel_code'):
                if vals.get('is_hotel_employee'):
                    vals['hotel_code'] = self.env['ir.sequence'].next_by_code('hotel.user.employee') or 'NV001'
                else:
                    vals['hotel_code'] = self.env['ir.sequence'].next_by_code('hotel.user.customer') or 'KH001'

        return super(HotelUser, self).create(vals)

    def write(self, vals):
        """Prevent changing critical info for users with history"""
        for record in self:
            if record.reservation_count > 0 or record.rental_count > 0:
                if 'identity_card' in vals and vals['identity_card'] != record.identity_card:
                    raise UserError('Không thể thay đổi CCCD khi đã có lịch sử giao dịch!')

        return super(HotelUser, self).write(vals)

    def unlink(self):
        """Prevent deleting partners with hotel history"""
        for record in self:
            if record.is_hotel_customer or record.is_hotel_employee:
                if record.reservation_count > 0 or record.rental_count > 0 or record.invoice_count > 0:
                    raise UserError(
                        f'Không thể xóa {record.name} vì đã có lịch sử giao dịch! '
                        'Hãy bỏ check "Là khách hàng KS" hoặc set "Inactive" thay vì xóa.'
                    )
        return super(HotelUser, self).unlink()

    # Actions (F5, F6)
    def action_view_reservations(self):
        """View reservation history (F5: Xem lịch sử thuê)"""
        self.ensure_one()
        return {
            'name': _('Lịch sử đặt phòng - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form',
            'domain': [('guest_id', '=', self.id)],
            'context': {'default_guest_id': self.id},
            'target': 'current',
        }

    def action_view_rentals(self):
        """View rental history (F5: Xem lịch sử thuê)"""
        self.ensure_one()
        return {
            'name': _('Lịch sử thuê phòng - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.rental',
            'view_mode': 'tree,form',
            'domain': [('guest_id', '=', self.id)],
            'context': {'default_guest_id': self.id},
            'target': 'current',
        }

    def action_view_invoices(self):
        """View invoice history (F5)"""
        self.ensure_one()
        return {
            'name': _('Hóa đơn - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.invoice',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
            'target': 'current',
        }

    def action_create_reservation(self):
        """Quick create reservation for customer"""
        self.ensure_one()
        if not self.is_hotel_customer:
            raise UserError('Chỉ có thể tạo reservation cho khách hàng!')

        return {
            'name': _('Tạo đặt phòng cho %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'form',
            'context': {'default_guest_id': self.id},
            'target': 'current',
        }

    def action_set_hotel_customer(self):
        """Set as hotel customer (F5: CRUD khách hàng)"""
        for record in self:
            if not record.is_hotel_customer:
                vals = {'is_hotel_customer': True}
                if not record.hotel_code:
                    vals['hotel_code'] = self.env['ir.sequence'].next_by_code('hotel.user.customer') or 'KH001'
                record.write(vals)

    def action_set_hotel_employee(self):
        """Set as hotel employee (F6: CRUD nhân viên)"""
        for record in self:
            if not record.is_hotel_employee:
                vals = {
                    'is_hotel_employee': True,
                    'employee_state': 'active'
                }
                if not record.hotel_code:
                    vals['hotel_code'] = self.env['ir.sequence'].next_by_code('hotel.user.employee') or 'NV001'
                record.write(vals)

    def action_create_user_account(self):
        """Create Odoo user account for employee (F6: Gán tài khoản)"""
        self.ensure_one()

        if not self.is_hotel_employee:
            raise UserError('Chỉ có thể tạo tài khoản cho nhân viên!')

        if self.system_user_id:
            raise UserError('Nhân viên này đã có tài khoản hệ thống!')

        if not self.email:
            raise UserError('Vui lòng nhập email trước khi tạo tài khoản!')

        # Create user account
        user_vals = {
            'name': self.name,
            'login': self.email,
            'email': self.email,
            'partner_id': self.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        }

        new_user = self.env['res.users'].create(user_vals)
        self.system_user_id = new_user.id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': f'Đã tạo tài khoản cho {self.name} với login: {self.email}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_assign_role(self):
        """Assign role/permission to employee (F6: Phân quyền, Gán vai trò)"""
        self.ensure_one()

        if not self.is_hotel_employee:
            raise UserError('Chỉ có thể phân quyền cho nhân viên!')

        return {
            'name': _('Phân quyền - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.assign.role.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_current_position': self.employee_position,
            }
        }

    # Search methods (F5: Tra cứu khách hàng)
    @api.model
    def search_hotel_customers(self, keyword):
        """Search customers by name, phone, email, code, identity_card"""
        domain = [
            ('is_hotel_customer', '=', True),
            '|', '|', '|', '|',
            ('name', 'ilike', keyword),
            ('phone', 'ilike', keyword),
            ('email', 'ilike', keyword),
            ('hotel_code', 'ilike', keyword),
            ('identity_card', 'ilike', keyword),
        ]
        return self.search(domain)

    @api.model
    def search_hotel_employees(self, keyword):
        """Search employees by name, phone, email, code (F6: Xem danh sách nhân viên)"""
        domain = [
            ('is_hotel_employee', '=', True),
            '|', '|', '|',
            ('name', 'ilike', keyword),
            ('phone', 'ilike', keyword),
            ('email', 'ilike', keyword),
            ('hotel_code', 'ilike', keyword),
        ]
        return self.search(domain)

    def name_get(self):
        """Custom display name with hotel_code"""
        result = []
        for record in self:
            name = record.name

            if record.hotel_code:
                name = f'[{record.hotel_code}] {name}'

            if record.phone and (record.is_hotel_customer or record.is_hotel_employee):
                name += f' - {record.phone}'

            result.append((record.id, name))

        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Enhanced search by name, hotel_code, phone, email, identity_card"""
        if domain is None:
            domain = []

        if name:
            domain += [
                '|', '|', '|', '|',
                ('name', operator, name),
                ('hotel_code', operator, name),
                ('phone', operator, name),
                ('email', operator, name),
                ('identity_card', operator, name),
            ]

        return self._search(domain, limit=limit, order=order)
