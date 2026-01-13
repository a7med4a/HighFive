{
    'name': 'HighFive API Connector',
    'version': '2.0.0',
    'summary': 'Complete API Integration with HighFive Platform',
    'description': """
        Complete webhook-based integration for HighFive platform.
        
        Version 2.0.0 Features:
        ========================
        
        Core Endpoints:
        - Partners API (Create/Update partners)
        - Customers API (Create/Update customers)
        - Branches API (Create/Update branches)
        - Units API (Create/Update units with default commissions)
        
        New in v2.0:
        - Commissions API (Manage scheduled commissions)
        - Bookings API (Full booking management)
        - Payment Updates API
        - Booking Cancellation API
        - Query APIs (Get booking status, commission info)
        
        Features:
        - Complete request/response logging
        - API Key authentication (Odoo's built-in system)
        - Comprehensive data validation
        - Automatic invoice generation (sales + vendor)
        - Commission calculation (default + scheduled)
        - Analytic account linking
        - Payment tracking
        - Error handling with detailed logging
        
        Architecture:
        - Webhook-based (reliable, simple)
        - Service layer pattern
        - Clean separation of concerns
        - Easy to extend and maintain
    """,
    'category': 'Technical',
    'author': 'HighFive Team',
    'website': 'https://www.highfive.sa',
    'depends': [
        'base',
        'web',
        'highfive_core',
        'highfive_booking_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/highfive_api_request_log_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
