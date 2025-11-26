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
import calendar
import io
import json
from datetime import datetime
import xlsxwriter
from odoo import models, fields, api
from odoo.tools.date_utils import (
    get_month,
    get_fiscal_year,
    get_quarter_number,
    subtract,
)


class TaxReport(models.TransientModel):
    """For creating Tax report."""

    _name = "tax.report"
    _description = "Tax Report"

    @api.model
    def action_periodic_vat_entries(self, options=None):
        """Create periodic VAT entries (Closing Entry) - مثل Enterprise"""
        if not options:
            options = {}

        company = self.env.company
        end_date = fields.Date.from_string(options.get("date_to", fields.Date.today()))

        # البحث عن closing entry موجود مسبقاً
        existing_closing = self.env["account.move"].search(
            [
                ("company_id", "=", company.id),
                ("date", "=", end_date),
                ("ref", "like", "Tax Closing Entry%"),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )

        if existing_closing:
            # فتح الـ closing entry الموجود
            return {
                "type": "ir.actions.act_window",
                "name": "Tax Closing Entry",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": existing_closing.id,
                "target": "current",
                "views": [(False, "form")],  # إضافة views
                "context": {},  # إضافة context فارغ
            }

        # إنشاء closing entry جديد
        try:
            closing_move = self._create_tax_closing_entry(options)

            return {
                "type": "ir.actions.act_window",
                "name": "Tax Closing Entry",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": closing_move.id,
                "target": "current",
                "views": [(False, "form")],  # إضافة views
                "context": {},  # إضافة context فارغ
            }
        except Exception as e:
            # في حالة حدوث خطأ، أرجع notification
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": f"Error creating closing entry: {str(e)}",
                    "type": "danger",
                },
            }

    def _create_tax_closing_entry(self, options):
        """Create the actual tax closing entry"""
        company = self.env.company
        end_date = fields.Date.from_string(options.get("date_to", fields.Date.today()))
        start_date = fields.Date.from_string(
            options.get("date_from", fields.Date.today().replace(day=1))
        )

        # Prepare move lines
        move_lines = []

        # Get tax data for the period
        sale_data = []
        purchase_data = []

        tax_ids = self.env["account.tax"].search(
            [
                ("type_tax_use", "in", ["sale", "purchase"]),
                ("company_id", "=", company.id),
            ]
        )

        for tax in tax_ids:
            # البحث عن base amounts
            base_lines = self.env["account.move.line"].search(
                [
                    ("tax_ids", "in", [tax.id]),
                    ("parent_state", "=", "posted"),
                    ("date", ">=", start_date),
                    ("date", "<=", end_date),
                    ("tax_line_id", "=", False),  # Base lines only
                ]
            )

            base_amount = sum(abs(line.balance) for line in base_lines)
            tax_amount = base_amount * (tax.amount / 100)

            if tax.type_tax_use == "sale" and base_amount > 0:
                sale_data.append(
                    {"tax": tax, "base_amount": base_amount, "tax_amount": tax_amount}
                )
            elif tax.type_tax_use == "purchase" and base_amount > 0:
                purchase_data.append(
                    {"tax": tax, "base_amount": base_amount, "tax_amount": tax_amount}
                )

        # Sales tax lines (Credit)
        for item in sale_data:
            if item["tax_amount"] != 0:
                tax_payable_account = self._get_tax_payable_account(item["tax"])
                if tax_payable_account:
                    move_lines.append(
                        (
                            0,
                            0,
                            {
                                "name": f"Tax Closing - {item['tax'].name}",
                                "account_id": tax_payable_account.id,
                                "debit": 0.0,
                                "credit": abs(item["tax_amount"]),
                            },
                        )
                    )

        # Purchase tax lines (Debit)
        for item in purchase_data:
            if item["tax_amount"] != 0:
                tax_receivable_account = self._get_tax_receivable_account(item["tax"])
                if tax_receivable_account:
                    move_lines.append(
                        (
                            0,
                            0,
                            {
                                "name": f"Tax Closing - {item['tax'].name}",
                                "account_id": tax_receivable_account.id,
                                "debit": abs(item["tax_amount"]),
                                "credit": 0.0,
                            },
                        )
                    )

        # Net VAT line (balancing line)
        total_sales_tax = sum(item["tax_amount"] for item in sale_data)
        total_purchase_tax = sum(item["tax_amount"] for item in purchase_data)
        net_vat = total_sales_tax - total_purchase_tax

        if abs(net_vat) > 0.01:  # تجنب الفروقات الصغيرة
            vat_account = self._get_vat_settlement_account()
            if vat_account:
                move_lines.append(
                    (
                        0,
                        0,
                        {
                            "name": (
                                "Net VAT Payable"
                                if net_vat > 0
                                else "Net VAT Receivable"
                            ),
                            "account_id": vat_account.id,
                            "debit": abs(net_vat) if net_vat > 0 else 0.0,
                            "credit": abs(net_vat) if net_vat < 0 else 0.0,
                        },
                    )
                )

        # التأكد من وجود move lines
        if not move_lines:
            raise ValueError("No tax transactions found for the selected period")

        # Create the closing move
        closing_move = self.env["account.move"].create(
            {
                "ref": f"Tax Closing Entry - {end_date}",
                "date": end_date,
                "journal_id": self._get_tax_closing_journal().id,
                "company_id": company.id,
                "move_type": "entry",
                "line_ids": move_lines,
            }
        )

        return closing_move

    def _get_tax_payable_account(self, tax):
        """Get tax payable account for a tax"""
        # البحث عن حساب الضريبة المستحقة
        payable_account = tax.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax" and line.account_id
        ).account_id

        if not payable_account:
            # استخدام حساب افتراضي
            payable_account = self.env["account.account"].search(
                [
                    (
                        "account_type",
                        "in",
                        ["liability_current", "liability_non_current"],
                    ),
                    ("company_id", "=", self.env.company.id),
                    ("name", "ilike", "tax"),
                ],
                limit=1,
            )

            if not payable_account:
                # إنشاء حساب جديد
                payable_account = self.env["account.account"].create(
                    {
                        "name": "Tax Payable",
                        "code": "242100",
                        "account_type": "liability_current",
                        "company_id": self.env.company.id,
                    }
                )

        return payable_account

    def _get_tax_receivable_account(self, tax):
        """Get tax receivable account for a tax"""
        # البحث عن حساب الضريبة المستردة
        receivable_account = tax.refund_repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax" and line.account_id
        ).account_id

        if not receivable_account:
            # استخدام حساب افتراضي
            receivable_account = self.env["account.account"].search(
                [
                    ("account_type", "in", ["asset_current", "asset_non_current"]),
                    ("company_id", "=", self.env.company.id),
                    ("name", "ilike", "tax"),
                ],
                limit=1,
            )

            if not receivable_account:
                # إنشاء حساب جديد
                receivable_account = self.env["account.account"].create(
                    {
                        "name": "Tax Receivable",
                        "code": "142100",
                        "account_type": "asset_current",
                        "company_id": self.env.company.id,
                    }
                )

        return receivable_account

    def _get_vat_settlement_account(self):
        """Get VAT settlement account"""
        settlement_account = self.env["account.account"].search(
            [
                ("name", "ilike", "VAT Settlement"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

        if not settlement_account:
            # إنشاء الحساب إذا لم يكن موجود
            settlement_account = self.env["account.account"].create(
                {
                    "name": "VAT Settlement",
                    "code": "242200",
                    "account_type": "liability_current",
                    "company_id": self.env.company.id,
                }
            )

        return settlement_account

    def _get_tax_closing_journal(self):
        """Get or create tax closing journal"""
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", self.env.company.id),
                ("name", "ilike", "Tax Closing"),
            ],
            limit=1,
        )

        if not journal:
            # البحث عن أي journal عام
            journal = self.env["account.journal"].search(
                [("type", "=", "general"), ("company_id", "=", self.env.company.id)],
                limit=1,
            )

            if not journal:
                # إنشاء journal جديد
                journal = self.env["account.journal"].create(
                    {
                        "name": "Tax Closing",
                        "code": "TAXCL",
                        "type": "general",
                        "company_id": self.env.company.id,
                    }
                )

        return journal

    @api.model
    def view_report(self):
        """
        View a tax report for the current month. This function retrieves
        tax-related information for the current month. It calculates the net
        amount and tax amount for both sales and purchases based on the tax
        information associated with account move lines.
            :return: Dictionary containing sale and purchase data for the
                     current month.
        """
        sale = []
        purchase = []
        tax_ids = self.env["account.move.line"].search([]).mapped("tax_ids")
        today = fields.Date.today()
        for tax in tax_ids:
            tax_id = (
                self.env["account.move.line"]
                .search(
                    [
                        ("tax_ids", "=", tax.id),
                        ("parent_state", "=", "posted"),
                        ("date", ">=", get_month(today)[0]),
                        ("date", "<=", get_month(today)[1]),
                    ]
                )
                .read(["debit", "credit"])
            )
            tax_debit_sums = sum(record["debit"] for record in tax_id)
            tax_credit_sums = sum(record["credit"] for record in tax_id)
            if tax.type_tax_use == "sale":
                sale.append(
                    {
                        "name": tax.name,
                        "amount": tax.amount,
                        "net": round(tax_debit_sums + tax_credit_sums, 2),
                        "tax": round(
                            (tax_debit_sums + tax_credit_sums) * (tax.amount / 100), 2
                        ),
                    }
                )
            elif tax.type_tax_use == "purchase":
                purchase.append(
                    {
                        "name": tax.name,
                        "amount": tax.amount,
                        "net": round(tax_debit_sums + tax_credit_sums, 2),
                        "tax": round(
                            (tax_debit_sums + tax_credit_sums) * (tax.amount / 100), 2
                        ),
                    }
                )
        return {"sale": sale, "purchase": purchase}

    @api.model
    def get_filter_values(
        self,
        start_date,
        end_date,
        comparison_number,
        comparison_type,
        options,
        report_type,
    ):
        """
        Get filtered tax values based on various criteria.

        :param start_date: Start date of the filter period.
        :param end_date: End date of the filter period.
        :param comparison_number: Number of comparison periods.
        :param comparison_type: Type of comparison (year, month, quarter).
        :param options: Filter options.
        :param report_type: Type of report (account, tax).
        :return: Dictionary containing dynamic_date_num, sale, and purchase
                 data.
        """
        sale = []
        purchase = []
        dynamic_date_num = {}
        if options == {}:
            options = None
        if options is None:
            option_domain = ["posted"]
        elif "draft" in options:
            option_domain = ["posted", "draft"]
        tax_ids = self.env["account.move.line"].search([]).mapped("tax_ids")
        start_date_first = (
            get_fiscal_year(datetime.strptime(start_date, "%Y-%m-%d").date())[0]
            if comparison_type == "year"
            else datetime.strptime(start_date, "%Y-%m-%d").date()
        )
        end_date_first = (
            get_fiscal_year(datetime.strptime(end_date, "%Y-%m-%d").date())[1]
            if comparison_type == "year"
            else datetime.strptime(end_date, "%Y-%m-%d").date()
        )
        if report_type is not None and "account" in report_type:
            start_date = start_date_first
            end_date = end_date_first
            account_ids = self.env["account.move.line"].search([]).mapped("account_id")
            for account in account_ids:
                tax_ids = (
                    self.env["account.move.line"]
                    .search([("account_id", "=", account.id)])
                    .mapped("tax_ids")
                )
                if tax_ids:
                    for tax in tax_ids:
                        dynamic_total_tax_sum = {}
                        dynamic_total_net_sum = {}
                        if comparison_number:
                            if comparison_type == "year":
                                start_date = start_date_first
                                end_date = end_date_first
                                for i in range(1, eval(comparison_number) + 1):
                                    com_start_date = subtract(start_date, years=i)
                                    com_end_date = subtract(end_date, years=i)
                                    tax_id = (
                                        self.env["account.move.line"]
                                        .search(
                                            [
                                                ("tax_ids", "=", tax.id),
                                                ("date", ">=", com_start_date),
                                                ("date", "<=", com_end_date),
                                                ("account_id", "=", account.id),
                                                ("parent_state", "in", option_domain),
                                            ]
                                        )
                                        .read(["debit", "credit"])
                                    )
                                    tax_debit_sums = sum(
                                        record["debit"] for record in tax_id
                                    )
                                    tax_credit_sums = sum(
                                        record["credit"] for record in tax_id
                                    )
                                    dynamic_total_net_sum[
                                        f"dynamic_total_net_sum{i}"
                                    ] = (tax_debit_sums + tax_credit_sums)
                                    dynamic_total_tax_sum[
                                        f"dynamic_total_tax_sum{i}"
                                    ] = dynamic_total_net_sum[
                                        f"dynamic_total_net_sum{i}"
                                    ] * (
                                        tax.amount / 100
                                    )
                            elif comparison_type == "month":
                                dynamic_date_num[f"dynamic_date_num{0}"] = (
                                    self.get_month_name(start_date)
                                    + " "
                                    + str(start_date.year)
                                )
                                for i in range(1, eval(comparison_number) + 1):
                                    com_start_date = subtract(start_date, months=i)
                                    com_end_date = subtract(end_date, months=i)
                                    tax_id = (
                                        self.env["account.move.line"]
                                        .search(
                                            [
                                                ("tax_ids", "=", tax.id),
                                                ("date", ">=", com_start_date),
                                                ("account_id", "=", account.id),
                                                ("date", "<=", com_end_date),
                                                ("parent_state", "in", option_domain),
                                            ]
                                        )
                                        .read(["debit", "credit"])
                                    )
                                    tax_debit_sums = sum(
                                        record["debit"] for record in tax_id
                                    )
                                    tax_credit_sums = sum(
                                        record["credit"] for record in tax_id
                                    )
                                    dynamic_total_net_sum[
                                        f"dynamic_total_net_sum{i}"
                                    ] = (tax_debit_sums + tax_credit_sums)
                                    dynamic_total_tax_sum[
                                        f"dynamic_total_tax_sum{i}"
                                    ] = dynamic_total_net_sum[
                                        f"dynamic_total_net_sum{i}"
                                    ] * (
                                        tax.amount / 100
                                    )
                                    dynamic_date_num[f"dynamic_date_num{i}"] = (
                                        self.get_month_name(com_start_date)
                                        + " "
                                        + str(com_start_date.year)
                                    )
                            elif comparison_type == "quarter":
                                dynamic_date_num[f"dynamic_date_num{0}"] = (
                                    "Q"
                                    + " "
                                    + str(get_quarter_number(start_date))
                                    + " "
                                    + str(start_date.year)
                                )
                                for i in range(1, eval(comparison_number) + 1):
                                    com_start_date = subtract(start_date, months=i * 3)
                                    com_end_date = subtract(end_date, months=i * 3)
                                    tax_id = (
                                        self.env["account.move.line"]
                                        .search(
                                            [
                                                ("tax_ids", "=", tax.id),
                                                ("date", ">=", com_start_date),
                                                ("account_id", "=", account.id),
                                                ("date", "<=", com_end_date),
                                                ("parent_state", "in", option_domain),
                                            ]
                                        )
                                        .read(["debit", "credit"])
                                    )
                                    tax_debit_sums = sum(
                                        record["debit"] for record in tax_id
                                    )
                                    tax_credit_sums = sum(
                                        record["credit"] for record in tax_id
                                    )
                                    dynamic_total_net_sum[
                                        f"dynamic_total_net_sum{i}"
                                    ] = (tax_debit_sums + tax_credit_sums)
                                    dynamic_total_tax_sum[
                                        f"dynamic_total_tax_sum{i}"
                                    ] = dynamic_total_net_sum[
                                        f"dynamic_total_net_sum{i}"
                                    ] * (
                                        tax.amount / 100
                                    )
                                    dynamic_date_num[f"dynamic_date_num{i}"] = (
                                        "Q"
                                        + " "
                                        + str(get_quarter_number(com_start_date))
                                        + " "
                                        + str(com_start_date.year)
                                    )
                        tax_id = (
                            self.env["account.move.line"]
                            .search(
                                [
                                    ("tax_ids", "=", tax.id),
                                    ("date", ">=", start_date_first),
                                    ("date", "<=", end_date_first),
                                    ("parent_state", "in", option_domain),
                                    ("account_id", "=", account.id),
                                ]
                            )
                            .read(["debit", "credit"])
                        )
                        tax_debit_sums = sum(record["debit"] for record in tax_id)
                        tax_credit_sums = sum(record["credit"] for record in tax_id)
                        if tax_id and tax.type_tax_use == "sale":
                            if comparison_number:
                                sale.append(
                                    {
                                        "name": tax.name,
                                        "amount": tax.amount,
                                        "net": round(
                                            tax_debit_sums + tax_credit_sums, 2
                                        ),
                                        "tax": round(
                                            (tax_debit_sums + tax_credit_sums)
                                            * (tax.amount / 100),
                                            2,
                                        ),
                                        "dynamic net": dynamic_total_net_sum,
                                        "dynamic tax": dynamic_total_tax_sum,
                                        "account": account.display_name,
                                    }
                                )
                            else:
                                sale.append(
                                    {
                                        "name": tax.name,
                                        "amount": tax.amount,
                                        "net": round(
                                            tax_debit_sums + tax_credit_sums, 2
                                        ),
                                        "tax": round(
                                            (tax_debit_sums + tax_credit_sums)
                                            * (tax.amount / 100),
                                            2,
                                        ),
                                        "account": account.display_name,
                                    }
                                )
                        elif tax_id and tax.type_tax_use == "purchase":
                            if comparison_number:
                                purchase.append(
                                    {
                                        "name": tax.name,
                                        "amount": tax.amount,
                                        "net": round(
                                            tax_debit_sums + tax_credit_sums, 2
                                        ),
                                        "tax": round(
                                            (tax_debit_sums + tax_credit_sums)
                                            * (tax.amount / 100),
                                            2,
                                        ),
                                        "dynamic net": dynamic_total_net_sum,
                                        "dynamic tax": dynamic_total_tax_sum,
                                        "account": account.display_name,
                                    }
                                )
                            else:
                                purchase.append(
                                    {
                                        "name": tax.name,
                                        "amount": tax.amount,
                                        "net": round(
                                            tax_debit_sums + tax_credit_sums, 2
                                        ),
                                        "tax": round(
                                            (tax_debit_sums + tax_credit_sums)
                                            * (tax.amount / 100),
                                            2,
                                        ),
                                        "account": account.display_name,
                                    }
                                )
        elif report_type is not None and "tax" in report_type:
            start_date = start_date_first
            end_date = end_date_first
            for tax in tax_ids:
                account_ids = (
                    self.env["account.move.line"]
                    .search([("tax_ids", "=", tax.id)])
                    .mapped("account_id")
                )
                for account in account_ids:
                    dynamic_total_tax_sum = {}
                    dynamic_total_net_sum = {}
                    if comparison_number:
                        if comparison_type == "year":
                            start_date = start_date_first
                            end_date = end_date_first
                            for i in range(1, eval(comparison_number) + 1):
                                com_start_date = subtract(start_date, years=i)
                                com_end_date = subtract(end_date, years=i)
                                tax_id = (
                                    self.env["account.move.line"]
                                    .search(
                                        [
                                            ("tax_ids", "=", tax.id),
                                            ("date", ">=", com_start_date),
                                            ("date", "<=", com_end_date),
                                            ("account_id", "=", account.id),
                                            ("parent_state", "in", option_domain),
                                        ]
                                    )
                                    .read(["debit", "credit"])
                                )
                                tax_debit_sums = sum(
                                    record["debit"] for record in tax_id
                                )
                                tax_credit_sums = sum(
                                    record["credit"] for record in tax_id
                                )
                                dynamic_total_net_sum[f"dynamic_total_net_sum{i}"] = (
                                    tax_debit_sums + tax_credit_sums
                                )
                                dynamic_total_tax_sum[f"dynamic_total_tax_sum{i}"] = (
                                    dynamic_total_net_sum[f"dynamic_total_net_sum{i}"]
                                    * (tax.amount / 100)
                                )
                        elif comparison_type == "month":
                            dynamic_date_num[f"dynamic_date_num{0}"] = (
                                self.get_month_name(start_date)
                                + " "
                                + str(start_date.year)
                            )
                            for i in range(1, eval(comparison_number) + 1):
                                com_start_date = subtract(start_date, months=i)
                                com_end_date = subtract(end_date, months=i)
                                tax_id = (
                                    self.env["account.move.line"]
                                    .search(
                                        [
                                            ("tax_ids", "=", tax.id),
                                            ("date", ">=", com_start_date),
                                            ("date", "<=", com_end_date),
                                            ("account_id", "=", account.id),
                                            ("parent_state", "in", option_domain),
                                        ]
                                    )
                                    .read(["debit", "credit"])
                                )
                                tax_debit_sums = sum(
                                    record["debit"] for record in tax_id
                                )
                                tax_credit_sums = sum(
                                    record["credit"] for record in tax_id
                                )
                                dynamic_total_net_sum[f"dynamic_total_net_sum{i}"] = (
                                    tax_debit_sums + tax_credit_sums
                                )
                                dynamic_total_tax_sum[f"dynamic_total_tax_sum{i}"] = (
                                    dynamic_total_net_sum[f"dynamic_total_net_sum{i}"]
                                    * (tax.amount / 100)
                                )
                                dynamic_date_num[f"dynamic_date_num{i}"] = (
                                    self.get_month_name(com_start_date)
                                    + " "
                                    + str(com_start_date.year)
                                )
                        elif comparison_type == "quarter":
                            dynamic_date_num[f"dynamic_date_num{0}"] = (
                                "Q"
                                + " "
                                + str(get_quarter_number(start_date))
                                + " "
                                + str(start_date.year)
                            )
                            for i in range(1, eval(comparison_number) + 1):
                                com_start_date = subtract(start_date, months=i * 3)
                                com_end_date = subtract(end_date, months=i * 3)
                                tax_id = (
                                    self.env["account.move.line"]
                                    .search(
                                        [
                                            ("tax_ids", "=", tax.id),
                                            ("date", ">=", com_start_date),
                                            ("date", "<=", com_end_date),
                                            ("account_id", "=", account.id),
                                            ("parent_state", "in", option_domain),
                                        ]
                                    )
                                    .read(["debit", "credit"])
                                )
                                tax_debit_sums = sum(
                                    record["debit"] for record in tax_id
                                )
                                tax_credit_sums = sum(
                                    record["credit"] for record in tax_id
                                )
                                dynamic_total_net_sum[f"dynamic_total_net_sum{i}"] = (
                                    tax_debit_sums + tax_credit_sums
                                )
                                dynamic_total_tax_sum[f"dynamic_total_tax_sum{i}"] = (
                                    dynamic_total_net_sum[f"dynamic_total_net_sum{i}"]
                                    * (tax.amount / 100)
                                )
                                dynamic_date_num[f"dynamic_date_num{i}"] = (
                                    "Q"
                                    + " "
                                    + str(get_quarter_number(com_start_date))
                                    + " "
                                    + str(com_start_date.year)
                                )
                    tax_id = (
                        self.env["account.move.line"]
                        .search(
                            [
                                ("tax_ids", "=", tax.id),
                                ("parent_state", "in", option_domain),
                                ("date", ">=", start_date_first),
                                ("date", "<=", end_date_first),
                                ("account_id", "=", account.id),
                            ]
                        )
                        .read(["debit", "credit"])
                    )
                    tax_debit_sums = sum(record["debit"] for record in tax_id)
                    tax_credit_sums = sum(record["credit"] for record in tax_id)
                    if tax_id and tax.type_tax_use == "sale":
                        if comparison_number:
                            sale.append(
                                {
                                    "name": tax.name,
                                    "amount": tax.amount,
                                    "net": round(tax_debit_sums + tax_credit_sums, 2),
                                    "tax": round(
                                        (tax_debit_sums + tax_credit_sums)
                                        * (tax.amount / 100),
                                        2,
                                    ),
                                    "dynamic net": dynamic_total_net_sum,
                                    "dynamic tax": dynamic_total_tax_sum,
                                    "account": account.display_name,
                                }
                            )
                        else:
                            sale.append(
                                {
                                    "name": tax.name,
                                    "amount": tax.amount,
                                    "net": round(tax_debit_sums + tax_credit_sums, 2),
                                    "tax": round(
                                        (tax_debit_sums + tax_credit_sums)
                                        * (tax.amount / 100),
                                        2,
                                    ),
                                    "account": account.display_name,
                                }
                            )
                    elif tax_id and tax.type_tax_use == "purchase":
                        if comparison_number:
                            purchase.append(
                                {
                                    "name": tax.name,
                                    "amount": tax.amount,
                                    "net": round(tax_debit_sums + tax_credit_sums, 2),
                                    "tax": round(
                                        (tax_debit_sums + tax_credit_sums)
                                        * (tax.amount / 100),
                                        2,
                                    ),
                                    "dynamic net": dynamic_total_net_sum,
                                    "dynamic tax": dynamic_total_tax_sum,
                                    "account": account.display_name,
                                }
                            )
                        else:
                            purchase.append(
                                {
                                    "name": tax.name,
                                    "amount": tax.amount,
                                    "net": round(tax_debit_sums + tax_credit_sums, 2),
                                    "tax": round(
                                        (tax_debit_sums + tax_credit_sums)
                                        * (tax.amount / 100),
                                        2,
                                    ),
                                    "account": account.display_name,
                                }
                            )
        else:
            start_date = start_date_first
            end_date = end_date_first
            for tax in tax_ids:
                dynamic_total_tax_sum = {}
                dynamic_total_net_sum = {}
                if comparison_number:
                    if comparison_type == "year":
                        start_date = start_date_first
                        end_date = end_date_first
                        for i in range(1, eval(comparison_number) + 1):
                            com_start_date = subtract(start_date, years=i)
                            com_end_date = subtract(end_date, years=i)
                            tax_id = (
                                self.env["account.move.line"]
                                .search(
                                    [
                                        ("tax_ids", "=", tax.id),
                                        ("date", ">=", com_start_date),
                                        ("date", "<=", com_end_date),
                                        ("parent_state", "in", option_domain),
                                    ]
                                )
                                .read(["debit", "credit"])
                            )
                            tax_debit_sums = sum(record["debit"] for record in tax_id)
                            tax_credit_sums = sum(record["credit"] for record in tax_id)
                            dynamic_total_net_sum[f"dynamic_total_net_sum{i}"] = (
                                tax_debit_sums + tax_credit_sums
                            )
                            dynamic_total_tax_sum[f"dynamic_total_tax_sum{i}"] = (
                                dynamic_total_net_sum[f"dynamic_total_net_sum{i}"]
                                * (tax.amount / 100)
                            )
                    elif comparison_type == "month":
                        dynamic_date_num[f"dynamic_date_num{0}"] = (
                            self.get_month_name(start_date) + " " + str(start_date.year)
                        )
                        for i in range(1, eval(comparison_number) + 1):
                            com_start_date = subtract(start_date, months=i)
                            com_end_date = subtract(end_date, months=i)
                            tax_id = (
                                self.env["account.move.line"]
                                .search(
                                    [
                                        ("tax_ids", "=", tax.id),
                                        ("date", ">=", com_start_date),
                                        ("date", "<=", com_end_date),
                                        ("parent_state", "in", option_domain),
                                    ]
                                )
                                .read(["debit", "credit"])
                            )
                            tax_debit_sums = sum(record["debit"] for record in tax_id)
                            tax_credit_sums = sum(record["credit"] for record in tax_id)
                            dynamic_total_net_sum[f"dynamic_total_net_sum{i}"] = (
                                tax_debit_sums + tax_credit_sums
                            )
                            dynamic_total_tax_sum[f"dynamic_total_tax_sum{i}"] = (
                                dynamic_total_net_sum[f"dynamic_total_net_sum{i}"]
                                * (tax.amount / 100)
                            )
                            dynamic_date_num[f"dynamic_date_num{i}"] = (
                                self.get_month_name(com_start_date)
                                + " "
                                + str(com_start_date.year)
                            )
                    elif comparison_type == "quarter":
                        dynamic_date_num[f"dynamic_date_num{0}"] = (
                            "Q"
                            + " "
                            + str(get_quarter_number(start_date))
                            + " "
                            + str(start_date.year)
                        )
                        for i in range(1, eval(comparison_number) + 1):
                            com_start_date = subtract(start_date, months=i * 3)
                            com_end_date = subtract(end_date, months=i * 3)
                            tax_id = (
                                self.env["account.move.line"]
                                .search(
                                    [
                                        ("tax_ids", "=", tax.id),
                                        ("date", ">=", com_start_date),
                                        ("date", "<=", com_end_date),
                                        ("parent_state", "in", option_domain),
                                    ]
                                )
                                .read(["debit", "credit"])
                            )
                            tax_debit_sums = sum(record["debit"] for record in tax_id)
                            tax_credit_sums = sum(record["credit"] for record in tax_id)
                            dynamic_total_net_sum[f"dynamic_total_net_sum{i}"] = (
                                tax_debit_sums + tax_credit_sums
                            )
                            dynamic_total_tax_sum[f"dynamic_total_tax_sum{i}"] = (
                                dynamic_total_net_sum[f"dynamic_total_net_sum{i}"]
                                * (tax.amount / 100)
                            )
                            dynamic_date_num[f"dynamic_date_num{i}"] = (
                                "Q"
                                + " "
                                + str(get_quarter_number(com_start_date))
                                + " "
                                + str(com_start_date.year)
                            )
                tax_id = (
                    self.env["account.move.line"]
                    .search(
                        [
                            ("tax_ids", "=", tax.id),
                            ("parent_state", "in", option_domain),
                            ("date", ">=", start_date_first),
                            ("date", "<=", end_date_first),
                        ]
                    )
                    .read(["debit", "credit"])
                )
                tax_debit_sums = sum(record["debit"] for record in tax_id)
                tax_credit_sums = sum(record["credit"] for record in tax_id)
                if tax.type_tax_use == "sale":
                    if comparison_number:
                        sale.append(
                            {
                                "name": tax.name,
                                "amount": tax.amount,
                                "net": round(tax_debit_sums + tax_credit_sums, 2),
                                "tax": round(
                                    (tax_debit_sums + tax_credit_sums)
                                    * (tax.amount / 100),
                                    2,
                                ),
                                "dynamic net": dynamic_total_net_sum,
                                "dynamic tax": dynamic_total_tax_sum,
                            }
                        )
                    else:
                        sale.append(
                            {
                                "name": tax.name,
                                "amount": tax.amount,
                                "net": round(tax_debit_sums + tax_credit_sums, 2),
                                "tax": round(
                                    (tax_debit_sums + tax_credit_sums)
                                    * (tax.amount / 100),
                                    2,
                                ),
                            }
                        )
                elif tax.type_tax_use == "purchase":
                    if comparison_number:
                        purchase.append(
                            {
                                "name": tax.name,
                                "amount": tax.amount,
                                "net": round(tax_debit_sums + tax_credit_sums, 2),
                                "tax": round(
                                    (tax_debit_sums + tax_credit_sums)
                                    * (tax.amount / 100),
                                    2,
                                ),
                                "dynamic net": dynamic_total_net_sum,
                                "dynamic tax": dynamic_total_tax_sum,
                            }
                        )
                    else:
                        purchase.append(
                            {
                                "name": tax.name,
                                "amount": tax.amount,
                                "net": round(tax_debit_sums + tax_credit_sums, 2),
                                "tax": round(
                                    (tax_debit_sums + tax_credit_sums)
                                    * (tax.amount / 100),
                                    2,
                                ),
                            }
                        )
        return {
            "dynamic_date_num": dynamic_date_num,
            "sale": sale,
            "purchase": purchase,
        }

    @api.model
    def get_month_name(self, date):
        """
        Retrieve the abbreviated name of the month for a given date.

        :param date: The date for which to retrieve the month's abbreviated
                     name.
        :type date: datetime.date
        :return: Abbreviated name of the month (e.g., 'Jan', 'Feb', ..., 'Dec').
        :rtype: str
        """
        month_names = calendar.month_abbr
        return month_names[date.month]

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an XLSX report based on provided data and response stream.

        Generates an Excel workbook with specified report format, including
        subheadings,column headers, and row data for the given financial report
        data.

        :param str data: JSON-encoded data for the report.
        :param response: Response object to stream the generated report.
        :param str report_name: Name of the financial report.
        """
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet()
        sub_heading = workbook.add_format(
            {
                "align": "center",
                "bold": True,
                "font_size": "10px",
                "border": 1,
                "border_color": "black",
            }
        )
        side_heading_sub = workbook.add_format(
            {
                "align": "left",
                "bold": True,
                "font_size": "10px",
                "border": 1,
                "border_color": "black",
            }
        )
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format({"font_size": "10px", "border": 1})
        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        col = 0
        sheet.write("A3:b4", report_name, sub_heading)
        sheet.write(5, col, "", sub_heading)
        i = 1
        for date_view in data["date_viewed"]:
            sheet.merge_range(5, col + i, 5, col + i + 1, date_view, sub_heading)
            i += 2
        j = 1
        prev_account = None
        prev_tax = None
        sheet.write(6, col, "", sub_heading)
        for date in data["date_viewed"]:
            sheet.write(6, col + j, "NET", sub_heading)
            sheet.write(6, col + j + 1, "TAX", sub_heading)
            j += 1
        sheet.write(7, col, "Sales", sub_heading)
        sheet.write(7, col + 1, " ", sub_heading)
        sheet.write(7, col + 2, data["sale_total"], sub_heading)
        row = 8
        for sale in data["data"]["sale"]:
            if data["report_type"]:
                if list(data["report_type"].keys())[0] == "account":
                    if prev_account != sale["account"]:
                        prev_account = sale["account"]
                        sheet.write(row, col, sale["account"], txt_name)
                        sheet.write(row, col + 1, "", txt_name)
                        sheet.write(row, col + 2, "", txt_name)
                elif list(data["report_type"].keys())[0] == "tax":
                    if prev_tax != sale["name"]:
                        prev_tax = sale["name"]
                        sheet.write(
                            row,
                            col,
                            sale["name"] + "(" + str(sale["amount"]) + "%)",
                            txt_name,
                        )
                        sheet.write(row, col + 1, "", txt_name)
                        sheet.write(row, col + 2, "", txt_name)
                row += 1
                if data["apply_comparison"]:
                    if sale["dynamic net"]:
                        periods = data["comparison_number_range"]
                        for num in periods:
                            if sale["dynamic net"]["dynamic_total_net_sum" + str(num)]:
                                sheet.write(
                                    row,
                                    col + j,
                                    sale["dynamic net"][
                                        "dynamic_total_net_sum" + str(num)
                                    ],
                                    txt_name,
                                )
                            if sale["dynamic tax"]["dynamic_total_tax_sum" + str(num)]:
                                sheet.write(
                                    row,
                                    col,
                                    sale["dynamic tax"][
                                        "dynamic_total_tax_sum" + str(num)
                                    ],
                                    txt_name,
                                )
                            j += 1
                j = 0
                sheet.write(row, col + j, sale["name"], txt_name)
                sheet.write(row, col + j + 1, sale["net"], txt_name)
                sheet.write(row, col + j + 2, sale["tax"], txt_name)
            else:
                j = 0
                sheet.write(row, col + j, sale["name"], txt_name)
                sheet.write(row, col + j + 1, sale["net"], txt_name)
                sheet.write(row, col + j + 2, sale["tax"], txt_name)
                row += 1
        row += 1
        sheet.write(row, col, "Purchase", sub_heading)
        sheet.write(row, col + 1, " ", sub_heading)
        sheet.write(row, col + 2, data["purchase_total"], sub_heading)
        row += 1
        for purchase in data["data"]["purchase"]:
            if data["report_type"]:
                if list(data["report_type"].keys())[0] == "account":
                    if prev_account != purchase["account"]:
                        prev_account = purchase["account"]
                        sheet.write(row, col, purchase["account"], txt_name)
                        sheet.write(row, col + 1, "", txt_name)
                        sheet.write(row, col + 2, "", txt_name)
                elif list(data["report_type"].keys())[0] == "tax":
                    if prev_tax != purchase["name"]:
                        prev_tax = purchase["name"]
                        sheet.write(
                            row,
                            col,
                            purchase["name"] + "(" + str(purchase["amount"]) + "%)",
                            txt_name,
                        )
                        sheet.write(row, col + 1, "", txt_name)
                        sheet.write(row, col + 2, "", txt_name)
                row += 1
                if data["apply_comparison"]:
                    if purchase["dynamic net"]:
                        periods = data["comparison_number_range"]
                        for num in periods:
                            if purchase["dynamic net"][
                                "dynamic_total_net_sum" + str(num)
                            ]:
                                sheet.write(
                                    row,
                                    col + j,
                                    purchase["dynamic net"][
                                        "dynamic_total_net_sum" + str(num)
                                    ],
                                    txt_name,
                                )
                            if purchase["dynamic tax"][
                                "dynamic_total_tax_sum" + str(num)
                            ]:
                                sheet.write(
                                    row,
                                    col,
                                    purchase["dynamic tax"][
                                        "dynamic_total_tax_sum" + str(num)
                                    ],
                                    txt_name,
                                )
                            j += 1
                j = 0
                sheet.write(row, col + j, purchase["name"], txt_name)
                sheet.write(row, col + j + 1, purchase["net"], txt_name)
                sheet.write(row, col + j + 2, purchase["tax"], txt_name)
            else:
                j = 0
                sheet.write(row, col + j, purchase["name"], txt_name)
                sheet.write(row, col + j + 1, purchase["net"], txt_name)
                sheet.write(row, col + j + 2, purchase["tax"], txt_name)
                row += 1
        row += 1
        sheet.write(row, col, "Purchase", sub_heading)
        sheet.write(row, col + 1, " ", sub_heading)
        sheet.write(row, col + 2, data["purchase_total"], sub_heading)
        row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
