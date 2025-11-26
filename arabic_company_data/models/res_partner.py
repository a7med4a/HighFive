from odoo import models, api, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    english_address = fields.Char(string="English Address", required=False)
    english_city = fields.Char(string="English City", required=False)
    english_country = fields.Char(string="English Country", required=False)
    english_name = fields.Char(string="English Name", required=False)
    english_street2 = fields.Char(string="English Street2", required=False)
