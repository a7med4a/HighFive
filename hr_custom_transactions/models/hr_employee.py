from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    is_freelancer = fields.Boolean(string='Is Freelancer', default=False)
    hourly_rate = fields.Float(string='Hourly Rate')

