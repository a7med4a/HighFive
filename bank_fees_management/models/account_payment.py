from pkg_resources import require

from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bank_fees_amount = fields.Monetary(
        string="Bank Fees Amount",
        currency_field='currency_id',
        help="Amount of bank fees for this payment.",
    )

    bank_fees_account_id = fields.Many2one(
        'account.account',
        compute='_compute_bank_fees_account_id',
        string='Bank Fees Account',
        readonly=True,
    )
    journal_type = fields.Char()

    @api.depends('journal_id')
    def _compute_bank_fees_account_id(self):
        for payment in self:
            payment.journal_type = payment.journal_id.type
            payment.bank_fees_account_id = payment.journal_id.bank_fees_account_id

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        moves = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)

        if self.bank_fees_account_id and self.bank_fees_amount > 0:
            for move in moves:
                if move.get('account_id') == self.journal_id.default_account_id.id:
                    # Liquidity line (bank)
                    if self.payment_type == 'inbound':  # Customer payment
                        if move['debit'] > 0:
                            move['debit'] -= self.bank_fees_amount
                            move['amount_currency'] -= self.bank_fees_amount
                    elif self.payment_type == 'outbound':  # Vendor payment
                        if move['credit'] > 0:
                            move['credit'] += self.bank_fees_amount
                            move['amount_currency'] -= self.bank_fees_amount
                    break

            # Add the bank fees expense line
            moves.append({
                'name': 'Bank Fees',
                'date_maturity': self.date,
                'currency_id': self.currency_id.id,
                'debit': self.bank_fees_amount,
                'credit': 0.0,
                'amount_currency': self.bank_fees_amount,
                'account_id': self.bank_fees_account_id.id,
                'partner_id': self.partner_id.id,
            })
        return moves
