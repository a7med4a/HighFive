# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PartnerService:
    """Partner (Supplier) Processing Service"""
    
    def __init__(self, env):
        self.env = env
    
    def process(self, data):
        """
        Process partner data
        
        Args:
            data: Partner data from HighFive
            
        Returns:
            Result dictionary with action and record info
        """
        # Validate
        self._validate(data)
        
        # Transform
        vals = self._transform(data)
        
        # Create or Update
        partner = self.env['res.partner'].search([
            ('highfive_partner_id', '=', str(data['id']))
        ], limit=1)
        
        if partner:
            partner.write(vals)
            _logger.info(f"Updated partner {partner.id}: {partner.name}")
            
            return {
                'action': 'updated',
                'partner_id': partner.id,
                'partner_name': partner.name,
                'model': 'res.partner',
            }
        else:
            partner = self.env['res.partner'].create(vals)
            _logger.info(f"Created partner {partner.id}: {partner.name}")
            
            return {
                'action': 'created',
                'partner_id': partner.id,
                'partner_name': partner.name,
                'model': 'res.partner',
            }
    
    def _validate(self, data):
        """Validate required fields"""
        required_fields = ['id', 'name']
        
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")
    
    def _transform(self, data):
        """Transform HighFive data to Odoo format"""
        vals = {
            'highfive_partner_id': str(data['id']),
            'name': data['name'],
            'is_highfive_partner': True,
            'supplier_rank': 1,
        }
        
        # Optional fields
        if data.get('company_name'):
            vals['company_name'] = data['company_name']
        
        if data.get('email'):
            vals['email'] = data['email']
        
        if data.get('phone'):
            vals['phone'] = data['phone']
        
        # Country
        if data.get('country'):
            country = self.env['res.country'].search([
                ('code', '=', data['country'])
            ], limit=1)
            if country:
                vals['country_id'] = country.id
        
        # Tax status
        if data.get('tax') and data.get('accept_tax'):
            tax_value = str(data['tax'])
            
            if tax_value == '15' and data['accept_tax']:
                vals['tax_status'] = 'standard_15'
            elif tax_value == '5' and data['accept_tax']:
                vals['tax_status'] = 'reduced_5'
            elif not data['accept_tax']:
                vals['tax_status'] = 'exempt'
            else:
                vals['tax_status'] = 'standard_15'
        
        # Commission rates
        if data.get('commission_rate_online'):
            vals['commission_rate_online'] = float(data['commission_rate_online'])
        
        if data.get('commission_rate_cash'):
            vals['commission_rate_cash'] = float(data['commission_rate_cash'])
        
        return vals
