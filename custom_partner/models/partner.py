from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    internal_ref = fields.Char()

    @api.model_create_multi
    def create(self, vals):
        for rec in vals:
            code = self.env['ir.sequence'].next_by_code('awc_partner') or 'New'
            rec['internal_ref'] = code

        new_record = super(ResPartner, self).create(vals)
        return new_record

    @api.depends('internal_ref', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.internal_ref} {rec.name}" if rec.internal_ref else rec.name

    def action_generate_code(self):
        for rec in self:
            if not rec.internal_ref:
                rec.internal_ref = self.env['ir.sequence'].next_by_code('awc_partner') or 'New'
                rec._compute_display_name()