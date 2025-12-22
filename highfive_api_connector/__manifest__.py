{
    'name': 'HighFive API Connector',
    'version': '1.0.0',
    'summary': 'Simple API Integration with HighFive Platform',
    'description': """
        Simple webhook-based integration for HighFive platform.
        
        Features:
        - Webhook endpoints for Partners, Customers, Branches, Units
        - Complete request/response logging
        - API Key authentication
        - Data validation
        - Automatic processing
        
        No complex sync mechanisms - just simple, reliable webhooks.
    """,
    'category': 'Technical',
    'author': 'HighFive Team',
    'website': 'https://www.highfive.sa',
    'depends': [
        'base',
        'web',
        'highfive_core',
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
