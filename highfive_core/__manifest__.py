{
    'name': 'HighFive Core Integration',
    'version': '1.1.0',
    'summary': 'Core Integration & Master Data Management for HighFive',
    'description': """
        This module is the foundation of the HighFive integration system.
        It manages:
        - Suppliers (Partners)
        - Customers (formerly Players)
        - Branches (Partner Branches)
        - Units (Services)
        - Analytic Accounts Hierarchy
        
        Version 1.1.0 Changes:
        - Added tax_status field for suppliers
        - Added commission rate fields
        - Enhanced logging
        - Improved product constraints
        - Renamed Players to Customers throughout the module
    """,
    'category': 'Technical',
    'author': 'Manus AI',
    'website': 'https://www.highfive.sa',
    'depends': ['base', 'product', 'analytic', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/highfive_analytic_plan.xml',
        'data/highfive_products.xml',
        'views/res_partner_views.xml',
        'views/partner_branch_views.xml',
        'views/product_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'auto_install': False,
}
