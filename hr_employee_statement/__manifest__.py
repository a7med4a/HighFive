{
    'name': 'HR Employee Statement',
    'version': '1.0',
    'author': 'Ahmed Amin',
    'category': 'Human Resources',
    'summary': 'Employee account statement (Salary, Loan, Expenses)',
    'depends': ['hr', 'hr_payroll', 'hr_expense', 'hr_loan'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_statement_view.xml',
        'report/hr_employee_statement_report.xml',
    ],
    'installable': True,
    'application': False,
}
