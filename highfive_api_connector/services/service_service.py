# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ServiceService:
    """Service (Additional Service) Processing Service"""
    
    def __init__(self, env):
        self.env = env
    
    def process(self, data):
        """
        Process service data
        
        Args:
            data: Service data from HighFive
            {
                "id": 10,
                "name": "Equipment Rental",
                "price": 10.00,
                "description": "Sports equipment rental",
                "category": "equipment"
            }
            
        Returns:
            Result dictionary with action and record info
        """
        # Validate
        self._validate(data)
        
        # Transform
        vals = self._transform(data)
        
        # Create or Update
        service = self.env['product.template'].search([
            ('highfive_service_id', '=', str(data['id']))
        ], limit=1)
        print("vals ==> ",vals)
        print("service ==> ",service)
        if service:
            service.write(vals)
            print("service.is_highfive_service",service.is_highfive_service)
            _logger.info(f"Updated service {service.id}: {service.name}")
            
            return {
                'action': 'updated',
                'service_id': service.id,
                'service_name': service.name,
                'model': 'product.template',
            }
        else:
            service = self.env['product.template'].create(vals)
            _logger.info(f"Created service {service.id}: {service.name}")
            
            # Ensure product variant is created
            if not service.product_variant_ids:
                _logger.warning(f"No variant created for service {service.id}, creating manually...")
                service._create_variant_ids()
                _logger.info(f"Created {len(service.product_variant_ids)} variant(s) for service {service.id}")
            
            # Verify variant exists
            if not service.product_variant_ids:
                raise ValidationError(f"Failed to create product variant for service {service.id}")
            
            return {
                'action': 'created',
                'service_id': service.id,
                'service_name': service.name,
                'model': 'product.template',
                'variant_id': service.product_variant_id.id if service.product_variant_id else None
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
            'highfive_service_id': str(data['id']),
            'name': data['name'],
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'list_price': float(data.get('price', 0)),
            'standard_price': 0,  # No cost for service
            'is_highfive_unit': False,  # Important: NOT a unit
            'is_highfive_service': True,  # Important: NOT a unit
        }
        partner = data.get('partner_id',False)
        branch = self.env['highfive.partner.branch']
        if partner:
            branch = self.env['highfive.partner.branch'].search([
                ('partner_id', '=', int(partner))
            ], limit=1)
        
        # Optional fields
        if branch:
            vals['branch_id'] = branch.id
        if data.get('description'):
            vals['description'] = data['description']
        
        if data.get('category'):
            vals['categ_id'] = self._get_category(data['category'])
        
        return vals
    
    def _get_category(self, category_name):
        """Get or create product category"""
        category = self.env['product.category'].search([
            ('name', '=', category_name)
        ], limit=1)
        
        if not category:
            category = self.env['product.category'].create({
                'name': category_name
            })
            _logger.info(f"Created product category: {category_name}")
        
        return category.id
