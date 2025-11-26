# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "Custom Sale",
    "version": "18.0.0.1",
    "category": "Sales",
    "license": "OPL-1",
    "summary": "Allow to print pdf report of Invoice Date.",
    "description": """
    
""",
    "currency": "SAR",
    "author": "Ahmed Amen",
    "depends": [
        'base',
        "l10n_sa",
        "account",
        "arabic_company_data",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/custom_sale_order_report.xml",
        "report/custom_portal_sale_order_report.xml",
        "views/menu_view.xml",
        "views/terms_and_conditions_view.xml",
        "views/sale_order_views.xml",
        "views/invoice_view.xml",
        "views/partner_view.xml",
        "views/journal_items_view.xml",
    ],
}
