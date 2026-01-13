# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HighFivePartnerBranch(models.Model):
    _inherit = 'highfive.partner.branch'
    
    # Booking count
    booking_count = fields.Integer(
        'Bookings Count',
        compute='_compute_booking_count'
    )
    
    @api.depends('highfive_branch_id')
    def _compute_booking_count(self):
        """Count bookings for this branch"""
        for branch in self:
            branch.booking_count = self.env['highfive.booking'].search_count([
                ('branch_id', '=', branch.id)
            ])
    
    def action_view_bookings(self):
        """Open bookings for this branch"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Branch Bookings',
            'res_model': 'highfive.booking',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
            'context': {
                'default_branch_id': self.id,
                'default_partner_id': self.partner_id.id,
                'search_default_group_by_state': 1,
            }
        }
