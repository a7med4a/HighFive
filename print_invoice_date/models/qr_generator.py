#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولد رمز QR للفواتير الضريبية السعودية
يتوافق مع متطلبات هيئة الزكاة والضريبة والجمارك السعودية (ZATCA)
"""

import qrcode
import base64
from io import BytesIO
import struct
from datetime import datetime


class SaudiInvoiceQRGenerator:
    """
    مولد رمز QR للفواتير الضريبية السعودية
    """

    def __init__(self):
        self.tags = {
            "seller_name": 1,  # اسم البائع
            "vat_number": 2,  # الرقم الضريبي
            "timestamp": 3,  # الطابع الزمني
            "invoice_total": 4,  # إجمالي الفاتورة
            "vat_total": 5,  # إجمالي ضريبة القيمة المضافة
        }

    def _encode_tlv(self, tag, value):
        """
        ترميز البيانات بتنسيق TLV (Tag-Length-Value)
        """
        if isinstance(value, str):
            value_bytes = value.encode("utf-8")
        else:
            value_bytes = str(value).encode("utf-8")

        length = len(value_bytes)
        return struct.pack("B", tag) + struct.pack("B", length) + value_bytes

    def generate_qr_data(
        self, seller_name, vat_number, timestamp, invoice_total, vat_total
    ):
        """
        توليد بيانات QR Code للفاتورة الضريبية

        Args:
            seller_name (str): اسم البائع
            vat_number (str): الرقم الضريبي
            timestamp (str): الطابع الزمني بتنسيق ISO
            invoice_total (float): إجمالي الفاتورة
            vat_total (float): إجمالي ضريبة القيمة المضافة

        Returns:
            str: البيانات المرمزة بـ Base64
        """
        tlv_data = b""

        # إضافة البيانات المطلوبة
        tlv_data += self._encode_tlv(self.tags["seller_name"], seller_name)
        tlv_data += self._encode_tlv(self.tags["vat_number"], vat_number)
        tlv_data += self._encode_tlv(self.tags["timestamp"], timestamp)
        tlv_data += self._encode_tlv(self.tags["invoice_total"], f"{invoice_total:.2f}")
        tlv_data += self._encode_tlv(self.tags["vat_total"], f"{vat_total:.2f}")

        # ترميز البيانات بـ Base64
        return base64.b64encode(tlv_data).decode("utf-8")

    def generate_qr_code(
        self,
        seller_name,
        vat_number,
        timestamp,
        invoice_total,
        vat_total,
        size=10,
        border=4,
    ):
        """
        توليد رمز QR للفاتورة الضريبية

        Args:
            seller_name (str): اسم البائع
            vat_number (str): الرقم الضريبي
            timestamp (str): الطابع الزمني
            invoice_total (float): إجمالي الفاتورة
            vat_total (float): إجمالي ضريبة القيمة المضافة
            size (int): حجم QR Code
            border (int): حجم الحدود

        Returns:
            str: QR Code كـ Base64 string
        """
        # توليد بيانات QR
        qr_data = self.generate_qr_data(
            seller_name, vat_number, timestamp, invoice_total, vat_total
        )

        # إنشاء QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=border,
        )

        qr.add_data(qr_data)
        qr.make(fit=True)

        # إنشاء الصورة
        img = qr.make_image(fill_color="black", back_color="white")

        # تحويل إلى Base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return img_str

    def generate_qr_for_odoo(
        self, company_name, vat_number, invoice_date, total_amount, vat_amount
    ):
        """
        توليد QR Code خاص بنظام أودو

        Args:
            company_name (str): اسم الشركة
            vat_number (str): الرقم الضريبي
            invoice_date (str): تاريخ الفاتورة
            total_amount (float): المبلغ الإجمالي
            vat_amount (float): مبلغ ضريبة القيمة المضافة

        Returns:
            str: QR Code كـ data URI
        """
        # تحويل التاريخ إلى تنسيق ISO
        if isinstance(invoice_date, str):
            try:
                date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
                timestamp = date_obj.isoformat() + "Z"
            except:
                timestamp = datetime.now().isoformat() + "Z"
        else:
            timestamp = datetime.now().isoformat() + "Z"

        # توليد QR Code
        qr_base64 = self.generate_qr_code(
            seller_name=company_name,
            vat_number=vat_number,
            timestamp=timestamp,
            invoice_total=float(total_amount),
            vat_total=float(vat_amount),
        )

        return f"data:image/png;base64,{qr_base64}"


def test_qr_generator():
    """
    اختبار مولد QR Code
    """
    generator = SaudiInvoiceQRGenerator()

    # بيانات تجريبية
    test_data = {
        "company_name": "شركة الجريسي للخدمات الإلكترونية",
        "vat_number": "300001234567890",
        "invoice_date": "2024-12-08",
        "total_amount": 1150.00,
        "vat_amount": 150.00,
    }

    # توليد QR Code
    qr_data_uri = generator.generate_qr_for_odoo(**test_data)

    print("تم توليد QR Code بنجاح!")
    print(f"طول البيانات: {len(qr_data_uri)} حرف")
    print(f"أول 100 حرف: {qr_data_uri[:100]}...")

    return qr_data_uri


if __name__ == "__main__":
    test_qr_generator()
