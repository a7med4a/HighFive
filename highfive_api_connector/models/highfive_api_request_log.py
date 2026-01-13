# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
import logging

_logger = logging.getLogger(__name__)


class HighFiveAPIRequestLog(models.Model):
    _name = 'highfive.api.request.log'
    _description = 'HighFive API Request Log'
    _order = 'create_date desc'
    _rec_name = 'request_id'

    # Basic Info
    request_id = fields.Char(
        'Request ID',
        required=True,
        index=True,
        copy=False,
        readonly=True,
        default=lambda self: f"REQ-{uuid.uuid4().hex[:12].upper()}"
    )

    endpoint = fields.Char('Endpoint', required=True, index=True)

    entity_type = fields.Selection([
        ('partner', 'Partner'),
        ('customer', 'Customer'),
        ('branch', 'Branch'),
        ('unit', 'Unit'),
        ('service', 'Service'),
        ('commission', 'Commission'),

        ('booking', 'Booking'),
    ], string='Entity Type', index=True)

    # Request/Response
    request_body = fields.Text('Request Body')
    response_body = fields.Text('Response Body')

    # IP & User Info
    remote_addr = fields.Char('IP Address', index=True)
    user_agent = fields.Char('User Agent')

    # State
    state = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='State', default='pending', required=True, index=True)

    # Results
    entity_id = fields.Integer('Entity ID (HighFive)')
    odoo_record_id = fields.Integer('Odoo Record ID')
    odoo_model = fields.Char('Odoo Model')
    action = fields.Selection([
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),  # ← أضف
        ('payment_updated', 'Payment Updated'),
    ('payment_registered', 'Payment Registered'),  # ← أضف هذا السطر
        ('get_all', 'Get All'),
        ('get_active', 'Get Active'),
        ('get_status', 'Get Status'),
    ], string='Action')

    # Error
    error_message = fields.Text('Error Message')
    error_details = fields.Text('Error Details')

    # Timing
    processing_time = fields.Float('Processing Time (ms)')
    create_date = fields.Datetime('Created At', default=fields.Datetime.now, readonly=True)

    # Company
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)

    # Actions
    def action_view_odoo_record(self):
        """Open the related Odoo record"""
        self.ensure_one()

        if not self.odoo_model or not self.odoo_record_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Record',
            'res_model': self.odoo_model,
            'res_id': self.odoo_record_id,
            'view_mode': 'form',
            'target': 'current',
        }