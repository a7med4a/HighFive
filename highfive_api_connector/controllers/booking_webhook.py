# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import json
import time
import traceback
import logging

_logger = logging.getLogger(__name__)


class HighFiveBookingWebhook(http.Controller):
    """
    Booking Webhook Controller

    Handles all booking-related API endpoints
    """

    # =========================================================================
    # BOOKING ENDPOINTS
    # =========================================================================

    @http.route('/api/odoo/bookings', type='json', auth='none', methods=['POST'], csrf=False)
    def create_booking(self, **kwargs):
        """Create or update booking"""
        data = request.get_json_data()
        return self._process_request('booking', data, 'create')

    @http.route('/api/odoo/bookings/<int:booking_id>/payment', type='json', auth='none', methods=['POST'], csrf=False)
    def update_payment(self, booking_id, **kwargs):
        """Update booking payment status"""
        data = request.get_json_data()
        data['booking_id'] = booking_id
        return self._process_request('booking', data, 'update_payment')



    @http.route('/api/odoo/bookings/<int:booking_id>/refund', type='json', auth='none', methods=['POST'], csrf=False)
    def refund_booking(self, booking_id, **kwargs):
        """Refund booking (credit notes & refund payments)"""
        data = request.get_json_data()
        data['booking_id'] = booking_id

        return self._process_request('booking', data, 'refund')

    @http.route('/api/odoo/bookings/<int:booking_id>/cancel', type='json', auth='none', methods=['POST'], csrf=False)
    def cancel_booking(self, booking_id, **kwargs):
        """Cancel booking (direct cancellation)"""
        data = request.get_json_data()
        data['booking_id'] = booking_id

        return self._process_request('booking', data, 'cancel')

    @http.route('/api/odoo/bookings/<int:booking_id>', type='http', auth='none', methods=['GET'], csrf=False)
    def get_booking(self, booking_id, **kwargs):
        """Get booking status"""
        data = {'booking_id': booking_id}
        result = self._process_request('booking', data, 'get_status')
        return request.make_json_response(result)

    # =========================================================================
    # MAIN PROCESSING
    # =========================================================================

    def _process_request(self, entity_type, data, action):
        """
        Main processing flow for booking requests

        Args:
            entity_type: 'booking'
            data: Request data
            action: 'create', 'update_payment', 'cancel', 'get_status'
        """
        start_time = time.time()
        log = None

        try:
            # ================================================================
            # 1. Create Log
            # ================================================================
            log = self._create_log(entity_type, data, request, action)

            _logger.info(f"[{log.request_id}] Received booking {action} request")

            # ================================================================
            # 2. Validate API Key
            # ================================================================
            self._validate_api_key(request)

            # ================================================================
            # 3. Route to Service
            # ================================================================
            from ..services.booking_service import BookingService
            service = BookingService(request.env)

            # Call appropriate method
            if action == 'create':
                result = service.process(data)
            elif action == 'update_payment':
                result = service.update_payment(data['booking_id'], data)
            elif action == 'refund':  # ← أضف
                result = service.refund_booking(
                    data['booking_id'],
                    data.get('reason', '')
                )
            elif action == 'cancel':  # ← أضف
                result = service.cancel_booking(
                    data['booking_id'],
                    data.get('reason', '')
                )
            elif action == 'get_status':
                result = service.get_booking_status(data['booking_id'])
            else:
                raise ValidationError(f"Unknown action: {action}")

            # ================================================================
            # 4. Update Log - Success
            # ================================================================
            processing_time = (time.time() - start_time) * 1000

            log.sudo().write({
                'state': 'success',
                'response_body': json.dumps(result, ensure_ascii=False),
                'processing_time': processing_time,
                'entity_id': data.get('id') or data.get('booking_id'),
                'odoo_record_id': result.get('booking_id'),
                'odoo_model': 'highfive.booking',
                'action': result.get('action', action),
            })

            _logger.info(
                f"[{log.request_id}] {result.get('action', action)} booking "
                f"in {processing_time:.2f}ms"
            )

            # ================================================================
            # 5. Return Success Response
            # ================================================================
            return {
                'success': True,
                'request_id': log.request_id,
                'data': result,
                'processing_time_ms': processing_time,
            }

        except ValidationError as e:
            # Validation error
            processing_time = (time.time() - start_time) * 1000

            # Save request_id before rollback
            request_id = log.request_id if log else None

            # Rollback the transaction
            request.env.cr.rollback()

            if log:
                log.sudo().write({
                    'state': 'failed',
                    'error_message': str(e),
                    'processing_time': processing_time,
                })
                request.env.cr.commit()

            _logger.warning(f"[{request_id}] Validation error: {str(e)}")

            return {
                'success': False,
                'request_id': request_id,
                'error': str(e),
                'error_type': 'validation_error',
                'processing_time_ms': processing_time,
            }

        except Exception as e:
            # Unexpected error
            processing_time = (time.time() - start_time) * 1000
            error_traceback = traceback.format_exc()

            # Save request_id before rollback
            request_id = log.request_id if log else None

            # Rollback the transaction
            request.env.cr.rollback()

            if log:
                log.sudo().write({
                    'state': 'failed',
                    'error_message': str(e),
                    'error_details': error_traceback,
                    'processing_time': processing_time,
                })
                request.env.cr.commit()

            _logger.error(
                f"[{request_id}] Unexpected error: {str(e)}\n"
                f"{error_traceback}"
            )

            return {
                'success': False,
                'request_id': request_id,
                'error': 'Internal server error',
                'error_type': 'server_error',
                'processing_time_ms': processing_time,
            }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _create_log(self, entity_type, data, http_request, action):
        """Create request log"""
        vals = {
            'endpoint': f'/api/odoo/bookings',
            'entity_type': entity_type,
            'request_body': json.dumps(data, ensure_ascii=False),
            'remote_addr': http_request.httprequest.remote_addr,
            'user_agent': http_request.httprequest.user_agent.string if http_request.httprequest.user_agent else None,
            'state': 'pending',
        }

        return http_request.env['highfive.api.request.log'].sudo().create(vals)

    def _validate_api_key(self, http_request):
        """Validate API Key using Odoo's API key system"""
        # Get Authorization header
        api_key = http_request.httprequest.headers.get('Authorization')

        if not api_key:
            raise ValidationError("API Key not found or invalid")

        # Remove 'Bearer ' prefix if exists
        if api_key.startswith('Bearer '):
            api_key = api_key.replace('Bearer ', '').strip()

        # Check credentials using Odoo's API key system
        try:
            user_id = http_request.env['res.users.apikeys'].sudo()._check_credentials(
                scope='rpc',
                key=api_key
            )
        except Exception as e:
            _logger.warning(f"API key validation error: {str(e)}")
            user_id = None

        if not user_id:
            _logger.warning(
                f"Invalid API key attempt from {http_request.httprequest.remote_addr}"
            )
            raise ValidationError("API Key not found or invalid")

        # Update environment with authenticated user
        http_request.update_env(user=user_id)

        _logger.debug(f"API Key validated for user {user_id}")