from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

class FreelanceService(models.Model):
    _name = 'freelance.service'
    _description = 'Freelance Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    create_date = fields.Datetime(string='Creation Date', default=fields.Datetime.now, readonly=True, tracking=True)
    request_date = fields.Date(string='Request Date', required=True, tracking=True)
    description = fields.Text(string='Service Description', required=True, tracking=True)
    hours_count = fields.Float(string='Number of Hours', required=True, tracking=True)
    total_value = fields.Monetary(string='Total Value', compute='_compute_total_value', store=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # _sql_constraints = [
    #     ('unique_freelance_service', 'unique(employee_id, request_date, description)', 'A freelance service with the same employee, date, and description already exists!')
    # ]

    @api.depends('employee_id', 'hours_count')
    def _compute_total_value(self):
        for record in self:
            if record.hours_count < 0:
                raise ValidationError('Number of hours cannot be negative.')
            if record.employee_id.is_freelancer:
                record.total_value = record.hours_count * record.employee_id.hourly_rate

    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'confirmed'
            else:
                raise UserError('Only draft services can be confirmed.')

    def action_cancel(self):
        for record in self:
            if record.state in ('draft', 'confirmed'):
                record.state = 'cancelled'
            else:
                raise UserError('Only draft or confirmed services can be cancelled.')

    def action_set_to_draft(self):
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
            else:
                raise UserError('Only cancelled services can be set back to draft.')

