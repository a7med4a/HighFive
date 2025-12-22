# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CustomerService:
    """Customer (Player) Processing Service"""
    
    def __init__(self, env):
        self.env = env
    
    def process(self, data):
        """Process customer data"""
        # Validate
        self._validate(data)
        
        # Transform
        vals = self._transform(data)
        
        # Create or Update
        customer = self.env['res.partner'].search([
            ('highfive_customer_id', '=', str(data['id']))
        ], limit=1)
        
        if customer:
            customer.write(vals)
            _logger.info(f"Updated customer {customer.id}: {customer.name}")
            
            return {
                'action': 'updated',
                'customer_id': customer.id,
                'customer_name': customer.name,
                'model': 'res.partner',
            }
        else:
            customer = self.env['res.partner'].create(vals)
            _logger.info(f"Created customer {customer.id}: {customer.name}")
            
            return {
                'action': 'created',
                'customer_id': customer.id,
                'customer_name': customer.name,
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
            'highfive_customer_id': str(data['id']),
            'name': data['name'],
            'is_highfive_customer': True,
            'customer_rank': 1,
        }
        
        # Optional fields
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
        
        # City
        if data.get('city'):
            vals['city'] = data['city']
        
        return vals
