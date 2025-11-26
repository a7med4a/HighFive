# -*- coding: utf-8 -*-

from odoo import api, fields, models, _



class TermsAndConditions(models.Model):
    _name = 'terms.and.conditions'
    _description = 'Terms and Conditions'

    name = fields.Char()
    description = fields.Html("Description")
    sit_is_default = fields.Boolean("Is Default")