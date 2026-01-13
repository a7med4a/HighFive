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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('exp.code') or _('New')
        return super().create(vals_list)


    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise exceptions.ValidationError(_('Cannot delete a expense After Confirm'))
        return super(easy_expense, self).unlink()

    # @api.model
    # def apply_tax_to_move(self):
    #     for exp in self:
    #         if not exp.move_id:
    #             continue
    #
    #         move = exp.move_id
    #
    #         # unpost move if posted
    #         if move.state == 'posted':
    #             move.button_draft()
    #
    #         # get product taxes
    #         taxes = exp.product_id.supplier_taxes_id
    #
    #         # apply tax on all lines (or only the relevant line)
    #         for line in move.line_ids:
    #             if line.debit:
    #                 line.tax_ids = taxes
    #
    #         # repost
    #         move.action_post()
    #
    #     return True




