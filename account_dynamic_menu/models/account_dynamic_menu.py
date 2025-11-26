from odoo import models, api, _
from odoo.exceptions import UserError

class AccountAccount(models.Model):
    _inherit = 'account.account'

    def create_separate_menu(self):
        """Create a submenu under the root 'حركات الحسابات الشائعة' for each account.
        - Avoid creating duplicate menus with the same name under the same parent.
        - Create an action with domain limited to the account.
        - Pass default_account_id in context so create form is prefilled.
        """
        parent_xmlid = 'account_dynamic_menu.menu_common_account_moves_root'
        try:
            parent_menu = self.env.ref(parent_xmlid)
        except ValueError:
            raise UserError(_('Parent menu ({} ) was not found. Make sure the XML that creates it is installed.').format(parent_xmlid))

        for account in self:
            menu_name = account.name or ('Account %s' % account.id)

            # Prevent duplicate menus with same name and parent
            existing = self.env['ir.ui.menu'].search([
                ('name', '=', menu_name),
                ('parent_id', '=', parent_menu.id)
            ], limit=1)
            if existing:
                # Update its action domain if needed and continue
                action = existing.action and getattr(existing.action, 'id', False)
                if action:
                    act = self.env['ir.actions.act_window'].browse(action)
                    act.write({
                        'res_model': 'account.move.line',
                        'view_mode': 'list,form',
                        'domain': [('account_id', '=', account.id)],
                        'context': {'default_account_id': account.id}
                    })
                continue

            # Create action
            action_vals = {
                'name': menu_name,
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.line',
                'view_mode': 'list,form',
                'domain': [('account_id', '=', account.id)],
                'context': "{'default_account_id': %d}" % account.id,
            }
            action = self.env['ir.actions.act_window'].create(action_vals)

            # Create the submenu pointing to the action
            self.env['ir.ui.menu'].create({
                'name': menu_name,
                'parent_id': parent_menu.id,
                'action': 'ir.actions.act_window,%d' % action.id,
            })
        return True

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        default_acc = self._context.get('default_account_id')
        if default_acc:
            res['account_id'] = default_acc
        return res
