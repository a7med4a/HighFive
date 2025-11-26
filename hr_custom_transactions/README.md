# HR Custom Transactions Module for Odoo 18 Community (Updated)

## Overview

This Odoo 18 Community module provides custom functionalities to manage freelance services, employee deductions, and employee bonuses. It integrates with existing HR and HR Contract modules to calculate values based on employee contracts. This updated version includes a workflow (Draft, Confirmed, Cancelled) for each transaction type and full Arabic translation.

## Features

*   **Freelance Services:** Record services provided by employees, calculate total value based on hourly rates from contracts. Includes a workflow with states: Draft, Confirmed, Cancelled.
*   **Employee Deductions:** Record deductions for employees, calculate deduction value based on salary and unit type (days/hours). Includes a workflow with states: Draft, Confirmed, Cancelled.
*   **Employee Bonuses:** Record bonuses for employees, calculate bonus value based on salary and unit type (days/hours). Includes a workflow with states: Draft, Confirmed, Cancelled.
*   **Arabic Translation:** Full Arabic translation for all module elements.
*   **Mail Activity & Followers:** Integrated mail activity and followers for better communication and tracking on each record.

## Installation

1.  **Download the Module:** Download the `hr_custom_transactions` folder.
2.  **Place in Odoo Addons Path:** Copy the `hr_custom_transactions` folder into your Odoo custom addons path (e.g., `/opt/odoo/custom_addons/`).
3.  **Update Odoo Addons List:**
    *   Log in to Odoo as an administrator.
    *   Activate Developer Mode (Settings -> Developer Tools -> Activate the developer mode).
    *   Go to Apps -> Update Apps List.
4.  **Install the Module:**
    *   Go to Apps.
    *   Search for "HR Custom Transactions".
    *   Click the "Install" button.

## Usage

After installation, a new top-level menu item named "HR Custom Transactions" will appear. Under this menu, you will find three sub-menus:

*   **Freelance Services:** To record and manage freelance work.
*   **Employee Deductions:** To record and manage employee deductions.
*   **Employee Bonuses:** To record and manage employee bonuses.

Each record in these screens will now have a workflow with "Draft", "Confirmed", and "Cancelled" states, along with corresponding buttons to manage these states.

## Testing

To test the module, follow these steps:

1.  **Ensure Dependencies:** Make sure `hr`, `hr_contract`, and `mail` modules are installed in your Odoo instance.
2.  **Create Employees and Contracts:**
    *   Go to Human Resources -> Employees and create a new employee.
    *   Go to Human Resources -> Contracts and create a contract for the employee, ensuring a `wage` and `resource_calendar_id` (working hours) are set.
3.  **Test Freelance Services:**
    *   Navigate to HR Custom Transactions -> Freelance Services.
    *   Create a new record.
    *   Select an employee with an active contract.
    *   Enter a `Request Date`, `Service Description`, and `Number of Hours`.
    *   Verify that `Total Value` is calculated automatically based on the employee's contract hourly rate.
    *   Test the workflow buttons: "Confirm", "Cancel", and "Set to Draft". Observe how the record state changes and fields become read-only.
4.  **Test Employee Deductions:**
    *   Navigate to HR Custom Transactions -> Employee Deductions.
    *   Create a new record.
    *   Select an employee with an active contract.
    *   Enter a `Request Date`, `Reason for Deduction`, `Unit Type` (Days/Hours), and `Count`.
    *   Verify that `Deduction Value` is calculated automatically based on the employee's monthly salary.
    *   Test the workflow buttons: "Confirm", "Cancel", and "Set to Draft".
5.  **Test Employee Bonuses:**
    *   Navigate to HR Custom Transactions -> Employee Bonuses.
    *   Create a new record.
    *   Select an employee with an active contract.
    *   Enter a `Request Date`, `Reason for Bonus`, `Unit Type` (Days/Hours), and `Count`.
    *   Verify that `Bonus Value` is calculated automatically based on the employee's monthly salary.
    *   Test the workflow buttons: "Confirm", "Cancel", and "Set to Draft".
6.  **Test Arabic Translation:** Change your Odoo user language to Arabic and verify that all module elements are translated correctly.

## Author

Manus AI

