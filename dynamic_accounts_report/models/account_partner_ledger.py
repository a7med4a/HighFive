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
import io
import json
from dateutil.relativedelta import relativedelta
import xlsxwriter
from odoo import api, fields, models
from datetime import datetime
from odoo.tools import date_utils


class AccountPartnerLedger(models.TransientModel):
    """For creating Partner Ledger report"""

    _name = "account.partner.ledger"
    _description = "Partner Ledger Report"

    @api.model
    def view_report(self, option, tag):
        """
        Retrieve partner-related data for generating a report.

        :param option: The option for filtering the data.
        :type option: str

        :param tag: The tag used for filtering the data.
        :type tag: str

        :return: A dictionary containing the partner data for the report.
        :rtype: dict
        """
        account_type_domain = []
        account_type_domain.append("liability_payable")
        account_type_domain.append("asset_cash")
        account_type_domain.append("asset_current")
        account_type_domain.append("asset_non_current")
        account_type_domain.append("asset_prepayments")
        account_type_domain.append("asset_fixed")
        account_type_domain.append("liability_credit_card")
        account_type_domain.append("liability_current")
        account_type_domain.append("liability_non_current")
        account_type_domain.append("equity")
        account_type_domain.append("income")
        account_type_domain.append("income_other")
        account_type_domain.append("expense")
        account_type_domain.append("expense_depreciation")
        account_type_domain.append("expense_direct_cost")
        account_type_domain.append("off_balance")
        fiscal_year = (
            self.env["res.company"]
            .search([])
            .mapped("account_opening_date")[0]
            .strftime("%Y-%m-%d")
        )
        fiscal_year_start = datetime.strptime(fiscal_year, "%Y-%m-%d").date()
        partner_dict = {}
        partner_totals = {}
        move_line_ids = self.env["account.move.line"].search(
            [
                ("account_type", "in", account_type_domain),
                ("parent_state", "=", "posted"),
            ]
        )
        partner_ids = move_line_ids.mapped("partner_id")
        for partner in partner_ids:
            total_debit_balance = 0
            total_credit_balance = 0
            balance = 0
            move_line_id = move_line_ids.filtered(lambda x: x.partner_id == partner)
            move_line_list = []
            for move_line in move_line_id:
                if move_line.invoice_date:
                    if move_line.invoice_date < fiscal_year_start:
                        total_debit_balance += move_line.debit
                        total_credit_balance += move_line.credit
                        balance = total_debit_balance - total_credit_balance
                move_line_data = move_line.read(
                    [
                        "date",
                        "move_name",
                        "account_type",
                        "debit",
                        "credit",
                        "date_maturity",
                        "account_id",
                        "journal_id",
                        "move_id",
                        "matching_number",
                        "amount_currency",
                    ]
                )
                account_code = (
                    self.env["account.account"].browse(move_line.account_id.id).code
                )
                journal_code = (
                    self.env["account.journal"].browse(move_line.journal_id.id).code
                )
                if account_code:
                    move_line_data[0]["jrnl"] = journal_code
                    move_line_data[0]["code"] = account_code
                move_line_list.append(move_line_data)
            partner_dict[partner.name] = move_line_list
            currency_id = self.env.company.currency_id.symbol
            partner_totals[partner.name] = {
                "total_debit": round(sum(move_line_id.mapped("debit")), 2),
                "total_credit": round(sum(move_line_id.mapped("credit")), 2),
                "currency_id": currency_id,
                "initial_balance": balance,
                "partner_id": partner.id,
                "move_name": "Initial Balance",
                "initial_debit": total_debit_balance,
                "initial_credit": total_credit_balance,
            }
            partner_dict["partner_totals"] = partner_totals
        return partner_dict

    @api.model
    def get_filter_values(self, partner_id, data_range, account, options, search_value):
        """
        Retrieve filtered partner-related data for generating a report.

        :param partner_id: The ID(s) of the partner(s) to filter by.
        :type partner_id: list or int

        :param data_range: The date range option for filtering the data.
        :type data_range: str

        :param account: The account type(s) to filter by.
        :type account: list or str

        :param options: Additional options for filtering the data.
        :type options: dict

        :return: A dictionary containing the filtered partner data.
        :rtype: dict
        """
        if options == {}:
            options = None
        if account == {}:
            account = None
        account_type_domain = []
        if options is None:
            option_domain = ["posted"]
        elif "draft" in options:
            option_domain = ["posted", "draft"]
        if account is None:
            account_type_domain.append("liability_payable")
            account_type_domain.append("asset_cash")
            account_type_domain.append("asset_current")
            account_type_domain.append("asset_non_current")
            account_type_domain.append("asset_prepayments")
            account_type_domain.append("asset_fixed")
            account_type_domain.append("liability_credit_card")
            account_type_domain.append("liability_current")
            account_type_domain.append("liability_non_current")
            account_type_domain.append("equity")
            account_type_domain.append("income")
            account_type_domain.append("income_other")
            account_type_domain.append("expense")
            account_type_domain.append("expense_depreciation")
            account_type_domain.append("expense_direct_cost")
            account_type_domain.append("off_balance")
        elif "Receivable" in account and "Payable" in account:
            account_type_domain.append("liability_payable")
            account_type_domain.append("asset_receivable")
        elif "Receivable" in account:
            account_type_domain.append("asset_receivable")
        elif "Payable" in account:
            account_type_domain.append("liability_payable")
        partner_dict = {}
        partner_totals = {}
        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        previous_quarter_start = quarter_start - relativedelta(months=3)
        previous_quarter_end = quarter_start - relativedelta(days=1)
        if not partner_id:
            partner_id = (
                self.env["account.move.line"]
                .search(
                    [
                        ("account_type", "in", account_type_domain),
                        ("parent_state", "in", option_domain),
                    ]
                )
                .mapped("partner_id")
                .ids
            )
        balance_move_line_ids = []
        for partners in partner_id:
            partner = self.env["res.partner"].browse(partners).name
            if search_value and search_value.lower() not in partner.lower():
                continue
            if data_range:
                if data_range == "month":
                    move_line_ids = (
                        self.env["account.move.line"]
                        .search(
                            [
                                ("partner_id", "=", partners),
                                ("account_type", "in", account_type_domain),
                                ("parent_state", "in", option_domain),
                            ]
                        )
                        .filtered(lambda x: x.date.month == fields.Date.today().month)
                    )
                    date_start = fields.Date.today().replace(day=1)
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif data_range == "year":
                    move_line_ids = (
                        self.env["account.move.line"]
                        .search(
                            [
                                ("partner_id", "=", partners),
                                ("account_type", "in", account_type_domain),
                                ("parent_state", "in", option_domain),
                            ]
                        )
                        .filtered(lambda x: x.date.year == fields.Date.today().year)
                    )
                    date_start = fields.Date.today().replace(month=1, day=1)
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif data_range == "quarter":
                    move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("date", ">=", quarter_start),
                            ("date", "<=", quarter_end),
                            ("parent_state", "in", option_domain),
                        ]
                    )
                    date_start = quarter_start
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif data_range == "last-month":
                    move_line_ids = (
                        self.env["account.move.line"]
                        .search(
                            [
                                ("partner_id", "=", partners),
                                ("account_type", "in", account_type_domain),
                                ("parent_state", "in", option_domain),
                            ]
                        )
                        .filtered(
                            lambda x: x.date.month == fields.Date.today().month - 1
                        )
                    )
                    date_start = fields.Date.today().replace(
                        day=1, month=fields.Date.today().month - 1
                    )
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif data_range == "last-year":
                    move_line_ids = (
                        self.env["account.move.line"]
                        .search(
                            [
                                ("partner_id", "=", partners),
                                ("account_type", "in", account_type_domain),
                                ("parent_state", "in", option_domain),
                            ]
                        )
                        .filtered(lambda x: x.date.year == fields.Date.today().year - 1)
                    )
                    date_start = fields.Date.today().replace(
                        day=1,
                        month=1,
                    )
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif data_range == "last-quarter":
                    move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("date", ">=", previous_quarter_start),
                            ("date", "<=", previous_quarter_end),
                            ("parent_state", "in", option_domain),
                        ]
                    )
                    date_start = previous_quarter_start
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif "start_date" in data_range and "end_date" in data_range:
                    start_date = datetime.strptime(
                        data_range["start_date"], "%Y-%m-%d"
                    ).date()
                    end_date = datetime.strptime(
                        data_range["end_date"], "%Y-%m-%d"
                    ).date()
                    move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("date", ">=", start_date),
                            ("date", "<=", end_date),
                            ("parent_state", "in", option_domain),
                        ]
                    )
                    date_start = start_date
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif "start_date" in data_range:
                    start_date = datetime.strptime(
                        data_range["start_date"], "%Y-%m-%d"
                    ).date()
                    move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("date", ">=", start_date),
                            ("parent_state", "in", option_domain),
                        ]
                    )
                    date_start = start_date
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
                elif "end_date" in data_range:
                    end_date = datetime.strptime(
                        data_range["end_date"], "%Y-%m-%d"
                    ).date()
                    move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("date", "<=", end_date),
                            ("parent_state", "in", option_domain),
                        ]
                    )
                    fiscal_year = (
                        self.env["res.company"]
                        .search([])
                        .mapped("account_opening_date")[0]
                        .strftime("%Y-%m-%d")
                    )
                    date_start = datetime.strptime(fiscal_year, "%Y-%m-%d").date()
                    balance_move_line_ids = self.env["account.move.line"].search(
                        [
                            ("partner_id", "=", partners),
                            ("account_type", "in", account_type_domain),
                            ("parent_state", "in", option_domain),
                            ("invoice_date", "<", date_start),
                        ]
                    )
            else:
                move_line_ids = self.env["account.move.line"].search(
                    [
                        ("partner_id", "=", partners),
                        ("account_type", "in", account_type_domain),
                        ("parent_state", "in", option_domain),
                    ]
                )
            total_debit_balance = 0
            total_credit_balance = 0
            balance = 0
            move_line_list = []
            for move_line in move_line_ids:
                move_line_data = move_line.read(
                    [
                        "date",
                        "move_name",
                        "account_type",
                        "debit",
                        "credit",
                        "date_maturity",
                        "account_id",
                        "journal_id",
                        "move_id",
                        "matching_number",
                        "amount_currency",
                    ]
                )
                account_code = (
                    self.env["account.account"].browse(move_line.account_id.id).code
                )
                journal_code = (
                    self.env["account.journal"].browse(move_line.journal_id.id).code
                )
                if account_code:
                    move_line_data[0]["jrnl"] = journal_code
                    move_line_data[0]["code"] = account_code
                move_line_list.append(move_line_data)
            for remaining_move in balance_move_line_ids:
                if remaining_move.invoice_date:
                    if remaining_move.invoice_date < date_start:
                        total_debit_balance += remaining_move.debit
                        total_credit_balance += remaining_move.credit
                        balance = total_debit_balance - total_credit_balance
            partner_dict[partner] = move_line_list
            currency_id = self.env.company.currency_id.symbol
            partner_totals[partner] = {
                "total_debit": round(sum(move_line_ids.mapped("debit")), 2),
                "total_credit": round(sum(move_line_ids.mapped("credit")), 2),
                "currency_id": currency_id,
                "partner_id": partners,
                "initial_balance": balance,
                "move_name": "Initial Balance",
                "initial_debit": total_debit_balance,
                "initial_credit": total_credit_balance,
            }
            partner_dict["partner_totals"] = partner_totals
        return partner_dict

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an Excel report based on the provided data.

        :param data: The data used to generate the report.
        :type data: str (JSON format)

        :param response: The response object to write the report to.
        :type response: object

        :param report_name: The name of the report.
        :type report_name: str

        :return: None
        """
        if self.env.company:
            company = self.env.company
            company_name = company.name
            company_vat = company.vat
            company_street = company.street
        else:
            company_name = ""
            company_vat = ""
            company_street = ""

        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        start_date = data['filters']['start_date'] if data['filters']['start_date'] else ''
        end_date = data['filters']['end_date'] if data['filters']['end_date'] else ''
        sheet = workbook.add_worksheet()

        # Define formats
        head = workbook.add_format({
            'font_size': 15, 'align': 'center', 'bold': True
        })

        head_highlight = workbook.add_format({
            'font_size': 10, 'align': 'center', 'bold': True
        })

        sub_heading = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 13,
            'bottom': 2, 'bottom_color': '#000000',
        })

        filter_head = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 13,
            'border': 1, 'bg_color': '#d6dbe1', 'border_color': '#000000'
        })

        filter_body = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 13
        })

        side_heading_sub = workbook.add_format({
            'align': 'left', 'bold': True, 'font_size': 11,
            'border': 1, 'border_color': '#000000'
        })
        side_heading_sub.set_indent(1)

        txt_name = workbook.add_format({
            'font_size': 11, 'border': 1
        })
        txt_name.set_indent(2)
        secend_seb_heading = workbook.add_format({
            'align': 'left', 'bold': True, 'font_size': 13, 'bg_color': '#d6dbe1',
        })
        num_format = workbook.add_format({
            'font_size': 13, 'border': 1, 'font_color': '#606060', 'num_format': '#,##0.00', 'align': 'left',
            'bold': True, 'bg_color': '#d6dbe1'
        })
        company_txt = workbook.add_format(
            {'align': 'left', 'valign': 'vcenter', 'bold': True,
             'font_size': 15, }
        )
        company_txt_last = workbook.add_format(
            {'align': 'left', 'valign': 'vcenter', 'bold': True,'bottom': 2, 'bottom_color': '#000000',
             'font_size': 15, }
        )
        # Set column widths
        sheet.set_column(0, 0, 50)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)

        # Write headers and filters
        col = 0
        #company info
        sheet.write(0, 0, 'Company name', company_txt)
        sheet.write(1, 0, 'Address', company_txt)
        sheet.write(2, 0, 'Vat', company_txt_last)

        sheet.merge_range(0, 1, 0, 5, company_name, company_txt)
        sheet.merge_range(1, 1, 1, 5, company_street, company_txt)
        sheet.merge_range(2, 1, 2, 5, company_vat, company_txt_last)

        sheet.write(4, 0, report_name, head)
        sheet.write('B6:B6', 'Date Range', filter_head)
        sheet.write('B7:B7', 'Partners', filter_head)
        sheet.write('B8:B8', 'Accounts', filter_head)
        sheet.write('B9:B9', 'Options', filter_head)

        if start_date or end_date:
            sheet.merge_range('C6:G6', f"{start_date} to {end_date}", filter_body)

        if data['filters']['partner']:
            display_names = [partner.get('display_name', 'undefined') for partner in data['filters']['partner']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C7:G7', display_names_str, filter_body)

        if data['filters']['account']:
            account_keys = list(data['filters']['account'].keys())
            account_keys_str = ', '.join(account_keys)
            sheet.merge_range('C8:G8', account_keys_str, filter_body)

        if data['filters']['options']:
            option_keys = list(data['filters']['options'].keys())
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C9:G9', option_keys_str, filter_body)

        # Define a helper function to format numbers with thousand separators
        def format_number(value):
            if value is None:
                return "0.00"
            return "{:,.2f}".format(float(value))

        # Process partner data
        if data and report_action == 'dynamic_accounts_report.action_partner_ledger':
            sheet.write(10, col, ' ')
            sheet.write(10, col + 1, 'JNRL', sub_heading)
            sheet.write(10, col + 2, 'Account', sub_heading)
            sheet.merge_range('D11:E11', 'Ref', sub_heading)
            sheet.merge_range('F11:G11', 'Due Date', sub_heading)
            sheet.merge_range('H11:I11', 'Debit', sub_heading)
            sheet.merge_range('J11:K11', 'Credit', sub_heading)
            sheet.merge_range('L11:M11', 'Balance', sub_heading)

            row = 10
            # Ensure data['partners'] is iterable; default to empty list if None
            partners = data.get('partners', []) or []
            for partner in partners:
                row += 1
                # Format partner totals
                total_debit = data['total'][partner]['total_debit'] if data['total'] and partner in data['total'] else 0
                total_credit = data['total'][partner]['total_credit'] if data['total'] and partner in data[
                    'total'] else 0
                balance = total_debit - total_credit

                sheet.write(row, col, partner, secend_seb_heading)
                sheet.write(row, col + 1, ' ', secend_seb_heading)
                sheet.write(row, col + 2, ' ', secend_seb_heading)
                sheet.merge_range(row, col + 3, row, col + 4, ' ', secend_seb_heading)
                sheet.merge_range(row, col + 5, row, col + 6, ' ', secend_seb_heading)
                sheet.merge_range(row, col + 7, row, col + 8, format_number(total_debit), num_format)
                sheet.merge_range(row, col + 9, row, col + 10, format_number(total_credit), num_format)
                sheet.merge_range(row, col + 11, row, col + 12, format_number(balance), num_format)

                # Handle initial balance
                initial_balance = data['total'][partner]['initial_balance'] if data['total'] and partner in data[
                    'total'] else 0
                if initial_balance != 0:
                    row += 1
                    initial_debit = data['total'][partner]['initial_debit'] if data['total'] and partner in data[
                        'total'] else 0
                    initial_credit = data['total'][partner]['initial_credit'] if data['total'] and partner in data[
                        'total'] else 0

                    sheet.write(row, col, '', txt_name)
                    sheet.write(row, col + 1, ' ', txt_name)
                    sheet.write(row, col + 2, ' ', txt_name)
                    sheet.merge_range(row, col + 3, row, col + 4, 'Initial Balance', txt_name)
                    sheet.merge_range(row, col + 5, row, col + 6, ' ', txt_name)
                    sheet.merge_range(row, col + 7, row, col + 8, format_number(initial_debit), txt_name)
                    sheet.merge_range(row, col + 9, row, col + 10, format_number(initial_credit), txt_name)
                    sheet.merge_range(row, col + 11, row, col + 12, format_number(initial_balance), txt_name)

                # Process move lines for the partner
                for rec in data['data'][partner]:
                    row += 1
                    sheet.write(row, col, rec[0]['date'], txt_name)
                    sheet.write(row, col + 1, rec[0]['jrnl'], txt_name)
                    sheet.write(row, col + 2, rec[0]['code'], txt_name)
                    sheet.merge_range(row, col + 3, row, col + 4, rec[0]['move_name'], txt_name)
                    sheet.merge_range(row, col + 5, row, col + 6, rec[0]['date_maturity'] or '', txt_name)
                    sheet.merge_range(row, col + 7, row, col + 8, format_number(rec[0]['debit']), txt_name)
                    sheet.merge_range(row, col + 9, row, col + 10, format_number(rec[0]['credit']), txt_name)
                    sheet.merge_range(row, col + 11, row, col + 12, ' ', txt_name)

            # Grand totals
            row += 1
            # Ensure grand_total values are numbers
            grand_total_debit = data['grand_total']['total_debit'] if data['grand_total'] and data['grand_total'][
                'total_debit'] is not None else 0
            grand_total_credit = data['grand_total']['total_credit'] if data['grand_total'] and data['grand_total'][
                'total_credit'] is not None else 0
            grand_balance = grand_total_debit - grand_total_credit

            sheet.merge_range(row, col, row, col + 6, 'Total', filter_head)
            sheet.merge_range(row, col + 7, row, col + 8, format_number(grand_total_debit), num_format)
            sheet.merge_range(row, col + 9, row, col + 10, format_number(grand_total_credit), num_format)
            sheet.merge_range(row, col + 11, row, col + 12, format_number(grand_balance), num_format)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
