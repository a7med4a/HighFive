from odoo import api, fields, models, _
from odoo.api import readonly


class AccountMove(models.Model):
    _inherit = "account.move"

    business_type = fields.Selection(
        selection=[
            ('printing', 'Printing'),
            ('marketing', 'Marketing'),
            ('printing_marketing', 'Printing and Marketing'),
        ],
        string='Business Type',
        readonly=True,
    )


