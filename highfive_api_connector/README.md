# 🚀 HighFive API Connector v2.0.0

Complete API integration module for HighFive platform with Odoo 18.

---

## 📋 Overview

This module provides comprehensive webhook-based integration between HighFive platform and Odoo, handling:
- Partners, Customers, Branches, Units
- Commission management (default + scheduled)
- Complete booking lifecycle
- Automated invoice generation
- Payment tracking

---

## ✨ Features

### **Core Entities**
- ✅ Partners (Suppliers)
- ✅ Customers (Players)
- ✅ Branches
- ✅ Units (Products/Services)

### **Commission Management**
- ✅ Default commissions (created with units)
- ✅ Scheduled commissions (promotions, special offers)
- ✅ Automatic selection (scheduled overrides default)
- ✅ Percentage & Fixed amount support

### **Booking Management**
- ✅ Create/Update bookings
- ✅ Online & Cash payment methods
- ✅ Automatic invoice generation
- ✅ Commission calculation
- ✅ Payment tracking
- ✅ Cancellation with refunds

### **Invoicing**
- ✅ Sales invoices (customer)
- ✅ Vendor bills (partner)
- ✅ Commission invoices (cash payments)
- ✅ Analytic account linking
- ✅ Automatic tax calculation

### **System Features**
- ✅ Complete request/response logging
- ✅ API Key authentication
- ✅ Comprehensive validation
- ✅ Error handling with detailed logs
- ✅ Performance tracking

---

## 📡 API Endpoints

### **1. Partners**
```
POST /api/odoo/partners
```
Create or update partner (supplier).

**Request:**
```json
{
  "id": 1,
  "name": "Ahmed Sports Center",
  "company_name": "Ahmed Sports LLC",
  "email": "ahmed@sports.sa",
  "phone": "+966501234567",
  "country": "SA",
  "tax": "15",
  "accept_tax": true,
  "commission_rate_online": 15,
  "commission_rate_cash": 10
}
```

---

### **2. Customers**
```
POST /api/odoo/players
```
Create or update customer (player).

**Request:**
```json
{
  "id": 100,
  "name": "Mohammed Ali",
  "email": "mohammed@example.com",
  "phone": "+966501234567",
  "country": "SA",
  "city": "Riyadh"
}
```

---

### **3. Branches**
```
POST /api/odoo/branches
```
Create or update branch.

---

### **4. Units**
```
POST /api/odoo/units
```
Create or update unit (with default commission).

**Request:**
```json
{
  "id": 5,
  "name": "Football Field A",
  "partner_id": 1,
  "branch_id": 2,
  "base_price": 100.00,
  "default_commission": {
    "online": {"type": "percentage", "value": 15},
    "cash": {"type": "percentage", "value": 10}
  }
}
```

---

### **5. Commissions**

#### **Create/Update Scheduled Commission**
```
POST /api/odoo/commissions
```

**Request:**
```json
{
  "id": 123,
  "unit_id": 5,
  "type": "scheduled",
  "name": "Ramadan Special Offer",
  "start_date": "2026-03-01",
  "end_date": "2026-03-30",
  "online_commission": {"type": "percentage", "value": 20},
  "cash_commission": {"type": "percentage", "value": 15}
}
```

#### **Delete Commission**
```
DELETE /api/odoo/commissions/{commission_id}
```

#### **Get All Commissions**
```
GET /api/odoo/commissions?unit_id=5
```

#### **Get Active Commission**
```
GET /api/odoo/commissions/active?unit_id=5&date=2026-03-15
```

---

### **6. Bookings**

#### **Create/Update Booking**
```
POST /api/odoo/bookings
```

**Request:**
```json
{
  "id": 123,
  "highfive_booking_id": "HF-2026-001",
  "booking_date": "2026-01-15",
  "session_start_time": 14.5,
  "session_end_time": 16.0,
  "unit_id": 5,
  "booker_id": 100,
  "session_base_price": 100.00,
  "discount": 0.00,
  "tax_percent": 15.00,
  "tax_status": "included",
  "total": 115.00,
  "payment_method": "online",
  "payment_card": 80.00,
  "payment_wallet": 20.00,
  "payment_coupon": 0.00,
  "payment_transaction_ref": "TXN123",
  "services": [
    {
      "service_id": 10,
      "name": "Equipment Rental",
      "quantity": 2,
      "price_unit": 10.00
    }
  ],
  "status": "confirmed"
}
```

**Response:**
```json
{
  "success": true,
  "request_id": "REQ-ABC123",
  "data": {
    "action": "created",
    "booking_id": 45,
    "booking_ref": "BOOK/2026/00045",
    "model": "highfive.booking",
    "state": "confirmed",
    "invoices": [
      {
        "type": "out_invoice",
        "id": 100,
        "ref": "INV/2026/00100",
        "state": "posted",
        "amount_total": 115.00
      },
      {
        "type": "in_invoice",
        "id": 50,
        "ref": "BILL/2026/00050",
        "state": "posted",
        "amount_total": 100.00
      }
    ]
  },
  "processing_time_ms": 234.5
}
```

#### **Update Payment**
```
POST /api/odoo/bookings/{booking_id}/payment
```

**Request:**
```json
{
  "payment_status": "paid",
  "paid_amount": 100.00,
  "payment_date": "2026-01-11",
  "payment_method_details": {
    "card": 80.00,
    "wallet": 20.00
  },
  "transaction_ref": "TXN123"
}
```

#### **Cancel Booking**
```
POST /api/odoo/bookings/{booking_id}/cancel
```

