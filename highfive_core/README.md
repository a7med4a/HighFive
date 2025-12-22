# HighFive Core Integration Module

## Overview

This module is the foundation of the HighFive integration system for Odoo 18. It manages the core master data and establishes the infrastructure for tracking operations by supplier and branch.

## Version

**1.1.0** - Enhanced version with tax configuration, commission rates, and improved logging

## Features

### 1. Supplier Management (Partners)
- Unique identification from HighFive system (`highfive_partner_id`)
- Tax status configuration (Standard 15%, Reduced 5%, Zero-rated, Exempt)
- Default commission rates for online and cash bookings
- Automatic creation of parent analytic accounts
- Branch management (one-to-many relationship)

### 2. Customer Management
- Unique identification from HighFive system (`highfive_customer_id`)
- Formerly called "Players" - now standardized as "Customers"
- Separate from suppliers (cannot be both)

### 3. Branch Management
- Physical locations for each supplier
- GPS coordinates support
- Automatic creation of child analytic accounts
- Hierarchical relationship: Supplier → Branch → Units
- Chatter integration for collaboration

### 4. Unit/Service Management
- Products representing bookable services
- Must be of type "Service"
- Must use "Ordered quantities" invoice policy
- Linked to specific branches
- Tracked by supplier and branch

### 5. Analytic Accounting Hierarchy
```
HighFive Operations Plan
└── Supplier - [Partner Name] (Parent Account)
    ├── Branch - [Partner Name] / [Branch 1]
    ├── Branch - [Partner Name] / [Branch 2]
    └── Branch - [Partner Name] / [Branch 3]
```

### 6. Commission Product
- Pre-configured product for HighFive commissions
- Product code: `HF-COMMISSION`
- Used by booking/invoicing module

## Key Changes in v1.1.0

### 1. Renamed "Players" to "Customers"
- All fields renamed: `highfive_player_id` → `highfive_customer_id`
- All flags renamed: `is_highfive_player` → `is_highfive_customer`
- All menus and views updated
- All documentation updated

### 2. Added Tax Configuration
- New field: `tax_status` on partners
- Options: Standard 15%, Reduced 5%, Zero-rated, Exempt
- Used by invoicing module to apply correct VAT

### 3. Added Commission Configuration
- New fields: `commission_rate_online`, `commission_rate_cash`
- Default rates at partner level
- Can be overridden at unit level

### 4. Enhanced Logging
- Comprehensive logging throughout the module
- INFO level for important operations
- DEBUG level for detailed traces
- ERROR level for failures

### 5. Improved Constraints
- Product invoice policy validation
- Commission rate validation (0-100%)
- Enhanced error messages

### 6. Enhanced UI/UX
- Branch count stat button
- Better help text
- Improved form layouts
- Added kanban views
- Enhanced search capabilities

### 7. Better Access Rights
- Three-tier access control:
  - Users: Read-only
  - Account Managers: Read/Write
  - System: Full control

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list: `Apps > Update Apps List`
3. Install the module: `Apps > Search "HighFive Core" > Install`

## Dependencies

- `base` - Odoo Base
- `product` - Product Management
- `analytic` - Analytic Accounting
- `account` - Accounting

## Configuration

### After Installation

1. **Review Analytic Plan**
   - Go to: HighFive Operations > Configuration > Analytic Plans
   - Verify "HighFive Operations" plan exists

2. **Commission Product**
   - Go to: HighFive Operations > Services > Units
   - Search for code: `HF-COMMISSION`
   - Verify it exists and is active

3. **Create First Supplier**
   - Go to: HighFive Operations > Suppliers > Suppliers
   - Click "Create"
   - Fill in required fields
   - Check "HighFive Partner"
   - Set tax status
   - Optionally set default commission rates
   - Save → Analytic account auto-created

4. **Create First Branch**
   - From the supplier form, click "Branches" button
   - Or go to: HighFive Operations > Suppliers > Branches
   - Click "Create"
   - Select supplier
   - Fill in branch details
   - Save → Analytic account auto-created

5. **Create First Unit**
   - Go to: HighFive Operations > Services > Units
   - Click "Create"
   - Select branch
   - Fill in service details
   - Save

## Usage

### Creating a Supplier

```python
partner = env['res.partner'].create({
    'name': 'Ahmed Sports Center',
    'is_highfive_partner': True,
    'highfive_partner_id': 'HF-001',
    'tax_status': 'standard_15',
    'commission_rate_online': 15.0,
    'commission_rate_cash': 10.0,
})
# Analytic parent account is auto-created
```

### Creating a Customer

```python
customer = env['res.partner'].create({
    'name': 'Mohammed Ali',
    'is_highfive_customer': True,
    'highfive_customer_id': 'CUS-001',
    'email': 'mohammed@example.com',
    'phone': '+966501234567',
})
```

### Creating a Branch

```python
branch = env['highfive.partner.branch'].create({
    'name': 'Main Branch',
    'highfive_branch_id': 'BR-001',
    'partner_id': partner.id,
    'country_id': env.ref('base.sa').id,
    'city': 'Riyadh',
    'latitude': '24.7136',
    'longitude': '46.6753',
})
# Analytic child account is auto-created under partner's parent
```

