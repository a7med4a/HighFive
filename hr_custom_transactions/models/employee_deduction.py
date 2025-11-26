from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

class EmployeeDeduction(models.Model):
    _name = 'employee.deduction'
    _description = 'Employee Deduction'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    create_date = fields.Datetime(string='Creation Date', default=fields.Datetime.now, readonly=True, tracking=True)
    request_date = fields.Date(string='Request Date', required=True, tracking=True)
    description = fields.Text(string='Reason for Deduction', required=True, tracking=True)
    deduction_type = fields.Selection([
        ('days', 'Days'),
        ('hours', 'Hours'),
    ], string='Unit Type', required=True, default='hours', tracking=True)
    unit_count = fields.Float(string='Count (Days/Hours)', required=True, tracking=True)
    total_value = fields.Monetary(string='Deduction Value', compute='_compute_total_value', store=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # _sql_constraints = [
    #     ('unique_employee_deduction', 'unique(employee_id, request_date, description)', 'An employee deduction with the same employee, date, and description already exists!')
    # ]

    @api.depends('employee_id', 'deduction_type', 'unit_count')
    def _compute_total_value(self):
        for record in self:
            deduction_amount = 0.0
            if record.unit_count < 0:
                raise ValidationError('Count (Days/Hours) cannot be negative.')
            if record.deduction_type == 'days' and not record.employee_id.contract_id:
                raise ValidationError('Employee must have a contract to calculate day-based deductions.')
            elif record.deduction_type == 'days' and record.employee_id.contract_id:
                contract = record.employee_id.contract_id
                wage = contract.wage  # Monthly salary
                days_in_month = 30 # Or calculate based on contract.resource_calendar_id
                daily_wage = wage / days_in_month
                deduction_amount = record.unit_count * daily_wage
            elif record.deduction_type == 'hours':
                if record.employee_id.is_freelancer:
                    deduction_amount = record.unit_count * record.employee_id.hourly_rate
                elif not record.employee_id.is_freelancer and record.employee_id.contract_id:
                    contract = record.employee_id.contract_id
                    wage = contract.wage # Monthly salary
                    hours_per_day = contract.resource_calendar_id.hours_per_day if contract.resource_calendar_id and contract.resource_calendar_id.hours_per_day else 8
                    days_in_month = 30 # Or calculate based on contract.resource_calendar_id
                    hourly_wage = wage / (days_in_month * hours_per_day)
                    deduction_amount = record.unit_count * hourly_wage
            record.total_value = deduction_amount

    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'confirmed'
            else:
                raise UserError('Only draft deductions can be confirmed.')

    def action_cancel(self):
        for record in self:
            if record.state in ('draft', 'confirmed'):
                record.state = 'cancelled'
            else:
                raise UserError('Only draft or confirmed deductions can be cancelled.')

    def action_set_to_draft(self):
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
            else:
                raise UserError('Only cancelled deductions can be set back to draft.')