**Request:**
```json
{
  "reason": "Customer requested cancellation"
}
```

#### **Get Booking Status**
```
GET /api/odoo/bookings/{booking_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "booking_id": 45,
    "name": "BOOK/2026/00045",
    "highfive_booking_id": "HF-2026-001",
    "state": "confirmed",
    "payment_state": "paid",
    "booking_date": "2026-01-15",
    "customer": {...},
    "unit": {...},
    "amounts": {...},
    "payment": {...},
    "invoices": [...]
  }
}
```

---

## 🔐 Authentication

All endpoints require API Key authentication using Odoo's built-in system.

**Header:**
```
Authorization: Bearer YOUR_API_KEY
```

**How to generate API Key:**
1. Go to Settings → Users & Companies → Users
2. Select user → API Keys tab
3. Generate new API key with 'RPC' scope

---

## 🎯 Business Logic

### **Online Payment Flow:**
```
1. Customer pays via platform → HighFive receives money
2. Create Sales Invoice (customer → HighFive):
   - Unit price (session_base_price)
   - Commission (calculated)
   - Additional services
   - Tax
3. Create Vendor Bill (HighFive → Partner):
   - Unit price only
   - Tax (based on partner tax_status)
4. Register payment on sales invoice
5. Link both invoices to analytic account
```

### **Cash Payment Flow:**
```
1. Customer pays directly to partner
2. Create Commission Invoice (partner → HighFive):
   - Commission only (calculated)
   - Tax
3. Partner pays commission later
```

### **Commission Selection:**
```
1. Check for scheduled commission active on booking_date
2. If found → use scheduled commission
3. Otherwise → use default commission
4. Calculate amount: base_price × (rate / 100)
```

---

## 📊 Request Logging

All API requests are logged in `highfive.api.request.log`:
- Request ID (unique)
- Endpoint
- Request/Response body
- Processing time
- Success/Failure state
- Error details
- IP address
- User agent

**Access logs:**
Menu: HighFive → API Connector → Request Logs

---

## 🏗️ Architecture

```
highfive_api_connector/
├── controllers/
│   ├── webhook.py              # Core endpoints (partners, customers, etc.)
│   ├── booking_webhook.py      # Booking endpoints
│   └── commission_webhook.py   # Commission endpoints
├── services/
│   ├── partner_service.py      # Partner processing
│   ├── customer_service.py     # Customer processing
│   ├── branch_service.py       # Branch processing
│   ├── unit_service.py         # Unit processing (with commission)
│   ├── commission_service.py   # Commission management
│   └── booking_service.py      # Booking processing
├── models/
│   └── highfive_api_request_log.py  # Request logging
├── security/
│   └── ir.model.access.csv     # Access rights
└── views/
    ├── highfive_api_request_log_views.xml
    └── menus.xml
```

---

## 🔧 Installation

### **1. Dependencies**
```python
'depends': [
    'base',
    'web',
    'highfive_core',
    'highfive_booking_management',
]
```

### **2. Install Module**
```bash
# Copy to addons folder
cp -r highfive_api_connector /opt/odoo18/addons/

# Restart Odoo
sudo systemctl restart odoo18

# Install via UI
Apps → Update Apps List → Search "HighFive API Connector" → Install
```

---

## 🧪 Testing

### **Test Endpoints**
```
GET /api/odoo/test/ping
POST /api/odoo/test/echo
```

### **Example Test (curl)**
```bash
# Ping
curl -X POST \
  https://your-domain.com/api/odoo/test/ping \
  -H 'Content-Type: application/json' \
  -d '{}'

# Create Partner
curl -X POST \
  https://your-domain.com/api/odoo/partners \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "id": 1,
    "name": "Test Partner",
    "email": "test@example.com"
  }'
```

---

## 📈 Monitoring

### **View API Logs:**
Menu: HighFive → API Connector → Request Logs

**Filters:**
- Entity Type (partner, customer, booking, etc.)
- State (success, failed)
- Date range
- IP address

**Metrics:**
- Total requests
- Success rate
- Average processing time
- Error distribution

---

## ⚠️ Error Handling

### **Validation Errors (400)**
```json
{
  "success": false,
  "error": "Missing required field: unit_id",
  "error_type": "validation_error"
}
```

### **Authentication Errors (401)**
```json
{
  "success": false,
  "error": "API Key not found or invalid",
  "error_type": "validation_error"
}
```

### **Server Errors (500)**
```json
{
  "success": false,
  "error": "Internal server error",
  "error_type": "server_error"
}
```

All errors are logged with full traceback for debugging.

---

## 🔄 Migration from v1.x

**Changes in v2.0:**
1. Added `highfive_booking_management` dependency
2. Added 2 new entity types: `commission`, `booking`
3. Added 3 new action types: `deleted`, `cancelled`, `payment_updated`
4. New endpoints: `/commissions`, `/bookings`

**No data migration required** - backward compatible with v1.x

---

## 📞 Support

For issues or questions:
- Check logs in Odoo: HighFive → API Connector → Request Logs
- Check Odoo logs: `/var/log/odoo/odoo.log`
- Contact: support@highfive.sa

---

## 📝 License

LGPL-3

---

## 🎉 Version History

### **v2.0.0 (2026-01-11)**
- Added Commission Management API
- Added Booking Management API
- Added Payment Update API
- Added Cancellation API
- Complete invoice generation
- Analytic account integration
- Enhanced logging

### **v1.1.0**
- Added Partners, Customers, Branches, Units
- Basic webhook integration
- Request logging

---

**🚀 Ready to integrate!**
