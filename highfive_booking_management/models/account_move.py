# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # HighFive Booking Link
    highfive_booking_id = fields.Many2one(
        'highfive.booking',
        'HighFive Booking',
        index=True
    )

    # HighFive Related Fields
    highfive_partner_id = fields.Many2one(
        'res.partner',
        string='HighFive Partner',
        store=True,
        index=True,
        help='Supplier/Partner from booking'
    )

    highfive_branch_id = fields.Many2one(
        'highfive.partner.branch',
        string='HighFive Branch',
        store=True,
        index=True,
        help='Branch from booking'
    )

    highfive_payment_method = fields.Selection([
        ('online', 'Online Payment'),
        ('cash', 'Cash Payment')
    ], string='Payment Method',
       store=True,
       index=True,
       help='Payment method from booking')

    # Payment Breakdown (for reference)
    payment_card = fields.Monetary(
        'Card Payment',
        currency_field='currency_id'
    )

    payment_wallet = fields.Monetary(
        'Wallet Payment',
        currency_field='currency_id'
    )

    payment_coupon = fields.Monetary(
        'Coupon Discount',
        currency_field='currency_id'
    )

    # Payment Reference
    payment_transaction_ref = fields.Char(
        'Payment Transaction Reference'
    )

