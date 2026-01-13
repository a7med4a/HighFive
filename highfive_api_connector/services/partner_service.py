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

        # Address fields - NEW
        if data.get('street'):
            vals['street'] = data['street']

        if data.get('city'):
            vals['city'] = data['city']

        # VAT number (الرقم الضريبي) - NEW
        if data.get('vat'):
            vals['vat'] = data['vat']

        # Country
        if data.get('country'):
            country = self.env['res.country'].search([
                ('code', '=', data['country'])
            ], limit=1)
            if country:
                vals['country_id'] = country.id

        # Tax status - FIXED: Default to 15%
        tax_value = data.get('tax', '15')  # Default to 15%
        accept_tax = data.get('accept_tax', True)  # Default to True

        if str(tax_value) == '15' and accept_tax:
            vals['tax_status'] = 'standard_15'
        elif str(tax_value) == '5' and accept_tax:
            vals['tax_status'] = 'reduced_5'
        elif str(tax_value) == '0' or not accept_tax:
            vals['tax_status'] = 'exempt'
        else:
            # Default to 15%
            vals['tax_status'] = 'standard_15'

        # Commission rates - FIXED: Don't multiply by 100
        # The value comes as 12 (meaning 12%), store as-is
        if data.get('commission_rate_online') is not None:
            # Store as received: 12 means 12%
            vals['commission_rate_online'] = float(data['commission_rate_online'])
            _logger.info(f"Partner commission_rate_online set to: {vals['commission_rate_online']}%")

        if data.get('commission_rate_cash') is not None:
            # Store as received: 10 means 10%
            vals['commission_rate_cash'] = float(data['commission_rate_cash'])
            _logger.info(f"Partner commission_rate_cash set to: {vals['commission_rate_cash']}%")

        return vals