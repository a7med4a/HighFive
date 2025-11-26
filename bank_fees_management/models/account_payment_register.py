from odoo import fields, models, api

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

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

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result=batch_result)

        payment_vals.update({'bank_fees_amount': self.bank_fees_amount})
        payment_vals.update({'journal_type': self.journal_type})
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_batch(batch_result=batch_result)

        payment_vals.update({'bank_fees_amount': self.bank_fees_amount})
        payment_vals.update({'journal_type': self.journal_type})
        return payment_vals