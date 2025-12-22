# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class UnitService:
    """Unit Processing Service"""
    
    def __init__(self, env):
        self.env = env
    
    def process(self, data):
        """Process unit data"""
        # Validate
        self._validate(data)
        
        # Get branch
        branch = self._get_branch(data.get('partner_branch_id'))
        
        # Transform
        vals = self._transform(data, branch)
        
        # Create or Update
        unit = self.env['product.template'].search([
            ('highfive_unit_id', '=', str(data['id']))
        ], limit=1)
        
        if unit:
            unit.write(vals)
            _logger.info(f"Updated unit {unit.id}: {unit.name}")
            
            return {
                'action': 'updated',
                'unit_id': unit.id,
                'unit_name': unit.name,
                'model': 'product.template',
            }
        else:
            unit = self.env['product.template'].create(vals)
            _logger.info(f"Created unit {unit.id}: {unit.name}")
            
            return {
                'action': 'created',
                'unit_id': unit.id,
                'unit_name': unit.name,
                'model': 'product.template',
            }
    
    def _validate(self, data):
        """Validate required fields"""
        required_fields = ['id', 'name', 'partner_branch_id']
        
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")
    
    def _get_branch(self, branch_id):
        """Get branch for unit"""
        if not branch_id:
            raise ValidationError("Unit must have a partner_branch_id")
        
        branch = self.env['highfive.partner.branch'].search([
            ('highfive_branch_id', '=', str(branch_id))
        ], limit=1)
        
        if not branch:
            raise ValidationError(
                f"Branch with highfive_branch_id={branch_id} not found. "
                f"Please sync the branch first."
            )
        
        return branch

    def _transform(self, data, branch):
        """Transform HighFive data to Odoo format"""
        vals = {
            'highfive_unit_id': str(data['id']),
            'name': data['name'],
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'branch_id': branch.id,  # ✅ استخدم branch_id
        }

        # Price
        if data.get('base_price'):
            vals['list_price'] = float(data['base_price'])

        # Description
        if data.get('description'):
            vals['description_sale'] = data['description']

        # Category
        if data.get('activity_type'):
            category = self.env['product.category'].search([
                ('name', '=', data['activity_type'])
            ], limit=1)

            if not category:
                category = self.env['product.category'].create({
                    'name': data['activity_type']
                })

            vals['categ_id'] = category.id

        return vals