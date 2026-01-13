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
        string='HighFive Supplier',
        compute='_compute_highfive_fields',
        store=True,
        index=True,
        help='Supplier/Partner from booking'
    )

    highfive_branch_id = fields.Many2one(
        'highfive.partner.branch',
        string='HighFive Branch',
        compute='_compute_highfive_fields',
        store=True,
        index=True,
        help='Branch from booking'
    )

    highfive_payment_method = fields.Selection([
        ('online', 'Online Payment'),
        ('cash', 'Cash Payment')
    ], string='Payment Method',
       compute='_compute_highfive_fields',
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

    @api.depends('highfive_booking_id',
                 'highfive_booking_id.partner_id',
                 'highfive_booking_id.branch_id',
                 'highfive_booking_id.payment_method')
    def _compute_highfive_fields(self):
        """Compute HighFive related fields from booking"""
        for move in self:
            if move.highfive_booking_id:
                move.highfive_partner_id = move.highfive_booking_id.partner_id
                move.highfive_branch_id = move.highfive_booking_id.branch_id
                move.highfive_payment_method = move.highfive_booking_id.payment_method
            else:
                move.highfive_partner_id = False
                move.highfive_branch_id = False
                move.highfive_payment_method = False