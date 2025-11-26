# Odoo 18 Community - Bank Fees Management Module

## Overview
This module extends Odoo 18 Community Edition to provide a robust solution for managing bank fees associated with payment transactions. It allows users to specify bank fees during payment registration and automatically generates the corresponding accounting entries, ensuring accurate financial records.

## Features
- **Bank Fees Account in Journal**: Add a dedicated field in the `account.journal` model to link a specific bank fees account to each bank journal.
- **Bank Fees Amount in Payment**: Introduce a field in the `account.payment` model to capture the bank fees amount during payment registration.
- **Automated Accounting Entries**: Automatically adjust the payment entry and create a separate line for bank fees, debiting the specified bank fees account and crediting the bank account.

## Installation
1.  **Clone/Download the Module**: Place the `bank_fees_management` folder into your Odoo custom addons path.
2.  **Update Odoo Modules List**: Go to `Apps` -> `Update Apps List` (you might need to activate Developer Mode first).
3.  **Install the Module**: Search for "Bank Fees Management" in the Apps list and click `Install`.

## Configuration
1.  **Configure Bank Journal**: Navigate to `Accounting` -> `Configuration` -> `Journals`. Open your bank journal (e.g., "Bank").
2.  **Set Bank Fees Account**: In the journal form, you will find a new field called "Bank Fees Account". Select the appropriate expense account for bank fees (e.g., "Bank Charges").

## Usage
1.  **Register a Payment**: When registering a payment (either from an invoice or directly from the Payments menu), select a bank journal.
2.  **Enter Bank Fees Amount**: A new field "Bank Fees Amount" will appear. Enter the amount of bank fees charged for this transaction.
3.  **Confirm Payment**: Upon confirming the payment, the system will automatically create the accounting entries as follows:
    -   Debit: Customer Account (Full Invoice Amount)
    -   Credit: Bank Account (Invoice Amount - Bank Fees Amount)
    -   Credit: Bank Fees Account (Bank Fees Amount)

## Example
If an invoice is 450 SAR and bank fees are 30 SAR:
-   Customer Account: Debit 450 SAR
-   Bank Account: Credit 420 SAR
-   Bank Fees Account: Credit 30 SAR

## Technical Details
-   **Models Extended**:
    -   `account.journal`: Added `bank_fees_account_id` (Many2one to `account.account`)
    -   `account.payment`: Added `bank_fees_amount` (Monetary) and `bank_fees_account_id` (Computed Many2one)
-   **Views Modified**:
    -   `account.journal.form`: Added `bank_fees_account_id` field.
    -   `account.payment.form`: Added `bank_fees_amount` and `bank_fees_account_id` fields, visible only for bank journals.
-   **Business Logic**: Overrode `_prepare_payment_moves` method in `account.payment` to adjust journal entries.

## Author
Your Name

## License
LGPL-3


