from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    terms_and_conditions = fields.Many2one(
        string='Terms and Conditions',
        comodel_name='terms.and.conditions',
        default=lambda self: self.env['terms.and.conditions'].search([('sit_is_default', '=', True)], limit=1),
    )

    business_type = fields.Selection(
        selection=[
            ('printing', 'Printing'),
            ('marketing', 'Marketing'),
            ('printing_marketing', 'Printing and Marketing'),
        ],
        string='Business Type',
    )

    @api.model
    def default_get(self, fields):
        result = super(SaleOrder, self).default_get(fields)
        if result.get('terms_and_conditions'):
            result['note'] = self.env['terms.and.conditions'].browse(result.get('terms_and_conditions')).description
        return result

    @api.depends('partner_id', 'terms_and_conditions')
    def _compute_note(self):
        if self.terms_and_conditions:
            self.note = self.terms_and_conditions.description
        else:
            super(SaleOrder, self)._compute_note()

    def action_print_sale_report(self):
        self.ensure_one()
        return self.env.ref(
            "sale_custom.action_report_sale_order_pdf"
        ).report_action(self)
    
    def _prepare_invoice(self):
        vales = super()._prepare_invoice()
        vales['business_type'] = self.business_type
        return vales
