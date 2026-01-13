# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # HighFive Integration
    highfive_booking_id = fields.Many2one(
        'highfive.booking',
        'HighFive Booking',
        index=True
    )

    highfive_payment_id = fields.Char(
        'HighFive Payment ID',
        index=True
    )

    # Payment Breakdown
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

    # Transaction Reference
    transaction_reference = fields.Char(
        'Transaction Reference'
    )