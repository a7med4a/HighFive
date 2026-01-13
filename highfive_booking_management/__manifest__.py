{
    'name': 'HighFive Booking Management',
    'version': '1.2.0',
    'summary': 'Complete Booking Management System',
    'description': """
        Complete booking management for HighFive platform.
        
        Features:
        - Full booking registration with all details
        - Additional services support
        - Multiple payment methods
        - Automatic invoice generation on confirmation
        - Link to analytical accounts by branch
        - Smart buttons for bookings in Branch and Partner
        - Payment tracking
        - Schedule management
        
        Manages complete booking lifecycle from creation to invoicing.
    """,
    'category': 'Services',
    'author': 'HighFive Team',
    'website': 'https://www.highfive.sa',
    'depends': [
        'base',
        'account',
        'product',
        'analytic',
        'mail',
        'highfive_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/booking_sequences.xml',
        'views/highfive_booking_views.xml',
        'views/res_partner_views.xml',
        'views/highfive_branch_views.xml',
        'views/account_payment_views.xml',  # ✅ أضف
        'views/booking_line_views.xml',  # أضف
        'views/unit_commission_views.xml',
        'views/account_move_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
