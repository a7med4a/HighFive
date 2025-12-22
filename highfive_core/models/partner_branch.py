# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HighFivePartnerBranch(models.Model):
    _name = "highfive.partner.branch"
    _description = "HighFive Partner Branch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, name"

    # -------------------------------------------------------------------------
    # Basic Info
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Branch Name",
        required=True,
        tracking=True,
        help="Name of the branch as it appears in HighFive system"
    )
    code = fields.Char(
        string="Branch Code",
        tracking=True,
        help="Internal code for the branch"
    )
    highfive_branch_id = fields.Char(
        string="HighFive Branch ID",
        required=True,
        copy=False,
        index=True,
        help="Unique identifier from HighFive system"
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        required=True,
        domain=[("is_highfive_partner", "=", True)],
        ondelete="restrict",
        tracking=True,
        help="The supplier/partner that owns this branch"
    )
    
    partner_name = fields.Char(
        related='partner_id.name',
        string='Supplier Name',
        store=True,
        readonly=True
    )

    # -------------------------------------------------------------------------
    # Location
    # -------------------------------------------------------------------------
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        default=lambda self: self.env.ref('base.sa', False),  # Saudi Arabia as default
        help="Country where the branch is located"
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        domain="[('country_id', '=', country_id)]",
        help="State/Province where the branch is located"
    )
    city = fields.Char(
        string="City",
        help="City where the branch is located"
    )
    street = fields.Char(
        string="Street",
        help="Street address of the branch"
    )

    latitude = fields.Char(
        string="Latitude",
        help="GPS Latitude coordinate"
    )
    longitude = fields.Char(
        string="Longitude",
        help="GPS Longitude coordinate"
    )

    active = fields.Boolean(
        default=True,
        tracking=True
    )

    # -------------------------------------------------------------------------
    # Analytic Account (Child)
    # -------------------------------------------------------------------------
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Branch Analytic Account",
        copy=False,
        ondelete="restrict",
        required=False,
        readonly=True,
        help="Analytic account for tracking revenues and costs specific to this branch"
    )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    unit_count = fields.Integer(
        string="Units",
        compute="_compute_unit_count",
        help="Number of units/services under this branch"
    )



    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        (
            "highfive_branch_id_uniq",
            "unique(highfive_branch_id)",
            "HighFive Branch ID must be unique.",
        ),
    ]



    # -------------------------------------------------------------------------
    # Computed Fields
    # -------------------------------------------------------------------------
    @api.depends('partner_id')
    def _compute_unit_count(self):
        """Count units/products linked to this branch"""
        for branch in self:
            branch.unit_count = self.env['product.template'].search_count([
                ('branch_id', '=', branch.id)
            ])



    # -------------------------------------------------------------------------
    # Create / Write
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-create analytic account"""
        records = super().create(vals_list)

        for rec, vals in zip(records, vals_list):
            # Ensure analytic child only if partner is provided
            if vals.get("partner_id"):
                rec._ensure_branch_analytic_child()

        return records

    def write(self, vals):
        """Override write to handle analytic account updates"""
        res = super().write(vals)

        # Only ensure analytic when partner changes
        if "partner_id" in vals:
            for rec in self:
                rec._ensure_branch_analytic_child()

        return res

    # -------------------------------------------------------------------------
    # Analytic Logic
    # -------------------------------------------------------------------------
    def _ensure_branch_analytic_child(self):
        """
        Ensure that this branch has an analytic account.

        This method is idempotent and safe to call multiple times.
        It will:
        1. Validate that the branch is linked to a HighFive partner
        2. Ensure the supplier parent analytic account exists
        3. Create an analytic account if it doesn't exist

        Note: In Odoo 18, analytic accounts are flat (no parent_id).
        The relationship is tracked via plan_id only.

        Raises:
            ValidationError: If branch is not linked to a HighFive partner
                           or if supplier analytic parent is missing
        """
        self.ensure_one()

        # Validate partner
        if not self.partner_id or not self.partner_id.is_highfive_partner:
            raise ValidationError(
                _("Branch '%s' must be linked to a HighFive Partner.") % self.name
            )

        # Ensure supplier parent analytic exists
        self.partner_id._ensure_supplier_analytic_parent()

        # If analytic already exists, skip
        if self.analytic_account_id:
            _logger.debug(f"Analytic account already exists for branch {self.id}")
            return

        # Get supplier parent analytic (for reference in naming)
        supplier_parent = self.partner_id.analytic_parent_id
        if not supplier_parent:
            raise ValidationError(
                _("Supplier analytic parent account is missing for partner '%s'.")
                % self.partner_id.name
            )

        _logger.info(
            f"Creating branch analytic account for branch {self.id} "
            f"({self.name}) under plan {supplier_parent.plan_id.name if supplier_parent.plan_id else 'None'}"
        )

        # Get analytic plan
        plan = self.env.ref(
            "highfive_core.analytic_plan_highfive",
            raise_if_not_found=False
        )

        # Prepare values (no parent_id in Odoo 18)
        vals = {
            "name": f"Branch - {self.partner_id.name} / {self.name}",
            "partner_id": self.partner_id.id,  # ✅ المورد
            "highfive_branch_id": self.id,      # ✅ الفرع
            "plan_id": plan.id if plan else False,
            "code": f"BRN-{self.id:06d}",  # e.g., BRN-000001
        }

        try:
            analytic = self.env["account.analytic.account"].create(vals)
            self.analytic_account_id = analytic.id
            _logger.info(
                f"Successfully created branch analytic account {analytic.id} "
                f"for branch {self.id} ({self.name})"
            )
        except Exception as e:
            _logger.error(
                f"Failed to create branch analytic account for branch {self.id}: {str(e)}"
            )
            raise
    # -------------------------------------------------------------------------
    # Deletion Safety
    # -------------------------------------------------------------------------
    def unlink(self):
        """Prevent deletion of branches with financial transactions"""
        AnalyticLine = self.env["account.analytic.line"]
        
        for branch in self:
            # Check if branch has any analytic lines (transactions)
            if branch.analytic_account_id:
                line_count = AnalyticLine.search_count([
                    ('account_id', '=', branch.analytic_account_id.id)
                ])
                if line_count > 0:
                    raise ValidationError(
                        _("You cannot delete branch '%s' because it has %d financial transaction(s). "
                          "Please archive it instead.") % (branch.name, line_count)
                    )
            
            # Check if branch has any units
            if branch.unit_count > 0:
                raise ValidationError(
                    _("You cannot delete branch '%s' because it has %d unit(s). "
                      "Please delete or reassign the units first.") % (branch.name, branch.unit_count)
                )
        
        return super().unlink()

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_open_units(self):
        """Open units/products for this branch"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Units - {self.name}',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
            'context': {
                'default_branch_id': self.id,
                'default_type': 'service',
            }
        }

    # -------------------------------------------------------------------------
    # Name Get
    # -------------------------------------------------------------------------
    def name_get(self):
        """Display branch name with partner name for clarity"""
        result = []
        for branch in self:
            name = f"{branch.partner_id.name} / {branch.name}"
            result.append((branch.id, name))
        return result
