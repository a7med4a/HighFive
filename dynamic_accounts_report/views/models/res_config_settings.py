from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Deferred expense management
    deferred_expense_journal_id = fields.Many2one(
        comodel_name="account.journal",
        help="Journal used for deferred entries",
        readonly=False,
        related="company_id.deferred_expense_journal_id",
    )
    deferred_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        help="Account used for deferred expenses",
        readonly=False,
        related="company_id.deferred_expense_account_id",
    )
    generate_deferred_expense_entries_method = fields.Selection(
        related="company_id.generate_deferred_expense_entries_method",
        readonly=False,
        required=True,
        help="Method used to generate deferred entries",
    )
    deferred_expense_amount_computation_method = fields.Selection(
        related="company_id.deferred_expense_amount_computation_method",
        readonly=False,
        required=True,
        help="Method used to compute the amount of deferred entries",
    )

    # Deferred revenue management
    deferred_revenue_journal_id = fields.Many2one(
        comodel_name="account.journal",
        help="Journal used for deferred entries",
        readonly=False,
        related="company_id.deferred_revenue_journal_id",
    )
    deferred_revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        help="Account used for deferred revenues",
        readonly=False,
        related="company_id.deferred_revenue_account_id",
    )
    generate_deferred_revenue_entries_method = fields.Selection(
        related="company_id.generate_deferred_revenue_entries_method",
        readonly=False,
        required=True,
        help="Method used to generate deferred entries",
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        related="company_id.deferred_revenue_amount_computation_method",
        readonly=False,
        required=True,
        help="Method used to compute the amount of deferred entries",
    )
