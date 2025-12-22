# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # -------------------------------------------------------------------------
    # HighFive Identifiers
    # -------------------------------------------------------------------------
    highfive_partner_id = fields.Char(
        string="HighFive Partner ID",
        copy=False,
        index=True,
        help="Unique identifier from HighFive system for suppliers/partners"
    )
    highfive_customer_id = fields.Char(
        string="HighFive Customer ID",
        copy=False,
        index=True,
        help="Unique identifier from HighFive system for customers"
    )
    highfive_account_name = fields.Char(
        string="HighFive Account Name",
        help="Account name as it appears in HighFive system"
    )

    # -------------------------------------------------------------------------
    # HighFive Classification
    # -------------------------------------------------------------------------
    is_highfive_partner = fields.Boolean(
        string="HighFive Partner",
        default=False,
        help="This partner is a HighFive service provider (supplier/owner).",
    )
    is_highfive_customer = fields.Boolean(
        string="HighFive Customer",
        default=False,
        help="This partner is a HighFive customer (end user).",
    )

    # -------------------------------------------------------------------------
    # Tax Configuration
    # -------------------------------------------------------------------------
    tax_status = fields.Selection([
        ('standard_15', 'Standard VAT 15%'),
        ('reduced_5', 'Reduced VAT 5%'),
        ('zero_rated', 'Zero Rated 0%'),
        ('exempt', 'VAT Exempt')
    ], string='Tax Status',
        default='standard_15',
        help="Tax status for this supplier as received from HighFive system. "
             "This determines which VAT rate applies to purchase invoices from this partner.")

    # -------------------------------------------------------------------------
    # Commission Configuration
    # -------------------------------------------------------------------------
    commission_rate_online = fields.Float(
        string='Default Online Commission %',
        digits=(5, 2),
        help="Default commission rate for online bookings (can be overridden at unit level)"
    )
    commission_rate_cash = fields.Float(
        string='Default Cash Commission %',
        digits=(5, 2),
        help="Default commission rate for cash bookings (can be overridden at unit level)"
    )

    # -------------------------------------------------------------------------
    # Analytic Hierarchy
    # -------------------------------------------------------------------------
    analytic_parent_id = fields.Many2one(
        "account.analytic.account",
        string="Supplier Analytic Account (Parent)",
        copy=False,
        ondelete="restrict",
        help="Parent analytic account for tracking all revenues and costs related to this supplier"
    )

    # -------------------------------------------------------------------------
    # Branches
    # -------------------------------------------------------------------------
    branch_ids = fields.One2many(
        "highfive.partner.branch",
        "partner_id",
        string="HighFive Branches",
    )
    branch_count = fields.Integer(
        string='Branches',
        compute='_compute_branch_count',
        help="Number of branches for this partner"
    )
    analytic_account_count = fields.Integer(
        string='Analytic Accounts',
        compute='_compute_analytic_account_count',
        help="Number of analytic accounts (supplier + branches)"
    )


    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        (
            "highfive_partner_id_uniq",
            "unique(highfive_partner_id)",
            "HighFive Partner ID must be unique.",
        ),
        (
            "highfive_customer_id_uniq",
            "unique(highfive_customer_id)",
            "HighFive Customer ID must be unique.",
        ),
    ]

    # -------------------------------------------------------------------------
    # Computed Fields
    # -------------------------------------------------------------------------
    @api.depends('branch_ids')
    def _compute_branch_count(self):
        for partner in self:
            partner.branch_count = len(partner.branch_ids)

    @api.depends('analytic_parent_id', 'branch_ids.analytic_account_id')
    def _compute_analytic_account_count(self):
        """Count analytic accounts for this supplier"""
        for partner in self:
            if not partner.is_highfive_partner:
                partner.analytic_account_count = 0
                continue

            # Get plan
            plan = self.env.ref('highfive_core.analytic_plan_highfive', raise_if_not_found=False)

            # Count all analytic accounts for this partner
            domain = [('partner_id', '=', partner.id)]
            if plan:
                domain.append(('plan_id', '=', plan.id))

            partner.analytic_account_count = self.env['account.analytic.account'].search_count(domain)
    # -------------------------------------------------------------------------
    # Business Constraints
    # -------------------------------------------------------------------------
    @api.constrains("is_highfive_partner", "is_highfive_customer")
    def _check_highfive_roles(self):
        """Ensure a partner cannot be both supplier and customer"""
        for rec in self:
            if rec.is_highfive_partner and rec.is_highfive_customer:
                raise ValidationError(
                    _("Partner cannot be both HighFive Partner (Supplier) and HighFive Customer.")
                )

    @api.constrains('commission_rate_online', 'commission_rate_cash')
    def _check_commission_rates(self):
        """Ensure commission rates are valid percentages"""
        for rec in self:
            if rec.commission_rate_online < 0 or rec.commission_rate_online > 100:
                raise ValidationError(
                    _("Online commission rate must be between 0 and 100.")
                )
            if rec.commission_rate_cash < 0 or rec.commission_rate_cash > 100:
                raise ValidationError(
                    _("Cash commission rate must be between 0 and 100.")
                )

    # -------------------------------------------------------------------------
    # Create / Write
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle HighFive-specific logic"""
        partners = super().create(vals_list)

        # Post-create actions (safe because records now exist)
        for partner, vals in zip(partners, vals_list):
            partner._apply_highfive_ranks(vals)
            if vals.get("is_highfive_partner"):
                partner._ensure_supplier_analytic_parent()

        return partners

    def write(self, vals):
        """Override write to handle HighFive-specific logic"""
        res = super().write(vals)

        # Apply ranks if flags changed
        if "is_highfive_partner" in vals or "is_highfive_customer" in vals:
            for partner in self:
                partner._apply_highfive_ranks(vals)

        # Create analytic account ONLY when supplier flag is explicitly turned on
        if "is_highfive_partner" in vals:
            for partner in self:
                if partner.is_highfive_partner:
                    partner._ensure_supplier_analytic_parent()

        return res

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _apply_highfive_ranks(self, vals):
        """
        Keep Odoo ranks consistent with HighFive classification.
        - HighFive Partner => supplier_rank >= 1
        - HighFive Customer => customer_rank >= 1
        
        We don't force reset to 0 to avoid side effects if partner is also 
        used elsewhere in the system.
        """
        self.ensure_one()

        # If flags are in vals, use post-write/current record values
        if "is_highfive_partner" in vals and self.is_highfive_partner:
            if self.supplier_rank < 1:
                self.supplier_rank = 1
                _logger.debug(f"Set supplier_rank=1 for partner {self.id} ({self.name})")

        if "is_highfive_customer" in vals and self.is_highfive_customer:
            if self.customer_rank < 1:
                self.customer_rank = 1
                _logger.debug(f"Set customer_rank=1 for partner {self.id} ({self.name})")

        # Also handle create case where vals may not include both keys
        if vals.get("is_highfive_partner") and self.supplier_rank < 1:
            self.supplier_rank = 1
        if vals.get("is_highfive_customer") and self.customer_rank < 1:
            self.customer_rank = 1

    def _get_default_analytic_plan_id(self):
        """Get the default HighFive analytic plan"""
        plan = self.env.ref(
            "highfive_core.analytic_plan_highfive",
            raise_if_not_found=False
        )
        return plan.id if plan else False

    def _ensure_supplier_analytic_parent(self):
        """
        Ensure that this partner has a parent analytic account.
        
        This method is idempotent and safe to call multiple times.
        It will only create the analytic account if:
        1. The partner is marked as HighFive partner (is_highfive_partner=True)
        2. No analytic parent exists yet (analytic_parent_id is False)
        
        The created analytic account will be linked to the HighFive Operations
        analytic plan and will serve as the parent for all branch-level analytics.
        
        Returns:
            None
        
        Raises:
            None (method is designed to be safe)
        """
        self.ensure_one()

        if not self.is_highfive_partner:
            # Not a supplier/partner → no analytic should be created
            _logger.debug(f"Skipping analytic creation for partner {self.id} - not a HighFive partner")
            return

        if self.analytic_parent_id:
            # Already exists → do nothing
            _logger.debug(f"Analytic parent already exists for partner {self.id}")
            return

        _logger.info(f"Creating supplier analytic parent for partner {self.id} ({self.name})")

        Analytic = self.env["account.analytic.account"].sudo()
        plan = self.env.ref(
            "highfive_core.analytic_plan_highfive",
            raise_if_not_found=False
        )

        vals = {
            "name": f"Supplier - {self.name}",
            "partner_id": self.id,
            "plan_id": plan.id if plan else False,
            "code": f"SUP-{self.id:06d}",  # e.g., SUP-000001
        }

        try:
            analytic = Analytic.create(vals)
            self.analytic_parent_id = analytic.id
            _logger.info(
                f"Successfully created analytic parent {analytic.id} "
                f"for partner {self.id} ({self.name})"
            )
        except Exception as e:
            _logger.error(
                f"Failed to create analytic parent for partner {self.id}: {str(e)}"
            )
            raise

    # -------------------------------------------------------------------------
    # Deletion Safety
    # -------------------------------------------------------------------------
    def unlink(self):
        """Prevent deletion of partners with branches"""
        for partner in self:
            if partner.branch_ids:
                raise ValidationError(
                    _("You cannot delete a HighFive Partner that has linked branches. "
                      "Please delete all branches first.")
                )
        return super().unlink()

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_open_highfive_branches(self):
        """Open the branches view for this partner"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "HighFive Branches",
            "res_model": "highfive.partner.branch",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {
                "default_partner_id": self.id,
                "search_default_partner_id": self.id,
            },
        }

    def action_view_analytic_accounts(self):
        """Open all analytic accounts for this supplier (including branches)"""
        self.ensure_one()

        if not self.is_highfive_partner:
            raise ValidationError(
                _("This partner is not a HighFive supplier.")
            )

        # Get HighFive plan
        plan = self.env.ref('highfive_core.analytic_plan_highfive', raise_if_not_found=False)

        # Build domain
        domain = [
            ('partner_id', '=', self.id),
        ]
        if plan:
            domain.append(('plan_id', '=', plan.id))

        return {
            'type': 'ir.actions.act_window',
            'name': f'Analytic Accounts - {self.name}',
            'res_model': 'account.analytic.account',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.id,
                'default_plan_id': plan.id if plan else False,
            },
            'help': '''
                <p class="o_view_nocontent_empty_folder">
                    No analytic accounts found
                </p>
                <p>
                    Analytic accounts are created automatically when you create the supplier and its branches.
                </p>
            '''
        }