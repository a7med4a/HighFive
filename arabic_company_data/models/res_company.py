from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    arabic_city = fields.Char(string="Arabic City", required=False)
    arabic_contact = fields.Char(string="Arabic Contact", required=False)
    arabic_contact_2 = fields.Char(string="Arabic Contact 2", required=False)
    arabic_country = fields.Char(string="Arabic Country", required=False)
    arabic_street = fields.Char(string="Arabic Street", required=False)
    arabic_street_2 = fields.Char(string="Arabic Street 2", required=False)
    english_contact = fields.Char(string="English Contact", required=False)
