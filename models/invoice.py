# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HotelInvoice(models.Model):
    """Model quản lý hóa đơn thanh toán (F7: Quản lý hóa đơn)"""
    _name = 'hotel.invoice'
    _description = 'Hotel Invoice'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã hóa đơn', required=True, copy=False, readonly=True, default='New', tracking=True)
    rental_id = fields.Many2one('hotel.rental', string='Thuê phòng', required=True, ondelete='restrict', tracking=True)
    guest_id = fields.Many2one('res.partner', related='rental_id.guest_id', string='Khách hàng', store=True, readonly=True)
    room_id = fields.Many2one('hotel.room', related='rental_id.room_id', string='Phòng', store=True, readonly=True)
    date = fields.Date(string='Ngày hóa đơn', required=True, default=fields.Date.today, tracking=True)

    unit_price = fields.Float(string='Đơn giá', digits='Product Price', required=True, tracking=True)
    quantity = fields.Float(string='Số lượng', default=1.0, required=True)
    subtotal = fields.Float(string='Tiền phòng', compute='_compute_amounts', store=True, digits='Product Price')

    surcharge_electricity = fields.Float(string='Tiền điện', digits='Product Price')
    surcharge_water = fields.Float(string='Tiền nước', digits='Product Price')
    surcharge_service = fields.Float(string='Phí dịch vụ', digits='Product Price')
    surcharge_minibar = fields.Float(string='Tiền minibar', digits='Product Price')
    surcharge_laundry =fields.Float(string='Giặt là', digits='Product Price')
    surcharge_breakfast = fields.Float(string='Ăn sáng', digits='Product Price')
    surcharge_other = fields.Float(string='Phụ thu khác', digits='Product Price')
    surcharge_total = fields.Float(string='Tổng phụ thu', compute='_compute_amounts', store=True, digits='Product Price')

    deposit_amount = fields.Float(string='Tiền cọc', digits='Product Price')
    late_checkout_hours = fields.Float(string='Giờ checkout trễ')
    late_checkout_surcharge = fields.Float(string='Phụ thu checkout trễ', digits='Product Price')

    discount_percent = fields.Float(string='Giảm giá', digits='Discount')
    discount_amount = fields.Float(string='Tiền giảm', compute='_compute_amounts', store=True, digits='Product Price')

    amount_untaxed = fields.Float(string='Tổng chưa thuế', compute='_compute_amounts', store=True, digits='Product Price')
    tax_percent = fields.Float(string='Thuế', default=0.0, digits='Discount')
    tax_amount = fields.Float(string='Tiền thuế', compute='_compute_amounts', store=True, digits='Product Price')
    total_amount = fields.Float(string='Tổng tiền', compute='_compute_amounts', store=True, digits='Product Price')
    amount_to_pay = fields.Float(string='Còn phải trả', compute='_compute_amounts', store=True, digits='Product Price')

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('paid', 'Đã thanh toán'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái TT', default='draft', required=True, tracking=True)

    payment_method = fields.Selection([
        ('cash', 'Tiền mặt'),
        ('bank_transfer', 'Chuyển khoản'),
        ('credit_card', 'Thẻ tín dụng'),
        ('debit_card', 'Thẻ ghi nợ'),
        ('e_wallet', 'Ví điện tử'),
        ('other', 'Khác'),
    ], string='Phương thức thanh toán', tracking=True)

    payment_reference = fields.Char(string='Mã tham chiếu')
    payment_date = fields.Datetime(string='Ngày thanh toán', readonly=True)
    payment_notes = fields.Text(string='Ghi chú thanh toán')

    notes = fields.Text(string='Ghi chú')
    internal_notes = fields.Text(string='Ghi chú nội bộ')

    invoice_date = fields.Datetime(string='Ngày tạo HĐ', default=fields.Datetime.now, readonly=True)
    confirmed_date = fields.Datetime(string='Ngày xác nhận', readonly=True)
    cancelled_date = fields.Datetime(string='Ngày hủy', readonly=True)

    user_id = fields.Many2one('res.users', string='Người tạo', default=lambda self: self.env.user, readonly=True)
    confirmed_by = fields.Many2one('res.users', string='Người xác nhận', readonly=True)
    cashier_id = fields.Many2one('res.users', string='Thu ngân', readonly=True)

    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    is_paid = fields.Boolean(string='Đã thanh toán', compute='_compute_is_paid', store=True)

    _sql_constraints = [
        ('unit_price_positive', 'check(unit_price >= 0)', 'Đơn giá không được âm!'),
        ('quantity_positive', 'check(quantity > 0)', 'Số lượng phải lớn hơn 0!'),
        ('deposit_positive', 'check(deposit_amount >= 0)', 'Tiền cọc không được âm!'),
        ('discount_valid', 'check(discount_percent >= 0 AND discount_percent <= 100)', 'Giảm giá phải từ 0-100%!'),
        ('tax_valid', 'check(tax_percent >= 0 AND tax_percent <= 100)', 'Thuế phải từ 0-100%!'),
    ]

    @api.depends('unit_price', 'quantity', 'surcharge_electricity', 'surcharge_water',
                 'surcharge_service', 'surcharge_minibar', 'surcharge_laundry', 'surcharge_breakfast',
                 'surcharge_other', 'late_checkout_surcharge', 'deposit_amount',
                 'discount_percent', 'tax_percent')
    def _compute_amounts(self):
        for record in self:
            record.subtotal = record.unit_price * record.quantity
            record.surcharge_total = (
                record.surcharge_electricity + record.surcharge_water +
                record.surcharge_service + record.surcharge_minibar +
                record.surcharge_laundry + record.surcharge_breakfast +
                record.surcharge_other + record.late_checkout_surcharge
            )
            subtotal_with_surcharge = record.subtotal + record.surcharge_total
            record.discount_amount = subtotal_with_surcharge * (record.discount_percent / 100.0)
            record.amount_untaxed = subtotal_with_surcharge - record.discount_amount
            record.tax_amount = record.amount_untaxed * (record.tax_percent / 100.0)
            record.total_amount = record.amount_untaxed + record.tax_amount
            record.amount_to_pay = record.total_amount - record.deposit_amount

    @api.depends('state')
    def _compute_is_paid(self):
        for record in self:
            record.is_paid = record.state == 'paid'

    @api.onchange('rental_id')
    def _onchange_rental_id(self):
        if self.rental_id:
            self.unit_price = self.rental_id.room_id.daily_price
            self.quantity = self.rental_id.duration_days or 1.0
            if self.rental_id.is_late_checkout and self.rental_id.extra_hours > 0:
                self.late_checkout_hours = self.rental_id.extra_hours
                hourly_rate = self.rental_id.room_id.hourly_price or (self.unit_price / 24.0)
                self.late_checkout_surcharge = hourly_rate * self.late_checkout_hours
            if self.rental_id.reservation_id:
                self.deposit_amount = self.rental_id.reservation_id.deposit

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.invoice') or 'New'
        return super(HotelInvoice, self).create(vals)

    def write(self, vals):
        if any(rec.state == 'paid' for rec in self):
            protected_fields = ['rental_id', 'unit_price', 'quantity']
            if any(field in vals for field in protected_fields):
                raise UserError('Không thể sửa thông tin cơ bản khi hóa đơn đã thanh toán!')
        return super(HotelInvoice, self).write(vals)

    def unlink(self):
        for record in self:
            if record.state == 'paid':
                raise UserError(f'Không thể xóa hóa đơn {record.name} đã thanh toán!')
        return super(HotelInvoice, self).unlink()

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('Chỉ có thể xác nhận hóa đơn ở trạng thái Nháp!')
            record.write({'state': 'confirmed', 'confirmed_date': fields.Datetime.now(), 'confirmed_by': self.env.user.id})

    def action_mark_paid(self):
        for record in self:
            if record.state == 'paid':
                raise UserError('Hóa đơn đã được thanh toán rồi!')
            if record.state == 'cancelled':
                raise UserError('Không thể thanh toán hóa đơn đã hủy!')
            record.write({'state': 'paid', 'payment_date': fields.Datetime.now(), 'cashier_id': self.env.user.id})

    def action_cancel(self):
        for record in self:
            if record.state == 'paid':
                raise UserError('Không thể hủy hóa đơn đã thanh toán!')
            record.write({'state': 'cancelled', 'cancelled_date': fields.Datetime.now()})

    def action_set_draft(self):
        for record in self:
            if record.state == 'paid':
                raise UserError('Không thể đưa về nháp hóa đơn đã thanh toán!')
            record.state = 'draft'

    def action_print_invoice(self):
        self.ensure_one()
        if self.state == 'draft':
            raise UserError('Vui lòng xác nhận hóa đơn trước khi in!')
        return self.env.ref('hotel_management.action_report_hotel_invoice').report_action(self)

    @api.model
    def get_revenue_by_period(self, date_from, date_to):
        invoices = self.search([('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'paid')])
        return sum(invoices.mapped('total_amount'))

    @api.model
    def get_revenue_by_room(self, room_id, date_from=None, date_to=None):
        domain = [('room_id', '=', room_id), ('state', '=', 'paid')]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        invoices = self.search(domain)
        return sum(invoices.mapped('total_amount'))