# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HotelPayment(models.Model):
    _name = 'hotel.payment'
    _description = 'Hotel Payment'
    _order = 'payment_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Ma thanh toan', required=True, copy=False, readonly=True, default='New', tracking=True)

    invoice_id = fields.Many2one('hotel.invoice', string='Hoa don', required=True, ondelete='restrict', tracking=True, domain=[('state', 'in', ('confirmed', 'paid'))])
    rental_id = fields.Many2one('hotel.rental', related='invoice_id.rental_id', string='Thue phong', store=True, readonly=True)
    guest_id = fields.Many2one('res.partner', related='invoice_id.guest_id', string='Khach hang', store=True, readonly=True)
    room_id = fields.Many2one('hotel.room', related='invoice_id.room_id', string='Phong', store=True, readonly=True)

    payment_date = fields.Datetime(string='Ngay thanh toan', required=True, default=fields.Datetime.now, tracking=True)
    amount = fields.Float(string='So tien thanh toan', required=True, digits='Product Price', tracking=True)
    payment_method = fields.Selection([('cash','Tien mat'),('bank_transfer','Chuyen khoan'),('credit_card','The tin dung'),('debit_card','The ghi no'),('e_wallet','Vi dien tu'),('other','Khac')], string='Phuong thuc TT', required=True, default='cash', tracking=True)
    payment_reference = fields.Char(string='Ma giao dich', tracking=True)
    state = fields.Selection([('draft','Nhap'),('confirmed','Da xac nhan'),('cancelled','Da huy')], string='Trang thai', default='draft', required=True, tracking=True)
    notes = fields.Text(string='Ghi chu')

    invoice_total = fields.Float(string='Tong hoa don', related='invoice_id.total_amount', readonly=True, digits='Product Price')
    invoice_deposit = fields.Float(string='Tien coc', related='invoice_id.deposit_amount', readonly=True, digits='Product Price')
    invoice_amount_to_pay = fields.Float(string='Con phai TT', related='invoice_id.amount_to_pay', readonly=True, digits='Product Price')
    amount_already_paid = fields.Float(string='Da TT truoc do', compute='_compute_payment_summary', digits='Product Price')
    remaining_after = fields.Float(string='Con lai sau TT', compute='_compute_payment_summary', digits='Product Price')

    user_id = fields.Many2one('res.users', string='Thu ngan', default=lambda self: self.env.user, readonly=True)
    confirmed_by = fields.Many2one('res.users', string='Nguoi xac nhan', readonly=True)
    cancelled_date = fields.Datetime(string='Ngay huy', readonly=True)
    company_id = fields.Many2one('res.company', string='Cong ty', default=lambda self: self.env.company)

    _sql_constraints = [('amount_positive', 'check(amount > 0)', 'So tien thanh toan phai lon hon 0!')]

    @api.depends('invoice_id', 'invoice_id.payment_ids.state', 'invoice_id.payment_ids.amount')
    def _compute_payment_summary(self):
        for rec in self:
            if rec.invoice_id:
                paid = sum(p.amount for p in rec.invoice_id.payment_ids if p.state == 'confirmed' and p.id != rec._origin.id)
                rec.amount_already_paid = paid
                rec.remaining_after = rec.invoice_id.amount_to_pay - paid - rec.amount
            else:
                rec.amount_already_paid = 0.0
                rec.remaining_after = 0.0

    @api.constrains('amount', 'invoice_id', 'state')
    def _check_amount_not_exceed_invoice(self):
        for rec in self:
            if rec.state != 'confirmed' or not rec.invoice_id:
                continue
            paid = sum(p.amount for p in rec.invoice_id.payment_ids if p.state == 'confirmed' and p.id != rec.id)
            if paid + rec.amount > rec.invoice_id.total_amount + 0.01:
                raise ValidationError('Tong so tien thanh toan vuot qua tong hoa don!')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.payment') or 'New'
        return super().create(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(f'Khong the xoa thanh toan {rec.name} da xac nhan!')
        return super().unlink()

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Chi co the xac nhan thanh toan o trang thai Nhap!')
            inv = rec.invoice_id
            if inv.state == 'cancelled':
                raise UserError('Khong the thanh toan cho hoa don da huy!')
            if inv.state == 'draft':
                raise UserError('Hoa don chua duoc xac nhan!')
            paid = sum(p.amount for p in inv.payment_ids if p.state == 'confirmed' and p.id != rec.id)
            if paid + rec.amount > inv.total_amount + 0.01:
                raise UserError('Tong so tien thanh toan vuot qua tong hoa don!')
            rec.write({'state': 'confirmed', 'confirmed_by': self.env.user.id})
            rec._sync_invoice_payment_state()

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError('Thanh toan nay da duoc huy roi!')
            rec.write({'state': 'cancelled', 'cancelled_date': fields.Datetime.now()})
            rec._sync_invoice_payment_state()

    def action_set_draft(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError('Khong the dua ve Nhap thanh toan da xac nhan!')
            rec.state = 'draft'

    def _sync_invoice_payment_state(self):
        self.ensure_one()
        inv = self.invoice_id
        if not inv or inv.state == 'cancelled':
            return
        total_paid = sum(p.amount for p in inv.payment_ids if p.state == 'confirmed')
        if total_paid >= inv.total_amount - 0.01:
            if inv.state != 'paid':
                inv.write({'state': 'paid', 'payment_date': fields.Datetime.now(), 'cashier_id': self.env.user.id, 'payment_method': self.payment_method, 'payment_reference': self.payment_reference or inv.payment_reference})
        else:
            if inv.state == 'paid':
                inv.write({'state': 'confirmed'})

    @api.model
    def get_payment_summary(self, invoice_id):
        payments = self.search([('invoice_id', '=', invoice_id), ('state', '=', 'confirmed')])
        inv = self.env['hotel.invoice'].browse(invoice_id)
        total_paid = sum(payments.mapped('amount'))
        return {'total_paid': total_paid, 'remaining': inv.amount_to_pay - total_paid, 'payment_count': len(payments), 'is_fully_paid': total_paid >= inv.total_amount - 0.01}
