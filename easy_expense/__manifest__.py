# coding: utf-8
##############################################################################
# This is for me 'A7med Amin
##############################################################################

{
    'name': 'HR Easy Expense',
    'version': '18.0.1.0.0',
    'author': 'Ahmed Amen',
    'website': 'https://www.odoo.com',  # <-- optional, change to your site if needed
    'license': 'AGPL-3',
    'category': 'Human Resources/Expenses',
    'summary': 'Manage Expense Requests',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/pay_wizard.xml',
        'views/easy_expense.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
