# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class HighFiveBooking(models.Model):
    _name = 'highfive.booking'
    _description = 'HighFive Booking'
    _order = 'booking_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    
    # =========================================================================
    # FIELDS - Basic Information
    # =========================================================================
    
    name = fields.Char(
        'Booking Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True
    )
    
    highfive_booking_id = fields.Char(
        'HighFive Booking ID',
        required=True,
        index=True,
        copy=False,
        tracking=True
    )

    # =========================================================================
    # FIELDS - Booking Schedule
    # =========================================================================

    booking_date = fields.Date(
        'Booking Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date of the booking'
    )

    booking_day = fields.Selection([
        ('saturday', 'السبت'),
        ('sunday', 'الأحد'),
        ('monday', 'الإثنين'),
        ('tuesday', 'الثلاثاء'),
        ('wednesday', 'الأربعاء'),
        ('thursday', 'الخميس'),
        ('friday', 'الجمعة')
    ], string='Day of Week',
        compute='_compute_booking_day',
        store=True,
        readonly=True)

    session_start_time = fields.Float(
        'Start Time',
        required=True,
        help='Session start time (e.g., 14.5 for 02:30 PM)'
    )

    session_end_time = fields.Float(
        'End Time',
        required=True,
        help='Session end time (e.g., 16.0 for 04:00 PM)'
    )

    session_start_datetime = fields.Datetime(
        'Session Start',
        compute='_compute_session_datetimes',
        store=True,
        readonly=True,
        help='Full start date and time'
    )

    session_end_datetime = fields.Datetime(
        'Session End',
        compute='_compute_session_datetimes',
        store=True,
        readonly=True,
        help='Full end date and time'
    )

    session_duration = fields.Float(
        'Duration (Hours)',
        compute='_compute_session_duration',
        store=True,
        readonly=True
    )
    
    # =========================================================================
    # FIELDS - Customer (العميل)
    # =========================================================================
    
    customer_id = fields.Many2one(
        'res.partner',
        'Customer',
        domain=[('is_highfive_customer', '!=', False)],
        tracking=True
    )



    customer_phone = fields.Char(
        related='customer_id.phone',
        string='Customer Phone',
        readonly=True
    )
    
    customer_email = fields.Char(
        related='customer_id.email',
        string='Customer Email',
        readonly=True
    )
    # =========================================================================
    # FIELDS - Booking Lines (الوحدات والخدمات)
    # =========================================================================

    booking_line_ids = fields.One2many(
        'highfive.booking.line',
        'booking_id',
        string='Booking Lines',
        copy=True
    )

    # For backward compatibility - computed from lines
    unit_id = fields.Many2one(
        'product.template',
        'Main Unit',
        required=True,
        domain=[('is_highfive_unit', '=', True)],
        help="The main unit/field being booked"
    )
    # =========================================================================
    # FIELDS - Partner/Supplier (المورد/الشريك)
    # =========================================================================
    
    partner_id = fields.Many2one(
        'res.partner',
        'Supplier/Partner',
        domain=[('is_highfive_partner', '=', True)],
        required=True,
        tracking=True
    )
    

    # =========================================================================
    # FIELDS - Branch (الفرع)
    # =========================================================================
    
    branch_id = fields.Many2one(
        'highfive.partner.branch',
        'Branch',
        required=True,
        tracking=True
    )
    

    
    branch_city = fields.Char(
        related='branch_id.city',
        string='Branch City',
        readonly=True
    )
    
    # Analytic Account from Branch
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account',
        store=True,
        readonly=True
    )

    
    # =========================================================================
    # FIELDS - Unit (الوحدة الرئيسية)
    # =========================================================================
    #
    # unit_id = fields.Many2one(
    #     'product.template',
    #     'Main Unit/Service',
    #     domain=[('highfive_unit_id', '!=', False)],
    #     required=True,
    #     tracking=True
    # )
    

    

    # =========================================================================
    # FIELDS - Amounts (المبالغ)
    # =========================================================================

    session_base_price = fields.Monetary(
        'Unit Base Price',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    
    services_total = fields.Monetary(
        'Additional Services Total',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True
    )
    
    discount = fields.Monetary(
        'Discount',
        currency_field='currency_id',
        default=0.0
    )
    
    subtotal = fields.Monetary(
        'Subtotal (Before Tax)',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True
    )
    
    tax_percent = fields.Float(
        'Tax Percentage',
        default=15.0,
        tracking=True
    )
    
    tax_amount = fields.Monetary(
        'Tax Amount',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True
    )
    
    total = fields.Monetary(
        'Total Amount',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    
    # =========================================================================
    # FIELDS - Tax Status
    # =========================================================================
    
    tax_status = fields.Selection([
        ('included', 'Tax Included in Prices'),
        ('excluded', 'Tax Excluded from Prices')
    ], string='Tax Status', default='included', required=True)
    
    # =========================================================================
    # FIELDS - Payment
    # =========================================================================
    
    payment_method = fields.Selection([
        ('online', 'Online Payment'),
        ('cash', 'Cash Payment')
    ], string='Payment Method', required=True, tracking=True)
    booking_type = fields.Selection([
        ('online_booking', 'Online Booking'),
        ('cash_booking', 'Cash Booking'),
        ('walk_in_booking', 'Walk-in Booking'),
        ('linked_booking', 'Linked Booking'),
        ('online_public_event', 'Online Public Event'),
        ('cash_public_event', 'Cash Public Event'),
    ], string='Booking Type', required=True, default='online_booking', tracking=True,
        help='Type of booking that determines commission calculation')

    payment_ids = fields.One2many(
        'account.payment',
        'highfive_booking_id',
        string='Payments',
        readonly=True
    )
    
    payment_count = fields.Integer(
        'Payments Count',
        compute='_compute_payment_count',
        store=True
    )
    
    paid_amount = fields.Monetary(
        'Paid Amount',
        currency_field='currency_id',
        compute='_compute_payment_status',
        store=True
    )

    # Payment Breakdown
    payment_card = fields.Monetary(
        'Card Payment',
        currency_field='currency_id',
        default=0.0
    )

    payment_wallet = fields.Monetary(
        'Wallet Payment',
        currency_field='currency_id',
        default=0.0
    )

    payment_coupon = fields.Monetary(
        'Coupon Discount',
        currency_field='currency_id',
        default=0.0
    )

    payment_transaction_ref = fields.Char(
        'Payment Transaction Reference',
        help='Reference number from payment gateway'
    )
    
    # =========================================================================
    # FIELDS - Status
    # =========================================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='Status', default='draft', required=True, tracking=True)
    
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded')
    ], string='Payment Status', 
       compute='_compute_payment_status',
       store=True)
    
    # =========================================================================
    # FIELDS - Invoices
    # =========================================================================
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        compute='_compute_invoices',
        store=True
    )
    
    invoice_count = fields.Integer(
        'Invoices Count',
        compute='_compute_invoices',
        store=True
    )
    
    sales_invoice_id = fields.Many2one(
        'account.move',
        'Sales Invoice',
        readonly=True,
        copy=False
    )
    
    vendor_bill_id = fields.Many2one(
        'account.move',
        'Vendor Bill',
        readonly=True,
        copy=False
    )
    
    # =========================================================================
    # FIELDS - Additional Info
    # =========================================================================
    
    notes = fields.Text('Internal Notes')
    
    description = fields.Text('Description')
    
    # Schedule info
    start_datetime = fields.Datetime('Start Date & Time')
    end_datetime = fields.Datetime('End Date & Time')
    duration_hours = fields.Float('Duration (Hours)', compute='_compute_duration')
    
    # System fields
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    active = fields.Boolean('Active', default=True)
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        compute='_compute_commission',
        store=True,
        help="Commission percentage applied to this booking"
    )

    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Commission Type', compute='_compute_commission', store=True)

    commission_amount_net = fields.Monetary(
        string='Commission (Net)',
        currency_field='currency_id',
        compute='_compute_commission',
        store=True,
        help="Commission amount before tax"
    )
    commission_id = fields.Many2one(
        'highfive.unit.commission',
        string='Applied Commission Rule',
        compute='_compute_commission',
        store=True,
        readonly=True,
        help='The commission rule that was applied to this booking'
    )

    commission_amount_tax = fields.Monetary(
        string='Commission Tax',
        currency_field='currency_id',
        compute='_compute_commission',
        store=True,
        help="Tax on commission"
    )

    commission_percent = fields.Float(
        string='Commission %',
        compute='_compute_commission',
        store=True,
        help="Commission percentage value"
    )

    commission_fixed = fields.Monetary(
        string='Commission Fixed',
        currency_field='currency_id',
        compute='_compute_commission',
        store=True,
        help="Fixed commission amount"
    )

    commission_amount_total = fields.Monetary(
        string='Commission (Total)',
        currency_field='currency_id',
        compute='_compute_commission',
        store=True,
        help="Commission amount including tax"
    )

    commission_invoice_id = fields.Many2one(
        'account.move',
        'Commission Invoice',
        readonly=True,
        copy=False,
        help='Commission invoice for cash payment bookings'
    )

    # ================================================================
    # Commission Computation
    # ================================================================

    @api.depends('commission_id', 'booking_type', 'subtotal', 'tax_percent')
    def _compute_commission(self):
        """
        Calculate commission based on commission_id and booking_type

        Simple Logic:
        1. Use commission_id (sent from API)
        2. Get percent + fixed for booking_type
        3. Calculate commission amount
        """
        for booking in self:
            # Reset if no commission
            if not booking.commission_id or not booking.booking_type:
                booking._reset_commission()
                continue

            # ================================================================
            # Get Commission Values (percent + fixed)
            # ================================================================
            commission = booking.commission_id
            percent, fixed = commission.get_commission_values(booking.booking_type)

            booking.commission_percent = percent
            booking.commission_fixed = fixed

            # ================================================================
            # Calculate Commission Amount
            # ================================================================
            # All prices are tax-included
            tax_rate = booking.tax_percent / 100.0

            # Get net amount (before tax)
            # Subtotal already includes tax
            total_net = booking.subtotal / (1 + tax_rate)

            # Commission = (Net × Percent%) + Fixed
            commission_net = (total_net * (percent / 100.0)) + fixed

            # Tax on commission
            commission_tax = commission_net * tax_rate
            commission_total = commission_net + commission_tax

            booking.commission_amount_net = round(commission_net, 2)
            booking.commission_amount_tax = round(commission_tax, 2)
            booking.commission_amount_total = round(commission_total, 2)

            _logger.info(
                f"Commission for booking {booking.name}: "
                f"Rule={commission.name}, Type={booking.booking_type}, "
                f"Formula=({percent}% × {total_net:.2f}) + {fixed} = {commission_net:.2f}, "
                f"Total={commission_total:.2f}"
            )

    def _reset_commission(self):
        """Reset all commission fields"""
        self.commission_percent = 0.0
        self.commission_fixed = 0.0
        self.commission_amount_net = 0.0
        self.commission_amount_tax = 0.0
        self.commission_amount_total = 0.0
    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    _sql_constraints = [
        ('highfive_booking_id_unique',
         'unique(highfive_booking_id)',
         'HighFive Booking ID must be unique!'),
    ]
    
    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================

    @api.depends('branch_id', 'branch_id.analytic_account_id', 'branch_id.partner_id.analytic_parent_id')
    def _compute_analytic_account(self):
        """Get analytic account from branch first, then partner"""
        for record in self:
            if record.branch_id:
                # أولاً: جرب من الفرع
                if record.branch_id.analytic_account_id:
                    record.analytic_account_id = record.branch_id.analytic_account_id
                # ثانياً: fallback للشريك
                elif record.branch_id.partner_id and record.branch_id.partner_id.analytic_parent_id:
                    record.analytic_account_id = record.branch_id.partner_id.analytic_parent_id
                else:
                    record.analytic_account_id = False
            else:
                record.analytic_account_id = False
    
    # @api.depends('service_ids')
    # def _compute_service_count(self):
    #     """Count additional services"""
    #     for record in self:
    #         record.service_count = len(record.service_ids)
    #
    @api.depends('payment_ids')
    def _compute_payment_count(self):
        """Count payments"""
        for record in self:
            record.payment_count = len(record.payment_ids)

    @api.depends('booking_line_ids', 'booking_line_ids.price_subtotal',
                 'booking_line_ids.line_type', 'discount', 'tax_percent', 'tax_status')
    def _compute_amounts(self):
        """Calculate amounts from booking lines"""
        for record in self:
            # Get unit line
            unit_line = record.booking_line_ids.filtered(
                lambda l: l.line_type == 'unit'
            )
            session_base_price = unit_line[0].price_subtotal if unit_line else 0.0
            record.session_base_price = session_base_price  # ✅



            # Services total
            service_lines = record.booking_line_ids.filtered(
                lambda l: l.line_type == 'service'
            )
            services_total = sum(service_lines.mapped('price_subtotal'))
            record.services_total = services_total

            # Calculate totals
            subtotal_before_discount = session_base_price + services_total

            if record.tax_status == 'included':
                tax_rate = record.tax_percent / 100
                total_with_tax = round(subtotal_before_discount - record.discount, 2)
                record.total = total_with_tax
                subtotal = round(total_with_tax / (1 + tax_rate), 2)
                record.subtotal = subtotal
                record.tax_amount = round(total_with_tax - subtotal, 2)
            else:
                subtotal = round(subtotal_before_discount - record.discount, 2)
                record.subtotal = subtotal
                tax_amount = round(subtotal * (record.tax_percent / 100), 2)
                record.tax_amount = tax_amount
                record.total = round(subtotal + tax_amount, 2)

    @api.depends('booking_date')
    def _compute_booking_day(self):
        """Compute day of week from booking date"""
        days = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday'
        }
        for record in self:
            if record.booking_date:
                weekday = record.booking_date.weekday()
                record.booking_day = days.get(weekday)
            else:
                record.booking_day = False

    @api.depends('booking_date', 'session_start_time', 'session_end_time')
    def _compute_session_datetimes(self):
        """Compute full datetimes from date and time"""
        for record in self:
            if record.booking_date and record.session_start_time is not False:
                # Convert float time to hours and minutes
                start_hours = int(record.session_start_time)
                start_minutes = int((record.session_start_time - start_hours) * 60)

                # Create datetime
                dt = datetime.combine(
                    record.booking_date,
                    datetime.min.time()
                )
                record.session_start_datetime = dt + timedelta(
                    hours=start_hours,
                    minutes=start_minutes
                )

                # Same for end time
                if record.session_end_time is not False:
                    end_hours = int(record.session_end_time)
                    end_minutes = int((record.session_end_time - end_hours) * 60)

                    record.session_end_datetime = dt + timedelta(
                        hours=end_hours,
                        minutes=end_minutes
                    )
                else:
                    record.session_end_datetime = False
            else:
                record.session_start_datetime = False
                record.session_end_datetime = False

    @api.depends('session_start_time', 'session_end_time')
    def _compute_session_duration(self):
        """Calculate session duration in hours"""
        for record in self:
            if record.session_start_time and record.session_end_time:
                record.session_duration = record.session_end_time - record.session_start_time
            else:
                record.session_duration = 0.0

    # @api.depends('booking_line_ids', 'booking_line_ids.line_type', 'booking_line_ids.product_id')
    # def _compute_unit_from_lines(self):
    #     """Get main unit from booking lines"""
    #     for record in self:
    #         unit_line = record.booking_line_ids.filtered(
    #             lambda l: l.line_type == 'unit'
    #         )
    #         record.unit_id = unit_line[0].product_id if unit_line else False

    @api.constrains('session_start_time', 'session_end_time')
    def _check_session_times(self):
        """Validate session times"""
        for record in self:
            if record.session_start_time < 0 or record.session_start_time >= 24:
                raise ValidationError("Start time must be between 0 and 24!")

            if record.session_end_time < 0 or record.session_end_time >= 24:
                raise ValidationError("End time must be between 0 and 24!")

            if record.session_end_time <= record.session_start_time:
                raise ValidationError("End time must be after start time!")

    @api.constrains('booking_line_ids')
    def _check_booking_lines(self):
        """Ensure there is exactly one unit line"""
        for record in self:
            unit_lines = record.booking_line_ids.filtered(
                lambda l: l.line_type == 'unit'
            )
            if len(unit_lines) == 0:
                raise ValidationError("Booking must have at least one Unit!")
            if len(unit_lines) > 1:
                raise ValidationError("Booking can have only one Unit!")

    @api.depends('payment_ids.amount', 'payment_ids.state', 'total')
    def _compute_payment_status(self):
        """Calculate payment status"""
        for record in self:
            paid_payments = record.payment_ids.filtered(lambda p: p.state == 'posted')
            record.paid_amount = sum(paid_payments.mapped('amount'))

            if record.paid_amount == 0:
                record.payment_state = 'not_paid'
            elif record.paid_amount >= record.total:
                record.payment_state = 'paid'
            else:
                record.payment_state = 'partial'
    
    @api.depends('sales_invoice_id', 'vendor_bill_id')
    def _compute_invoices(self):
        """Compute invoice list and count"""
        for record in self:
            invoices = self.env['account.move']
            if record.sales_invoice_id:
                invoices |= record.sales_invoice_id
            if record.vendor_bill_id:
                invoices |= record.vendor_bill_id
            
            record.invoice_ids = invoices
            record.invoice_count = len(invoices)
    
    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        """Calculate duration in hours"""
        for record in self:
            if record.start_datetime and record.end_datetime:
                delta = record.end_datetime - record.start_datetime
                record.duration_hours = delta.total_seconds() / 3600
            else:
                record.duration_hours = 0.0
    
    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        """Update partner when branch changes"""
        if self.branch_id:
            self.partner_id = self.branch_id.partner_id
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Filter branches by partner"""
        if self.partner_id:
            return {
                'domain': {
                    'branch_id': [('partner_id', '=', self.partner_id.id)]
                }
            }
        return {'domain': {'branch_id': []}}
    
    # =========================================================================
    # CRUD METHODS
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Create booking with sequence (batch-friendly)"""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('highfive.booking') or 'New'
        return super().create(vals_list)
    
    def write(self, vals):
        """Prevent editing confirmed bookings"""
        for record in self:
            if record.state in ('completed', 'cancelled') and not self.env.user.has_group('account.group_account_manager'):
                raise UserError("Cannot modify completed or cancelled bookings!")
        return super(HighFiveBooking, self).write(vals)
    
    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_confirm(self):
        """Confirm booking and create invoices"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Only draft bookings can be confirmed!")
            
            # Create invoices
            record._create_invoices()
            
            # Update state
            record.state = 'confirmed'
            
            _logger.info(f"Booking {record.name} confirmed and invoices created")
    
    def action_set_in_progress(self):
        """Mark booking as in progress"""
        self.write({'state': 'in_progress'})
    
    def action_complete(self):
        """Mark booking as completed"""
        self.write({'state': 'completed'})
    
    def action_cancel(self):
        """Cancel booking"""
        for record in self:
            if record.state == 'completed':
                raise UserError("Cannot cancel completed bookings!")
            
            # TODO: Handle invoice cancellation/refund
            record.state = 'cancelled'
    
    def action_set_no_show(self):
        """Mark as no show"""
        self.write({'state': 'no_show'})
    
    def action_view_invoices(self):
        """Open invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'create': False}
        }

    def action_view_payments(self):
        """Open payments for this booking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',  # ✅
            'view_mode': 'list,form',
            'domain': [('highfive_booking_id', '=', self.id)],  # ✅
            'context': {'default_highfive_booking_id': self.id}
        }
    
    # =========================================================================
    # INVOICE CREATION
    # =========================================================================

    def _create_invoices(self):
        """
        Create invoices based on payment method

        Logic:
        - payment_method = 'online': Sales Invoice (3 lines) + Vendor Bill (2 lines)
        - payment_method = 'cash': Sales Invoice (1 line: commission)

        All prices include tax (price_include_override = 'tax_included')
        """
        self.ensure_one()

        if not self.analytic_account_id:
            raise UserError("No analytic account found for this branch!")

        # Get commission
        commission_net = self.commission_amount_net
        commission_total = self.commission_amount_total

        if commission_total <= 0:
            raise UserError("Commission calculation failed!")

        # Route based on payment_method
        if self.payment_method == 'online':
            self._create_online_invoices(commission_net, commission_total)
        elif self.payment_method == 'cash':
            self._create_cash_invoice(commission_total)
        else:
            raise ValidationError(f"Unknown payment method: {self.payment_method}")

    # ============================================================================
    # METHOD: _create_online_invoices() - UPDATED
    # ============================================================================

    def _create_online_invoices(self, commission_net, commission_total):
        """
        Create invoices for ONLINE payment

        Creates:
        1. Sales Invoice → Partner (Unit + Services + Commission) = 200 SAR
        2. Vendor Bill → Partner (Unit + Services) = 174.25 SAR

        All prices include tax (tax_included)
        """
        self.ensure_one()

        # Get tax (tax_included for both sale and purchase)
        tax_sale = self._get_tax('sale')
        tax_purchase = self._get_tax('purchase')

        # Get lines
        unit_line = self.booking_line_ids.filtered(lambda l: l.line_type == 'unit')
        if not unit_line:
            raise ValidationError("Unit line not found!")

        service_lines = self.booking_line_ids.filtered(lambda l: l.line_type == 'service')

        # Calculate unit price after commission deduction
        tax_rate = self.tax_percent / 100.0
        unit_price_incl = unit_line.price_unit  # 150 SAR (includes tax)
        unit_price_net = unit_price_incl / (1 + tax_rate)  # 130.43 SAR
        unit_net_after_commission = unit_price_net - commission_net  # 130.43 - 22.39 = 108.04
        unit_incl_after_commission = unit_net_after_commission * (1 + tax_rate)  # 124.25 SAR
        unit_incl_after_commission = round(unit_incl_after_commission, 2)

        # ================================================================
        # 1. SALES INVOICE (Partner → HighFive)
        # ================================================================
        # Partner owes HighFive for booking (Unit + Services + Commission)

        invoice_lines = []

        # Line 1: Unit (after commission deduction)
        invoice_lines.append((0, 0, {
            'product_id': unit_line.product_id.id,
            'name': unit_line.name,
            'quantity': unit_line.quantity,
            'price_unit': unit_incl_after_commission,  # 124.25 SAR (tax included)
            'tax_ids': [(6, 0, [tax_sale.id])],
            'analytic_distribution': {str(self.analytic_account_id.id): 100},
        }))

        # Line 2: Services (as-is)
        for service_line in service_lines:
            invoice_lines.append((0, 0, {
                'product_id': service_line.product_id.id,
                'name': service_line.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,  # Tax included
                'tax_ids': [(6, 0, [tax_sale.id])],
                'analytic_distribution': {str(self.analytic_account_id.id): 100},
            }))

        # Line 3: Commission
        commission_product = self._get_commission_product()
        invoice_lines.append((0, 0, {
            'product_id': commission_product.id,
            'name': f'HighFive Commission {self.commission_percent}% + {self.commission_fixed}',
            'quantity': 1,
            'price_unit': commission_total,  # 25.75 SAR (tax included)
            'tax_ids': [(6, 0, [tax_sale.id])],
            'analytic_distribution': {str(self.analytic_account_id.id): 100},
        }))

        # Create sales invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,  # المورد
            'currency_id': self.currency_id.id,
            'invoice_date': self.booking_date,
            'invoice_line_ids': invoice_lines,
            'ref': f'Booking: {self.name}',
            'narration': (
                f'HighFive Booking ID: {self.highfive_booking_id}\n'
                f'Customer: {self.customer_id.name if self.customer_id else "N/A"}\n'
                f'Payment: Online\n'
                f'Booking Type: {dict(self._fields["booking_type"].selection).get(self.booking_type)}\n'
                f'Commission: {commission_total:.2f} ({self.commission_percent}% + {self.commission_fixed})\n'
                f'Unit after commission: {unit_incl_after_commission:.2f}'
            ),
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        self.sales_invoice_id = invoice.id

        _logger.info(
            f"Sales invoice created: {invoice.name} - "
            f"Total={invoice.amount_total:.2f} "
            f"(Unit={unit_incl_after_commission:.2f} + Services + Commission={commission_total:.2f})"
        )

        # ================================================================
        # 2. VENDOR BILL (HighFive → Partner)
        # ================================================================
        # HighFive owes Partner for services (Unit + Services, no commission)

        bill_lines = []

        # Line 1: Unit (after commission deduction, same price)
        bill_lines.append((0, 0, {
            'product_id': unit_line.product_id.id,
            'name': unit_line.name,
            'quantity': unit_line.quantity,
            'price_unit': unit_incl_after_commission,  # 124.25 SAR (tax included)
            'tax_ids': [(6, 0, [tax_purchase.id])],
            'analytic_distribution': {str(self.analytic_account_id.id): 100},
        }))

        # Line 2: Services (as-is)
        for service_line in service_lines:
            bill_lines.append((0, 0, {
                'product_id': service_line.product_id.id,
                'name': service_line.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,  # Tax included
                'tax_ids': [(6, 0, [tax_purchase.id])],
                'analytic_distribution': {str(self.analytic_account_id.id): 100},
            }))

        # Create vendor bill
        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,  # المورد
            'currency_id': self.currency_id.id,
            'invoice_date': self.booking_date,
            'invoice_line_ids': bill_lines,
            'ref': f'Booking: {self.name}',
            'narration': (
                f'HighFive Booking ID: {self.highfive_booking_id}\n'
                f'Payment to partner for services\n'
                f'Unit price (after commission): {unit_incl_after_commission:.2f}\n'
                f'Commission: {commission_total:.2f} deducted'
            ),
        }

        bill = self.env['account.move'].create(bill_vals)
        bill.action_post()
        self.vendor_bill_id = bill.id

        _logger.info(
            f"Vendor bill created: {bill.name} - "
            f"Total={bill.amount_total:.2f} "
            f"(Unit + Services, commission deducted)"
        )

    # ============================================================================
    # METHOD: _create_cash_invoice() - CASH PAYMENT
    # ============================================================================

    def _create_cash_invoice(self, commission_total):
        """
        Create commission invoice for CASH payment

        Creates:
        - Sales Invoice → Partner (Commission only) = 25.75 SAR

        Price includes tax (tax_included)
        """
        self.ensure_one()

        # Get tax
        tax_sale = self._get_tax('sale')

        # Get commission product
        commission_product = self._get_commission_product()

        # Get customer name for narration
        customer_name = self.customer_id.name if self.customer_id else 'غير محدد'

        invoice_lines = []

        # Line 1: Commission only
        invoice_lines.append((0, 0, {
            'product_id': commission_product.id,
            'name': (
                f'HighFive Commission - Cash Booking\n'
                f'{self.commission_percent}% + {self.commission_fixed}\n'
                f'Booking: {self.name}'
            ),
            'quantity': 1,
            'price_unit': commission_total,  # 25.75 SAR (tax included)
            'tax_ids': [(6, 0, [tax_sale.id])],
            'analytic_distribution': {str(self.analytic_account_id.id): 100},
        }))

        # Create sales invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,  # المورد
            'currency_id': self.currency_id.id,
            'invoice_date': self.booking_date,
            'invoice_line_ids': invoice_lines,
            'ref': f'Commission: {self.name}',
            'narration': (
                f'عميل الحجز: {customer_name}\n'
                f'تم الدفع: كاش\n'
                f'ـــــــــــــــــــــــــــــــــــــ\n'
                f'HighFive Booking ID: {self.highfive_booking_id}\n'
                f'Booking Type: {dict(self._fields["booking_type"].selection).get(self.booking_type)}\n'
                f'Booking Date: {self.booking_date}\n'
                f'Commission: {commission_total:.2f} {self.currency_id.name} '
                f'({self.commission_percent}% + {self.commission_fixed})'
            ),
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        self.sales_invoice_id = invoice.id

        _logger.info(
            f"Cash commission invoice created: {invoice.name} - "
            f"Total={commission_total:.2f}"
        )

    def _get_commission_product(self):
        """Get or create commission product"""
        commission_product = self.env['product.product'].search([
            ('default_code', '=', 'HF-COMMISSION')
        ], limit=1)

        if not commission_product:
            commission_product = self.env['product.product'].create({
                'name': 'HighFive Commission',
                'default_code': 'HF-COMMISSION',
                'type': 'service',
                'categ_id': self.env.ref('product.product_category_all').id,
                'list_price': 0.0,
                'taxes_id': [(5, 0, 0)],  # No default taxes
                'supplier_taxes_id': [(5, 0, 0)],
            })
            _logger.info("Created commission product: HF-COMMISSION")

        return commission_product



    def _get_tax(self, tax_type='sale'):
        """
        Get tax with price_include_override = tax_included

        Args:
            tax_type: 'sale' or 'purchase'
        """
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', tax_type),
            ('amount', '=', self.tax_percent),
            ('price_include_override', '=', 'tax_included'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not tax:
            raise UserError(
                f"Tax {self.tax_percent}% (tax_included) not found for {tax_type}!\n"
                "Please create it in: Accounting → Configuration → Taxes\n"
                "Domain: price_include_override = 'tax_included'"
            )

        return tax

    # =========================================================================
    # INVOICE PAYMENT
    # =========================================================================


    def _register_payment(self, invoice, payment_details=None):
        """Register payment for invoice and reconcile"""

        # تأكد من أن الفاتورة مرحّلة
        if invoice.state != 'posted':
            _logger.warning(f"Invoice {invoice.name} is not posted")
            return None

        # Get journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', invoice.company_id.id)
        ], limit=1)

        if not journal:
            _logger.warning("No bank journal found")
            return None

        payment_details = payment_details or {}

        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': invoice.amount_total,
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'memo': f"Payment for Booking {self.name}",  # ✅ memo بدلاً من ref

            # HighFive Fields
            'highfive_booking_id': self.id,
            'highfive_payment_id': payment_details.get('payment_id'),
            'payment_card': payment_details.get('card', 0) or self.payment_card,
            'payment_wallet': payment_details.get('wallet', 0) or self.payment_wallet,
            'payment_coupon': payment_details.get('coupon', 0) or self.payment_coupon,
            'transaction_reference': payment_details.get('transaction_ref'),
        }

        try:
            # إنشاء الدفعة
            payment = self.env['account.payment'].create(payment_vals)
            _logger.info(f"Payment created: {payment.name}")

            # ترحيل الدفعة
            payment.action_post()
            _logger.info(f"Payment posted: {payment.name}")

            # ✅ في Odoo 18: استخدم move_id.line_ids بدلاً من line_ids
            if not payment.move_id:
                _logger.error("Payment has no move_id")
                return payment

            # ابحث عن سطور الذمم
            invoice_receivable_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )

            payment_receivable_line = payment.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )

            _logger.info(
                f"Invoice lines: {len(invoice_receivable_line)}, Payment lines: {len(payment_receivable_line)}")

            if invoice_receivable_line and payment_receivable_line:
                # تحقق من تطابق الحسابات
                if invoice_receivable_line[0].account_id == payment_receivable_line[0].account_id:
                    # Reconcile
                    lines_to_reconcile = invoice_receivable_line + payment_receivable_line
                    lines_to_reconcile.reconcile()
                    _logger.info(f"✅ Payment reconciled for invoice {invoice.name}")
                else:
                    _logger.error(f"Account mismatch")
            else:
                _logger.warning(f"No lines to reconcile")

            return payment

        except Exception as e:
            _logger.error(f"❌ Error: {str(e)}", exc_info=True)
            return None

    def _create_commission_invoice(self, commission_amount):
        """Create commission-only invoice for cash bookings"""
        commission_product = self.env.ref('highfive_core.product_highfive_commission',
                                         raise_if_not_found=False)
        if not commission_product:
            raise UserError("Commission product not found!")
        
        tax = self._get_tax(self.tax_percent, 'sale')
        
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,  # Partner pays commission
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': commission_product.id,
                    'name': f'Commission - {self.unit_id.name}',
                    'quantity': 1,
                    'price_unit': commission_amount,
                    'tax_ids': [(6, 0, [tax.id])] if tax else False,
                    'analytic_distribution': {
                        str(self.analytic_account_id.id): 100
                    } if self.analytic_account_id else False,
                }),
            ],
            'narration': f'Commission for Booking: {self.name}\nHighFive ID: {self.highfive_booking_id}',
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.write({
            'highfive_booking_id': self.id,
        })
        invoice.action_post()
        
        return invoice
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_commission_rate(self):
        """Get commission rate for this booking"""
        # Try to get from unit commission
        commission = self.env['highfive.unit.commission'].search([
            ('unit_id', '=', self.unit_id.id),
            ('type', '=', 'default')
        ], limit=1)

        if commission:
            import json
            try:
                if self.payment_method == 'online':
                    data = json.loads(commission.online_booking or '{}')
                else:
                    data = json.loads(commission.cash_booking or '{}')
                
                if data.get('type') == 'percentage':
                    return float(data.get('value', 15.0))
            except:
                pass
        
        # Default rates
        return 15.0 if self.payment_method == 'online' else 10.0
    
    def _get_partner_tax_rate(self):
        """Get tax rate for partner"""
        if hasattr(self.partner_id, 'tax_status') and self.partner_id.tax_status:
            tax_map = {
                'standard_15': 0.15,
                'reduced_5': 0.05,
                'zero': 0.0,
                'exempt': 0.0,
            }
            return tax_map.get(self.partner_id.tax_status, 0.15)
        return 0.15
    


    # في BUTTON METHODS section:

    def action_view_sales_invoice(self):
        """Open the sales invoice"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'res_model': 'account.move',
            'res_id': self.sales_invoice_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'context': {'default_move_type': 'out_invoice'}
        }

    def action_view_vendor_bill(self):
        """Open the vendor bill"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bill',
            'res_model': 'account.move',
            'res_id': self.vendor_bill_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'context': {'default_move_type': 'in_invoice'}
        }

    @api.constrains('session_start_time', 'session_end_time')
    def _check_session_times(self):
        """Validate session times"""
        for record in self:
            if record.session_start_time < 0 or record.session_start_time >= 24:
                raise ValidationError("Start time must be between 0 and 24!")
            if record.session_end_time < 0 or record.session_end_time >= 24:
                raise ValidationError("End time must be between 0 and 24!")
            if record.session_end_time <= record.session_start_time:
                raise ValidationError("End time must be after start time!")

    @api.constrains('booking_line_ids')
    def _check_booking_lines(self):
        """Ensure at least one unit line exists"""
        for record in self:
            if record.booking_line_ids:
                unit_lines = record.booking_line_ids.filtered(lambda l: l.line_type == 'unit')
                if len(unit_lines) == 0:
                    raise ValidationError("At least one Unit line is required!")
                if len(unit_lines) > 1:
                    raise ValidationError("Only one Unit line is allowed!")