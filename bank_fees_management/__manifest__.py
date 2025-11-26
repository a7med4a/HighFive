{
    'name': 'Bank Fees Management',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Manage bank fees for payments in Odoo 18 Community Edition.',
    'description': """
        This module allows users to specify bank fees during payment registration
        and automatically creates the corresponding accounting entries.
    """,
    'author': 'Your Name',
    'website': 'http://www.yourwebsite.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

