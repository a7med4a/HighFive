from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_tax_periodicity = fields.Selection(
        related="company_id.account_tax_periodicity",
        string="Periodicity",
        readonly=False,
        required=True,
    )
    account_tax_periodicity_reminder_day = fields.Integer(
        related="company_id.account_tax_periodicity_reminder_day",
        string="Reminder",
        readonly=False,
        required=True,
    )
    account_tax_periodicity_journal_id = fields.Many2one(
        related="company_id.account_tax_periodicity_journal_id",
        string="Journal",
        readonly=False,
    )

    def open_tax_group_list(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tax groups",
            "res_model": "account.tax.group",
            "view_mode": "list",
            "context": {
                "default_country_id": self.account_fiscal_country_id.id,
                "search_default_country_id": self.account_fiscal_country_id.id,
            },
        }
