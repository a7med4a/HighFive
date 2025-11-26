from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    move_count = fields.Integer(string="Partner Ledger", compute="_compute_move_count")

    def _compute_move_count(self):
        for partner in self:
            partner.move_count = self.env['account.move.line'].search_count([('partner_id', '=', partner.id)])

    def open_partner_ledger_action(self):
        self.ensure_one()  # تأكد إنك في record واحد
        return {
            'type': 'ir.actions.client',
            'tag': 'p_l',
            'params': {
                'partner_id': self.id,
                'partner_name': self.name,
                'display_name': 'Partner Ledger',
                'action_xml_id': 'dynamic_accounts_report.action_partner_ledger',
            }
        }
