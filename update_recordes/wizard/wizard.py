# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.exceptions import UserError

class WizardUpdate(models.TransientModel):
    _name = "wizard.update"


    def update_easy_expenses_records(self):
        Expense = self.env['easy.expense']
        AccountMove = self.env['account.move']
        vendor_id = 86

        expenses = Expense.search([
            ('state', '=', 'paid'),
            ('move_id', '!=', False),
        ])

        if not expenses:
            raise UserError(_("No paid expenses found have move line."))

        for expense in expenses:
            # print(expense.read())
            # print("===============================")
            if expense.move_id:
                move = expense.move_id
                # print(move.read())
                # print("===============================")
                if move.state != 'draft':
                    move.button_draft()

                move.unlink()

            tax_id = expense.product_id.supplier_taxes_id[:1]
            # print(tax_id)
            # print("===============================")
            bill = AccountMove.create({
                'move_type': 'in_invoice',
                'partner_id': vendor_id,
                'invoice_date': expense.exp_date,
                'invoice_line_ids': [(0, 0, {
                    'product_id': expense.product_id.id,
                    'name': expense.name or expense.product_id.name,
                    'quantity': 1,
                    'price_unit': expense.amount,
                    'tax_ids': [(6, 0, tax_id.ids)],
                })],
            })
            # print(bill.read())
            # print("===============================")
            bill.action_post()

            expense.write({
                'move_id': bill.id,
            })

        return {'type': 'ir.actions.act_window_close'}