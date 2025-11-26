# -*- coding: utf-8 -*-

import io
import json
import calendar
from dateutil.relativedelta import relativedelta
import xlsxwriter
from odoo import api, fields, models
from datetime import datetime
from odoo.tools import date_utils


class DeferredReport(models.TransientModel):
    """For creating Deferred Revenue and Expense reports"""

    _name = "deferred.report"
    _description = "Deferred Revenue and Expense Report"

    @api.model
    def _get_deferred_periods(self, date_from, date_to, period_type="month"):
        """Get periods for the report similar to the original system"""
        periods = []
        current_date = date_from

        while current_date <= date_to:
            if period_type == "month":
                period_end = current_date.replace(
                    day=calendar.monthrange(current_date.year, current_date.month)[1]
                )
                period_end = min(period_end, date_to)

                # Create period tuple similar to original system
                period = (
                    current_date,
                    period_end,
                    f"{current_date.strftime('%b')} - {period_end.strftime('%b %Y')}",
                )
                periods.append(period)

                current_date = period_end + relativedelta(days=1)
            else:
                break

        return periods

    @api.model
    def _get_deferred_amounts_by_line(self, lines, periods, deferred_type):
        """Calculate deferred amounts for each line and period"""
        results = []

        for line in lines:
            line_start = fields.Date.to_date(line["deferred_start_date"])
            line_end = fields.Date.to_date(line["deferred_end_date"])
            total_balance = abs(line["balance"])

            # Calculate total duration in days
            total_days = (line_end - line_start).days + 1

            # Create result dict for this line
            line_result = {
                "account_id": line["account_id"],
                "partner_id": line["partner_id"],
                "product_id": line["product_id"],
                "product_category_id": line.get("product_category_id"),
                "balance": total_balance,
                "move_id": line["move_id"],
                "move_name": line["move_name"],
                "name": line["name"],
                "date": line["date"],
                "deferred_start_date": line["deferred_start_date"],
                "deferred_end_date": line["deferred_end_date"],
            }

            # Calculate amounts for each period
            for period in periods:
                period_start, period_end, period_label = period

                # Calculate overlap between line period and report period
                overlap_start = max(line_start, period_start)
                overlap_end = min(line_end, period_end)

                if overlap_start <= overlap_end:
                    overlap_days = (overlap_end - overlap_start).days + 1
                    period_amount = (overlap_days / total_days) * total_balance
                else:
                    period_amount = 0.0

                line_result[period] = period_amount

            results.append(line_result)

        return results

    @api.model
    def view_deferred_revenue_report(self, option, tag):
        """Retrieve deferred revenue report data based on options and tags."""
        return self._get_deferred_data("revenue")

    @api.model
    def view_deferred_expense_report(self, option, tag):
        """Retrieve deferred expense report data based on options and tags."""
        return self._get_deferred_data("expense")

    @api.model
    def _get_deferred_data(self, report_type):
        """Get deferred data for both revenue and expense reports"""
        account_dict = {}
        account_totals = {}

        # Set domain based on report type
        if report_type == "revenue":
            domain = [
                ("parent_state", "=", "posted"),
                ("deferred_start_date", "!=", False),
                ("deferred_end_date", "!=", False),
                ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                ("account_id.account_type", "in", ("income", "income_other")),
            ]
        else:  # expense
            domain = [
                ("parent_state", "=", "posted"),
                ("deferred_start_date", "!=", False),
                ("deferred_end_date", "!=", False),
                ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
                (
                    "account_id.account_type",
                    "in",
                    ("expense", "expense_depreciation", "expense_direct_cost"),
                ),
            ]

        move_line_ids = self.env["account.move.line"].search(domain)
        account_ids = move_line_ids.mapped("account_id")

        account_dict["journal_ids"] = self.env["account.journal"].search_read(
            [], ["name"]
        )
        account_dict["analytic_ids"] = self.env["account.analytic.account"].search_read(
            [], ["name"]
        )

        # Get current date for period calculation
        today = fields.Date.today()
        current_quarter_start, current_quarter_end = date_utils.get_quarter(today)

        # Define periods similar to the original system
        periods = [
            (
                fields.Date.from_string("1900-01-01"),
                fields.Date.from_string("9999-12-31"),
                "total",
            ),
            (
                current_quarter_end + relativedelta(days=1),
                fields.Date.from_string("9999-12-31"),
                "not_started",
            ),
            (
                fields.Date.from_string("1900-01-01"),
                current_quarter_start - relativedelta(days=1),
                "before",
            ),
            (current_quarter_start, current_quarter_end, "current"),
            (
                current_quarter_end + relativedelta(days=1),
                fields.Date.from_string("9999-12-31"),
                "later",
            ),
        ]

        for account in account_ids:
            move_line_id = move_line_ids.filtered(lambda x: x.account_id == account)
            move_line_list = []

            for move_line in move_line_id:
                # Get deferred moves for this line
                deferred_moves = move_line.move_id.deferred_move_ids

                # Calculate recognized amount based on report type
                if report_type == "revenue":
                    recognized_amount = sum(
                        deferred_moves.line_ids.filtered(
                            lambda l: l.account_id == move_line.account_id
                        ).mapped("credit")
                    )
                else:  # expense
                    recognized_amount = sum(
                        deferred_moves.line_ids.filtered(
                            lambda l: l.account_id == move_line.account_id
                        ).mapped("debit")
                    )

                # Prepare line data for period calculation
                line_data = {
                    "account_id": move_line.account_id.id,
                    "partner_id": (
                        move_line.partner_id.id if move_line.partner_id else False
                    ),
                    "product_id": (
                        move_line.product_id.id if move_line.product_id else False
                    ),
                    "product_category_id": (
                        move_line.product_id.categ_id.id
                        if move_line.product_id and move_line.product_id.categ_id
                        else False
                    ),
                    "balance": move_line.balance,
                    "move_id": move_line.move_id.id,
                    "move_name": move_line.move_id.name,
                    "name": move_line.name,
                    "date": move_line.date,
                    "deferred_start_date": move_line.deferred_start_date,
                    "deferred_end_date": move_line.deferred_end_date,
                }

                # Calculate period amounts
                period_amounts = self._get_deferred_amounts_by_line(
                    [line_data], periods, report_type
                )[0]

                move_line_data = {
                    "date": move_line.date,
                    "name": move_line.name,
                    "move_name": move_line.move_id.name,
                    "debit": move_line.debit,
                    "credit": move_line.credit,
                    "partner_id": (
                        move_line.partner_id.name if move_line.partner_id else ""
                    ),
                    "account_id": move_line.account_id.id,
                    "journal_id": move_line.journal_id.id,
                    "move_id": move_line.move_id.id,
                    "deferred_start_date": move_line.deferred_start_date,
                    "deferred_end_date": move_line.deferred_end_date,
                    "deferred_amount": abs(move_line.balance),
                    "recognized_amount": recognized_amount,
                    # Add period breakdowns
                    "total": period_amounts.get(periods[0], 0),
                    "not_started": period_amounts.get(periods[1], 0),
                    "before": period_amounts.get(periods[2], 0),
                    "current": period_amounts.get(periods[3], 0),
                    "later": period_amounts.get(periods[4], 0),
                }
                move_line_data["remaining_amount"] = (
                    move_line_data["deferred_amount"]
                    - move_line_data["recognized_amount"]
                )
                move_line_list.append(move_line_data)

            if move_line_list:
                account_dict[account.display_name] = move_line_list
                currency_id = self.env.company.currency_id.symbol
                account_totals[account.display_name] = {
                    "total_deferred": round(
                        sum([line["deferred_amount"] for line in move_line_list]), 2
                    ),
                    "total_recognized": round(
                        sum([line["recognized_amount"] for line in move_line_list]), 2
                    ),
                    "total_remaining": round(
                        sum([line["remaining_amount"] for line in move_line_list]), 2
                    ),
                    "total": round(sum([line["total"] for line in move_line_list]), 2),
                    "not_started": round(
                        sum([line["not_started"] for line in move_line_list]), 2
                    ),
                    "before": round(
                        sum([line["before"] for line in move_line_list]), 2
                    ),
                    "current": round(
                        sum([line["current"] for line in move_line_list]), 2
                    ),
                    "later": round(sum([line["later"] for line in move_line_list]), 2),
                    "currency_id": currency_id,
                    "account_id": account.id,
                }

        account_dict["account_totals"] = account_totals
        return account_dict

    @api.model
    def get_filter_values(
        self, journal_id, date_range, options, analytic, method, report_type
    ):
        """Retrieve filtered values for the deferred reports."""
        account_dict = {}
        account_totals = {}
        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        previous_quarter_start = quarter_start - relativedelta(months=3)
        previous_quarter_end = quarter_start - relativedelta(days=1)

        if options == {}:
            options = None
        if options is None:
            option_domain = ["posted"]
        elif "draft" in options:
            option_domain = ["posted", "draft"]

        # Base domain for deferred entries
        domain = [
            ("parent_state", "in", option_domain),
            ("deferred_start_date", "!=", False),
            ("deferred_end_date", "!=", False),
        ]

        # Add report type filter
        if report_type == "revenue":
            domain.extend(
                [
                    ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                    ("account_id.account_type", "in", ("income", "income_other")),
                ]
            )
        else:  # expense
            domain.extend(
                [
                    ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
                    (
                        "account_id.account_type",
                        "in",
                        ("expense", "expense_depreciation", "expense_direct_cost"),
                    ),
                ]
            )

        # Add journal filter
        if journal_id:
            domain.append(("journal_id", "in", journal_id))

        # Add analytic filter
        if analytic:
            analytic_line = (
                self.env["account.analytic.line"]
                .search([("account_id", "in", analytic)])
                .mapped("id")
            )
            domain.append(("analytic_line_ids", "in", analytic_line))

        # Add date filter
        if date_range:
            if date_range == "month":
                domain += [("date", ">=", today.replace(day=1)), ("date", "<=", today)]
            elif date_range == "year":
                domain += [
                    ("date", ">=", today.replace(month=1, day=1)),
                    ("date", "<=", today),
                ]
            elif date_range == "quarter":
                domain += [("date", ">=", quarter_start), ("date", "<=", quarter_end)]
            elif date_range == "last-month":
                last_month_start = today.replace(day=1) - relativedelta(months=1)
                last_month_end = last_month_start + relativedelta(
                    day=calendar.monthrange(
                        last_month_start.year, last_month_start.month
                    )[1]
                )
                domain += [
                    ("date", ">=", last_month_start),
                    ("date", "<=", last_month_end),
                ]
            elif date_range == "last-year":
                last_year_start = today.replace(month=1, day=1) - relativedelta(years=1)
                last_year_end = last_year_start.replace(month=12, day=31)
                domain += [
                    ("date", ">=", last_year_start),
                    ("date", "<=", last_year_end),
                ]
            elif date_range == "last-quarter":
                domain += [
                    ("date", ">=", previous_quarter_start),
                    ("date", "<=", previous_quarter_end),
                ]
            elif isinstance(date_range, dict):
                if "start_date" in date_range and "end_date" in date_range:
                    start_date = datetime.strptime(
                        date_range["start_date"], "%Y-%m-%d"
                    ).date()
                    end_date = datetime.strptime(
                        date_range["end_date"], "%Y-%m-%d"
                    ).date()
                    domain += [("date", ">=", start_date), ("date", "<=", end_date)]
                elif "start_date" in date_range:
                    start_date = datetime.strptime(
                        date_range["start_date"], "%Y-%m-%d"
                    ).date()
                    domain += [("date", ">=", start_date)]
                elif "end_date" in date_range:
                    end_date = datetime.strptime(
                        date_range["end_date"], "%Y-%m-%d"
                    ).date()
                    domain += [("date", "<=", end_date)]

        move_line_ids = self.env["account.move.line"].search(domain)
        account_ids = move_line_ids.mapped("account_id")

        account_dict["journal_ids"] = self.env["account.journal"].search_read(
            [], ["name"]
        )
        account_dict["analytic_ids"] = self.env["account.analytic.account"].search_read(
            [], ["name"]
        )

        # Define periods
        current_quarter_start, current_quarter_end = date_utils.get_quarter(today)
        periods = [
            (
                fields.Date.from_string("1900-01-01"),
                fields.Date.from_string("9999-12-31"),
                "total",
            ),
            (
                current_quarter_end + relativedelta(days=1),
                fields.Date.from_string("9999-12-31"),
                "not_started",
            ),
            (
                fields.Date.from_string("1900-01-01"),
                current_quarter_start - relativedelta(days=1),
                "before",
            ),
            (current_quarter_start, current_quarter_end, "current"),
            (
                current_quarter_end + relativedelta(days=1),
                fields.Date.from_string("9999-12-31"),
                "later",
            ),
        ]

        for account in account_ids:
            move_line_id = move_line_ids.filtered(lambda x: x.account_id == account)
            move_line_list = []

            for move_line in move_line_id:
                deferred_moves = move_line.move_id.deferred_move_ids

                if report_type == "revenue":
                    recognized_amount = sum(
                        deferred_moves.line_ids.filtered(
                            lambda l: l.account_id == move_line.account_id
                        ).mapped("credit")
                    )
                else:  # expense
                    recognized_amount = sum(
                        deferred_moves.line_ids.filtered(
                            lambda l: l.account_id == move_line.account_id
                        ).mapped("debit")
                    )

                # Prepare line data for period calculation
                line_data = {
                    "account_id": move_line.account_id.id,
                    "partner_id": (
                        move_line.partner_id.id if move_line.partner_id else False
                    ),
                    "product_id": (
                        move_line.product_id.id if move_line.product_id else False
                    ),
                    "product_category_id": (
                        move_line.product_id.categ_id.id
                        if move_line.product_id and move_line.product_id.categ_id
                        else False
                    ),
                    "balance": move_line.balance,
                    "move_id": move_line.move_id.id,
                    "move_name": move_line.move_id.name,
                    "name": move_line.name,
                    "date": move_line.date,
                    "deferred_start_date": move_line.deferred_start_date,
                    "deferred_end_date": move_line.deferred_end_date,
                }

                # Calculate period amounts
                period_amounts = self._get_deferred_amounts_by_line(
                    [line_data], periods, report_type
                )[0]

                move_line_data = {
                    "date": move_line.date,
                    "name": move_line.name,
                    "move_name": move_line.move_id.name,
                    "debit": move_line.debit,
                    "credit": move_line.credit,
                    "partner_id": (
                        move_line.partner_id.name if move_line.partner_id else ""
                    ),
                    "account_id": move_line.account_id.id,
                    "journal_id": move_line.journal_id.id,
                    "move_id": move_line.move_id.id,
                    "deferred_start_date": move_line.deferred_start_date,
                    "deferred_end_date": move_line.deferred_end_date,
                    "deferred_amount": abs(move_line.balance),
                    "recognized_amount": recognized_amount,
                    # Add period breakdowns
                    "total": period_amounts.get(periods[0], 0),
                    "not_started": period_amounts.get(periods[1], 0),
                    "before": period_amounts.get(periods[2], 0),
                    "current": period_amounts.get(periods[3], 0),
                    "later": period_amounts.get(periods[4], 0),
                }
                move_line_data["remaining_amount"] = (
                    move_line_data["deferred_amount"]
                    - move_line_data["recognized_amount"]
                )
                move_line_list.append(move_line_data)

            if move_line_list:
                account_dict[account.display_name] = move_line_list
                currency_id = self.env.company.currency_id.symbol
                account_totals[account.display_name] = {
                    "total_deferred": round(
                        sum([line["deferred_amount"] for line in move_line_list]), 2
                    ),
                    "total_recognized": round(
                        sum([line["recognized_amount"] for line in move_line_list]), 2
                    ),
                    "total_remaining": round(
                        sum([line["remaining_amount"] for line in move_line_list]), 2
                    ),
                    "total": round(sum([line["total"] for line in move_line_list]), 2),
                    "not_started": round(
                        sum([line["not_started"] for line in move_line_list]), 2
                    ),
                    "before": round(
                        sum([line["before"] for line in move_line_list]), 2
                    ),
                    "current": round(
                        sum([line["current"] for line in move_line_list]), 2
                    ),
                    "later": round(sum([line["later"] for line in move_line_list]), 2),
                    "currency_id": currency_id,
                    "account_id": account.id,
                }

        account_dict["account_totals"] = account_totals
        return account_dict

    def get_xlsx_report(self, data, response, report_name, dfr_data):
        """Generate XLSX report for deferred revenue/expense"""
        import logging

        _logger = logging.getLogger(__name__)

        try:
            _logger.info(f"Starting XLSX generation with report_name: {report_name}")
            _logger.info(f"dfr_data content: {dfr_data}")

            # التعامل مع البيانات القادمة من Cybrosys controller
            if isinstance(data, str):
                try:
                    report_data = json.loads(data)
                    _logger.info("Successfully parsed JSON data from 'data' parameter")
                except json.JSONDecodeError as e:
                    _logger.error(f"JSON decode error in 'data': {e}")
                    report_data = {}
            elif isinstance(data, dict):
                report_data = data
                _logger.info("Using 'data' parameter directly")
            else:
                # محاولة استخدام dfr_data
                if isinstance(dfr_data, str):
                    try:
                        report_data = json.loads(dfr_data)
                        _logger.info(
                            "Successfully parsed JSON data from 'dfr_data' parameter"
                        )
                    except json.JSONDecodeError:
                        report_data = {}
                else:
                    report_data = dfr_data if isinstance(dfr_data, dict) else {}

            if not report_data:
                _logger.warning("No valid data received for XLSX generation")
                report_data = {
                    "title": "No Data Available",
                    "account": [],
                    "account_data": {},
                    "total": {},
                    "grand_total": {},
                }

            _logger.info(f"Report data keys: {list(report_data.keys())}")

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {"in_memory": True})
            sheet = workbook.add_worksheet("Deferred Report")

            # Define formats
            format_title = workbook.add_format(
                {
                    "bold": True,
                    "align": "center",
                    "font_size": 16,
                    "font_color": "white",
                    "bg_color": "#5A5A5A",
                }
            )

            format_header = workbook.add_format(
                {
                    "bold": True,
                    "align": "center",
                    "font_size": 12,
                    "font_color": "white",
                    "bg_color": "#2B547E",
                    "border": 1,
                }
            )

            format_subheader = workbook.add_format(
                {
                    "bold": True,
                    "font_size": 11,
                    "font_color": "black",
                    "bg_color": "#E8E8E8",
                    "border": 1,
                }
            )

            txt_name = workbook.add_format({"border": 1, "font_size": 10})
            txt_right = workbook.add_format(
                {
                    "border": 1,
                    "font_size": 10,
                    "num_format": "#,##0.00",
                    "align": "right",
                }
            )

            # Set column widths
            sheet.set_column("A:A", 35)
            sheet.set_column("B:F", 18)

            # Write title
            title = report_data.get("title", report_name or "Deferred Revenue Report")
            sheet.merge_range("A1:F1", title, format_title)
            row = 2

            # Write filter information
            filters = report_data.get("filters", {})
            if filters and any(filters.values()):
                sheet.write(row, 0, "Filters Applied:", format_header)
                sheet.merge_range(row, 1, row, 5, "", format_header)
                row += 1

                if filters.get("start_date") or filters.get("end_date"):
                    date_range = f"Date: {filters.get('start_date', 'N/A')} to {filters.get('end_date', 'N/A')}"
                    sheet.write(row, 0, date_range, txt_name)
                    sheet.merge_range(row, 1, row, 5, "", txt_name)
                    row += 1

                if filters.get("journal"):
                    journals = ", ".join(filters.get("journal", []))
                    sheet.write(row, 0, f"Journals: {journals}", txt_name)
                    sheet.merge_range(row, 1, row, 5, "", txt_name)
                    row += 1

                if filters.get("analytic"):
                    analytics = ", ".join(filters.get("analytic", []))
                    sheet.write(row, 0, f"Analytics: {analytics}", txt_name)
                    sheet.merge_range(row, 1, row, 5, "", txt_name)
                    row += 1

                row += 1

            # Write headers
            headers = [
                "Account/Description",
                "Total",
                "Not Started",
                "Before",
                "Current Quarter",
                "Later",
            ]
            for col, header in enumerate(headers):
                sheet.write(row, col, header, format_header)
            row += 1

            # Get data
            account_list = report_data.get("account", [])
            account_totals = report_data.get("total", {})
            account_data = report_data.get("account_data", {})

            _logger.info(f"Processing {len(account_list)} accounts")

            # Write account data
            if account_list:
                for account_name in account_list:
                    _logger.info(f"Processing account: {account_name}")

                    if account_name in account_totals:
                        account_total = account_totals[account_name]

                        # Write account header
                        sheet.write(row, 0, account_name, format_subheader)
                        sheet.write(
                            row, 1, float(account_total.get("total", 0)), txt_right
                        )
                        sheet.write(
                            row,
                            2,
                            float(account_total.get("not_started", 0)),
                            txt_right,
                        )
                        sheet.write(
                            row, 3, float(account_total.get("before", 0)), txt_right
                        )
                        sheet.write(
                            row, 4, float(account_total.get("current", 0)), txt_right
                        )
                        sheet.write(
                            row, 5, float(account_total.get("later", 0)), txt_right
                        )
                        row += 1

                        # Write account details
                        if account_name in account_data:
                            account_lines = account_data[account_name]

                            if isinstance(account_lines, list):
                                for line in account_lines:
                                    # Create description
                                    description_parts = []
                                    if line.get("move_name"):
                                        description_parts.append(
                                            f"  {line.get('move_name')}"
                                        )
                                    if line.get("date"):
                                        description_parts.append(
                                            f"({line.get('date')})"
                                        )
                                    if line.get("name"):
                                        description_parts.append(
                                            f"- {line.get('name')}"
                                        )

                                    description = (
                                        " ".join(description_parts)
                                        if description_parts
                                        else "  [No description]"
                                    )

                                    sheet.write(row, 0, description, txt_name)
                                    sheet.write(
                                        row, 1, float(line.get("total", 0)), txt_right
                                    )
                                    sheet.write(
                                        row,
                                        2,
                                        float(line.get("not_started", 0)),
                                        txt_right,
                                    )
                                    sheet.write(
                                        row, 3, float(line.get("before", 0)), txt_right
                                    )
                                    sheet.write(
                                        row, 4, float(line.get("current", 0)), txt_right
                                    )
                                    sheet.write(
                                        row, 5, float(line.get("later", 0)), txt_right
                                    )
                                    row += 1

                        # Add space between accounts
                        row += 1
            else:
                sheet.write(row, 0, "No data available", txt_name)
                sheet.merge_range(row, 1, row, 5, "", txt_name)
                row += 1

            # Write grand totals
            grand_total = report_data.get("grand_total", {})
            if grand_total:
                row += 1
                sheet.write(row, 0, "GRAND TOTAL", format_subheader)
                sheet.write(
                    row, 1, float(grand_total.get("total_deferred", 0)), txt_right
                )
                sheet.write(
                    row, 2, float(grand_total.get("total_not_started", 0)), txt_right
                )
                sheet.write(
                    row, 3, float(grand_total.get("total_before", 0)), txt_right
                )
                sheet.write(
                    row, 4, float(grand_total.get("total_current", 0)), txt_right
                )
                sheet.write(row, 5, float(grand_total.get("total_later", 0)), txt_right)

            workbook.close()
            output.seek(0)
            response.stream.write(output.read())
            output.close()

            _logger.info("XLSX generation completed successfully")

        except Exception as e:
            _logger.error(f"Error in get_xlsx_report: {e}", exc_info=True)

            # Create error report
            try:
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {"in_memory": True})
                sheet = workbook.add_worksheet("Error Report")

                error_format = workbook.add_format(
                    {"bold": True, "font_color": "red", "bg_color": "#FFCCCC"}
                )

                sheet.write(0, 0, "XLSX Generation Error:", error_format)
                sheet.write(1, 0, f"Error: {str(e)}")
                sheet.write(2, 0, f"Report Name: {report_name}")
                sheet.write(3, 0, f"Data Type: {type(data)}")
                sheet.write(4, 0, f"Data Content (first 500 chars):")
                sheet.write(5, 0, str(data)[:500] if data else "No data provided")

                workbook.close()
                output.seek(0)
                response.stream.write(output.read())
                output.close()
            except:
                response.stream.write(f"Error: {str(e)}".encode("utf-8"))
