from odoo import models, api, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    arabic_name = fields.Char(string="Arabic Name", required=False)
