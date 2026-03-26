# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class HotelRental(models.Model):
    """Model quản lý thuê phòng thực tế (F4: Checkin/Checkout)"""
    _name = 'hotel.rental'
    _description = 'Hotel Rental'
    _order = 'checkin_datetime desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã thuê phòng', required=True, copy=False, readonly=True, default='New', tracking=True)
    reservation_id = fields.Many2one('hotel.reservation', string='Đặt phòng', ondelete='restrict')
    guest_id = fields.Many2one('res.partner', string='Khách hàng', required=True, tracking=True, domain=[('is_company', '=', False)])
    guest_phone = fields.Char(related='guest_id.phone', string='Số điện thoại', readonly=True)
    guest_email = fields.Char(related='guest_id.email', string='Email', readonly=True)

    room_id = fields.Many2one('hotel.room', string='Phòng', required=True, tracking=True, ondelete='restrict')
    room_type_id = fields.Many2one('hotel.room.type', related='room_id.room_type_id', string='Loại phòng', store=True, readonly=True)
    room_number = fields.Char(related='room_id.room_number', string='Số phòng', readonly=True)

    checkin_datetime = fields.Datetime(string='Checkin thực tế', required=True, tracking=True, default=fields.Datetime.now)
    checkout_datetime_expected = fields.Datetime(string='Checkout dự kiến', required=True, tracking=True)
    checkout_datetime_actual = fields.Datetime(string='Checkout thực tế', tracking=True)

    duration_hours = fields.Float(string='Số giờ thực tế', compute='_compute_duration', store=True)
    duration_days = fields.Float(string='Số ngày thực tế', compute='_compute_duration', store=True)

    guest_count_expected = fields.Integer(string='Số người dự kiến', default=1)
    guest_count_actual = fields.Integer(string='Số người thực tế', default=1, required=True, tracking=True)

    state = fields.Selection([
        ('ongoing', 'Đang diễn ra'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='ongoing', required=True, tracking=True)

    invoice_ids = fields.One2many('hotel.invoice', 'rental_id', string='Hóa đơn')
    invoice_count = fields.Integer(string='Số hóa đơn', compute='_compute_invoice_count')

    notes = fields.Text(string='Ghi chú')
    special_services = fields.Text(string='Dịch vụ sử dụng')

    completed_date = fields.Datetime(string='Ngày hoàn thành', readonly=True)

    user_id = fields.Many2one('res.users', string='Nhân viên checkin', default=lambda self: self.env.user, readonly=True)
    checkout_by = fields.Many2one('res.users', string='Nhân viên checkout', readonly=True)

    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)

    is_late_checkout = fields.Boolean(string='Checkout trễ', compute='_compute_is_late_checkout')
    extra_hours = fields.Float(string='Giờ vượt', compute='_compute_extra_hours')

    _sql_constraints = [
        ('guest_count_positive', 'check(guest_count_actual > 0)', 'Số người thực tế phải lớn hơn 0!'),
        ('checkin_before_checkout', 'check(checkout_datetime_expected > checkin_datetime)', 'Thời gian checkout dự kiến phải sau checkin!'),
    ]

    @api.depends('checkin_datetime', 'checkout_datetime_actual')
    def _compute_duration(self):
        for record in self:
            if record.checkin_datetime:
                end_time = record.checkout_datetime_actual or fields.Datetime.now()
                delta = end_time - record.checkin_datetime
                record.duration_hours = delta.total_seconds() / 3600.0
                record.duration_days = record.duration_hours / 24.0
            else:
                record.duration_hours = 0
                record.duration_days = 0

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.depends('checkout_datetime_actual', 'checkout_datetime_expected')
    def _compute_is_late_checkout(self):
        for record in self:
            if record.checkout_datetime_actual and record.checkout_datetime_expected:
                record.is_late_checkout = record.checkout_datetime_actual > record.checkout_datetime_expected
            else:
                record.is_late_checkout = False

    @api.depends('checkout_datetime_actual', 'checkout_datetime_expected')
    def _compute_extra_hours(self):
        for record in self:
            if record.checkout_datetime_actual and record.checkout_datetime_expected:
                if record.checkout_datetime_actual > record.checkout_datetime_expected:
                    delta = record.checkout_datetime_actual - record.checkout_datetime_expected
                    record.extra_hours = delta.total_seconds() / 3600.0
                else:
                    record.extra_hours = 0
            else:
                record.extra_hours = 0

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        if self.reservation_id:
            self.guest_id = self.reservation_id.guest_id
            self.room_id = self.reservation_id.room_id
            self.checkout_datetime_expected = self.reservation_id.checkout_date
            self.guest_count_expected = self.reservation_id.guest_count
            self.guest_count_actual = self.reservation_id.guest_count

    @api.constrains('guest_count_actual', 'room_id')
    def _check_guest_capacity(self):
        for record in self:
            if record.room_id and record.guest_count_actual:
                max_allowed = record.room_id.capacity * 1.5
                if record.guest_count_actual > max_allowed:
                    raise ValidationError(f'Số người thực tế ({record.guest_count_actual}) vượt quá giới hạn cho phép ({int(max_allowed)}) của phòng {record.room_id.name}!')

    @api.constrains('checkout_datetime_actual', 'checkin_datetime')
    def _check_checkout_after_checkin(self):
        for record in self:
            if record.checkout_datetime_actual and record.checkin_datetime:
                if record.checkout_datetime_actual <= record.checkin_datetime:
                    raise ValidationError('Thời gian checkout phải sau checkin!')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.rental') or 'New'
        rental = super(HotelRental, self).create(vals)
        if rental.room_id:
            rental.room_id.write({'state': 'occupied'})
        if rental.reservation_id:
            rental.reservation_id.write({'state': 'checked_in', 'rental_id': rental.id})
        return rental

    def write(self, vals):
        if any(rec.state == 'completed' for rec in self):
            protected_fields = ['room_id', 'checkin_datetime', 'guest_id']
            if any(field in vals for field in protected_fields):
                raise UserError('Không thể sửa thông tin cơ bản khi rental đã hoàn thành!')
        return super(HotelRental, self).write(vals)

    def unlink(self):
        for record in self:
            if record.state == 'ongoing':
                raise UserError(f'Không thể xóa rental "{record.name}" đang diễn ra! Vui lòng checkout hoặc hủy trước.')
            if record.invoice_ids:
                raise UserError(f'Không thể xóa rental "{record.name}" đã có hóa đơn!')
        return super(HotelRental, self).unlink()

    def action_checkout(self):
        self.ensure_one()
        if self.state != 'ongoing':
            raise UserError('Chỉ có thể checkout rental đang diễn ra!')
        return {
            'name': _('Checkout'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.checkout.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rental_id': self.id,
                'default_room_id': self.room_id.id,
                'default_guest_id': self.guest_id.id,
                'default_checkout_datetime': fields.Datetime.now(),
            }
        }

    def action_complete_checkout(self, checkout_datetime=None, checkout_notes=None):
        self.ensure_one()
        if self.state != 'ongoing':
            raise UserError('Rental không ở trạng thái ongoing!')
        if not checkout_datetime:
            checkout_datetime = fields.Datetime.now()
        self.write({
            'state': 'completed',
            'checkout_datetime_actual': checkout_datetime,
            'completed_date': fields.Datetime.now(),
            'checkout_by': self.env.user.id,
        })
        if checkout_notes:
            self.notes = (self.notes or '') + '\n\nCheckout: ' + checkout_notes
        self.room_id.write({'state': 'cleaning'})
        if self.reservation_id and self.reservation_id.state == 'checked_in':
            self.reservation_id.write({'state': 'done'})
        return True

    def action_change_room(self):
        self.ensure_one()
        if self.state != 'ongoing':
            raise UserError('Chỉ có thể đổi phòng khi rental đang diễn ra!')
        return {
            'name': _('Đ��i phòng'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.change.room.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rental_id': self.id,
                'default_old_room_id': self.room_id.id,
                'default_room_type_id': self.room_type_id.id,
                'default_guest_count': self.guest_count_actual,
            }
        }

    def action_cancel(self):
        for record in self:
            if record.state != 'ongoing':
                raise UserError('Chỉ có thể hủy rental đang diễn ra!')
            if record.invoice_ids.filtered(lambda inv: inv.state == 'paid'):
                raise UserError('Không thể hủy rental đã có hóa đơn thanh toán!')
            record.write({'state': 'cancelled'})
            record.room_id.write({'state': 'available'})
            if record.reservation_id:
                record.reservation_id.write({'state': 'cancelled', 'cancel_reason': 'Rental bị hủy'})

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Hóa đơn'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.invoice',
            'view_mode': 'tree,form',
            'domain': [('rental_id', '=', self.id)],
            'context': {'default_rental_id': self.id, 'default_guest_id': self.guest_id.id}
        }

    def action_create_invoice(self):
        self.ensure_one()
        if self.state not in ['ongoing', 'completed']:
            raise UserError('Chỉ có thể tạo hóa đơn cho rental đang diễn ra hoặc đã hoàn thành!')
        return {
            'name': _('Tạo hóa đơn'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.create.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rental_id': self.id,
                'default_guest_id': self.guest_id.id,
                'default_room_id': self.room_id.id,
            }
        }

    @api.model
    def get_ongoing_rentals(self):
        return self.search([('state', '=', 'ongoing')])

    @api.model
    def get_rentals_by_room(self, room_id):
        return self.search([('room_id', '=', room_id)], order='checkin_datetime desc')

    @api.model
    def get_rentals_by_guest(self, guest_id):
        return self.search([('guest_id', '=', guest_id)], order='checkin_datetime desc')

    @api.model
    def _cron_check_overdue_checkouts(self):
        now = fields.Datetime.now()
        overdue_rentals = self.search([('state', '=', 'ongoing'), ('checkout_datetime_expected', '<', now)])
        for rental in overdue_rentals:
            rental.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Rental quá giờ checkout: {rental.name}',
                note=f'Khách {rental.guest_id.name} ở phòng {rental.room_id.name} đã quá giờ checkout dự kiến ({rental.checkout_datetime_expected})',
                user_id=rental.user_id.id
            )

    @api.model
    def _cron_send_checkout_reminders(self):
        now = fields.Datetime.now()
        reminder_time = now + timedelta(hours=2)
        upcoming_checkouts = self.search([
            ('state', '=', 'ongoing'),
            ('checkout_datetime_expected', '>=', now),
            ('checkout_datetime_expected', '<=', reminder_time)
        ])
        for rental in upcoming_checkouts:
            rental.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Sắp đến giờ checkout: {rental.name}',
                note=f'Khách {rental.guest_id.name} ở phòng {rental.room_id.name} sẽ checkout lúc {rental.checkout_datetime_expected}',
                user_id=rental.user_id.id,
                date_deadline=fields.Date.today()
            )
