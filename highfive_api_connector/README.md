# HighFive API Connector - Simple Edition

**Version**: 1.0.0 (Simple)  
**Compatible with**: Odoo 18

---

## 🎯 What is this?

A **simple, clean webhook-based integration** between HighFive and Odoo.

No complex sync mechanisms. No wizards. No bloat.

**Just**: Receive → Log → Validate → Process → Done.

---

## ✨ Features

✅ **Webhook Endpoints** - 4 endpoints for Partners, Customers, Branches, Units  
✅ **Complete Logging** - Every request logged with full details  
✅ **API Key Auth** - Simple Bearer token authentication  
✅ **Data Validation** - Check required fields before processing  
✅ **Auto Processing** - Create or update records automatically  
✅ **Error Handling** - Graceful error handling with detailed logs

---

## 📦 Installation

```bash
# 1. Upload module
Odoo → Apps → Upload Module → highfive_api_connector.zip

# 2. Update apps list
Apps → Update Apps List

# 3. Install
Apps → Search "HighFive API Connector" → Install
```

---

## ⚙️ Configuration

### 1. Set API Key

The API Key must be set in **System Parameters**:

```
Settings → Technical → Parameters → System Parameters

Click "Create":
Key: highfive.api.key
Value: YOUR_API_KEY_FROM_HIGHFIVE

Save
```

**Or use existing parameter**: If you already have `API-HI5` or `hi5` parameter, you can use it by modifying the controller code to read from that key instead.

### 2. Configure HighFive Webhooks

In HighFive admin panel, add these webhooks:

```
Partners:   http://your-odoo.com/api/odoo/partners
Customers:  http://your-odoo.com/api/odoo/players
Branches:   http://your-odoo.com/api/odoo/branches
Units:      http://your-odoo.com/api/odoo/units

Authorization: Bearer 7f92a0fccf67560bf1adfdf0d414f6bf9eff26ba
```

---

## 🚀 Usage

### Sending Data from HighFive

**Create/Update Partner**:
```bash
POST http://your-odoo.com/api/odoo/partners
Authorization: Bearer 7f92a0fccf67560bf1adfdf0d414f6bf9eff26ba
Content-Type: application/json

{
  "id": 1,
  "name": "Ahmed Sports Center",
  "email": "ahmed@sports.sa",
  "phone": "+966501234567",
  "country": "SA",
  "tax": "15",
  "accept_tax": 1
}
```

**Response**:
```json
{
  "success": true,
  "request_id": "REQ-ABC123",
  "data": {
    "action": "created",
    "partner_id": 42,
    "partner_name": "Ahmed Sports Center"
  },
  "processing_time_ms": 145.32
}
```

### Viewing Logs

```
HighFive API → Request Logs
```

See all requests with:
- Request ID
- Entity Type
- Success/Failed status
- Processing time
- Full request/response data

---

## 📊 Data Flow

```
HighFive
    ↓ (webhook)
Controller
    ↓ (create log)
Log Created
    ↓ (validate API key)
Validated
    ↓ (validate data)
Data OK
    ↓ (process)
Service
    ↓ (create/update)
Odoo Record
    ↓ (update log)
Success!
```

---

## 🔍 Troubleshooting

### Error: "Missing Authorization header"
**Solution**: Add Authorization header with Bearer token

### Error: "Invalid API Key"
**Solution**: Check API key in System Parameters

### Error: "Partner not found"
**Solution**: Sync partners before branches/units

### Error: "Missing required field"
**Solution**: Check request data includes all required fields

---

## 📝 API Reference

### Endpoints

| Endpoint | Entity | Required Fields |
|----------|--------|-----------------|
| `/api/odoo/partners` | Partner | id, name |
| `/api/odoo/players` | Customer | id, name |
| `/api/odoo/branches` | Branch | id, name, partner_id |
| `/api/odoo/units` | Unit | id, name, partner_branch_id |

### Test Endpoints

```bash
# Ping
curl -X POST http://localhost:8069/api/odoo/test/ping

# Echo
curl -X POST http://localhost:8069/api/odoo/test/echo \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

---

## 📂 File Structure

```
highfive_api_connector/
├── models/
│   └── highfive_api_request_log.py
├── services/
│   ├── partner_service.py
│   ├── customer_service.py
│   ├── branch_service.py
│   └── unit_service.py
├── controllers/
│   └── webhook.py
├── views/
│   ├── highfive_api_request_log_views.xml
│   └── menus.xml
├── data/
│   └── system_parameters.xml
└── security/
    └── ir.model.access.csv
```

**Total**: ~7 files (vs 20+ in complex version)

---

## 🎓 Next Steps

After successful installation:

1. ✅ Configure webhooks in HighFive
2. ✅ Test with sample data
3. ✅ Monitor logs
4. ✅ Ready for production!

---

## 🚦 Future Enhancements (v1.1.0)

When needed, we can add:
- Bookings → Invoices
- Payment processing
- Commission calculation

But for now: **Keep it simple!** ✅

---

## License

LGPL-3

---

**Simple. Clean. Effective.** 🚀
