# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class UnitCommission(models.Model):
    _name = 'highfive.unit.commission'
    _description = 'Unit Commission Rules'
    _order = 'type, start_date desc, id desc'

    # =========================================================================
    # FIELDS - Basic Info
    # =========================================================================

    name = fields.Char(
        string='Commission Name',
        required=True,
        help='e.g., Ramadan Special, Summer Promotion, Default Commission'
    )

    unit_id = fields.Many2one(
        'product.template',
        string='Unit',
        required=True,
        ondelete='cascade',
        index=True,
        domain=[('is_highfive_unit', '=', True)]
    )

    highfive_commission_id = fields.Char(
        string='HighFive Commission ID',
        help='Original ID from HighFive database',
        index=True
    )

    type = fields.Selection([
        ('default', 'Default Commission'),
        ('scheduled', 'Scheduled Commission')
    ], string='Type', required=True, default='scheduled')

    # =========================================================================
    # FIELDS - Schedule (for type='scheduled')
    # =========================================================================

    start_date = fields.Date(
        string='Start Date',
        help='Commission applies from this date (inclusive)'
    )

    end_date = fields.Date(
        string='End Date',
        help='Commission applies until this date (inclusive)'
    )

    # =========================================================================
    # FIELDS - Commission Rates (6 Booking Types × 2 Values)
    # =========================================================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # 1. Online Booking
    commission_online_percent = fields.Float(
        string='Online Booking %',
        default=0.0,
        help='Commission percentage for online bookings'
    )
    commission_online_fixed = fields.Monetary(
        string='Online Booking Fixed',
        currency_field='currency_id',
        default=0.0,
        help='Fixed commission amount for online bookings'
    )

    # 2. Cash Booking
    commission_cash_percent = fields.Float(
        string='Cash Booking %',
        default=0.0,
        help='Commission percentage for cash bookings'
    )
    commission_cash_fixed = fields.Monetary(
        string='Cash Booking Fixed',
        currency_field='currency_id',
        default=0.0,
        help='Fixed commission amount for cash bookings'
    )

    # 3. Walk-in Booking
    commission_walkin_percent = fields.Float(
        string='Walk-in Booking %',
        default=0.0,
        help='Commission percentage for walk-in bookings'
    )
    commission_walkin_fixed = fields.Monetary(
        string='Walk-in Booking Fixed',
        currency_field='currency_id',
        default=0.0,
        help='Fixed commission amount for walk-in bookings'
    )

    # 4. Linked Booking
    commission_linked_percent = fields.Float(
        string='Linked Booking %',
        default=0.0,
        help='Commission percentage for linked bookings'
    )
    commission_linked_fixed = fields.Monetary(
        string='Linked Booking Fixed',
        currency_field='currency_id',
        default=0.0,
        help='Fixed commission amount for linked bookings'
    )

    # 5. Online Public Event
    commission_online_event_percent = fields.Float(
        string='Online Event %',
        default=0.0,
        help='Commission percentage for online public events'
    )
    commission_online_event_fixed = fields.Monetary(
        string='Online Event Fixed',
        currency_field='currency_id',
        default=0.0,
        help='Fixed commission amount for online public events'
    )

    # 6. Cash Public Event
    commission_cash_event_percent = fields.Float(
        string='Cash Event %',
        default=0.0,
        help='Commission percentage for cash public events'
    )
    commission_cash_event_fixed = fields.Monetary(
        string='Cash Event Fixed',
        currency_field='currency_id',
        default=0.0,
        help='Fixed commission amount for cash public events'
    )

    # =========================================================================
    # FIELDS - Display & Status
    # =========================================================================

    status = fields.Selection([
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('expired', 'Expired')
    ], string='Status', compute='_compute_status', store=True)

    active = fields.Boolean('Active', default=True)

    # Display fields for tree view
    online_display = fields.Char(
        string='Online Booking',
        compute='_compute_display_fields',
        store=True
    )
    cash_display = fields.Char(
        string='Cash Booking',
        compute='_compute_display_fields',
        store=True
    )
    walkin_display = fields.Char(
        string='Walk-in',
        compute='_compute_display_fields',
        store=True
    )

    # =========================================================================
    # SQL CONSTRAINTS
    # =========================================================================

    _sql_constraints = [
        ('unique_default_unit',
         "unique(unit_id, type) WHERE type = 'default'",
         'Each unit can have only one default commission!'),
    ]

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================

    @api.depends('type', 'start_date', 'end_date')
    def _compute_status(self):
        """Compute commission status based on dates"""
        today = fields.Date.today()
        for record in self:
            if record.type == 'default':
                record.status = 'active'
            elif record.type == 'scheduled':
                if not record.start_date or not record.end_date:
                    record.status = 'active'
                elif today < record.start_date:
                    record.status = 'upcoming'
                elif today > record.end_date:
                    record.status = 'expired'
                else:
                    record.status = 'active'
            else:
                record.status = 'active'

    @api.depends(
        'commission_online_percent', 'commission_online_fixed',
        'commission_cash_percent', 'commission_cash_fixed',
        'commission_walkin_percent', 'commission_walkin_fixed',
        'currency_id'
    )
    def _compute_display_fields(self):
        """Compute display strings for commission rates"""
        for record in self:
            currency = record.currency_id.symbol or ''

            # Online Booking
            if record.commission_online_percent > 0 and record.commission_online_fixed > 0:
                record.online_display = f"{record.commission_online_percent}% + {currency}{record.commission_online_fixed}"
            elif record.commission_online_percent > 0:
                record.online_display = f"{record.commission_online_percent}%"
            elif record.commission_online_fixed > 0:
                record.online_display = f"{currency}{record.commission_online_fixed}"
            else:
                record.online_display = "0"

            # Cash Booking
            if record.commission_cash_percent > 0 and record.commission_cash_fixed > 0:
                record.cash_display = f"{record.commission_cash_percent}% + {currency}{record.commission_cash_fixed}"
            elif record.commission_cash_percent > 0:
                record.cash_display = f"{record.commission_cash_percent}%"
            elif record.commission_cash_fixed > 0:
                record.cash_display = f"{currency}{record.commission_cash_fixed}"
            else:
                record.cash_display = "0"

            # Walk-in
            if record.commission_walkin_percent > 0 and record.commission_walkin_fixed > 0:
                record.walkin_display = f"{record.commission_walkin_percent}% + {currency}{record.commission_walkin_fixed}"
            elif record.commission_walkin_percent > 0:
                record.walkin_display = f"{record.commission_walkin_percent}%"
            elif record.commission_walkin_fixed > 0:
                record.walkin_display = f"{currency}{record.commission_walkin_fixed}"
            else:
                record.walkin_display = "0"

    # =========================================================================
    # CONSTRAINTS VALIDATION
    # =========================================================================

    @api.constrains('type', 'start_date', 'end_date')
    def _check_dates(self):
        """Validate scheduled commission dates"""
        for record in self:
            if record.type == 'scheduled':
                if not record.start_date or not record.end_date:
                    raise ValidationError(
                        "Scheduled commissions must have start and end dates!"
                    )
                if record.start_date > record.end_date:
                    raise ValidationError(
                        "End date must be after start date!"
                    )

    @api.constrains('unit_id', 'start_date', 'end_date', 'type')
    def _check_overlap(self):
        """Check for overlapping scheduled commissions"""
        for record in self:
            if record.type == 'scheduled' and record.start_date and record.end_date:
                overlapping = self.search([
                    ('unit_id', '=', record.unit_id.id),
                    ('type', '=', 'scheduled'),
                    ('id', '!=', record.id),
                    ('start_date', '<=', record.end_date),
                    ('end_date', '>=', record.start_date),
                    ('active', '=', True)
                ])
                if overlapping:
                    raise ValidationError(
                        f"Commission period overlaps with: {overlapping[0].name}\n"
                        f"({overlapping[0].start_date} - {overlapping[0].end_date})"
                    )

    @api.constrains('unit_id', 'type')
    def _check_default_unique(self):
        """Only one default commission per unit"""
        for record in self:
            if record.type == 'default':
                existing = self.search([
                    ('unit_id', '=', record.unit_id.id),
                    ('type', '=', 'default'),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(
                        f"Unit '{record.unit_id.name}' already has a default commission: {existing[0].name}"
                    )

    # =========================================================================
    # BUSINESS METHODS - Commission Calculation
    # =========================================================================

    def get_commission_values(self, booking_type):
        """
        Get commission percent and fixed values for booking type

        Args:
            booking_type (str): One of:
                - online_booking
                - cash_booking
                - walk_in_booking
                - linked_booking
                - online_public_event
                - cash_public_event

        Returns:
            tuple: (percent, fixed)
        """
        self.ensure_one()

        commission_map = {
            'online_booking': (
                self.commission_online_percent,
                self.commission_online_fixed
            ),
            'cash_booking': (
                self.commission_cash_percent,
                self.commission_cash_fixed
            ),
            'walk_in_booking': (
                self.commission_walkin_percent,
                self.commission_walkin_fixed
            ),
            'linked_booking': (
                self.commission_linked_percent,
                self.commission_linked_fixed
            ),
            'online_public_event': (
                self.commission_online_event_percent,
                self.commission_online_event_fixed
            ),
            'cash_public_event': (
                self.commission_cash_event_percent,
                self.commission_cash_event_fixed
            ),
        }

        return commission_map.get(booking_type, (0.0, 0.0))

    def calculate_commission(self, base_amount, booking_type, tax_rate=0.15):
        """
        Calculate commission amount

        Formula: Commission = (Base × Percent%) + Fixed

        Args:
            base_amount (float): Base amount (before tax)
            booking_type (str): Booking type
            tax_rate (float): Tax rate (default 0.15 = 15%)

        Returns:
            dict: {
                'percent': float,
                'fixed': float,
                'commission_net': float,
                'commission_tax': float,
                'commission_total': float
            }
        """
        self.ensure_one()

        percent, fixed = self.get_commission_values(booking_type)

        # Calculate net commission
        commission_net = (base_amount * (percent / 100.0)) + fixed

        # Calculate tax on commission
        commission_tax = commission_net * tax_rate

        # Total with tax
        commission_total = commission_net + commission_tax

        result = {
            'percent': percent,
            'fixed': fixed,
            'commission_net': round(commission_net, 2),
            'commission_tax': round(commission_tax, 2),
            'commission_total': round(commission_total, 2)
        }

        _logger.info(
            f"Commission calculated for {self.name} ({booking_type}): "
            f"Base={base_amount:.2f}, "
            f"Rate={percent}% + {fixed}, "
            f"Net={result['commission_net']:.2f}, "
            f"Total={result['commission_total']:.2f}"
        )

        return result

    # =========================================================================
    # MODEL METHODS - Active Commission Selection
    # =========================================================================

    @api.model
    def get_active_commission(self, unit_id, booking_date):
        """
        Get active commission for unit at specific date

        Priority:
        1. Scheduled commission (if date in range)
        2. Default commission
        3. None (empty recordset)

        Args:
            unit_id (int): Product template ID
            booking_date (date): Booking date

        Returns:
            recordset: Active commission record (or empty)
        """
        # Try to find scheduled commission first
        scheduled = self.search([
            ('unit_id', '=', unit_id),
            ('type', '=', 'scheduled'),
            ('start_date', '<=', booking_date),
            ('end_date', '>=', booking_date),
            ('active', '=', True)
        ], order='start_date desc', limit=1)

        if scheduled:
            _logger.info(
                f"Using scheduled commission '{scheduled.name}' "
                f"for unit {unit_id} on {booking_date}"
            )
            return scheduled

        # Fallback to default commission
        default = self.search([
            ('unit_id', '=', unit_id),
            ('type', '=', 'default'),
            ('active', '=', True)
        ], limit=1)

        if default:
            _logger.info(
                f"Using default commission '{default.name}' "
                f"for unit {unit_id}"
            )
            return default

        # No commission found
        _logger.warning(
            f"No commission found for unit {unit_id}! "
            "Please configure default commission."
        )
        return self.browse()

    @api.model
    def get_commission_for_booking(self, unit_id, booking_date, booking_type, base_amount, tax_rate=0.15):
        """
        Complete commission lookup and calculation for booking

        Args:
            unit_id (int): Product template ID
            booking_date (date): Booking date
            booking_type (str): Booking type (online_booking, etc.)
            base_amount (float): Base amount before tax
            tax_rate (float): Tax rate (default 0.15)

        Returns:
            dict: {
                'found': bool,
                'commission_id': int or False,
                'commission_name': str,
                'commission_type': str ('default' or 'scheduled'),
                'percent': float,
                'fixed': float,
                'commission_net': float,
                'commission_tax': float,
                'commission_total': float
            }
        """
        commission = self.get_active_commission(unit_id, booking_date)

        if not commission:
            return {
                'found': False,
                'commission_id': False,
                'commission_name': '',
                'commission_type': '',
                'percent': 0.0,
                'fixed': 0.0,
                'commission_net': 0.0,
                'commission_tax': 0.0,
                'commission_total': 0.0
            }

        calculation = commission.calculate_commission(
            base_amount,
            booking_type,
            tax_rate
        )

        return {
            'found': True,
            'commission_id': commission.id,
            'commission_name': commission.name,
            'commission_type': commission.type,
            **calculation
        }

    # =========================================================================
    # BACKWARD COMPATIBILITY (DEPRECATED)
    # =========================================================================

    def get_commission_rate(self, payment_method):
        """
        DEPRECATED: Use get_commission_values() instead

        Legacy method for backward compatibility
        Maps old payment_method to new booking_type
        """
        _logger.warning(
            "get_commission_rate() is deprecated. "
            "Use get_commission_values() instead."
        )

        # Map old payment_method to booking_type
        booking_type_map = {
            'online': 'online_booking',
            'cash': 'cash_booking'
        }

        booking_type = booking_type_map.get(payment_method, 'online_booking')
        percent, fixed = self.get_commission_values(booking_type)

        return percent  # Return only percent for backward compatibility

    def calculate_commission_amount(self, base_amount, payment_method):
        """
        DEPRECATED: Use calculate_commission() instead

        Legacy method for backward compatibility
        """
        _logger.warning(
            "calculate_commission_amount() is deprecated. "
            "Use calculate_commission() instead."
        )

        booking_type_map = {
            'online': 'online_booking',
            'cash': 'cash_booking'
        }

        booking_type = booking_type_map.get(payment_method, 'online_booking')
        result = self.calculate_commission(base_amount, booking_type)

        return result['commission_net']  # Return only net for backward compatibility