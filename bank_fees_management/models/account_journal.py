from pkg_resources import require

from odoo import fields, models

class AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_fees_account_id = fields.Many2one(
        "account.account",
        string="Bank Fees Account",
        domain=[('account_type', "=", 'expense')],
        help="Account used to record bank fees for payments made through this journal.",
    )


