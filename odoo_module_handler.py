# -*- coding: utf-8 -*-
# Server Connection Parameters
HOST = "http://167.71.241.12:8070"  # Odoo server address
DB = "HighFive-Test"            # Database name
USERNAME = "admin"            # Odoo username
PASSWORD = "Admin2025"  # Odoo password

# Localhost Connection Parameters

# HOST = "http://localhost:9018/"  # Odoo server address
# DB = "ASw12-10"            # Database name
# USERNAME = "admin"            # Odoo username
# PASSWORD = "Admin@2025"

# List of modules to handle
MODULES_TO_HANDLE = [
    "base_account_budget",
    "base_accounting_kit",
    "custom_partner",
    "easy_expense",
    "highfive_api_connector",
    "highfive_core",
    "hr_employee_updation",
    "hr_payroll_account_community",
    "hr_payroll_community",
    "hr_payslip_monthly_report",
    "ohrms_loan",
    "ohrms_loan_accounting",
    "ohrms_salary_advance",
    "print_invoice_date",
    "sale_custom",
]


import xmlrpc.client
import logging
import time
import os

class OdooModuleUpdater:
    def __init__(self, host, db, username, password):
        """Initialize connection to Odoo"""
        # Ensure proper URL formatting
        self.url = f'http://{host}' if not host.startswith(('http://', 'https://')) else host
        self.db = db
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
        # XML-RPC endpoints with proper URL formatting
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

        # Authenticate
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})

    def handle_module(self, module_name):
        """Handle a specific module: install if not installed, upgrade if installed"""
        try:
            # Search for the module and get its state
            module_data = self.models.execute_kw(
                self.db, self.uid, self.password,
                'ir.module.module', 'search_read',
                [[['name', '=', module_name]]],
                {'fields': ['state'], 'limit': 1}
            )

            if not module_data:
                self.logger.error(f"Module '{module_name}' not found!")
                return False, "Not Found"

            state = module_data[0]['state']
            module_id = module_data[0]['id']

            if state == 'installed':
                # Trigger module upgrade
                self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'ir.module.module', 'button_immediate_upgrade',
                    [[module_id]]
                )
                self.logger.info(f"Module '{module_name}' upgrade triggered successfully")
                return True, "Upgraded"
            elif state in ['uninstalled', 'to install', 'to upgrade']:
                # Trigger module install
                self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'ir.module.module', 'button_immediate_install',
                    [[module_id]]
                )
                self.logger.info(f"Module '{module_name}' install triggered successfully")
                return True, "Installed"
            else:
                self.logger.warning(f"Module '{module_name}' in unexpected state: {state}")
                return False, f"Unexpected State: {state}"

        except Exception as e:
            self.logger.error(f"Error handling module '{module_name}': {str(e)}")
            return False, str(e)

    def handle_modules(self, module_list):
        """Handle multiple modules"""
        results = {}
        for module in module_list:
            print(f"Handling module: {module}")
            success, status = self.handle_module(module)
            results[module] = {'success': success, 'status': status}
            time.sleep(2)  # Add delay between operations
        return results

# Usage example
if __name__ == "__main__":
    # Initialize updater
    updater = OdooModuleUpdater(HOST, DB, USERNAME, PASSWORD)
    print("updater", updater)

    # Configuration
    base_path = ''
    translate_path = False
    translate_module = False
    translate_module_name = ''

    print(f"\nProcessing modules: {MODULES_TO_HANDLE}")

    if translate_path:
        print("Processing all modules in path...")
        for folder_name in os.listdir(base_path):
            folder_path = os.path.join(base_path, folder_name)
            manifest_path = os.path.join(folder_path, '__manifest__.py')
            # Check if it's a directory and contains a manifest file
            if os.path.isdir(folder_path) and os.path.exists(manifest_path):
                MODULES_TO_HANDLE.append(folder_name)

    if translate_module:
        print(f"\nProcessing specific module: {translate_module_name}")
        MODULES_TO_HANDLE.append(translate_module_name)

    # Handle modules
    results = updater.handle_modules(MODULES_TO_HANDLE)

    # Print results
    print("\nHandle Results:")
    for module, info in results.items():
        print(f"{module}: {'Success' if info['success'] else 'Failed'} - {info['status']}")