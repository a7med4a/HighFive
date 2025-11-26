# -*- coding: utf-8 -*-

from odoo import api, fields, models, _,exceptions
from datetime import timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta



class easy_expense(models.Model):
    _name = 'easy.expense'
    _description = 'Easy Expense'

    name = fields.Char()
    note = fields.Text("Description")
    product_id = fields.Many2one(comodel_name="product.product", string="Expense Product",domain="[('type', '=', 'service')]" , required=False, )
    exp_date = fields.Date(string="Date", required=True, )
    post_date = fields.Date(string="Post Date", required=False, )
    due_date = fields.Date(string="Due Date", required=False, )
    amount = fields.Float(string="Amount",  required=True )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, store=True)

    state = fields.Selection(string="", selection=[('draft', 'Draft'), ('confirm', 'Confirm'),('paid', 'Paid'),('cancel', 'Canceled') ],default="draft", required=False, )
    payment_date = fields.Date(readonly=True,copy=False)
    move_id = fields.Many2one(comodel_name="account.move", string="Move",readonly=True,copy=False, required=False, )


    @api.constrains('due_date')
    def _check_date(self):
        if self.due_date:
            date_order = datetime.strptime(str(self.due_date), '%Y-%m-%d')
            date_today = datetime.strptime(str(fields.Date.context_today(self)), '%Y-%m-%d')
            if (date_order < date_today):
                raise exceptions.ValidationError(_('The Due date is in the past.'))


    def action_cancel(self):
        self.state='cancel'
    def action_confirm(self):
        self.state='confirm'
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('exp.code') or 'New'
        new_record= super(easy_expense, self).create(vals)
        return new_record


    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise exceptions.ValidationError(_('Cannot delete a expense After Confirm'))
        return super(easy_expense, self).unlink()

    @api.model
    def apply_tax_to_move(self):
        for exp in self:
            if not exp.move_id:
                continue
            move = exp.move_id
            # unpost move if posted
            # if move.state == 'posted':
            #     move.button_draft()
            print("unpost Done ==> ", move)
            # get product taxes

            taxes = exp.product_id.supplier_taxes_id
            grad_base = taxes.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'base').tag_ids
            grad_tax = taxes.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').tag_ids
            tax_account_id = taxes.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').account_id
            print("taxes ==> ", taxes)
            print("grad_base ==> ", grad_base)
            print("grad_tax ==> ", grad_tax)
            expense_lines = move.line_ids.filtered(lambda l: l.account_id.account_type == 'expense')
            tax_lines = move.line_ids.filtered(lambda l: l.account_id.id == tax_account_id.id)
            # total = expense_lines.debit + tax_lines.debit
            print("expense_lines ==> ", expense_lines)
            print("tax_lines ==> ", tax_lines)
            # expense_lines.write(
            #     {
            #         "tax_ids": [(6, 0, taxes.ids)],
            #         "debit": total,
            #         "tax_tag_ids": [(6, 0, grad_base.ids)],
            #     })
            self.env.cr.execute("""
                                UPDATE account_move_line
                                SET tax_line_id = %s
                                WHERE id = %s
                                """, (taxes.id, tax_lines.id))
            # account_move_line.write(
            #     {
            #         "tax_line_id": taxes.id
            #     })
            # tax_lines.unlink()
            # repost
            # move.action_post()

        return True




