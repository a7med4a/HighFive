from odoo import models, fields, api

class HrEmployeeStatementWizard(models.TransientModel):
    _name = 'hr.employee.statement.wizard'
    _description = 'Employee Account Statement Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)

    def action_print_report(self):
        return self.env.ref('hr_employee_statement.action_report_employee_statement').report_action(self)

class HrEmployeeStatementReport(models.AbstractModel):
    _name = 'report.hr_employee_statement.report_employee_statement_template'
    _description = 'Employee Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['hr.employee.statement.wizard'].browse(docids)
        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', wizard.employee_id.id),
            ('date_from', '>=', wizard.date_from),
            ('date_to', '<=', wizard.date_to),
            ('state', '=', 'done')
        ])
        loans = self.env['hr.loan.line'].search([
            ('employee_id', '=', wizard.employee_id.id),
            ('date', '>=', wizard.date_from),
            ('date', '<=', wizard.date_to),
        ])
        expenses = self.env['hr.expense'].search([
            ('employee_id', '=', wizard.employee_id.id),
            ('date', '>=', wizard.date_from),
            ('date', '<=', wizard.date_to),
            ('state', '=', 'approved')
        ])

        movements = []
        balance = 0

        for slip in payslips:
            amount = slip.net_wage or 0
            balance += amount
            movements.append({
                'date': slip.date_to,
                'desc': f'Salary Slip {slip.name}',
                'debit': 0,
                'credit': amount,
                'balance': balance,
            })

        for loan in loans:
            amount = loan.amount or 0
            balance -= amount
            movements.append({
                'date': loan.date,
                'desc': f'Loan {loan.loan_id.name}',
                'debit': amount,
                'credit': 0,
                'balance': balance,
            })

        for exp in expenses:
            amount = exp.total_amount or 0
            balance -= amount
            movements.append({
                'date': exp.date,
                'desc': f'Expense {exp.name}',
                'debit': amount,
                'credit': 0,
                'balance': balance,
            })

        movements = sorted(movements, key=lambda m: m['date'])
        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee.statement.wizard',
            'data': data,
            'docs': wizard,
            'movements': movements,
            'balance': balance,
        }
