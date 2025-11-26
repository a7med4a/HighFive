# -*- coding: utf-8 -*-

from odoo import models, fields, api
import qrcode
import base64
from io import BytesIO
import struct
from datetime import datetime


class AccountMove(models.Model):
    _inherit = "account.move"

    qr_code_image = fields.Binary(string="QR Code", compute="_compute_qr_code")
    qr_code_data = fields.Text(string="QR Code Data", compute="_compute_qr_code")

    def _encode_tlv(self, tag, value):
        """
        ترميز البيانات بتنسيق TLV (Tag-Length-Value) للمعايير السعودية
        """
        if isinstance(value, str):
            value_bytes = value.encode("utf-8")
        else:
            value_bytes = str(value).encode("utf-8")

        length = len(value_bytes)
        return struct.pack("B", tag) + struct.pack("B", length) + value_bytes

    def _generate_saudi_qr_data(self):
        """
        توليد بيانات QR Code وفقاً لمعايير هيئة الزكاة والضريبة والجمارك السعودية
        """
        # التأكد من أن الفاتورة من النوع الصحيح
        if self.move_type not in ["out_invoice", "out_refund"]:
            return False

        # البيانات المطلوبة للـ QR Code
        seller_name = self.company_id.name or ""
        vat_number = self.company_id.vat or ""

        # تحويل التاريخ إلى تنسيق ISO
        if self.invoice_date:
            timestamp = self.invoice_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        invoice_total = float(self.amount_total)
        vat_total = float(self.amount_tax)

        # ترميز البيانات بتنسيق TLV
        tlv_data = b""
        tlv_data += self._encode_tlv(1, seller_name)  # اسم البائع
        tlv_data += self._encode_tlv(2, vat_number)  # الرقم الضريبي
        tlv_data += self._encode_tlv(3, timestamp)  # الطابع الزمني
        tlv_data += self._encode_tlv(4, f"{invoice_total:.2f}")  # إجمالي الفاتورة
        tlv_data += self._encode_tlv(
            5, f"{vat_total:.2f}"
        )  # إجمالي ضريبة القيمة المضافة

        # ترميز البيانات بـ Base64
        return base64.b64encode(tlv_data).decode("utf-8")

    @api.depends("company_id", "invoice_date", "amount_total", "amount_tax")
    def _compute_qr_code(self):
        """
        حساب QR Code للفاتورة
        """
        for record in self:
            try:
                # توليد بيانات QR
                qr_data = record._generate_saudi_qr_data()

                if qr_data:
                    # إنشاء QR Code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )

                    qr.add_data(qr_data)
                    qr.make(fit=True)

                    # إنشاء الصورة
                    img = qr.make_image(fill_color="black", back_color="white")

                    # تحويل إلى Base64
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    img_str = base64.b64encode(buffer.getvalue())

                    record.qr_code_image = img_str
                    record.qr_code_data = qr_data
                else:
                    record.qr_code_image = False
                    record.qr_code_data = False

            except Exception as e:
                record.qr_code_image = False
                record.qr_code_data = False

    def generate_saudi_qr_code(self):
        """
        دالة لتوليد QR Code كـ data URI للاستخدام في التقارير
        """
        try:
            if self.qr_code_image:
                return f"data:image/png;base64,{self.qr_code_image.decode('utf-8')}"
            else:
                return False
        except:
            return False

    def get_qr_code_base64(self):
        """
        إرجاع QR Code كـ Base64 string
        """
        try:
            if self.qr_code_image:
                return self.qr_code_image.decode("utf-8")
            else:
                return False
        except:
            return False
