from odoo import models, fields, _
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from datetime import timedelta
from odoo.tools import date_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    # Deferred expense management
    deferred_expense_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Deferred Expense Journal",
    )
    deferred_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Deferred Expense Account",
    )
    generate_deferred_expense_entries_method = fields.Selection(
        string="Generate Deferred Expense Entries",
        selection=[
            ("on_validation", "On bill validation"),
            ("manual", "Manually & Grouped"),
        ],
        default="on_validation",
        required=True,
    )
    deferred_expense_amount_computation_method = fields.Selection(
        string="Deferred Expense Based on",
        selection=[
            ("day", "Days"),
            ("month", "Months"),
            ("full_months", "Full Months"),
        ],
        default="month",
        required=True,
    )

    # Deferred revenue management
    deferred_revenue_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Deferred Revenue Journal",
    )
    deferred_revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Deferred Revenue Account",
    )
    generate_deferred_revenue_entries_method = fields.Selection(
        string="Generate Deferred Revenue Entries",
        selection=[
            ("on_validation", "On bill validation"),
            ("manual", "Manually & Grouped"),
        ],
        default="on_validation",
        required=True,
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        string="Deferred Revenue Based on",
        selection=[
            ("day", "Days"),
            ("month", "Months"),
            ("full_months", "Full Months"),
        ],
        default="month",
        required=True,
    )
