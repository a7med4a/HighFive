from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    internal_ref = fields.Char()

    @api.model_create_multi
    def create(self, vals):
        for rec in vals:
            code = self.env['ir.sequence'].next_by_code('awc_product') or 'New'
            rec['internal_ref'] = code
            rec['default_code'] = code
        new_record = super(ProductTemplate, self).create(vals)
        return new_record

    def action_generate_code(self):
        for rec in self:
            if not rec.internal_ref:
                code = self.env['ir.sequence'].next_by_code('awc_product') or 'New'
                rec.internal_ref = code
                rec.default_code = code
                rec._compute_display_name()

    @api.depends('internal_ref', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.internal_ref} {rec.name}" if rec.internal_ref else rec.name
