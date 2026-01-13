# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class UnitService:
    """Unit (Product/Service) Processing Service"""

    def __init__(self, env):
        self.env = env

    def process(self, data):
        """
        Process unit data (with default commission)

        Args:
            data: Unit data from HighFive including default_commission

        Returns:
            Result dictionary with action and record info
        """
        # Validate
        self._validate(data)

        # Transform
        vals = self._transform(data)

        # Create or Update Unit
        unit = self.env['product.template'].search([
            ('highfive_unit_id', '=', str(data['id']))
        ], limit=1)

        if unit:
            unit.write(vals)
            action = 'updated'
            _logger.info(f"Updated unit {unit.id}: {unit.name}")
        else:
            unit = self.env['product.template'].create(vals)
            action = 'created'
            _logger.info(f"Created unit {unit.id}: {unit.name}")

        # Handle Default Commission
        commission_result = self._handle_default_commission(unit, data)

        return {
            'action': action,
            'unit_id': unit.id,
            'unit_name': unit.name,
            'model': 'product.template',
            'commission': commission_result
        }

    def _validate(self, data):
        """Validate required fields"""
        # Changed: partner_branch_id instead of partner_id
        required_fields = ['id', 'name', 'partner_branch_id']

        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")

    def _transform(self, data):
        """Transform HighFive data to Odoo format"""
        # Get branch (not partner directly)
        branch = self.env['highfive.partner.branch'].search([
            ('highfive_branch_id', '=', str(data['partner_branch_id']))
        ], limit=1)

        if not branch:
            raise ValidationError(f"Branch {data['partner_branch_id']} not found")

        vals = {
            'highfive_unit_id': str(data['id']),
            'name': data['name'],
            'is_highfive_unit': True,
            'type': 'service',
            'list_price': float(data.get('base_price', 0)),
            'standard_price': 0,  # No cost for service
            'branch_id': branch.id,  # FIXED: Use partner_branch_id
        }

        # Optional fields
        if data.get('description'):
            vals['description'] = data['description']

        if data.get('activity_type'):
            vals['activity_type'] = data['activity_type']

        return vals

    def _handle_default_commission(self, unit, data):
        """
        Handle default commission for unit

        Args:
            unit: product.template record
            data: Original data from HighFive

        Returns:
            dict: Commission result
        """
        default_commission = data.get('default_commission', {})

        if not default_commission:
            _logger.warning(f"No default commission provided for unit {unit.id}")
            return {'action': 'skipped', 'reason': 'No commission data'}

        # Check if default commission exists
        existing = self.env['highfive.unit.commission'].search([
            ('unit_id', '=', unit.id),
            ('type', '=', 'default')
        ], limit=1)

        # Prepare commission values
        commission_vals = {
            'unit_id': unit.id,
            'type': 'default',
            'name': f'Default - {unit.name}',
        }

        # Online commission
        online = default_commission.get('online', {})
        if online:
            commission_vals['online_booking'] = json.dumps({
                'type': online.get('type', 'percentage'),
                'value': float(online.get('value', 0))
            })

        # Cash commission
        cash = default_commission.get('cash', {})
        if cash:
            commission_vals['cash_booking'] = json.dumps({
                'type': cash.get('type', 'percentage'),
                'value': float(cash.get('value', 0))
            })

        if existing:
            existing.write(commission_vals)
            _logger.info(f"Updated default commission for unit {unit.id}")
            return {
                'action': 'updated',
                'commission_id': existing.id
            }
        else:
            commission = self.env['highfive.unit.commission'].create(commission_vals)
            _logger.info(f"Created default commission for unit {unit.id}")
            return {
                'action': 'created',
                'commission_id': commission.id
            }