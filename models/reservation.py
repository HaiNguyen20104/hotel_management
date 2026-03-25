# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class HotelReservation(models.Model):
    """Model quản lý đặt phòng (F4: Đặt phòng)"""
    _name = 'hotel.reservation'
    _description = 'Hotel Reservation'
    _order = 'checkin_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã đặt phòng', required=True, copy=False, readonly=True, default='New')

    # Guest Information
    guest_id = fields.Many2one('res.partner', string='Khách hàng', required=True, tracking=True)
    guest_phone = fields.Char(related='guest_id.phone', string='Số điện thoại', readonly=True)
    guest_email = fields.Char(related='guest_id.email', string='Email', readonly=True)

    # Room Information
    room_id = fields.Many2one('hotel.room', string='Phòng', required=True, tracking=True)
    room_type_id = fields.Many2one('hotel.room.type', related='room_id.room_type_id', string='Loại phòng', store=True, readonly=True)

    # Dates
    checkin_date = fields.Datetime(string='Ngày nhận phòng dự kiến', required=True, tracking=True, default=fields.Datetime.now)
    checkout_date = fields.Datetime(string='Ngày trả phòng dự kiến', required=True, tracking=True)
    duration_days = fields.Float(string='Số ngày', compute='_compute_duration', store=True)
    duration_nights = fields.Integer(string='Số đêm', compute='_compute_duration', store=True)

    # Pricing
    price_per_day = fields.Float(string='Giá/ngày', digits='Product Price')
    deposit = fields.Float(string='Tiền cọc', digits='Product Price', tracking=True)
    total_amount = fields.Float(string='Tổng tiền dự kiến', compute='_compute_total_amount', store=True, digits='Product Price')

    # Guest Count
    guest_count = fields.Integer(string='Số người', default=1)

    # State
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('checked_in', 'Đã checkin'),
        ('cancelled', 'Đã hủy'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    notes = fields.Text(string='Ghi chú')
    cancel_reason = fields.Text(string='Lý do hủy')

    # Date tracking
    reservation_date = fields.Datetime(string='Ngày đặt', default=fields.Datetime.now, readonly=True)
    confirmed_date = fields.Datetime(string='Ngày xác nhận', readonly=True)
    cancelled_date = fields.Datetime(string='Ngày hủy', readonly=True)

    # Rental link
    rental_id = fields.Many2one('hotel.rental', string='Thuê phòng', readonly=True)

    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)

    # Computed fields
    is_overdue = fields.Boolean(string='Quá hạn checkin', compute='_compute_is_overdue')
    can_checkin = fields.Boolean(string='Có thể checkin', compute='_compute_can_checkin')

    _sql_constraints = [
        ('dates_check', 'check(checkout_date > checkin_date)', 'Ngày trả phòng phải sau ngày nhận phòng!'),
        ('guest_count_positive', 'check(guest_count > 0)', 'Số người phải lớn hơn 0!'),
        ('deposit_positive', 'check(deposit >= 0)', 'Tiền cọc không được âm!'),
    ]

    @api.depends('checkin_date', 'checkout_date')
    def _compute_duration(self):
        for record in self:
            if record.checkin_date and record.checkout_date:
                delta = record.checkout_date - record.checkin_date
                record.duration_days = delta.total_seconds() / 86400.0
                record.duration_nights = delta.days if delta.days > 0 else 1
            else:
                record.duration_days = 0
                record.duration_nights = 0

    @api.depends('price_per_day', 'duration_days')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.price_per_day * record.duration_days

    @api.depends('checkin_date', 'state')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = (record.state == 'confirmed' and record.checkin_date < now)

    @api.depends('state', 'checkin_date', 'room_id.state')
    def _compute_can_checkin(self):
        now = fields.Datetime.now()
        for record in self:
            can_checkin = (
                record.state == 'confirmed' and
                record.checkin_date <= now <= record.checkin_date + timedelta(hours=24) and
                record.room_id.state in ('available', 'reserved')
            )
            record.can_checkin = can_checkin

    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.price_per_day = self.room_id.daily_price

    @api.onchange('guest_count', 'room_id')
    def _onchange_guest_count(self):
        if self.room_id and self.guest_count > self.room_id.capacity:
            return {
                'warning': {
                    'title': _('Cảnh báo'),
                    'message': _(f'Số người ({self.guest_count}) vượt quá sức chứa của phòng ({self.room_id.capacity})!')
                }
            }

    @api.constrains('checkin_date', 'checkout_date', 'room_id', 'state')
    def _check_room_availability(self):
        for record in self:
            if record.state in ('confirmed', 'checked_in'):
                conflicting = self.search([
                    ('id', '!=', record.id),
                    ('room_id', '=', record.room_id.id),
                    ('state', 'in', ('confirmed', 'checked_in')),
                    ('checkin_date', '<', record.checkout_date),
                    ('checkout_date', '>', record.checkin_date),
                ])
                if conflicting:
                    raise ValidationError(
                        f'Phòng {record.room_id.name} đã được đặt trong thời gian này! '
                        f'Conflict với reservation {conflicting[0].name}'
                    )

    @api.constrains('guest_count', 'room_id')
    def _check_guest_capacity(self):
        for record in self:
            if record.room_id and record.guest_count:
                max_allowed = record.room_id.capacity * 1.5
                if record.guest_count > max_allowed:
                    raise ValidationError(
                        f'Số người ({record.guest_count}) vượt quá giới hạn cho phép '
                        f'({int(max_allowed)}) của phòng {record.room_id.name}!'
                    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.reservation') or 'New'
        if vals.get('room_id') and not vals.get('price_per_day'):
            room = self.env['hotel.room'].browse(vals['room_id'])
            vals['price_per_day'] = room.daily_price
        return super(HotelReservation, self).create(vals)

    def write(self, vals):
        if any(rec.state == 'checked_in' for rec in self):
            protected_fields = ['room_id', 'checkin_date', 'checkout_date']
            if any(field in vals for field in protected_fields):
                raise UserError('Không thể thay đổi phòng hoặc ngày khi đã checkin!')
        return super(HotelReservation, self).write(vals)

    def unlink(self):
        for record in self:
            if record.state == 'checked_in':
                raise UserError(f'Không thể xóa reservation {record.name} đã checkin!')
            if record.rental_id:
                raise UserError(f'Không thể xóa reservation {record.name} đã có rental!')
        return super(HotelReservation, self).unlink()

    def action_confirm(self):
        for record in self:
            if not record.room_id.check_availability(record.checkin_date, record.checkout_date):
                raise UserError(f'Phòng {record.room_id.name} không khả dụng trong thời gian này!')
            record.room_id.write({'state': 'reserved'})
            record.write({'state': 'confirmed', 'confirmed_date': fields.Datetime.now()})

    def action_cancel(self):
        for record in self:
            if record.state == 'checked_in':
                raise UserError('Không thể hủy reservation đã checkin!')
            if record.room_id.state == 'reserved':
                other_reservations = self.search([
                    ('id', '!=', record.id),
                    ('room_id', '=', record.room_id.id),
                    ('state', '=', 'confirmed')
                ], limit=1)
                if not other_reservations:
                    record.room_id.write({'state': 'available'})
            record.write({'state': 'cancelled', 'cancelled_date': fields.Datetime.now()})

    def action_checkin(self):
        self.ensure_one()
        if not self.can_checkin:
            raise UserError('Không thể checkin lúc này!')
        return {
            'name': _('Checkin'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_guest_id': self.guest_id.id,
                'default_room_id': self.room_id.id,
                'default_guest_count': self.guest_count,
            }
        }

    def action_change_room(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError('Chỉ có thể đổi phòng khi reservation ở trạng thái Confirmed!')
        return {
            'name': _('Đổi phòng'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.change.room.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id, 'default_current_room_id': self.room_id.id}
        }

    def action_view_rental(self):
        self.ensure_one()
        if not self.rental_id:
            raise UserError('Reservation này chưa có rental!')
        return {
            'name': _('Thuê phòng'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.rental',
            'res_id': self.rental_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_set_done(self):
        for record in self:
            if record.state != 'checked_in':
                raise UserError('Chỉ có thể đánh dấu done khi đã checkin!')
            if record.rental_id and record.rental_id.state != 'completed':
                raise UserError('Vui lòng checkout rental trước!')
            record.write({'state': 'done'})

    @api.model
    def _cron_send_checkin_reminders(self):
        """Cronjob gửi nhắc nhở checkin (F8)"""
        now = fields.Datetime.now()
        tomorrow = now + timedelta(days=1)
        upcoming_reservations = self.search([
            ('state', '=', 'confirmed'),
            ('checkin_date', '>=', now),
            ('checkin_date', '<=', tomorrow),
        ])
        for reservation in upcoming_reservations:
            reservation.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Nhắc nhở checkin: {reservation.name}',
                note=f'Khách {reservation.guest_id.name} sẽ checkin vào {reservation.checkin_date}',
                user_id=self.env.user.id,
                date_deadline=reservation.checkin_date.date(),
            )

    @api.model
    def _cron_cancel_expired_reservations(self):
        """Cronjob tự động hủy reservation quá hạn"""
        expired_time = fields.Datetime.now() - timedelta(hours=24)
        expired_reservations = self.search([
            ('state', '=', 'confirmed'),
            ('checkin_date', '<', expired_time),
        ])
        for reservation in expired_reservations:
            reservation.write({
                'state': 'cancelled',
                'cancel_reason': 'Tự động hủy do quá hạn checkin',
                'cancelled_date': fields.Datetime.now()
            })
            if reservation.room_id.state == 'reserved':
                reservation.room_id.write({'state': 'available'})
