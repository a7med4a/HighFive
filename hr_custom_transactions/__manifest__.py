{
    'name': 'HR Custom Transactions',
    'version': '1.1',
    'category': 'Human Resources',
    'summary': 'Manage Freelance Services, Employee Deductions, and Bonuses with Workflow and Arabic Translation',
    'description': """
HR Custom Transactions Module
============================
This module provides custom functionalities for managing:
- Freelance Services provided by employees.
- Deductions applied to employees.
- Bonuses awarded to employees.

It includes a workflow (Draft, Confirmed, Cancelled) for each transaction type and full Arabic translation.
    """,
    'author': 'Manus AI',
    'depends': ['base', 'hr', 'hr_contract', 'mail', 'hr_payroll_community', 'hr_attendance', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/freelance_service_views.xml',
        'views/employee_deduction_views.xml',
        'views/employee_bonus_views.xml',
        'views/hr_employee_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
