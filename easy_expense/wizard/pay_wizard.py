# © 2016 Serpent Consulting Services Pvt. Ltd. (support@serpentcs.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from lxml import etree

from odoo import tools
from odoo import api, models,fields,exceptions


class PayExpWizard(models.TransientModel):
    _name = 'pay.exp.wizard'
    _description = 'Pay Exp Wizard'

    expense_id = fields.Many2one(comodel_name="easy.expense", string="Expense", required=True, )
    product_id = fields.Many2one(comodel_name="product.product", string="Expense Product", required=True, related='expense_id.product_id')
    journal_id = fields.Many2one(comodel_name="account.journal",default=lambda self: self.env['account.journal'].search([('type','=','cash')],limit=1),
                                 string="Journal", required=True,domain="[('type','=','cash')]" )
    amount = fields.Float(string="Amount",related='expense_id.amount',readonly=True )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, ondelete='cascade')
    payment_date = fields.Date(string="", default=lambda self: fields.Datetime.now(), required=True, )

    def action_pay(self):
        account_move_obj=self.env['account.move']
        product_account_id = 0
        if self.expense_id.product_id.property_account_expense_id.id:
            product_account_id = self.expense_id.product_id.property_account_expense_id.id
        elif self.expense_id.product_id.categ_id.property_account_expense_categ_id.id:
            product_account_id = self.expense_id.product_id.categ_id.property_account_expense_categ_id.id

        if not product_account_id:
            raise exceptions.ValidationError("Debit Account Can't Be Null")
        if not self.journal_id.default_account_id:
            raise exceptions.ValidationError("Credit Account Can't Be Null")

        vals = []
        price = self.amount
        name = self.expense_id.product_id.name + ' # '+self.expense_id.name
        currant_company = self.env.user.company_id
        tax_id = self.expense_id.product_id.supplier_taxes_id[:1]
        # Calculate tax amount
        tax_amount = 0.0
        if tax_id:
            if tax_id.amount_type == 'percent':
                tax_amount = price * tax_id.amount / 100.0
            elif tax_id.amount_type == 'fixed':
                tax_amount = tax_id.amount

        # Get account_id from refund_repartition_line_ids where repartition_type == 'tax'
        account_tax_line = next((line for line in tax_id.refund_repartition_line_ids if line.repartition_type == 'tax'), None)
        account_tax_id = account_tax_line.account_id.id if account_tax_line and account_tax_line.account_id else False
        if price:
            vals.append((0, 0, {'name': self.expense_id.note,
                                'product_id': self.expense_id.product_id.id,
                                'partner_id': currant_company.partner_id.id,
                                'account_id': product_account_id,
                                'debit': price - tax_amount if tax_amount and account_tax_id else price,
                                'credit': 0.0}))
            vals.append((0, 0, {'name': self.expense_id.note,
                                'product_id': self.expense_id.product_id.id,
                                'partner_id': currant_company.partner_id.id,
                                'account_id': self.journal_id.default_account_id.id,
                                'debit': 0.0,
                                'credit': price}))
            if tax_amount and account_tax_id:
                vals.append((0, 0, {'name': tax_id.name,
                                    'product_id': self.expense_id.product_id.id,
                                    'partner_id': currant_company.partner_id.id,
                                    'account_id': account_tax_id,
                                    'debit': tax_amount,
                                    'credit': 0.0}))

        account_move_id=account_move_obj.create({
            'ref': name,
            'partner_id':currant_company.partner_id.id,
            'move_type':'entry',
            'date':self.payment_date,
            'journal_id':self.journal_id.id,
            'line_ids':vals,
        })

        account_move_id.post()
        self.expense_id.state = 'paid'
        self.expense_id.move_id = account_move_id.id
        self.expense_id.payment_date = self.payment_date



