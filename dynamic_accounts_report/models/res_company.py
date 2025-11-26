from odoo import models, fields, _
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from datetime import timedelta
from odoo.tools import date_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    account_tax_periodicity = fields.Selection(
        [
            ("year", "annually"),
            ("semester", "semi-annually"),
            ("4_months", "every 4 months"),
            ("trimester", "quarterly"),
            ("2_months", "every 2 months"),
            ("monthly", "monthly"),
        ],
        string="Delay units",
        help="Periodicity",
        default="monthly",
        required=True,
    )
    account_tax_periodicity_reminder_day = fields.Integer(
        string="Start from", default=7, required=True
    )
    account_tax_periodicity_journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        domain=[("type", "=", "general")],
        check_company=True,
    )
