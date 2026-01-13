# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    commission_ids = fields.One2many(
        'highfive.unit.commission',
        'unit_id',
        string='Commission Rates'
    )

    commission_count = fields.Integer(
        'Commissions',
        compute='_compute_commission_count'
    )

    def _compute_commission_count(self):
        """Count commissions"""
        for record in self:
            record.commission_count = len(record.commission_ids)

    def action_view_commissions(self):
        """Open commissions"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commission Rates',
            'res_model': 'highfive.unit.commission',
            'view_mode': 'tree,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
        }