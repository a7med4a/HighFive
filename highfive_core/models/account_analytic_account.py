# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # نحتاج فقط هذا الحقل لربط الفروع
    highfive_branch_id = fields.Many2one(
        'highfive.partner.branch',
        string='HighFive Branch',
        help='The branch this analytic account belongs to (if applicable)'
    )

    # Optional: computed field لمعرفة النوع
    highfive_account_type = fields.Selection([
        ('supplier', 'Supplier Account'),
        ('branch', 'Branch Account'),
    ], string='Account Type', compute='_compute_highfive_account_type', store=True)

    @api.depends('highfive_branch_id')
    def _compute_highfive_account_type(self):
        for record in self:
            if record.highfive_branch_id:
                record.highfive_account_type = 'branch'
            elif record.partner_id and record.partner_id.is_highfive_partner:
                record.highfive_account_type = 'supplier'
            else:
                record.highfive_account_type = False

    # -------------------------------------------------------------------------
    # Enhanced Display
    # -------------------------------------------------------------------------
    def name_get(self):
        """Enhanced name display with code"""
        result = []
        for account in self:
            if account.code:
                name = f"[{account.code}] {account.name}"
            else:
                name = account.name
            result.append((account.id, name))
        return result

    def action_view_highfive_analytics(self):
        """Open HighFive analytic accounts"""
        plan = self.env.ref('highfive_core.analytic_plan_highfive', raise_if_not_found=False)

        domain = []
        if plan:
            domain = [('plan_id', '=', plan.id)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'HighFive Analytic Accounts',
            'res_model': 'account.analytic.account',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_plan_id': plan.id if plan else False},
            'help': '''
                   <p class="o_view_nocontent_empty_folder">
                       No analytic accounts yet
                   </p>
                   <p>
                       Analytic accounts are created automatically when you create suppliers and branches.
                       Advanced reporting features will be added in future modules.
                   </p>
               '''
        }


