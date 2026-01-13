# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class CommissionService:
    """Commission Management Service"""
    
    def __init__(self, env):
        self.env = env
    
    def process(self, data):
        """
        Process commission data (create/update scheduled commission)
        
        Args:
            data: Commission data from HighFive
            
        Returns:
            Result dictionary with action and record info
        """
        # Validate
        self._validate(data)
        
        # Get unit
        unit = self._get_unit(data['unit_id'])
        
        # Transform
        vals = self._transform(data, unit)
        
        # Create or Update
        commission = None
        if data.get('id'):
            commission = self.env['highfive.unit.commission'].search([
                ('highfive_commission_id', '=', str(data['id']))
            ], limit=1)
        
        if commission:
            commission.write(vals)
            _logger.info(f"Updated commission {commission.id}")
            
            return {
                'action': 'updated',
                'commission_id': commission.id,
                'unit_id': unit.id,
                'type': commission.type,
                'model': 'highfive.unit.commission'
            }
        else:
            commission = self.env['highfive.unit.commission'].create(vals)
            _logger.info(f"Created commission {commission.id}")
            
            return {
                'action': 'created',
                'commission_id': commission.id,
                'unit_id': unit.id,
                'type': commission.type,
                'model': 'highfive.unit.commission'
            }
    
    def delete(self, commission_id):
        """
        Delete commission
        
        Args:
            commission_id: HighFive commission ID
            
        Returns:
            Result dictionary
        """
        commission = self.env['highfive.unit.commission'].search([
            ('highfive_commission_id', '=', str(commission_id))
        ], limit=1)
        
        if not commission:
            raise ValidationError(f"Commission {commission_id} not found")
        
        # Don't allow deleting default commission
        if commission.type == 'default':
            raise ValidationError("Cannot delete default commission")
        
        unit_id = commission.unit_id.id
        commission.unlink()
        
        _logger.info(f"Deleted commission {commission_id}")
        
        return {
            'action': 'deleted',
            'commission_id': commission_id,
            'unit_id': unit_id
        }
    
    def get_all(self, unit_id):
        """
        Get all commissions for a unit
        
        Args:
            unit_id: HighFive unit ID
            
        Returns:
            dict: All commissions for unit
        """
        unit = self._get_unit(unit_id)
        
        commissions = self.env['highfive.unit.commission'].search([
            ('unit_id', '=', unit.id)
        ])
        
        result = {
            'unit_id': unit.id,
            'unit_name': unit.name,
            'highfive_unit_id': unit.highfive_unit_id,
            'default_commission': None,
            'scheduled_commissions': []
        }
        
        for comm in commissions:
            comm_data = self._format_commission(comm)
            if comm.type == 'default':
                result['default_commission'] = comm_data
            else:
                result['scheduled_commissions'].append(comm_data)
        
        return result
    
    def get_active(self, unit_id, date):
        """
        Get active commission for specific date
        
        Args:
            unit_id: HighFive unit ID
            date: Date string (YYYY-MM-DD)
            
        Returns:
            dict: Active commission info
        """
        unit = self._get_unit(unit_id)
        
        # Convert date string to datetime
        from datetime import datetime
        booking_datetime = datetime.strptime(date, '%Y-%m-%d')
        
        # Get active commission
        commission = self.env['highfive.unit.commission'].get_active_commission(
            unit.id, 
            booking_datetime
        )
        
        if not commission:
            raise ValidationError(f"No commission configured for unit {unit_id}")
        
        return {
            'unit_id': unit.id,
            'unit_name': unit.name,
            'date': date,
            'active_commission': self._format_commission(commission)
        }
    
    def _validate(self, data):
        """Validate commission data"""
        required = ['unit_id', 'type']
        
        for field in required:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        if data['type'] not in ['default', 'scheduled']:
            raise ValidationError("Invalid commission type")
        
        if data['type'] == 'scheduled':
            if 'start_date' not in data or 'end_date' not in data:
                raise ValidationError(
                    "Scheduled commissions require start_date and end_date"
                )
    
    def _get_unit(self, unit_id):
        """Get unit by HighFive ID"""
        unit = self.env['product.template'].search([
            ('highfive_unit_id', '=', str(unit_id))
        ], limit=1)
        
        if not unit:
            raise ValidationError(f"Unit {unit_id} not found")
        
        return unit
    
    def _transform(self, data, unit):
        """Transform HighFive data to Odoo format"""
        vals = {
            'unit_id': unit.id,
            'type': data['type'],
            'highfive_commission_id': str(data.get('id', '')),
            'name': data.get('name', ''),
        }
        
        # Online commission
        online = data.get('online_commission', {})
        if online:
            vals['online_booking'] = json.dumps({
                'type': online.get('type', 'percentage'),
                'value': float(online.get('value', 0))
            })
        
        # Cash commission
        cash = data.get('cash_commission', {})
        if cash:
            vals['cash_booking'] = json.dumps({
                'type': cash.get('type', 'percentage'),
                'value': float(cash.get('value', 0))
            })
        
        # Dates (for scheduled)
        if data['type'] == 'scheduled':
            from datetime import datetime
            vals['start_at'] = datetime.strptime(data['start_date'], '%Y-%m-%d')
            vals['end_at'] = datetime.strptime(data['end_date'], '%Y-%m-%d')
        
        return vals
    
    def _format_commission(self, commission):
        """Format commission for API response"""
        if not commission:
            return None
        
        online_data = json.loads(commission.online_booking or '{}')
        cash_data = json.loads(commission.cash_booking or '{}')
        
        result = {
            'id': commission.id,
            'highfive_id': commission.highfive_commission_id,
            'type': commission.type,
            'name': commission.name,
            'online': {
                'type': online_data.get('type', 'percentage'),
                'value': online_data.get('value', 0)
            },
            'cash': {
                'type': cash_data.get('type', 'percentage'),
                'value': cash_data.get('value', 0)
            },
            'status': commission.status
        }
        
        if commission.type == 'scheduled':
            result['start_date'] = commission.start_at.strftime('%Y-%m-%d') if commission.start_at else None
            result['end_date'] = commission.end_at.strftime('%Y-%m-%d') if commission.end_at else None
        
        return result
