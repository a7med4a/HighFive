# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # -------------------------------------------------------------------------
    # HighFive Identifiers
    # -------------------------------------------------------------------------
    highfive_unit_id = fields.Char(
        string="HighFive Unit ID",
        copy=False,
        index=True,
        help="Unique identifier from HighFive system for this unit/service"
    )

    # -------------------------------------------------------------------------
    # HighFive Relations
    # -------------------------------------------------------------------------
    branch_id = fields.Many2one(
        "highfive.partner.branch",
        string="HighFive Branch",
        ondelete="restrict",
        help="Operational branch that provides this unit/service.",
    )
    is_highfive_service = fields.Boolean(
        'Is HighFive Service',
        default=False,
        help='Check this if this is an additional service (not a main unit)'
    )
    is_highfive_unit = fields.Boolean(
        string='Is HighFive Unit',
        store=True,
        help='Automatically set when highfive_unit_id is provided'
    )
    highfive_service_id = fields.Char(
        string="HighFive Service ID",
        copy=False,
        index=True,
        help="Unique identifier from HighFive system for additional services"
    )
    
    partner_id = fields.Many2one(
        "res.partner",
        string="HighFive Supplier",
        related="branch_id.partner_id",
        store=True,
        readonly=True,
        help="Supplier/partner that owns the branch providing this service"
    )

    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------
    _sql_constraints = [
        (
            "highfive_unit_id_uniq",
            "unique(highfive_unit_id)",
            "HighFive Unit ID must be unique.",
        ),
        (
            "highfive_service_id_uniq",
            "unique(highfive_service_id)",
            "HighFive Service ID must be unique.",
        ),
    ]

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains("highfive_unit_id", "branch_id", "type", "invoice_policy")
    def _check_highfive_unit(self):
        """
        Validate HighFive unit configuration.
        
        Rules:
        1. HighFive units must be of type 'Service'
        2. HighFive units must be linked to a branch
        3. HighFive units must use 'Ordered quantities' invoice policy
        
        Raises:
            ValidationError: If any validation rule is violated
        """
        for product in self:
            if product.highfive_unit_id:
                _logger.debug(f"Validating HighFive unit {product.id} ({product.name})")
                
                # Check type
                if product.type != "service":
                    raise ValidationError(
                        _("HighFive Unit '%s' must be of type 'Service', not '%s'.") 
                        % (product.name, product.type)
                    )
                
                # Check branch link
                if not product.branch_id:
                    raise ValidationError(
                        _("HighFive Unit '%s' must be linked to a Branch.") 
                        % product.name
                    )
                
                # Check invoice policy
                if product.invoice_policy != 'order':
                    raise ValidationError(
                        _("HighFive Unit '%s' must use 'Ordered quantities' invoice policy.") 
                        % product.name
                    )
                
                _logger.debug(f"HighFive unit {product.id} validation passed")

    # -------------------------------------------------------------------------
    # Defaults
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        """Set default values for HighFive units"""
        defaults = super().default_get(fields_list)
        
        # If creating from HighFive context, set service defaults
        if self.env.context.get('default_highfive_unit_id'):
            defaults.update({
                'type': 'service',
                'invoice_policy': 'order',
                'sale_ok': True,
                'purchase_ok': False,
            })
        
        return defaults

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_view_branch(self):
        """Open the branch record for this product"""
        self.ensure_one()
        
        if not self.branch_id:
            raise ValidationError(_("This product is not linked to any branch."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Branch',
            'res_model': 'highfive.partner.branch',
            'res_id': self.branch_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_supplier(self):
        """Open the supplier/partner record for this product"""
        self.ensure_one()
        
        if not self.partner_id:
            raise ValidationError(_("This product is not linked to any supplier."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Inherit the same fields from template for easier access
    highfive_unit_id = fields.Char(
        related='product_tmpl_id.highfive_unit_id',
        string="HighFive Unit ID",
        readonly=True,
        store=True
    )
    
    branch_id = fields.Many2one(
        related='product_tmpl_id.branch_id',
        string="HighFive Branch",
        readonly=True,
        store=True
    )
    
    partner_id = fields.Many2one(
        related='product_tmpl_id.partner_id',
        string="HighFive Supplier",
        readonly=True,
        store=True
    )
