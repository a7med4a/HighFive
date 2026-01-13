# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Booking count
    booking_count = fields.Integer(
        'Bookings Count',
        compute='_compute_booking_count'
    )
    
    @api.depends('highfive_partner_id')
    def _compute_booking_count(self):
        """Count bookings for this partner"""
        for partner in self:
            if partner.highfive_partner_id:
                partner.booking_count = self.env['highfive.booking'].search_count([
                    ('partner_id', '=', partner.id)
                ])
            else:
                partner.booking_count = 0
    
    def action_view_bookings(self):
        """Open bookings for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bookings',
            'res_model': 'highfive.booking',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_group_by_state': 1,
            }
        }
