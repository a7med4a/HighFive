# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HighFiveBookingLine(models.Model):
    _name = 'highfive.booking.line'
    _description = 'HighFive Booking Line'
    _order = 'sequence, id'

    # Reference
    booking_id = fields.Many2one(
        'highfive.booking',
        'Booking',
        required=True,
        ondelete='cascade',
        index=True
    )

    sequence = fields.Integer('Sequence', default=10)

    # Type
    line_type = fields.Selection([
        ('unit', 'Main Unit'),
        ('service', 'Additional Service')
    ], string='Type', required=True, default='service')

    # Product/Service
    product_id = fields.Many2one(
        'product.template',
        'Product/Service',
        required=True,
        domain=[
            '|',
            ('highfive_unit_id', '!=', False),
            ('is_highfive_service', '=', True)
        ]
    )

    name = fields.Char(
        'Description',
        required=True
    )

    # Pricing
    price_unit = fields.Monetary(
        'Unit Price',
        currency_field='currency_id',
        required=True
    )

    quantity = fields.Float(
        'Quantity',
        default=1.0,
        required=True
    )

    price_subtotal = fields.Monetary(
        'Subtotal',
        currency_field='currency_id',
        compute='_compute_price_subtotal',
        store=True
    )

    currency_id = fields.Many2one(
        related='booking_id.currency_id',
        store=True,
        string='Currency'
    )

    @api.depends('price_unit', 'quantity')
    def _compute_price_subtotal(self):
        """Calculate subtotal"""
        for line in self:
            line.price_subtotal = line.price_unit * line.quantity

    @api.onchange('line_type')
    def _onchange_line_type(self):
        """Filter products based on line type"""
        if self.line_type == 'unit':
            return {
                'domain': {
                    'product_id': [('highfive_unit_id', '!=', False)]
                }
            }
        else:
            return {
                'domain': {
                    'product_id': [('is_highfive_service', '=', True)]
                }
            }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update name and price when product changes"""
        if self.product_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price

    @api.constrains('line_type', 'product_id')
    def _check_line_type(self):
        """Validate line type matches product"""
        for line in self:
            print("line.line_type ==> ",line.line_type)
            print("line.product_id ==> ",line.product_id)
            print("line.product_id.is_highfive_service ==> ",line.product_id.is_highfive_service)
            if line.line_type == 'unit' and not line.product_id.highfive_unit_id:
                raise ValidationError(
                    "Main Unit line must use a HighFive Unit product!"
                )
            if line.line_type == 'service' and not line.product_id.is_highfive_service:
                raise ValidationError(
                    "Service line must use a HighFive Service product!"
                )