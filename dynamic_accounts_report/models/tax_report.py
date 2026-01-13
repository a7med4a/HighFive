# -*- coding: utf-8 -*-
import calendar
import io
import json
from datetime import datetime
import xlsxwriter
from odoo import models, fields, api, Command, _
from odoo.tools.date_utils import (
    get_month,
    get_fiscal_year,
    get_quarter_number,
    subtract,
)
from odoo.tools import SQL
from collections import defaultdict


class TaxReport(models.TransientModel):
    """For creating Tax report."""

    _name = "tax.report"
    _description = "Tax Report"

    @api.model
    def action_periodic_vat_entries(self, options=None):
        """Create periodic VAT entries (Closing Entry) - مثل Enterprise"""
        if not options:
            options = {}

        # تحويل options إلى format مشابه للـ Enterprise
        report_options = self._prepare_report_options(options)

        # استخدام نفس منطق Enterprise
        moves = self._get_periodic_vat_entries(report_options)

        # إرجاع نفس action format كما في Enterprise
        if len(moves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Tax Closing Entry"),
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": moves.id,
                "views": [(False, "form")],
                "target": "current",
                "context": {},
            }
        else:
            return {
                "type": "ir.actions.act_window",
                "name": _("Tax Closing Entries"),
                "res_model": "account.move",
                "view_mode": "tree,form",
                "domain": [("id", "in", moves.ids)],
                "views": [(False, "list"), (False, "form")],
                "target": "current",
                "context": {},
            }

    def _prepare_report_options(self, options):
        """تحضير options بنفس format الـ Enterprise"""
        return {
            "date": {
                "date_from": options.get(
                    "date_from", fields.Date.today().replace(day=1)
                ),
                "date_to": options.get("date_to", fields.Date.today()),
                "filter": "custom",
                "period_type": "custom",
            },
            "fiscal_position": "domestic",  # يمكن تعديلها حسب الحاجة
            "companies": options.get("company_ids", [self.env.company.id]),
            "report_id": None,  # لن نحتاجه في حالتنا
        }

    def _get_periodic_vat_entries(self, options):
        """نفس منطق Enterprise لإنشاء/تحديث closing entries"""
        moves = self.env["account.move"]
        companies = self.env["res.company"].browse(options["companies"])

        # البحث عن existing closing entries
        existing_moves = self._get_tax_closing_entries_for_closed_period(
            options, companies
        )
        moves += existing_moves

        # إنشاء closing entries جديدة للشركات التي لا تملك closing entries
        companies_without_closing = companies.filtered(
            lambda company: company not in existing_moves.company_id
        )
        moves += self._generate_tax_closing_entries(options, companies_without_closing)

        return moves

    def _get_tax_closing_entries_for_closed_period(self, options, companies):
        """البحث عن existing closing entries"""
        closing_moves = self.env["account.move"]
        end_date = fields.Date.from_string(options["date"]["date_to"])

        for company in companies:
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
                closing_moves += existing_closing

        return closing_moves

    def _generate_tax_closing_entries(self, options, companies):
        """إنشاء closing entries جديدة"""
        closing_moves = self.env["account.move"]

        for company in companies:
            # حساب VAT closing entry للشركة
            line_ids_vals, tax_group_subtotal = self._compute_vat_closing_entry(
                company, options
            )

            # إضافة balancing lines
            line_ids_vals += self._add_tax_group_closing_items(
                tax_group_subtotal, company, options
            )

            if line_ids_vals:
                # إنشاء closing move
                closing_move = self._create_closing_move(
                    company, options, line_ids_vals
                )
                closing_moves += closing_move

        return closing_moves

    def _compute_vat_closing_entry(self, company, options):
        """حساب VAT closing entry - مطابق للـ Enterprise"""
        start_date = fields.Date.from_string(options["date"]["date_from"])
        end_date = fields.Date.from_string(options["date"]["date_to"])

        # البحث عن tax lines في الفترة المحددة
        domain = [
            ("company_id", "=", company.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("tax_line_id", "!=", False),
            ("tax_repartition_line_id.use_in_tax_closing", "=", True),
        ]

        tax_lines = self.env["account.move.line"].search(domain)

        # تجميع النتائج حسب tax_group
        tax_groups = defaultdict(lambda: defaultdict(list))

        for line in tax_lines:
            tax = line.tax_line_id
            tax_group = tax.tax_group_id
            if (
                tax_group
                and tax_group.tax_receivable_account_id
                and tax_group.tax_payable_account_id
            ):
                tax_groups[tax_group][tax.id].append(
                    {
                        "name": tax.name,
                        "account_id": line.account_id.id,
                        "amount": line.balance,
                    }
                )

        # إنشاء move lines
        move_vals_lines = []
        tax_group_subtotal = {}
        currency = company.currency_id

        for tax_group, taxes in tax_groups.items():
            total = 0
            for tax_id, lines in taxes.items():
                for line_data in lines:
                    # Line to balance
                    move_vals_lines.append(
                        Command.create(
                            {
                                "name": line_data["name"],
                                "debit": (
                                    abs(line_data["amount"])
                                    if line_data["amount"] < 0
                                    else 0
                                ),
                                "credit": (
                                    line_data["amount"]
                                    if line_data["amount"] > 0
                                    else 0
                                ),
                                "account_id": line_data["account_id"],
                            }
                        )
                    )
                    total += line_data["amount"]

            if not currency.is_zero(total):
                # إضافة المجموع للـ tax group
                key = (
                    tax_group.advance_tax_payment_account_id.id or False,
                    tax_group.tax_receivable_account_id.id,
                    tax_group.tax_payable_account_id.id,
                )

                if key in tax_group_subtotal:
                    tax_group_subtotal[key] += total
                else:
                    tax_group_subtotal[key] = total

        # إذا لم توجد tax lines، أضف lines فارغة
        if not move_vals_lines:
            move_vals_lines = self._create_empty_tax_lines(company)

        return move_vals_lines, tax_group_subtotal

    def _create_empty_tax_lines(self, company):
        """إنشاء lines فارغة إذا لم توجد معاملات ضريبية"""
        # البحث عن tax accounts
        rep_ln_in = self.env["account.tax.repartition.line"].search(
            [
                ("company_id", "=", company.id),
                ("account_id.deprecated", "=", False),
                ("repartition_type", "=", "tax"),
                ("document_type", "=", "invoice"),
                ("tax_id.type_tax_use", "=", "purchase"),
            ],
            limit=1,
        )

        rep_ln_out = self.env["account.tax.repartition.line"].search(
            [
                ("company_id", "=", company.id),
                ("account_id.deprecated", "=", False),
                ("repartition_type", "=", "tax"),
                ("document_type", "=", "invoice"),
                ("tax_id.type_tax_use", "=", "sale"),
            ],
            limit=1,
        )

        if rep_ln_out.account_id and rep_ln_in.account_id:
            return [
                Command.create(
                    {
                        "name": _("Tax Received Adjustment"),
                        "debit": 0,
                        "credit": 0.0,
                        "account_id": rep_ln_out.account_id.id,
                    }
                ),
                Command.create(
                    {
                        "name": _("Tax Paid Adjustment"),
                        "debit": 0.0,
                        "credit": 0,
                        "account_id": rep_ln_in.account_id.id,
                    }
                ),
            ]

        return []

    def _add_tax_group_closing_items(self, tax_group_subtotal, company, options):
        """إضافة balancing lines للـ tax groups"""
        currency = company.currency_id
        line_ids_vals = []

        for key, value in tax_group_subtotal.items():
            total = value

            # Balance على receivable/payable tax account
            if not currency.is_zero(total):
                line_ids_vals.append(
                    Command.create(
                        {
                            "name": (
                                _("Payable tax amount")
                                if total < 0
                                else _("Receivable tax amount")
                            ),
                            "debit": total if total > 0 else 0,
                            "credit": abs(total) if total < 0 else 0,
                            "account_id": (
                                key[2] if total < 0 else key[1]
                            ),  # payable if negative, receivable if positive
                        }
                    )
                )

        return line_ids_vals

    def _create_closing_move(self, company, options, line_ids_vals):
        """إنشاء closing move"""
        end_date = fields.Date.from_string(options["date"]["date_to"])

        closing_move = self.env["account.move"].create(
            {
                "ref": f"Tax Closing Entry - {end_date}",
                "date": end_date,
                "journal_id": self._get_tax_closing_journal(company).id,
                "company_id": company.id,
                "move_type": "entry",
                "line_ids": line_ids_vals,
            }
        )

        return closing_move

    def _get_tax_closing_journal(self, company):
        """الحصول على أو إنشاء journal للـ tax closing"""
        # البحث عن misc journal
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )

        if not journal:
            # إنشاء journal جديد
            journal = self.env["account.journal"].create(
                {
                    "name": "Tax Closing",
                    "code": "TAXCL",
                    "type": "general",
                    "company_id": company.id,
                }
            )

        return journal

    # باقي الدوال الأصلية كما هي...
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

        # Get all taxes used in move lines
        tax_ids = self.env["account.move.line"].search([]).mapped("tax_ids")

        today = fields.Date.today()
        start_date, end_date = get_month(today)

        for tax in tax_ids:
            # Get move lines related to this tax within the month
            move_lines = self.env["account.move.line"].search([
                ("tax_ids", "=", tax.id),
                ("parent_state", "=", "posted"),
                ("date", ">=", start_date),
                ("date", "<=", end_date),
            ])

            # Compute total debit, credit, and balance
            total_debit = sum(move_lines.mapped("debit"))
            total_credit = sum(move_lines.mapped("credit"))
            balance = total_debit - total_credit
            # Prepare data according to tax type
            tax_data = {
                "name": tax.name,
                "amount": tax.amount,
                "balance": round(balance, 2),
                "tax_value": round(balance * (tax.amount / 100), 2),
            }

            if tax.type_tax_use == "sale":
                sale.append(tax_data)
            elif tax.type_tax_use == "purchase":
                purchase.append(tax_data)

        return {"sale": sale, "purchase": purchase}

    # باقي الدوال get_filter_values, get_month_name, get_xlsx_report تبقى كما هي...

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
        sale = []
        purchase = []
        dynamic_date_num = {}

        # Handle empty options safely
        if not options:
            option_domain = ["posted"]
        elif "draft" in options:
            option_domain = ["posted", "draft"]
        else:
            option_domain = ["posted"]

        # Convert dates safely
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

        # Handle fiscal year if needed
        if comparison_type == "year":
            start_date_first, end_date_first = get_fiscal_year(start_date_obj)
        else:
            start_date_first, end_date_first = start_date_obj, end_date_obj

        # Search for taxes
        tax_ids = self.env["account.move.line"].search([]).mapped("tax_ids")

        # Compute taxes for the given date range
        for tax in tax_ids:
            tax_lines = self.env["account.move.line"].search([
                ("tax_ids", "in", [tax.id]),
                ("parent_state", "in", option_domain),
                ("date", ">=", start_date_first),
                ("date", "<=", end_date_first),
            ])

            # Calculate totals
            total_debit = sum(line.debit for line in tax_lines)
            total_credit = sum(line.credit for line in tax_lines)
            net = round(total_debit - total_credit, 2)
            tax_value = round(net * (tax.amount / 100), 2)

            data = {
                "name": tax.name,
                "amount": tax.amount,
                "net": net,
                "tax": tax_value,
            }

            # Separate sale and purchase taxes
            if tax.type_tax_use == "sale":
                sale.append(data)
            elif tax.type_tax_use == "purchase":
                purchase.append(data)

        return {
            "dynamic_date_num": dynamic_date_num,
            "sale": sale,
            "purchase": purchase,
        }

    @api.model
    def get_month_name(self, date):
        """
        Retrieve the abbreviated name of the month for a given date.
        """
        month_names = calendar.month_abbr
        return month_names[date.month]

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an XLSX report based on provided data and response stream.
        """
        if isinstance(data, str):
            try:
                data = json.loads(data)  # convert JSON string to dict
            except Exception:
                data = {}
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet(report_name[:31])
        # Styles
        header_format = workbook.add_format({'bold': True, 'bg_color': '#d6dbe1', 'align': 'center', 'border': 1})
        subheader_format = workbook.add_format({'bold': True, 'bg_color': '#f0f0f0', 'align': 'left', 'border': 1})
        cell_format = workbook.add_format({'align': 'center', 'border': 1})
        bold_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})
        worksheet.set_column(0, 0, 10)
        worksheet.set_column(1, 1, 15)
        worksheet.set_column(2, 2, 25)
        worksheet.set_column(3, 3, 5)
        worksheet.set_column(5, 5, 5)
        worksheet.set_column(6, 6, 5)
        worksheet.set_column(7, 7, 5)

        row = 0
        col = 0

        # Report Title
        worksheet.merge_range(row, col, row, col + 7, report_name, bold_format)
        row += 2

        # Filters Table
        worksheet.write(row, col + 1, 'Date Range', header_format)
        worksheet.write(row + 1, col + 1, 'Comparison', header_format)
        worksheet.write(row + 2, col + 1, 'Options', header_format)
        worksheet.write(row + 3, col + 1, 'Report', header_format)
        worksheet.write(row + 4, col + 1, 'Periods', header_format)

        filters = data.get('filters', {})
        date_range = ''
        if filters.get('start_date'):
            date_range += str(filters['start_date'])
        if filters.get('end_date'):
            date_range += ' to ' + str(filters['end_date'])
        worksheet.write(row, col + 2, date_range, cell_format)

        comparison = ''
        if filters.get('comparison_number_range'):
            comparison = f"{filters.get('comparison_type', '')}: {filters['comparison_number_range']}"
        worksheet.write(row + 1, col + 2, comparison, cell_format)

        options = ', '.join(filters.get('options', [])) if filters.get('options') else ''
        worksheet.write(row + 2, col + 2, options, cell_format)

        report_type = data.get('report_type')
        if report_type:
            if isinstance(report_type, dict):
                key = list(report_type.keys())[0]
                worksheet.write(row + 3, col + 2, key.capitalize(), cell_format)
            else:
                worksheet.write(row + 3, col + 2, str(report_type), cell_format)

        date_viewed = data.get('date_viewed', [])
        if date_viewed:
            for i, date_view in enumerate(date_viewed):
                worksheet.write(row + 4, col + 2 + i, str(date_view), cell_format)
        row += 6

        # Table Headers
        headers = [''] * 6 + ['NET', 'TAX']
        apply_comparison = data.get('apply_comparison', False)
        comparison_number_range = data.get('comparison_number_range', 0)
        if apply_comparison:
            for i in range(comparison_number_range):
                headers += [f'NET {i + 1}', f'TAX {i + 1}']
        worksheet.write_row(row, col, headers, header_format)
        row += 1

        # Sales Section
        worksheet.write(row, col, 'Sales', subheader_format)
        row += 1
        sale_total = data.get('sale_total', '')
        if sale_total:
            worksheet.write(row, col + 6, sale_total, bold_format)
        row += 1
        for sale in data.get('sale', []):
            name = sale.get('name', '')
            account = sale.get('account', '')
            amount = sale.get('amount', '')
            net = sale.get('net', 0)
            tax = sale.get('tax', 0)
            worksheet.write(row, col, name, cell_format)
            worksheet.write(row, col + 1, account, cell_format)
            worksheet.write(row, col + 2, amount, cell_format)
            worksheet.write(row, col + 6, net, cell_format)
            worksheet.write(row, col + 7, tax, cell_format)
            # Dynamic comparison columns
            if apply_comparison:
                dynamic_net = sale.get('dynamic net', {})
                dynamic_tax = sale.get('dynamic tax', {})
                for i in range(comparison_number_range):
                    worksheet.write(row, col + 8 + i * 2, dynamic_net.get(f'dynamic_total_net_sum{i + 1}', ''),
                                    cell_format)
                    worksheet.write(row, col + 9 + i * 2, dynamic_tax.get(f'dynamic_total_tax_sum{i + 1}', ''),
                                    cell_format)
            row += 1

        row += 1
        worksheet.write(row, col, 'Purchase', subheader_format)
        row += 1
        purchase_total = data.get('purchase_total', '')
        if purchase_total:
            worksheet.write(row, col + 6, purchase_total, bold_format)
        row += 1

        for purchase in data.get('purchase', []):
            name = purchase.get('name', '')
            account = purchase.get('account', '')
            amount = purchase.get('amount', '')
            net = purchase.get('net', 0)
            tax = purchase.get('tax', 0)
            worksheet.write(row, col, name, cell_format)
            worksheet.write(row, col + 1, account, cell_format)
            worksheet.write(row, col + 2, amount, cell_format)
            worksheet.write(row, col + 6, net, cell_format)
            worksheet.write(row, col + 7, tax, cell_format)
            # Dynamic comparison columns
            if apply_comparison:
                dynamic_net = purchase.get('dynamic net', {})
                dynamic_tax = purchase.get('dynamic tax', {})
                for i in range(comparison_number_range):
                    worksheet.write(row, col + 8 + i * 2, dynamic_net.get(f'dynamic_total_net_sum{i + 1}', ''),
                                    cell_format)
                    worksheet.write(row, col + 9 + i * 2, dynamic_tax.get(f'dynamic_total_tax_sum{i + 1}', ''),
                                    cell_format)
            row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
