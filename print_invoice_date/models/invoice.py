from odoo import api, fields, models
from odoo.tools import float_repr
import base64
from num2words import num2words
from odoo import api, fields, models, _
from odoo.tools.misc import clean_context, get_lang


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # إضافة الحقل المفقود الذي يتطلبه l10n_gcc_invoice
    extra_fees = fields.Monetary(
        string="Extra Fees",
        currency_field="currency_id",
        default=0.0,
        help="Additional fees for this line",
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_sa_qr_code_str = fields.Char(
        string="Zatka QR Code", compute="_compute_qr_code_str"
    )
    company_bank_account_id = fields.Many2one(
        string="Company Bank Account",
        comodel_name="res.partner.bank",
        help="The IBAN account number to use for Company Bank Account. Leave blank if you don't use Company Bank Account.",
    )

    @api.depends("company_id")
    def _compute_bank_account_domain(self):
        for record in self:
            if record.company_id:
                record.company_bank_account_id_domain = [
                    ("id", "in", record.company_id.partner_id.bank_ids.ids)
                ]
            else:
                record.company_bank_account_id_domain = []

    company_bank_account_id_domain = fields.Char(
        compute="_compute_bank_account_domain", invisible=True
    )

    def action_print_inv(self):
        self.ensure_one()
        return self.env.ref(
            "print_invoice_date.action_report_jes_inv_date"
        ).report_action(self)

    def action_print_bill_of_entry(self):
        self.ensure_one()
        return self.env.ref(
            "print_invoice_date.action_report_jes_bill_of_entry"
        ).report_action(self)

    def action_print_journal_entry(self):
        self.ensure_one()
        return self.env.ref(
            "print_invoice_date.action_print_journal_entry_report"
        ).report_action(self)

    @api.depends(
        "amount_total_signed",
        "amount_tax_signed",
        "l10n_sa_confirmation_datetime",
        "company_id",
        "invoice_date",
        "company_id.vat",
    )
    def _compute_qr_code_str(self):
        """Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
        https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
        """

        def get_qr_encoding(tag, field):
            company_name_byte_array = field.encode()
            company_name_tag_encoding = tag.to_bytes(length=1, byteorder="big")
            company_name_length_encoding = len(company_name_byte_array).to_bytes(
                length=1, byteorder="big"
            )
            return (
                company_name_tag_encoding
                + company_name_length_encoding
                + company_name_byte_array
            )

        for record in self:
            qr_code_str = ""
            if record.invoice_date and record.company_id.vat:
                seller_name_enc = get_qr_encoding(1, record.company_id.display_name)
                company_vat_enc = get_qr_encoding(2, record.company_id.vat)
                time_sa = record.invoice_date
                timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
                invoice_total_enc = get_qr_encoding(
                    4, float_repr(abs(record.amount_total_signed), 2)
                )
                total_vat_enc = get_qr_encoding(
                    5, float_repr(abs(record.amount_tax_signed), 2)
                )

                str_to_encode = (
                    seller_name_enc
                    + company_vat_enc
                    + timestamp_enc
                    + invoice_total_enc
                    + total_vat_enc
                )
                qr_code_str = base64.b64encode(str_to_encode).decode()
            record.l10n_sa_qr_code_str = qr_code_str
