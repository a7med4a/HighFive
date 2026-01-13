# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class UnitCommission(models.Model):
    _name = 'highfive.unit.commission'
    _description = 'Unit Commission Rates'
    _order = 'type desc, id desc'

    # =========================================================================
    # FIELDS - Basic Info
    # =========================================================================

    unit_id = fields.Many2one(
        'product.template',
        string='Unit',
        required=True,
        ondelete='cascade',
        index=True,
        domain=[('is_highfive_unit', '=', True)]
    )

    highfive_commission_id = fields.Char(
        'HighFive Commission ID',
        help='Original ID from HighFive database',
        index=True
    )

    name = fields.Char(
        'Commission Name',
        help='e.g., Ramadan Special Offer, Summer Promotion'
    )

    type = fields.Selection([
        ('default', 'Default Commission'),
        ('scheduled', 'Scheduled Commission')
    ], string='Type', default='default', required=True)

    # =========================================================================
    # FIELDS - Commission Rates (JSON format)
    # =========================================================================

    online_booking = fields.Char(
        'Online Booking Rate',
        help='JSON format: {"type": "percentage", "value": 15}',
        default='{"type": "percentage", "value": 15}'
    )

    cash_booking = fields.Char(
        'Cash Booking Rate',
        help='JSON format: {"type": "percentage", "value": 10}',
        default='{"type": "percentage", "value": 10}'
    )

    # =========================================================================
    # FIELDS - Schedule (for type='scheduled')
    # =========================================================================

    start_at = fields.Datetime('Start Date')
    end_at = fields.Datetime('End Date')

    # =========================================================================
    # FIELDS - Display & Status
    # =========================================================================

    online_rate_display = fields.Char(
        'Online Rate',
        compute='_compute_rate_display',
        store=True
    )

    cash_rate_display = fields.Char(
        'Cash Rate',
        compute='_compute_rate_display',
        store=True
    )

    status = fields.Selection([
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('expired', 'Expired')
    ], string='Status', compute='_compute_status', store=True)

    active = fields.Boolean('Active', default=True)

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    _sql_constraints = [
        ('unique_default_unit',
         'unique(unit_id, type) WHERE type = \'default\'',
         'Each unit can have only one default commission!'),
    ]

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================

    @api.depends('online_booking', 'cash_booking')
    def _compute_rate_display(self):
        """Compute display values for rates"""
        for record in self:
            # Online rate display
            try:
                online_data = json.loads(record.online_booking or '{}')
                if online_data.get('type') == 'percentage':
                    record.online_rate_display = f"{online_data.get('value', 0)}%"
                else:
                    # Fixed amount
                    currency = self.env.company.currency_id
                    record.online_rate_display = f"{currency.symbol} {online_data.get('value', 0)}"
            except:
                record.online_rate_display = '0%'

            # Cash rate display
            try:
                cash_data = json.loads(record.cash_booking or '{}')
                if cash_data.get('type') == 'percentage':
                    record.cash_rate_display = f"{cash_data.get('value', 0)}%"
                else:
                    # Fixed amount
                    currency = self.env.company.currency_id
                    record.cash_rate_display = f"{currency.symbol} {cash_data.get('value', 0)}"
            except:
                record.cash_rate_display = '0%'

    @api.depends('type', 'start_at', 'end_at')
    def _compute_status(self):
        """Compute commission status"""
        now = fields.Datetime.now()
        for record in self:
            if record.type == 'default':
                record.status = 'active'
            elif record.type == 'scheduled':
                if not record.start_at or not record.end_at:
                    record.status = 'active'
                elif now < record.start_at:
                    record.status = 'upcoming'
                elif now > record.end_at:
                    record.status = 'expired'
                else:
                    record.status = 'active'
            else:
                record.status = 'active'

    # =========================================================================
    # CONSTRAINTS VALIDATION
    # =========================================================================

    @api.constrains('start_at', 'end_at')
    def _check_dates(self):
        """Validate scheduled commission dates"""
        for record in self:
            if record.type == 'scheduled':
                if not record.start_at or not record.end_at:
                    raise ValidationError(
                        "Scheduled commissions must have start and end dates!"
                    )
                if record.start_at >= record.end_at:
                    raise ValidationError(
                        "End date must be after start date!"
                    )

    @api.constrains('online_booking', 'cash_booking')
    def _check_json_format(self):
        """Validate JSON format for commission rates"""
        for record in self:
            # Check online_booking
            try:
                online_data = json.loads(record.online_booking or '{}')
                if 'type' not in online_data or 'value' not in online_data:
                    raise ValidationError(
                        "Online booking commission must have 'type' and 'value' keys!"
                    )
                if online_data['type'] not in ['percentage', 'fixed']:
                    raise ValidationError(
                        "Commission type must be 'percentage' or 'fixed'!"
                    )
                # Validate value is numeric
                try:
                    float(online_data['value'])
                except (ValueError, TypeError):
                    raise ValidationError(
                        "Commission value must be numeric!"
                    )
            except json.JSONDecodeError:
                raise ValidationError(
                    "Invalid JSON format for online booking commission!"
                )

            # Check cash_booking
            try:
                cash_data = json.loads(record.cash_booking or '{}')
                if 'type' not in cash_data or 'value' not in cash_data:
                    raise ValidationError(
                        "Cash booking commission must have 'type' and 'value' keys!"
                    )
                if cash_data['type'] not in ['percentage', 'fixed']:
                    raise ValidationError(
                        "Commission type must be 'percentage' or 'fixed'!"
                    )
                # Validate value is numeric
                try:
                    float(cash_data['value'])
                except (ValueError, TypeError):
                    raise ValidationError(
                        "Commission value must be numeric!"
                    )
            except json.JSONDecodeError:
                raise ValidationError(
                    "Invalid JSON format for cash booking commission!"
                )

    # =========================================================================
    # BUSINESS METHODS - Commission Retrieval
    # =========================================================================

    def get_commission_data(self, payment_method):
        """
        Get full commission data for payment method

        Args:
            payment_method (str): 'online' or 'cash'

        Returns:
            dict: {
                'type': 'percentage' or 'fixed',
                'value': float,
                'commission_id': int,
                'commission_name': str,
                'commission_type': str ('default' or 'scheduled')
            }
        """
        self.ensure_one()

        try:
            if payment_method == 'online':
                data = json.loads(self.online_booking or '{}')
            else:  # cash
                data = json.loads(self.cash_booking or '{}')

            return {
                'type': data.get('type', 'percentage'),
                'value': float(data.get('value', 0)),
                'commission_id': self.id,
                'commission_name': self.name or 'Default Commission',
                'commission_type': self.type
            }
        except Exception as e:
            _logger.error(
                f"Error parsing commission data for unit {self.unit_id.name}: {e}"
            )
            # Return safe default
            return {
                'type': 'percentage',
                'value': 0.0,
                'commission_id': self.id,
                'commission_name': 'Default Commission',
                'commission_type': self.type
            }

    def get_commission_rate(self, payment_method):
        """
        Get commission rate (percentage only)

        DEPRECATED: Use get_commission_data() for full info
        Kept for backward compatibility

        Args:
            payment_method (str): 'online' or 'cash'

        Returns:
            float: Commission percentage (0 if fixed type)
        """
        data = self.get_commission_data(payment_method)
        if data['type'] == 'percentage':
            return data['value']
        return 0.0

    def calculate_commission_amount(self, base_amount, payment_method):
        """
        Calculate actual commission amount in currency

        Args:
            base_amount (float): Base price (e.g., session_base_price)
            payment_method (str): 'online' or 'cash'

        Returns:
            float: Commission amount in currency (rounded to 2 decimals)

        Examples:
            - Percentage: base=100, rate=15% → 15.00
            - Fixed: base=100, amount=10 → 10.00
        """
        self.ensure_one()

        data = self.get_commission_data(payment_method)

        if data['type'] == 'percentage':
            # Percentage commission
            rate = data['value'] / 100
            amount = base_amount * rate
        else:
            # Fixed amount commission
            amount = data['value']

        amount = round(amount, 2)

        _logger.info(
            f"Commission calculated for unit '{self.unit_id.name}': "
            f"base={base_amount}, method={payment_method}, "
            f"commission_type={data['type']}, value={data['value']}, "
            f"result={amount}"
        )

        return amount

    # =========================================================================
    # MODEL METHODS - Active Commission Selection
    # =========================================================================

    @api.model
    def get_active_commission(self, unit_id, booking_date):
        """
        Get active commission for unit at specific date

        Logic:
        1. Search for scheduled commission active on booking_date
        2. If found, return it
        3. Otherwise, return default commission
        4. If no commission found, return empty recordset

        Args:
            unit_id (int): Product template ID
            booking_date (datetime): Booking date/time

        Returns:
            recordset: Active commission record (or empty)
        """
        # Try to find scheduled commission first
        scheduled = self.search([
            ('unit_id', '=', unit_id),
            ('type', '=', 'scheduled'),
            ('start_at', '<=', booking_date),
            ('end_at', '>=', booking_date),
            ('active', '=', True)
        ], order='start_at desc', limit=1)

        if scheduled:
            _logger.info(
                f"Using scheduled commission '{scheduled.name}' "
                f"for unit {unit_id}"
            )
            return scheduled

        # Fallback to default commission
        default = self.search([
            ('unit_id', '=', unit_id),
            ('type', '=', 'default'),
            ('active', '=', True)
        ], limit=1)

        if default:
            _logger.info(f"Using default commission for unit {unit_id}")
            return default

        # No commission found - log warning
        _logger.warning(
            f"No commission found for unit {unit_id}! "
            f"Please configure default commission."
        )
        return self.browse()

    @api.model
    def get_commission_for_booking(self, unit_id, booking_date, payment_method, base_amount):
        """
        Complete commission lookup and calculation for booking

        Convenience method that combines:
        - Finding active commission
        - Getting commission data
        - Calculating amount

        Args:
            unit_id (int): Product template ID
            booking_date (datetime): Booking date/time
            payment_method (str): 'online' or 'cash'
            base_amount (float): Base price

        Returns:
            dict: {
                'commission_record': recordset,
                'commission_data': dict,
                'commission_amount': float,
                'found': bool
            }
        """
        commission = self.get_active_commission(unit_id, booking_date)

        if not commission:
            return {
                'commission_record': self.browse(),
                'commission_data': None,
                'commission_amount': 0.0,
                'found': False
            }

        commission_data = commission.get_commission_data(payment_method)
        commission_amount = commission.calculate_commission_amount(
            base_amount,
            payment_method
        )

        return {
            'commission_record': commission,
            'commission_data': commission_data,
            'commission_amount': commission_amount,
            'found': True
        }