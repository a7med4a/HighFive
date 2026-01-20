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
        Process commission data (create/update commission)

        Args:
            data: Commission data from HighFive API:
            {
                "id": 123,
                "unit_id": 5,
                "type": "scheduled" or "default",
                "name": "Ramadan Special",
                "start_date": "2026-03-01",  # Only for scheduled
                "end_date": "2026-04-15",    # Only for scheduled
                "online_booking": {"percent": 5, "fixed": 3},
                "cash_booking": {"percent": 3, "fixed": 2},
                "walk_in_booking": {"percent": 4, "fixed": 0},
                "linked_booking": {"percent": 6, "fixed": 5},
                "online_public_event": {"percent": 10, "fixed": 10},
                "cash_public_event": {"percent": 8, "fixed": 5}
            }

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
            _logger.info(
                f"Updated commission {commission.id} - {commission.name}"
            )

            return {
                'action': 'updated',
                'commission_id': commission.id,
                'highfive_commission_id': commission.highfive_commission_id,
                'commission_name': commission.name,
                'unit_id': unit.id,
                'unit_name': unit.name,
                'type': commission.type,
                'model': 'highfive.unit.commission'
            }
        else:
            commission = self.env['highfive.unit.commission'].create(vals)
            _logger.info(
                f"Created commission {commission.id} - {commission.name}"
            )

            return {
                'action': 'created',
                'commission_id': commission.id,
                'highfive_commission_id': commission.highfive_commission_id,
                'commission_name': commission.name,
                'unit_id': unit.id,
                'unit_name': unit.name,
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
            raise ValidationError(
                "Cannot delete default commission! "
                "Default commissions can only be updated, not deleted."
            )

        unit_id = commission.unit_id.id
        unit_name = commission.unit_id.name
        commission_name = commission.name

        commission.unlink()

        _logger.info(
            f"Deleted commission {commission_id} - {commission_name}"
        )

        return {
            'action': 'deleted',
            'commission_id': commission_id,
            'commission_name': commission_name,
            'unit_id': unit_id,
            'unit_name': unit_name
        }

    def get_all(self, unit_id):
        """
        Get all commissions for a unit

        Args:
            unit_id: HighFive unit ID

        Returns:
            dict: {
                'unit_id': int,
                'unit_name': str,
                'default_commission': dict or None,
                'scheduled_commissions': [dict, ...]
            }
        """
        unit = self._get_unit(unit_id)

        commissions = self.env['highfive.unit.commission'].search([
            ('unit_id', '=', unit.id),
            ('active', '=', True)
        ], order='type, start_date desc')

        result = {
            'unit_id': int(unit.highfive_unit_id) if unit.highfive_unit_id else unit.id,
            'unit_name': unit.name,
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
            dict: {
                'unit_id': int,
                'unit_name': str,
                'date': str,
                'active_commission': dict
            }
        """
        unit = self._get_unit(unit_id)

        # Convert date string to date object
        from datetime import datetime
        booking_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Get active commission using model method
        commission = self.env['highfive.unit.commission'].get_active_commission(
            unit.id,
            booking_date
        )

        if not commission:
            raise ValidationError(
                f"No commission configured for unit {unit_id}. "
                "Please create a default commission first."
            )

        return {
            'unit_id': int(unit.highfive_unit_id) if unit.highfive_unit_id else unit.id,
            'unit_name': unit.name,
            'date': date,
            'active_commission': self._format_commission(commission)
        }

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _validate(self, data):
        """Validate commission data"""
        required = ['unit_id', 'type']

        for field in required:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")

        if data['type'] not in ['default', 'scheduled']:
            raise ValidationError(
                f"Invalid commission type: {data['type']}. "
                "Must be 'default' or 'scheduled'"
            )

        if data['type'] == 'scheduled':
            if 'start_date' not in data or 'end_date' not in data:
                raise ValidationError(
                    "Scheduled commissions require start_date and end_date"
                )

            # Validate date format
            try:
                from datetime import datetime
                start = datetime.strptime(data['start_date'], '%Y-%m-%d')
                end = datetime.strptime(data['end_date'], '%Y-%m-%d')

                if start >= end:
                    raise ValidationError(
                        "End date must be after start date"
                    )
            except ValueError as e:
                raise ValidationError(
                    f"Invalid date format. Use YYYY-MM-DD. Error: {e}"
                )

    def _get_unit(self, unit_id):
        """Get unit by HighFive ID"""
        unit = self.env['product.template'].search([
            ('highfive_unit_id', '=', str(unit_id)),
            ('is_highfive_unit', '=', True)
        ], limit=1)

        if not unit:
            raise ValidationError(
                f"Unit {unit_id} not found. "
                "Please create the unit first."
            )

        return unit

    def _transform(self, data, unit):
        """
        Transform HighFive API data to Odoo format

        Args:
            data: API data with 6 booking types
            unit: Odoo unit record

        Returns:
            dict: Values for create/write
        """
        vals = {
            'unit_id': unit.id,
            'type': data['type'],
            'highfive_commission_id': str(data.get('id', '')),
            'name': data.get('name', f"{data['type'].title()} Commission - {unit.name}"),
        }

        # ================================================================
        # Commission Values (6 Types × 2 Values)
        # ================================================================

        # 1. Online Booking
        online = data.get('online_booking', {})
        vals['commission_online_percent'] = float(online.get('percent', 0))
        vals['commission_online_fixed'] = float(online.get('fixed', 0))

        # 2. Cash Booking
        cash = data.get('cash_booking', {})
        vals['commission_cash_percent'] = float(cash.get('percent', 0))
        vals['commission_cash_fixed'] = float(cash.get('fixed', 0))

        # 3. Walk-in Booking
        walkin = data.get('walk_in_booking', {})
        vals['commission_walkin_percent'] = float(walkin.get('percent', 0))
        vals['commission_walkin_fixed'] = float(walkin.get('fixed', 0))

        # 4. Linked Booking
        linked = data.get('linked_booking', {})
        vals['commission_linked_percent'] = float(linked.get('percent', 0))
        vals['commission_linked_fixed'] = float(linked.get('fixed', 0))

        # 5. Online Public Event
        online_event = data.get('online_public_event', {})
        vals['commission_online_event_percent'] = float(online_event.get('percent', 0))
        vals['commission_online_event_fixed'] = float(online_event.get('fixed', 0))

        # 6. Cash Public Event
        cash_event = data.get('cash_public_event', {})
        vals['commission_cash_event_percent'] = float(cash_event.get('percent', 0))
        vals['commission_cash_event_fixed'] = float(cash_event.get('fixed', 0))

        # ================================================================
        # Dates (for scheduled type)
        # ================================================================
        if data['type'] == 'scheduled':
            from datetime import datetime
            vals['start_date'] = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            vals['end_date'] = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        else:
            # Default commission has no dates
            vals['start_date'] = None
            vals['end_date'] = None

        return vals

    def _format_commission(self, commission):
        """
        Format commission record for API response

        Args:
            commission: Odoo commission record

        Returns:
            dict: Formatted commission data
        """
        if not commission:
            return None

        result = {
            'id': commission.id,
            'highfive_id': commission.highfive_commission_id,
            'type': commission.type,
            'name': commission.name,
            'status': commission.status,

            # 6 Booking Types
            'online_booking': {
                'percent': commission.commission_online_percent,
                'fixed': commission.commission_online_fixed
            },
            'cash_booking': {
                'percent': commission.commission_cash_percent,
                'fixed': commission.commission_cash_fixed
            },
            'walk_in_booking': {
                'percent': commission.commission_walkin_percent,
                'fixed': commission.commission_walkin_fixed
            },
            'linked_booking': {
                'percent': commission.commission_linked_percent,
                'fixed': commission.commission_linked_fixed
            },
            'online_public_event': {
                'percent': commission.commission_online_event_percent,
                'fixed': commission.commission_online_event_fixed
            },
            'cash_public_event': {
                'percent': commission.commission_cash_event_percent,
                'fixed': commission.commission_cash_event_fixed
            }
        }

        # Add dates for scheduled
        if commission.type == 'scheduled':
            result['start_date'] = commission.start_date.strftime('%Y-%m-%d') if commission.start_date else None
            result['end_date'] = commission.end_date.strftime('%Y-%m-%d') if commission.end_date else None

        return result