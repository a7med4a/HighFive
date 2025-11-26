# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "Print Invoice Report with Date",
    "version": "18.0.0.1",
    "category": "Sales",
    "license": "OPL-1",
    "summary": "Allow to print pdf report of Invoice Date.",
    "description": """
    
""",
    "currency": "SAR",
    "author": "Ahmed Amen",
    "depends": [
        "l10n_sa",
        "account",
        "arabic_company_data",
        "sale",
    ],
    "data": [
        "report/inv_date_action.xml",
        "report/journal_entry_report.xml",
        "report/inv_date_doc.xml",
        "report/bill_date_doc_entry.xml",
        "views/views.xml",
    ],
}
