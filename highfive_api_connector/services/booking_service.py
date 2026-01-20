# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from datetime import datetime
import logging
from odoo import fields
_logger = logging.getLogger(__name__)


class BookingService:
    """Booking Processing Service"""

    def __init__(self, env):
        self.env = env

    def process(self, data):
        """
        Process booking data - create or update booking

        Args:
            data: Booking data from HighFive

        Returns:
            Result dictionary with booking and invoices info
        """
        # Validate
        self._validate(data)

        # Check if booking exists
        booking = self.env['highfive.booking'].search([
            ('highfive_booking_id', '=', str(data['id']))
        ], limit=1)

        if booking:
            return self._update_booking(booking, data)
        else:
            return self._create_booking(data)

    def _create_booking(self, data):
        """Create new booking"""
        # Get unit first (needed for lines)
        unit = self._get_unit(data['unit_id'])

        # Transform data
        vals = self._transform(data)

        # Create booking
        booking = self.env['highfive.booking'].create(vals)

        _logger.info(f"Created booking {booking.id}: {booking.name}")

        # Create booking lines (pass unit directly)
        self._create_booking_lines(booking, data, unit)

        # Auto-confirm if status is confirmed
        if data.get('status') == 'confirmed':
            booking.action_confirm()
            _logger.info(f"Auto-confirmed booking {booking.id}")

        # Prepare result
        result = {
            'action': 'created',
            'booking_id': booking.id,
            'booking_ref': booking.name,
            'model': 'highfive.booking',
            'state': booking.state
        }

        # Add invoice info if confirmed
        if booking.state == 'confirmed':
            result['invoices'] = self._get_invoice_info(booking)

        return result

    def _update_booking(self, booking, data):
        """Update existing booking (non-financial data only)"""

        # Don't update if completed or cancelled
        if booking.state in ['completed', 'cancelled']:
            _logger.warning(
                f"Cannot update booking {booking.id} - state is {booking.state}"
            )
            return {
                'action': 'skipped',
                'booking_id': booking.id,
                'reason': f'Booking is {booking.state}',
                'model': 'highfive.booking'
            }

        # ✅ إذا confirmed، فقط non-financial updates مسموحة
        if booking.state == 'confirmed':
            # قائمة الحقول المسموح تحديثها
            allowed_fields = [
                'booking_date',
                'session_start_time',
                'session_end_time',
                'notes'
            ]

            # فلتر data: فقط الحقول المسموحة
            vals = {}
            for field in allowed_fields:
                if field in data:
                    if field in ['session_start_time', 'session_end_time']:
                        vals[field] = float(data[field])
                    else:
                        vals[field] = data[field]

            if vals:
                booking.write(vals)
                _logger.info(
                    f"Updated non-financial data for booking {booking.id}: {list(vals.keys())}"
                )

            # تجاهل الحقول المالية بصمت
            ignored_fields = [
                f for f in ['session_base_price', 'services', 'discount', 'tax_percent']
                if f in data
            ]
            if ignored_fields:
                _logger.info(
                    f"Ignored financial fields for confirmed booking {booking.id}: {ignored_fields}"
                )

        else:
            # ✅ إذا draft، يمكن تحديث كل شيء
            vals = self._transform(data, is_update=True)
            booking.write(vals)
            _logger.info(f"Updated booking {booking.id}")

            # Update booking lines if services changed
            if 'services' in data:
                self._update_booking_lines(booking, data)

            # Confirm if needed
            if data.get('status') == 'confirmed' and booking.state == 'draft':
                booking.action_confirm()
                _logger.info(f"Confirmed booking {booking.id}")

        # Prepare result
        result = {
            'action': 'updated',
            'booking_id': booking.id,
            'booking_ref': booking.name,
            'model': 'highfive.booking',
            'state': booking.state
        }

        if booking.state == 'confirmed':
            result['invoices'] = self._get_invoice_info(booking)

        return result

    def update_payment(self, booking_id, payment_data):
        """
        Register payment for booking invoice (accounting only)
        Does NOT update booking fields - only creates payment record

        Args:
            booking_id: HighFive booking ID
            payment_data: Payment information

        Returns:
            Result dictionary
        """
        # Find booking
        booking = self.env['highfive.booking'].search([
            ('highfive_booking_id', '=', str(booking_id))
        ], limit=1)

        if not booking:
            raise ValidationError(f"Booking {booking_id} not found")

        # يجب أن يكون confirmed
        if booking.state != 'confirmed':
            raise ValidationError(
                f"Cannot register payment for {booking.state} booking. "
                "Only confirmed bookings can receive payments."
            )

        # Validate payment data
        self._validate_payment(payment_data)

        result = {
            'action': 'payment_updated',
            'booking_id': booking.id,
            'payments': []
        }

        # ✅ Register payment for sales invoice (online payment)
        if booking.sales_invoice_id:
            invoice = booking.sales_invoice_id

            if invoice.state == 'posted' and invoice.payment_state in ['not_paid', 'partial']:
                payment = self._register_payment(invoice, payment_data)

                if payment:
                    result['payments'].append({
                        'type': 'customer_payment',
                        'invoice_id': invoice.id,
                        'invoice_ref': invoice.name,
                        'payment_id': payment.id,
                        'payment_ref': payment.name,
                        'amount': payment.amount,
                        'date': str(payment.date)
                    })
                    _logger.info(
                        f"Registered payment {payment.name} for invoice {invoice.name}"
                    )
            else:
                result['payments'].append({
                    'type': 'customer_payment',
                    'invoice_id': invoice.id,
                    'status': 'already_paid' if invoice.payment_state == 'paid' else 'not_posted'
                })

        # ✅ معلومات نهائية
        result['invoice_states'] = {
            'sales_invoice': booking.sales_invoice_id.payment_state if booking.sales_invoice_id else None,
            'vendor_bill': booking.vendor_bill_id.payment_state if booking.vendor_bill_id else None,
        }
        result['invoice_states'] = {
            'sales_invoice': booking.sales_invoice_id.payment_state if booking.sales_invoice_id else None,
            # vendor_bill_id is no longer used
        }

        return result

    def refund_booking(self, booking_id, reason=''):
        """
        Refund booking with proper accounting (credit notes & refund payments)

        Args:
            booking_id: HighFive booking ID
            reason: Refund reason

        Returns:
            Result dictionary
        """
        booking = self.env['highfive.booking'].search([
            ('highfive_booking_id', '=', str(booking_id))
        ], limit=1)

        if not booking:
            raise ValidationError(f"Booking {booking_id} not found")

        if booking.state == 'cancelled':
            return {
                'action': 'already_cancelled',
                'booking_id': booking.id,
                'state': 'cancelled'
            }

        result = {
            'action': 'refunded',
            'booking_id': booking.id,
            'credit_notes': [],
            'refund_payments': []
        }

        # ================================================================
        # 1. Sales Invoice - Credit Note & Refund Payment
        # ================================================================
        if booking.sales_invoice_id and booking.sales_invoice_id.state == 'posted':
            invoice = booking.sales_invoice_id

            # Create credit note
            credit_note = invoice._reverse_moves(
                default_values_list=[{
                    'ref': f'Refund: {reason}',
                    'invoice_date': fields.Date.today(),
                }]
            )
            credit_note.action_post()

            result['credit_notes'].append({
                'type': 'sales_invoice',
                'original_invoice': invoice.name,
                'credit_note': credit_note.name,
                'amount': credit_note.amount_total
            })

            _logger.info(f"Created credit note {credit_note.name} for invoice {invoice.name}")

            # Refund payment if paid
            if invoice.payment_state == 'paid':
                refund_payment = self._create_refund_payment(invoice, credit_note)
                if refund_payment:
                    result['refund_payments'].append({
                        'type': 'customer_refund',
                        'payment_ref': refund_payment.name,
                        'amount': refund_payment.amount
                    })
                    _logger.info(f"Created refund payment {refund_payment.name}")

        # ================================================================
        # 2. Vendor Bill - Cancel or Refund
        # ================================================================
        if booking.vendor_bill_id:
            bill = booking.vendor_bill_id

            if bill.state == 'posted':
                # إذا مدفوعة → credit note
                if bill.payment_state == 'paid':
                    bill_credit = bill._reverse_moves(
                        default_values_list=[{
                            'ref': f'Refund: {reason}',
                            'invoice_date': fields.Date.today(),
                        }]
                    )
                    bill_credit.action_post()

                    result['credit_notes'].append({
                        'type': 'vendor_bill',
                        'original_bill': bill.name,
                        'credit_note': bill_credit.name,
                        'amount': bill_credit.amount_total
                    })

                    _logger.info(f"Created credit note {bill_credit.name} for bill {bill.name}")



                # إذا غير مدفوعة → إلغاء مباشر
                else:
                    bill.button_draft()
                    bill.button_cancel()
                    result['credit_notes'].append({
                        'type': 'vendor_bill',
                        'original_bill': bill.name,
                        'action': 'cancelled',
                        'amount': bill.amount_total
                    })
                    _logger.info(f"Cancelled unpaid bill {bill.name}")

            elif bill.state == 'draft':
                bill.button_cancel()
                result['credit_notes'].append({
                    'type': 'vendor_bill',
                    'original_bill': bill.name,
                    'action': 'cancelled',
                    'amount': bill.amount_total
                })

        # ================================================================
        # 3. Update Booking State
        # ================================================================
        booking.write({
            'state': 'cancelled',
            'notes': f"Refunded: {reason}"
        })

        _logger.info(f"Refunded booking {booking.id}")

        result['state'] = 'cancelled'
        return result

    def cancel_booking(self, booking_id, reason=''):
        """
        Cancel booking directly (no credit notes, just cancel)

        Args:
            booking_id: HighFive booking ID
            reason: Cancellation reason

        Returns:
            Result dictionary
        """
        booking = self.env['highfive.booking'].search([
            ('highfive_booking_id', '=', str(booking_id))
        ], limit=1)

        if not booking:
            raise ValidationError(f"Booking {booking_id} not found")

        if booking.state == 'cancelled':
            return {
                'action': 'already_cancelled',
                'booking_id': booking.id,
                'state': 'cancelled'
            }

        result = {
            'action': 'cancelled',
            'booking_id': booking.id,
            'cancelled_items': []
        }

        # ================================================================
        # 1. Cancel Sales Invoice
        # ================================================================
        if booking.sales_invoice_id:
            invoice = booking.sales_invoice_id

            if invoice.state == 'draft':
                invoice.button_cancel()
                result['cancelled_items'].append({
                    'type': 'sales_invoice',
                    'ref': invoice.name,
                    'state': 'cancelled'
                })
            elif invoice.state == 'posted':
                # لا يمكن إلغاء posted مباشرة
                invoice.button_draft()
                invoice.button_cancel()
                result['cancelled_items'].append({
                    'type': 'sales_invoice',
                    'ref': invoice.name,
                    'state': 'posted',
                    'note': 'Cannot cancel posted invoice directly'
                })

            _logger.info(f"Cancelled sales invoice {invoice.name}")

        # ================================================================
        # 2. Cancel Vendor Bill
        # ================================================================
        if booking.vendor_bill_id:
            bill = booking.vendor_bill_id

            if bill.state == 'draft':
                bill.button_cancel()
                result['cancelled_items'].append({
                    'type': 'vendor_bill',
                    'ref': bill.name,
                    'state': 'cancelled'
                })
            elif bill.state == 'posted':
                # تحويل إلى draft ثم cancel
                bill.button_draft()
                bill.button_cancel()
                result['cancelled_items'].append({
                    'type': 'vendor_bill',
                    'ref': bill.name,
                    'state': 'cancelled'
                })

            _logger.info(f"Cancelled vendor bill {bill.name}")

        # ================================================================
        # 3. Cancel Payments (if draft)
        # ================================================================
        payment_count = 0
        if booking.sales_invoice_id:
            payments = self.env['account.payment'].search([
                ('ref', 'ilike', booking.sales_invoice_id.name),
                ('state', '=', 'draft')
            ])
            for payment in payments:
                payment.action_cancel()
                payment_count += 1

        if payment_count > 0:
            result['cancelled_items'].append({
                'type': 'payments',
                'count': payment_count,
                'state': 'cancelled'
            })

        # ================================================================
        # 4. Update Booking State
        # ================================================================
        booking.write({
            'state': 'cancelled',
            'notes': f"Cancelled: {reason}"
        })

        _logger.info(f"Cancelled booking {booking.id}")

        result['state'] = 'cancelled'
        return result

    def get_booking_status(self, booking_id):
        """
        Get booking status and details

        Args:
            booking_id: HighFive booking ID

        Returns:
            Booking details dictionary
        """
        booking = self.env['highfive.booking'].search([
            ('highfive_booking_id', '=', str(booking_id))
        ], limit=1)

        if not booking:
            raise ValidationError(f"Booking {booking_id} not found")

        return {
            'booking_id': booking.id,
            'name': booking.name,
            'highfive_booking_id': booking.highfive_booking_id,
            'state': booking.state,
            'payment_state': booking.payment_state,
            'booking_date': booking.booking_date.isoformat() if booking.booking_date else None,
            'customer': {
                'id': booking.customer_id.id,
                'name': booking.customer_id.name,
                'phone': booking.customer_phone,
                'email': booking.customer_email
            },
            'unit': {
                'id': booking.unit_id.id if booking.unit_id else None,
                'name': booking.unit_id.name if booking.unit_id else None
            },
            'amounts': {
                'session_base_price': booking.session_base_price,
                'services_total': booking.services_total,
                'discount': booking.discount,
                'subtotal': booking.subtotal,
                'tax_amount': booking.tax_amount,
                'total': booking.total
            },
            'payment': {
                'method': booking.payment_method,
                'card': booking.payment_card,
                'wallet': booking.payment_wallet,
                'coupon': booking.payment_coupon,
                'transaction_ref': booking.payment_transaction_ref
            },
            # ================================================================
            # Commission Info (NEW)
            # ================================================================
            'commission': {
                'id': booking.commission_id.id if booking.commission_id else None,
                'name': booking.commission_id.name if booking.commission_id else None,
                'booking_type': booking.booking_type,
                'percent': booking.commission_percent,
                'fixed': booking.commission_fixed,
                'amount_net': booking.commission_amount_net,
                'amount_tax': booking.commission_amount_tax,
                'amount_total': booking.commission_amount_total
            },
            'invoices': self._get_invoice_info(booking)
        }

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def _validate(self, data):
        """Validate booking data"""
        required_fields = [
            'id',
            'highfive_booking_id',
            'booking_date',
            'session_start_time',
            'session_end_time',
            'unit_id',
            'booker_id',
            'session_base_price',
            'tax_percent',
            'tax_status',
            'total',
            'payment_method',
            'booking_type',  # ← جديد: نوع الحجز (6 أنواع)
            'commission_id',  # ← جديد: ID قاعدة العمولة
            'status'
        ]

        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValidationError(f"Missing required field: {field}")

        # Validate times
        if data['session_end_time'] <= data['session_start_time']:
            raise ValidationError("End time must be after start time")

        # Validate payment method
        if data['payment_method'] not in ['online', 'cash']:
            raise ValidationError("Invalid payment method")

        # ================================================================
        # Validate booking_type (NEW)
        # ================================================================
        valid_booking_types = [
            'online_booking',
            'cash_booking',
            'walk_in_booking',
            'linked_booking',
            'online_public_event',
            'cash_public_event'
        ]
        if data['booking_type'] not in valid_booking_types:
            raise ValidationError(
                f"Invalid booking_type: {data['booking_type']}. "
                f"Must be one of: {', '.join(valid_booking_types)}"
            )

        # ================================================================
        # Validate commission_id exists (NEW)
        # ================================================================
        commission = self.env['highfive.unit.commission'].search([
            ('highfive_commission_id', '=', str(data['commission_id']))
        ], limit=1)

        if not commission:
            raise ValidationError(
                f"Commission rule {data['commission_id']} not found. "
                "Please create/sync commission rule first."
            )

        # Validate tax status
        if data['tax_status'] not in ['included', 'excluded']:
            raise ValidationError("Invalid tax status")

        # Validate status
        if data['status'] not in ['pending', 'confirmed', 'completed', 'cancelled']:
            raise ValidationError("Invalid status")

    def _validate_payment(self, payment_data):
        """Validate payment data"""
        if 'payment_status' not in payment_data and 'payment_method_details' not in payment_data:
            raise ValidationError("Payment data must include payment_status or payment_method_details")

    # =========================================================================
    # TRANSFORMATION
    # =========================================================================

    def _transform(self, data, is_update=False):
        """Transform HighFive data to Odoo format"""
        # Get unit
        unit = self._get_unit(data['unit_id'])

        # Get customer
        customer = self._get_customer(data['booker_id'])

        # Get partner from unit
        partner = unit.partner_id
        if not partner:
            raise ValidationError(f"Unit {data['unit_id']} has no partner assigned")

        # Get branch from unit
        branch = unit.branch_id
        if not branch:
            raise ValidationError(f"Unit {data['unit_id']} has no branch assigned")

        # ================================================================
        # Get commission (NEW)
        # ================================================================
        commission = self.env['highfive.unit.commission'].search([
            ('highfive_commission_id', '=', str(data['commission_id']))
        ], limit=1)

        if not commission:
            raise ValidationError(f"Commission {data['commission_id']} not found")

        # Get currency
        currency_id = self._get_currency(data.get('currency', 'SAR'))

        vals = {
            'highfive_booking_id': str(data['id']),
            'booking_date': data['booking_date'],
            'session_start_time': float(data['session_start_time']),
            'session_end_time': float(data['session_end_time']),
            'session_base_price': float(data['session_base_price']),
            'customer_id': customer.id,
            'partner_id': partner.id,
            'unit_id': unit.id,
            'currency_id': currency_id,
            'branch_id': branch.id,
            'discount': float(data.get('discount', 0)),
            'tax_percent': float(data['tax_percent']),
            'tax_status': data['tax_status'],
            'payment_method': data['payment_method'],

            # ================================================================
            # NEW FIELDS
            # ================================================================
            'booking_type': data['booking_type'],  # نوع الحجز
            'commission_id': commission.id,  # ربط قاعدة العمولة
        }

        # Payment details
        if data['payment_method'] == 'online':
            vals['payment_card'] = float(data.get('payment_card', 0))
            vals['payment_wallet'] = float(data.get('payment_wallet', 0))
            vals['payment_coupon'] = float(data.get('payment_coupon', 0))

        if data.get('payment_transaction_ref'):
            vals['payment_transaction_ref'] = data['payment_transaction_ref']

        # Notes
        if data.get('notes'):
            vals['notes'] = data['notes']

        return vals

    # =========================================================================
    # BOOKING LINES
    # =========================================================================

    def _create_booking_lines(self, booking, data, unit):
        """Create booking lines (unit + services)"""
        # Unit line (main product)
        # Get product.product variant from product.template
        unit_product = unit.product_variant_id
        if not unit_product:
            # Fallback: get first variant
            unit_product = unit.product_variant_ids[0] if unit.product_variant_ids else None

        if not unit_product:
            raise ValidationError(f"Unit {unit.id} has no product variant")

        unit_vals = {
            'booking_id': booking.id,
            'line_type': 'unit',
            'product_id': unit_product.id,  # Use product.product ID
            'name': unit.name,
            'quantity': 1,
            'price_unit': float(data['session_base_price']),
        }
        self.env['highfive.booking.line'].create(unit_vals)

        _logger.info(f"Created unit line for booking {booking.id}")

        # Service lines
        services = data.get('services', [])
        for service_data in services:
            service_template = self._get_service(service_data['service_id'])

            # Get product.product variant
            service_product = service_template.product_variant_id
            if not service_product:
                service_product = service_template.product_variant_ids[
                    0] if service_template.product_variant_ids else None

            if not service_product:
                raise ValidationError(f"Service {service_template.id} has no product variant")

            service_vals = {
                'booking_id': booking.id,
                'line_type': 'service',
                'product_id': service_product.id,
                'name': service_data.get('name', service_template.name),
                'quantity': float(service_data.get('quantity', 1)),
                'price_unit': float(service_data.get('price_unit', service_template.list_price)),
            }
            self.env['highfive.booking.line'].create(service_vals)

        if services:
            _logger.info(f"Created {len(services)} service lines for booking {booking.id}")

    def _update_booking_lines(self, booking, data):
        """Update booking lines"""
        # Remove old service lines
        booking.booking_line_ids.filtered(lambda l: l.line_type == 'service').unlink()

        # Create new service lines
        services = data.get('services', [])
        for service_data in services:
            service_template = self._get_service(service_data['service_id'])

            # Get product.product variant
            service_product = service_template.product_variant_id
            if not service_product:
                service_product = service_template.product_variant_ids[
                    0] if service_template.product_variant_ids else None

            if not service_product:
                raise ValidationError(f"Service {service_template.id} has no product variant")

            service_vals = {
                'booking_id': booking.id,
                'line_type': 'service',
                'product_id': service_product.id,  # FIXED: Use product.product ID
                'name': service_data.get('name', service_template.name),
                'quantity': float(service_data.get('quantity', 1)),
                'price_unit': float(service_data.get('price_unit', service_template.list_price)),
            }
            self.env['highfive.booking.line'].create(service_vals)

        _logger.info(f"Updated service lines for booking {booking.id}")

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_unit(self, unit_id):
        """Get unit by HighFive ID"""
        unit = self.env['product.template'].search([
            ('highfive_unit_id', '=', str(unit_id))
        ], limit=1)

        if not unit:
            raise ValidationError(f"Unit {unit_id} not found")

        return unit

    def _get_customer(self, customer_id):
        """Get customer by HighFive ID"""
        customer = self.env['res.partner'].search([
            ('highfive_customer_id', '=', str(customer_id))
        ], limit=1)

        if not customer:
            raise ValidationError(f"Customer {customer_id} not found")

        return customer

    def _get_service(self, service_id):
        """Get service product by ID"""
        service = self.env['product.template'].search([
            ('highfive_service_id', '=', str(service_id))
        ], limit=1)

        if not service.exists():
            raise ValidationError(f"Service {service_id} not found")

        return service

    def _reverse_and_recreate_invoice(self, booking):
        """Reverse invoice and create new one with updated amounts"""
        if not booking.sales_invoice_id:
            return

        invoice = booking.sales_invoice_id

        # إذا الفاتورة draft، يمكن حذفها مباشرة
        if invoice.state == 'draft':
            booking.write({'sales_invoice_id': False})
            invoice.button_cancel()
            invoice.unlink()

        # إذا posted، يجب عمل credit note
        elif invoice.state == 'posted':
            credit_note = invoice._reverse_moves(
                default_values_list=[{
                    'ref': f'Update booking: {booking.name}',
                    'invoice_date': fields.Date.today(),
                }]
            )
            credit_note.action_post()
            _logger.info(f"Created credit note {credit_note.name} for booking update")

            # حذف ربط الفاتورة القديمة
            booking.write({'sales_invoice_id': False})

        # نفس الشيء للـ vendor bill
        if booking.vendor_bill_id:
            bill = booking.vendor_bill_id
            if bill.state == 'draft':
                booking.write({'vendor_bill_id': False})
                bill.button_cancel()
                bill.unlink()
            elif bill.state == 'posted':
                bill_credit = bill._reverse_moves(
                    default_values_list=[{
                        'ref': f'Update booking: {booking.name}',
                        'invoice_date': fields.Date.today(),  # ← أضف هذا السطر
                    }]
                )
                bill_credit.action_post()
                booking.write({'vendor_bill_id': False})

        # ✅ أعد الحالة إلى draft أولاً
        booking.write({'state': 'draft'})

        # ✅ الآن يمكن إعادة التأكيد
        booking.action_confirm()

        _logger.info(f"Re-confirmed booking {booking.id} with new invoices")

    def _get_invoice_info(self, booking):
        """Get invoice information"""
        invoices = []

        # Sales invoice (always exists for both online and cash)
        if booking.sales_invoice_id:
            invoices.append({
                'type': 'sales_invoice',
                'id': booking.sales_invoice_id.id,
                'ref': booking.sales_invoice_id.name,
                'state': booking.sales_invoice_id.state,
                'payment_state': booking.sales_invoice_id.payment_state,
                'amount_total': booking.sales_invoice_id.amount_total,
                'partner': booking.sales_invoice_id.partner_id.name,
                'description': (
                    'Customer invoice (Unit + Services + Commission)'
                    if booking.payment_method == 'online'
                    else 'Partner invoice (Commission only)'
                )
            })

        # Note: vendor_bill_id is no longer used in the new system
        # All invoicing is done through sales_invoice_id

        return invoices

    def _register_payment(self, invoice, payment_data):
        """Register payment for invoice"""
        try:
            # Get payment journal
            journal = self.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', invoice.company_id.id)
            ], limit=1)

            if not journal:
                _logger.warning("No payment journal found")
                return

            # Create payment
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': invoice.partner_id.id,
                'amount': invoice.amount_residual,
                'journal_id': journal.id,
                'date': payment_data.get('payment_date', datetime.now().date()),
                'ref': payment_data.get('transaction_ref', invoice.name),
            }

            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()

            # Reconcile with invoice
            payment_line = payment.line_ids.filtered(
                lambda l: l.account_id == invoice.partner_id.property_account_receivable_id
            )
            invoice_line = invoice.line_ids.filtered(
                lambda l: l.account_id == invoice.partner_id.property_account_receivable_id
            )

            (payment_line + invoice_line).reconcile()

            _logger.info(f"Registered payment for invoice {invoice.id}")

        except Exception as e:
            _logger.error(f"Error registering payment: {e}")
            # Don't raise - payment registration is not critical

    def _create_refund_payment(self, invoice, credit_note):
        """Create refund payment for cancelled booking"""
        try:
            # Get payment journal
            journal = self.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', invoice.company_id.id)
            ], limit=1)

            if not journal:
                _logger.warning("No payment journal found for refund")
                return None

            # Create refund payment
            refund_vals = {
                'payment_type': 'outbound',
                'partner_type': 'customer',
                'partner_id': invoice.partner_id.id,
                'amount': credit_note.amount_total,
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': f'Refund: {invoice.name}',
            }

            refund = self.env['account.payment'].create(refund_vals)
            refund.action_post()

            # Reconcile with credit note
            refund_line = refund.line_ids.filtered(
                lambda l: l.account_id == invoice.partner_id.property_account_receivable_id
            )
            credit_line = credit_note.line_ids.filtered(
                lambda l: l.account_id == invoice.partner_id.property_account_receivable_id
            )

            (refund_line + credit_line).reconcile()

            return refund

        except Exception as e:
            _logger.error(f"Error creating refund payment: {e}")
            return Nonecurrency_code

    def _get_currency(self, currency_code):
        """
        Get currency by code

        Args:
            currency_code: Currency code (SAR, USD, EUR, etc.)

        Returns:
            Currency ID
        """
        if not currency_code:
            # Default to company currency
            return self.env.company.currency_id.id

        currency = self.env['res.currency'].search([
            ('name', '=', currency_code.upper())
        ], limit=1)

        if not currency:
            # If not found, use company currency
            _logger.warning(f"Currency {currency_code} not found, using company currency")
            return self.env.company.currency_id.id

        return currency.id