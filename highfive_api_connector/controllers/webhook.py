# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import json
import time
import traceback
import logging

_logger = logging.getLogger(__name__)


class HighFiveWebhookController(http.Controller):
    """
    Simple Webhook Controller

    Receives webhooks from HighFive and processes them:
    1. Log request
    2. Validate API Key
    3. Validate data
    4. Process
    """

    @http.route('/api/odoo/partners', type='json', auth='none', methods=['POST'], csrf=False)
    def create_partner(self, **kwargs):
        """Receive partner webhook"""
        data = request.get_json_data()
        return self._process_request('partner', data)

    @http.route('/api/odoo/customers', type='json', auth='none', methods=['POST'], csrf=False)
    def create_customer(self, **kwargs):
        """Receive customer webhook"""
        data = request.get_json_data()
        return self._process_request('customer', data)

    @http.route('/api/odoo/branches', type='json', auth='none', methods=['POST'], csrf=False)
    def create_branch(self, **kwargs):
        """Receive branch webhook"""
        data = request.get_json_data()
        return self._process_request('branch', data)

    @http.route('/api/odoo/units', type='json', auth='none', methods=['POST'], csrf=False)
    def create_unit(self, **kwargs):
        """Receive unit webhook"""
        data = request.get_json_data()
        return self._process_request('unit', data)

    @http.route('/api/odoo/services', type='json', auth='none', methods=['POST'], csrf=False)
    def create_service(self, **kwargs):
        """Receive service webhook"""
        data = request.get_json_data()
        return self._process_request('service', data)

    # =========================================================================
    # Main Processing
    # =========================================================================
    def _process_request(self, entity_type, data):
        """
        Main processing flow:
        1. Create log
        2. Validate API Key
        3. Route to service
        4. Update log
        5. Return response
        """
        start_time = time.time()
        log = None

        try:
            # ================================================================
            # 1. Create Log (First thing!)
            # ================================================================
            log = self._create_log(entity_type, data, request)

            _logger.info(f"[{log.request_id}] Received {entity_type} webhook")

            # ================================================================
            # 2. Validate API Key
            # ================================================================
            self._validate_api_key(request)

            # ================================================================
            # 3. Route to Service
            # ================================================================
            service = self._get_service(entity_type)
            result = service.process(data)

            # ================================================================
            # 4. Update Log - Success
            # ================================================================
            processing_time = (time.time() - start_time) * 1000

            log.sudo().write({
                'state': 'success',
                'response_body': json.dumps(result, ensure_ascii=False),
                'processing_time': processing_time,
                'entity_id': data.get('id'),
                'odoo_record_id': (
                    result.get(f"{entity_type}_id") or
                    result.get('branch_id') or
                    result.get('unit_id') or
                    result.get('service_id')
                ),
                'odoo_model': result.get('model'),
                'action': result.get('action'),
            })

            _logger.info(
                f"[{log.request_id}] {result.get('action')} {entity_type} "
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

            if log:
                log.sudo().write({
                    'state': 'failed',
                    'error_message': str(e),
                    'processing_time': processing_time,
                })

            _logger.warning(f"[{log.request_id if log else 'N/A'}] Validation error: {str(e)}")

            return {
                'success': False,
                'request_id': log.request_id if log else None,
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
    # Helper Methods
    # =========================================================================
    def _create_log(self, entity_type, data, http_request):
        """Create request log"""
        vals = {
            'endpoint': f'/api/odoo/{entity_type}s',
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

    def _get_service(self, entity_type):
        """Get service for entity type"""
        from ..services.partner_service import PartnerService
        from ..services.customer_service import CustomerService
        from ..services.branch_service import BranchService
        from ..services.unit_service import UnitService
        from ..services.service_service import ServiceService

        services = {
            'partner': PartnerService,
            'customer': CustomerService,
            'branch': BranchService,
            'unit': UnitService,
            'service': ServiceService,
        }

        service_class = services.get(entity_type)

        if not service_class:
            raise ValidationError(f"Unknown entity type: {entity_type}")

        return service_class(request.env)

    # =========================================================================
    # Test Endpoints
    # =========================================================================
    @http.route('/api/odoo/test/ping', type='json', auth='none', methods=['GET', 'POST'], csrf=False)
    def test_ping(self, **kwargs):
        """Simple ping test"""
        return {
            'success': True,
            'message': 'pong',
            'timestamp': time.time(),
        }

    @http.route('/api/odoo/test/echo', type='json', auth='none', methods=['POST'], csrf=False)
    def test_echo(self, **kwargs):
        """Echo back request data"""
        data = request.get_json_data()
        return {
            'success': True,
            'data': data,
            'headers': dict(request.httprequest.headers),
        }