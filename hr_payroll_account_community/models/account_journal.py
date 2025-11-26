from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    
    is_salaries = fields.Boolean(
        string='Salaries Journal',
        help='Check this box if this journal is used to post salary entries.'
    )

    is_loan = fields.Boolean(
        string='Loan Journal',
        help='Check this box if this journal is used to post loan entries.'
    )

    is_expense = fields.Boolean(
        string='Expense Journal',
        help='Check this box if this journal is used to post expense entries.'
    )
