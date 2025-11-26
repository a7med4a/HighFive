# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Bhagyadev KP (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
{
    "name": "Odoo18 Dynamic Accounting Reports",
    "version": "18.0.1.2.3",
    "category": "Accounting",
    "summary": "Odoo 18 Accounting Financial Reports,Dynamic Accounting Reports, Dynamic Financial Reports,Dynamic Report Odoo18, Odoo18,Financial Reports, Odoo18 Accounting,Accounting, Odoo Apps",
    "description": "This module creates dynamic Accounting General Ledger, Trial"
                   "Balance, Balance Sheet, Profit and Loss, Cash Book, Partner"
                   "Ledger, Aged Payable, Aged Receivable, Bank book and Tax"
                   "Reports in Odoo 18 community edition, Reporting, Odoo18 Accounting, odoo18 reporting, odoo18, odoo18 accounts reports",
    "author": "Cybrosys Techno Solutions",
    "company": "Cybrosys Techno Solutions",
    "maintainer": "Cybrosys Techno Solutions",
    "website": "https://www.cybrosys.com",
    "depends": ["base_accounting_kit"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
        "views/res_company.xml",
        "views/accounting_report_views.xml",
        "report/trial_balance.xml",
        "report/general_ledger_templates.xml",
        "report/financial_report_template.xml",
        "report/partner_ledger_templates.xml",
        "report/financial_reports_views.xml",
        "report/balance_sheet_report_templates.xml",
        "report/bank_book_templates.xml",
        "report/aged_payable_templates.xml",
        "report/aged_receivable_templates.xml",
        "report/tax_report_templates.xml",
        "report/deferred_report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Partner Ledger
            "dynamic_accounts_report/static/src/partner_ledger/xml/partner_ledger_view.xml",
            "dynamic_accounts_report/static/src/partner_ledger/css/partner_ledger.css",
            "dynamic_accounts_report/static/src/partner_ledger/js/partner_ledger.js",

            # General Ledger
            "dynamic_accounts_report/static/src/general_ledger/xml/general_ledger_view.xml",
            "dynamic_accounts_report/static/src/general_ledger/css/general_ledger.css",
            "dynamic_accounts_report/static/src/general_ledger/js/general_ledger.js",

            # Bank Book
            "dynamic_accounts_report/static/src/bank_book/xml/bank_flow_templates.xml",
            "dynamic_accounts_report/static/src/bank_book/css/bank_book.css",
            "dynamic_accounts_report/static/src/bank_book/js/bank_flow.js",

            # Cash Flow
            "dynamic_accounts_report/static/src/cash_flow/css/cash_flow.css",
            "dynamic_accounts_report/static/src/cash_flow/js/cash_flow.js",
            "dynamic_accounts_report/static/src/cash_flow/xml/cash_flow_templates.xml",

            # Trial Balance
            "dynamic_accounts_report/static/src/trial_balance/xml/trial_balance_view.xml",
            "dynamic_accounts_report/static/src/trial_balance/js/trial_balance.js",
            "dynamic_accounts_report/static/src/trial_balance/css/trial_balance.css",

            # Aged Receivable
            "dynamic_accounts_report/static/src/aged_receivable/js/aged_receivable_report.js",
            "dynamic_accounts_report/static/src/aged_receivable/xml/aged_receivable_report_views.xml",
            "dynamic_accounts_report/static/src/aged_receivable/css/aged_receivable.css",

            # profit and loss
            "dynamic_accounts_report/static/src/profit_and_loss/css/profit_and_loss.css",
            "dynamic_accounts_report/static/src/profit_and_loss/js/profit_and_loss.js",
            "dynamic_accounts_report/static/src/profit_and_loss/xml/profit_and_loss_templates.xml",
            
            # Balance Sheet
            "dynamic_accounts_report/static/src/balance_sheet/css/balance_sheet.css",
            "dynamic_accounts_report/static/src/balance_sheet/js/balance_sheet.js",
            "dynamic_accounts_report/static/src/balance_sheet/xml/balance_sheet_template.xml",

            # Aged Payable
            "dynamic_accounts_report/static/src/aged_payable/css/aged_payable_report.css",
            "dynamic_accounts_report/static/src/aged_payable/js/aged_payable_report.js",
            "dynamic_accounts_report/static/src/aged_payable/xml/aged_payable_report_views.xml",

            # Tax Report
            "dynamic_accounts_report/static/src/tax_report/css/tax_report.css",
            "dynamic_accounts_report/static/src/tax_report/js/tax_report.js",
            "dynamic_accounts_report/static/src/tax_report/xml/tax_report_views.xml",

            # Deferred Revenue
            "dynamic_accounts_report/static/src/deferred_revenue/css/deferred_revenue_report.css",
            "dynamic_accounts_report/static/src/deferred_revenue/js/deferred_revenue_report.js",
            "dynamic_accounts_report/static/src/deferred_revenue/xml/deferred_revenue_report.xml",

            # Deferred Expense
            "dynamic_accounts_report/static/src/deferred_expense/css/deferred_expense_report.css",
            "dynamic_accounts_report/static/src/deferred_expense/js/deferred_expense_report.js",
            "dynamic_accounts_report/static/src/deferred_expense/xml/deferred_expense_template.xml",
        ],
    },
    "images": ["static/description/banner.png"],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
