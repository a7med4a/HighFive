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
import calendar
from dateutil.relativedelta import relativedelta
import xlsxwriter
from odoo import api, fields, models
from datetime import datetime
from odoo.tools import date_utils


class AccountGeneralLedger(models.TransientModel):
    """For creating General Ledger report"""

    _name = "account.general.ledger"
    _description = "General Ledger Report"

    @api.model
    def view_report(self, option, tag):
        """
        Retrieve partner ledger report data based on options and tags.

        :param option: The options to filter the report data.
        :type option: str

        :param tag: The tag to filter the report data.
        :type tag: str

        :return: A dictionary containing the partner ledger report data.
        :rtype: dict
        """
        account_dict = {}
        account_totals = {}
        move_line_ids = self.env["account.move.line"].search(
            [("parent_state", "=", "posted")]
        )
        account_ids = move_line_ids.mapped("account_id").sorted(key=lambda acc: acc.code)
        account_dict["journal_ids"] = self.env["account.journal"].search_read(
            [], ["name"]
        )
        account_dict["analytic_ids"] = self.env["account.analytic.account"].search_read(
            [], ["name"]
        )
        for account in account_ids:
            move_line_id = move_line_ids.filtered(lambda x: x.account_id == account)
            move_line_list = []
            for move_line in move_line_id:
                move_line_data = move_line.read(
                    [
                        "date",
                        "name",
                        "move_name",
                        "debit",
                        "credit",
                        "partner_id",
                        "account_id",
                        "journal_id",
                        "move_id",
                        "analytic_line_ids",
                    ]
                )
                move_line_list.append(move_line_data)
            account_dict[account.display_name] = move_line_list
            currency_id = self.env.company.currency_id.symbol
            account_totals[account.display_name] = {
                "total_debit": round(sum(move_line_id.mapped("debit")), 2),
                "total_credit": round(sum(move_line_id.mapped("credit")), 2),
                "currency_id": currency_id,
                "account_id": account.id,
            }
            account_dict["account_totals"] = account_totals
        return account_dict

    @api.model
    def get_filter_values(self, journal_id, date_range, options, analytic, method, search_value):
        """
        Retrieve filtered values for the partner ledger report.

        :param journal_id: The journal IDs to filter the report data.
        :type journal_id: list

        :param date_range: The date range option to filter the report data.
        :type date_range: str or dict

        :param options: The additional options to filter the report data.
        :type options: dict

        :param method: Find the method
        :type options: dict

        :param analytic: The analytic IDs to filter the report data.
        :type analytic: list

        :return: A dictionary containing the filtered values for the partner
        ledger report.
        :rtype: dict
        """
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
        domain = (
            [
                ("journal_id", "in", journal_id),
                ("parent_state", "in", option_domain),
            ]
            if journal_id
            else [
                ("parent_state", "in", option_domain),
            ]
        )
        if method == {}:
            method = None
        if method is not None and "cash" in method:
            domain += [
                ("journal_id", "in", self.env.company.tax_cash_basis_journal_id.ids),
            ]
        if analytic:
            analytic_line = (
                self.env["account.analytic.line"]
                .search([("account_id", "in", analytic)])
                .mapped("id")
            )
            domain += [("analytic_line_ids", "in", analytic_line)]
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
            elif "start_date" in date_range and "end_date" in date_range:
                start_date = datetime.strptime(
                    date_range["start_date"], "%Y-%m-%d"
                ).date()
                end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d").date()
                domain += [("date", ">=", start_date), ("date", "<=", end_date)]
            elif "start_date" in date_range:
                start_date = datetime.strptime(
                    date_range["start_date"], "%Y-%m-%d"
                ).date()
                domain += [("date", ">=", start_date)]
            elif "end_date" in date_range:
                end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d").date()
                domain += [("date", "<=", end_date)]
        move_line_ids = self.env["account.move.line"].search(domain)
        account_ids = move_line_ids.mapped("account_id").sorted(key=lambda acc: acc.code)
        account_dict["journal_ids"] = self.env["account.journal"].search_read(
            [], ["name"]
        )
        account_dict["analytic_ids"] = self.env["account.analytic.account"].search_read(
            [], ["name"]
        )
        for account in account_ids:
            if search_value and search_value.lower() not in account.display_name.lower():
                continue
            move_line_id = move_line_ids.filtered(lambda x: x.account_id == account)
            move_line_list = []
            for move_line in move_line_id:
                move_line_data = move_line.read(
                    [
                        "date",
                        "name",
                        "move_name",
                        "debit",
                        "credit",
                        "partner_id",
                        "account_id",
                        "journal_id",
                        "move_id",
                        "analytic_line_ids",
                    ]
                )
                move_line_list.append(move_line_data)
            account_dict[account.display_name] = move_line_list
            currency_id = self.env.company.currency_id.symbol
            account_totals[account.display_name] = {
                "total_debit": round(sum(move_line_id.mapped("debit")), 2),
                "total_credit": round(sum(move_line_id.mapped("credit")), 2),
                "currency_id": currency_id,
                "account_id": account.id,
            }
            account_dict["account_totals"] = account_totals
        return account_dict

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an XLSX report based on the provided data and write it to the
        response stream.

        :param data: The data used to generate the report.
        :type data: str (JSON format)

        :param response: The response object to write the generated report to.
        :type response: werkzeug.wrappers.Response

        :param report_name: The name of the report.
        :type report_name: str
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
        start_date = data['filters']['start_date'] if \
            data['filters']['start_date'] else ''
        end_date = data['filters']['end_date'] if \
            data['filters']['end_date'] else ''
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 15
        })

        sub_heading = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 13,
            'bottom': 2, 'bottom_color': '#000000',
        })

        filter_head = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 13,
            'border': 1, 'bg_color': '#d6dbe1',
            'border_color': '#000000'
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
        # Number format with thousand separator
        num_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'num_format': '#,##0.00'
        })
        num_format_sub_heading = workbook.add_format({
            'font_size': 13, 'border': 1, 'font_color': '#606060', 'num_format': '#,##0.00', 'align': 'left',
            'bold': True, 'bg_color': '#d6dbe1',
        })
        num_format.set_indent(2)

        # Number format for totals with background
        total_num_format = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 13,
            'border': 1, 'bg_color': '#d6dbe1', 'font_color': '#606060', 'border_color': '#000000',
            'num_format': '#,##0.00'
        })
        secend_seb_heading = workbook.add_format({
            'align': 'left', 'bold': True, 'font_size': 13, 'bg_color': '#d6dbe1',
        })
        company_txt = workbook.add_format(
            {'align': 'left', 'valign': 'vcenter', 'bold': True,
             'font_size': 15, }
        )
        company_txt_last = workbook.add_format(
            {'align': 'left', 'valign': 'vcenter', 'bold': True,'bottom': 2, 'bottom_color': '#000000',
             'font_size': 15, }
        )
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.set_column(5, 5, 25)
        col = 0
        #company info
        sheet.write(0, 0, 'Company name', company_txt)
        sheet.write(1, 0, 'Address', company_txt)
        sheet.write(2, 0, 'Vat', company_txt_last)

        sheet.merge_range(0, 1, 0, 4, company_name, company_txt)
        sheet.merge_range(1, 1, 1, 4, company_street, company_txt)
        sheet.merge_range(2, 1, 2, 4, company_vat, company_txt_last)

        sheet.write('A5:b5', report_name, head)
        sheet.write('B6:b6', 'Date Range', filter_head)
        sheet.write('B7:b7', 'Journals', filter_head)
        sheet.write('B8:b8', 'Analytic', filter_head)
        sheet.write('B9:b9', 'Options', filter_head)
        if start_date or end_date:
            sheet.merge_range('C6:G6', f"{start_date} to {end_date}",
                              filter_body)
        if data['filters']['journal']:
            display_names = [journal for
                             journal in data['filters']['journal']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C7:G7', display_names_str, filter_body)
        if data['filters']['analytic']:
            display_names = [analytic for
                             analytic in data['filters']['analytic']]
            account_keys_str = ', '.join(display_names)
            sheet.merge_range('C8:G8', account_keys_str, filter_body)
        if data['filters']['options']:
            option_keys = list(data['filters']['options'].keys())
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C9:G9', option_keys_str, filter_body)
        if data:
            if report_action == 'dynamic_accounts_report.action_general_ledger':
                sheet.write(12, col, ' ')
                sheet.write(12, col + 1, 'Date', sub_heading)
                sheet.merge_range('C13:E13', 'Communication', sub_heading)
                sheet.merge_range('F13:G13', 'Partner', sub_heading)
                sheet.merge_range('H13:I13', 'Debit', sub_heading)
                sheet.merge_range('J13:K13', 'Credit', sub_heading)
                sheet.merge_range('L13:M13', 'Balance', sub_heading)
                row = 12
                if data['account']:
                    for account in data['account']:
                        row += 1
                        sheet.write(row, col, account, secend_seb_heading)
                        sheet.write(row, col + 1, ' ', secend_seb_heading)
                        sheet.merge_range(row, col + 2, row, col + 4, ' ', secend_seb_heading)
                        sheet.merge_range(row, col + 5, row, col + 6, ' ',
                                          secend_seb_heading)
                        sheet.merge_range(row, col + 7, row, col + 8,
                                          data['total'][account]['total_debit'],
                                          num_format_sub_heading)
                        sheet.merge_range(row, col + 9, row, col + 10,
                                          data['total'][account]['total_credit'],
                                          num_format_sub_heading)
                        sheet.merge_range(row, col + 11, row, col + 12,
                                          data['total'][account].get('balance_display'),
                                          num_format_sub_heading)
                        for rec in data['data'][account]:
                            row += 1
                            partner = rec[0]['partner_id']
                            name = partner[1] if partner else None
                            sheet.write(row, col, rec[0]['move_name'], txt_name)
                            sheet.write(row, col + 1, rec[0]['date'], txt_name)
                            sheet.merge_range(row, col + 2, row, col + 4,
                                              rec[0]['name'], txt_name)
                            sheet.merge_range(row, col + 5, row, col + 6, name,
                                              txt_name)
                            sheet.merge_range(row, col + 7, row, col + 8,
                                              rec[0]['debit'],
                                              txt_name)
                            sheet.merge_range(row, col + 9, row, col + 10,
                                              rec[0]['credit'], txt_name)
                            sheet.merge_range(row, col + 11, row, col + 12, ' ',
                                              txt_name)
                    row += 1
                    sheet.merge_range(row, col, row, col + 6, 'Total',
                                      filter_head)
                    sheet.merge_range(row, col + 7, row, col + 8,
                                      data['grand_total']['total_debit_display'],
                                      total_num_format)
                    sheet.merge_range(row, col + 9, row, col + 10,
                                      data['grand_total']['total_credit_display'],
                                      total_num_format)
                    sheet.merge_range(row, col + 11, row, col + 12,
                                      float(data['grand_total']['total_debit']) -
                                      float(data['grand_total']['total_credit']),
                                      total_num_format)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