### Creating a Unit

```python
unit = env['product.template'].create({
    'name': 'Football Field - Standard',
    'highfive_unit_id': 'UNIT-001',
    'branch_id': branch.id,
    'type': 'service',
    'invoice_policy': 'order',
    'list_price': 100.0,
})
```

## Data Model

### res.partner (Extended)
- `highfive_partner_id` (Char) - Unique ID for suppliers
- `highfive_customer_id` (Char) - Unique ID for customers
- `is_highfive_partner` (Boolean) - Is supplier flag
- `is_highfive_customer` (Boolean) - Is customer flag
- `tax_status` (Selection) - Tax configuration
- `commission_rate_online` (Float) - Default online commission %
- `commission_rate_cash` (Float) - Default cash commission %
- `analytic_parent_id` (Many2one) - Parent analytic account
- `branch_ids` (One2many) - Related branches
- `branch_count` (Integer) - Number of branches

### highfive.partner.branch
- `name` (Char) - Branch name
- `code` (Char) - Branch code
- `highfive_branch_id` (Char) - Unique ID
- `partner_id` (Many2one) - Supplier
- `country_id` (Many2one) - Country
- `state_id` (Many2one) - State
- `city` (Char) - City
- `street` (Char) - Street address
- `latitude` (Char) - GPS latitude
- `longitude` (Char) - GPS longitude
- `active` (Boolean) - Active flag
- `analytic_account_id` (Many2one) - Child analytic account
- `unit_count` (Integer) - Number of units

### product.template (Extended)
- `highfive_unit_id` (Char) - Unique ID
- `branch_id` (Many2one) - Branch
- `partner_id` (Many2one) - Supplier (computed from branch)

## Constraints

### Business Rules
1. A partner cannot be both supplier and customer
2. HighFive units must be of type "Service"
3. HighFive units must be linked to a branch
4. HighFive units must use "Ordered quantities" invoice policy
5. Commission rates must be between 0 and 100
6. Cannot delete supplier with branches
7. Cannot delete branch with units or transactions

### SQL Constraints
1. `highfive_partner_id` must be unique
2. `highfive_customer_id` must be unique
3. `highfive_branch_id` must be unique
4. `highfive_unit_id` must be unique

## Logging

The module provides comprehensive logging:

```python
# INFO level - Important operations
_logger.info(f"Creating supplier analytic parent for partner {partner.id}")

# DEBUG level - Detailed traces
_logger.debug(f"Set supplier_rank=1 for partner {partner.id}")

# ERROR level - Failures
_logger.error(f"Failed to create analytic parent: {str(e)}")
```

To view logs:
```bash
tail -f /var/log/odoo/odoo.log | grep highfive
```

## Security

### Access Rights
- **Users** (base.group_user): Read-only access to branches
- **Account Managers** (account.group_account_manager): Full CRUD except delete
- **System Administrators** (base.group_system): Full control

### Record Rules
No custom record rules in this version. All users with access can see all records.

## Technical Notes

### Idempotent Methods
All creation methods are idempotent - safe to call multiple times:
- `_ensure_supplier_analytic_parent()`
- `_ensure_branch_analytic_child()`

### Performance Considerations
- Indexes on all HighFive ID fields
- Stored computed fields where appropriate
- Lazy creation of analytic accounts

### Extension Points
The module is designed to be extended by:
- `highfive_api_connector` - API integration
- `highfive_booking_invoicing` - Booking and invoicing logic
- `highfive_reporting` - Custom reports

## Troubleshooting

### Analytic Account Not Created
**Problem**: Supplier created but no analytic account

**Solution**: 
```python
partner._ensure_supplier_analytic_parent()
```

### Cannot Create Unit
**Problem**: Validation error when creating unit

**Check**:
1. Is it type "Service"?
2. Is it linked to a branch?
3. Is invoice policy "order"?

### Branch Not Showing in List
**Problem**: Branch created but not visible

**Check**:
1. Is the branch active?
2. Are you using the correct filters?
3. Do you have access rights?

## Migration from v1.0 to v1.1

If upgrading from v1.0:

1. **Database Changes**
   - New fields added automatically
   - No data loss
   - Old `is_highfive_player` migrated to `is_highfive_customer`

2. **API Changes**
   - Update API calls to use `is_highfive_customer` instead of `is_highfive_player`
   - Update API calls to use `highfive_customer_id` instead of `highfive_player_id`

3. **Post-Upgrade Steps**
   - Review and set `tax_status` for existing suppliers
   - Optionally set default commission rates
   - Test analytic account creation
   - Review access rights

## Support

For issues or questions:
1. Check the log files
2. Review this README
3. Contact: support@highfive.sa

## License

LGPL-3

## Author

Manus AI - HighFive Development Team

## Changelog

### v1.1.0 (2024-12-18)
- Renamed Players to Customers throughout
- Added tax_status field for suppliers
- Added commission rate fields
- Enhanced logging throughout
- Improved product constraints
- Enhanced UI/UX
- Better access rights
- Added kanban views
- Improved documentation

### v1.0.0 (2024-12-15)
- Initial release
- Supplier management
- Player (Customer) management
- Branch management
- Unit management
- Analytic hierarchy
- Basic UI
