# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class BranchService:
    """Branch Processing Service"""
    
    def __init__(self, env):
        self.env = env
    
    def process(self, data):
        """Process branch data"""
        # Validate
        self._validate(data)
        
        # Get partner
        partner = self._get_partner(data.get('partner_id'))
        
        # Transform
        vals = self._transform(data, partner)
        
        # Create or Update
        branch = self.env['highfive.partner.branch'].search([
            ('highfive_branch_id', '=', str(data['id']))
        ], limit=1)
        
        if branch:
            branch.write(vals)
            _logger.info(f"Updated branch {branch.id}: {branch.name}")
            
            return {
                'action': 'updated',
                'branch_id': branch.id,
                'branch_name': branch.name,
                'model': 'highfive.partner.branch',
            }
        else:
            branch = self.env['highfive.partner.branch'].create(vals)
            _logger.info(f"Created branch {branch.id}: {branch.name}")
            
            return {
                'action': 'created',
                'branch_id': branch.id,
                'branch_name': branch.name,
                'model': 'highfive.partner.branch',
            }
    
    def _validate(self, data):
        """Validate required fields"""
        required_fields = ['id', 'name', 'partner_id']
        
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")
    
    def _get_partner(self, partner_id):
        """Get partner for branch"""
        if not partner_id:
            raise ValidationError("Branch must have a partner_id")
        
        partner = self.env['res.partner'].search([
            ('highfive_partner_id', '=', str(partner_id))
        ], limit=1)
        
        if not partner:
            raise ValidationError(
                f"Partner with highfive_partner_id={partner_id} not found. "
                f"Please sync the partner first."
            )
        
        return partner
    
    def _transform(self, data, partner):
        """Transform HighFive data to Odoo format"""
        vals = {
            'highfive_branch_id': str(data['id']),
            'name': data['name'],
            'partner_id': partner.id,
        }
        
        # Code
        if data.get('code'):
            vals['code'] = data['code']
        
        # Location
        if data.get('country'):
            country = self.env['res.country'].search([
                ('code', '=', data['country'])
            ], limit=1)
            if country:
                vals['country_id'] = country.id
        
        if data.get('state'):
            state = self.env['res.country.state'].search([
                ('name', 'ilike', data['state']),
                ('country_id', '=', vals.get('country_id'))
            ], limit=1)
            if state:
                vals['state_id'] = state.id
        
        if data.get('city'):
            vals['city'] = data['city']
        
        if data.get('street'):
            vals['street'] = data['street']
        
        # GPS
        if data.get('latitude'):
            vals['latitude'] = float(data['latitude'])
        
        if data.get('longitude'):
            vals['longitude'] = float(data['longitude'])
        
        return vals
