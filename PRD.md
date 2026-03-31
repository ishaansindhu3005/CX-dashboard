# Ozi CX Dashboard — Product Requirements Document

**Version:** 1.0
**Date:** March 2026
**Author:** Ishaan Sindhu, Ozi
**Status:** Production (v1)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture](#3-architecture)
4. [User Roles & Permissions (RBAC)](#4-user-roles--permissions-rbac)
5. [Database Schema](#5-database-schema)
6. [Module Specifications](#6-module-specifications)
   - 6.1 [Authentication & Sidebar](#61-authentication--sidebar)
   - 6.2 [Dashboard](#62-dashboard)
   - 6.3 [Orders](#63-orders)
   - 6.4 [Customers](#64-customers)
   - 6.5 [Returns & Exchanges](#65-returns--exchanges)
   - 6.6 [Refunds](#66-refunds)
   - 6.7 [CRM Calling](#67-crm-calling)
   - 6.8 [Short Picks](#68-short-picks)
   - 6.9 [User Management](#69-user-management)
7. [Data Sources](#7-data-sources)
8. [Status Flows & State Machines](#8-status-flows--state-machines)
9. [API / Query Reference](#9-api--query-reference)
10. [UI Design System](#10-ui-design-system)
11. [Session State & Navigation](#11-session-state--navigation)
12. [Test Cases](#12-test-cases)
13. [Deployment](#13-deployment)
14. [Known Gaps & Future Roadmap](#14-known-gaps--future-roadmap)

---

## 1. Overview

### 1.1 Product Summary

The **Ozi CX Dashboard** is an internal, multi-role customer experience management system for Ozi — a baby/kids quick-commerce startup based in Gurugram. It centralises all post-order CX workflows into a single interface used by agents, CX leads, warehouse staff, supervisors, and admins.

### 1.2 Problem Statement

Ozi's CX team was managing returns, refunds, retention calls, and short-pick actions across separate tools (WhatsApp, Shopify Admin, spreadsheets). This caused:
- No audit trail on return approvals
- Agents unable to see real-time return status
- Refunds initiated inconsistently across channels
- No structured retention call logging

### 1.3 Goals

| Goal | Metric |
|------|--------|
| Centralise returns lifecycle | All returns created, approved, dispatched in one tool |
| Structured refund approval | 2-step approval with rejection logging |
| CRM call logging | 100% of outbound retention calls logged |
| Short-pick resolution | Every OMS short-pick actioned with customer notes |
| Role-based access | CX agents see only what they need |

### 1.4 Out of Scope (v1)

- Real Pidge API integration (simulated)
- Real OMS sync (stub function exists)
- Payment gateway integration for refund disbursement
- WhatsApp bot integration
- Mobile app

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Streamlit | ≥ 1.36 |
| Language | Python | ≥ 3.9 |
| Database | SQLite (WAL mode) | — |
| DB Migration Target | MySQL | — |
| Data processing | Pandas | ≥ 2.0 |
| Charts (future) | Plotly | ≥ 5.18 |
| Deployment | Streamlit Cloud | — |
| Source Control | GitHub | — |

### 2.1 File Structure

```
ozi_cx_dashboard/
├── app.py                    # Entry point, auth, sidebar, routing
├── requirements.txt
├── seed.py                   # Initial data seeding
├── .streamlit/
│   └── config.toml           # Theme config (purple, Inter font)
├── db/
│   ├── connection.py         # SQLite connection + init_db()
│   └── queries.py            # All DB read/write functions
├── utils/
│   ├── rbac.py               # Role-based access control
│   ├── page_utils.py         # Auth guard per page
│   └── oms_sync.py           # OMS short-pick sync (stub)
├── pages/
│   ├── 0_Dashboard.py
│   ├── 1_Returns.py
│   ├── 2_Refunds.py
│   ├── 3_Customers.py
│   ├── 4_Orders.py
│   ├── 5_Users.py
│   ├── 6_Roles.py            # Placeholder (not implemented)
│   ├── 7_CRM_Calling.py
│   └── 8_Short_Picks.py
└── data/
    ├── orders.csv            # ~50,000 rows, tracked in git
    └── order_details.csv     # ~98,000 rows, tracked in git
```

---

## 3. Architecture

### 3.1 Request Flow

```
User opens app.py
    ↓
Auth check (st.session_state["current_user"])
    ↓ logged out         ↓ logged in
Login screen        Load sidebar + navigation
                         ↓
                    Page renders
                         ↓
                    page_utils.get_page_user()
                         ↓
                    has_permission(role, module, action)
                         ↓ denied           ↓ allowed
                    st.error + st.stop()  Render page content
                                               ↓
                                    DB queries via db/queries.py
                                               ↓
                                    CSV data via @st.cache_data
```

### 3.2 RBAC Flow

```python
# utils/rbac.py
def has_permission(role, module, action) -> bool:
    if role == "admin":
        return True          # Admin bypasses everything
    return (module, action) in _get_permissions(role)
    # _get_permissions() → loads from DB (cached 60s) → fallback to _DEFAULTS
```

### 3.3 Data Sources

- **SQLite DB** (`ozi_cx.db`): All CX-generated data (returns, refunds, calls, users)
- **orders.csv**: Historical order data, used read-only for lookups
- **order_details.csv**: Line-item data per order, used for item selection and order summary

### 3.4 DB Connection

```python
DB_PATH = os.getenv("DB_PATH", "../ozi_cx.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row   # dict-like access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

**MySQL migration path:** Replace `sqlite3` with `mysql.connector`, swap `?` placeholders with `%s`. DB_PATH env var can be overridden with MySQL DSN.

---

## 4. User Roles & Permissions (RBAC)

### 4.1 Role Hierarchy

```
admin
  └── supervisor
        └── cx_lead
              └── agent
wh_user  (parallel track — warehouse only)
```

### 4.2 Permission Matrix

| Module | Action | Agent | CX Lead | WH User | Supervisor | Admin |
|--------|--------|:-----:|:-------:|:-------:|:----------:|:-----:|
| dashboard | view | ✓ | ✓ | ✓ | ✓ | ✓ |
| returns | view | ✓ | ✓ | ✓ | ✓ | ✓ |
| returns | action (submit form) | ✓ | ✓ | — | ✓ | ✓ |
| returns | create (manual return) | ✓ | ✓ | — | ✓ | ✓ |
| returns | approve | — | ✓ | — | ✓ | ✓ |
| returns | reject | — | ✓ | — | ✓ | ✓ |
| returns | pickup (send to Pidge) | — | — | ✓ | ✓ | ✓ |
| refunds | view | ✓ | ✓ | ✓ | ✓ | ✓ |
| refunds | action | — | ✓ | — | ✓ | ✓ |
| refunds | approve | — | ✓ | — | ✓ | ✓ |
| refunds | create | — | ✓ | — | ✓ | ✓ |
| refunds | override_amount | — | — | — | — | ✓ |
| customers | view | ✓ | ✓ | — | ✓ | ✓ |
| orders | view | ✓ | ✓ | — | ✓ | ✓ |
| crm_calling | view | ✓ | ✓ | ✓ | ✓ | ✓ |
| crm_calling | call (work on calls) | ✓ | ✓ | — | ✓ | ✓ |
| crm_calling | reassign | — | — | — | ✓ | ✓ |
| short_picks | view | ✓ | ✓ | ✓ | ✓ | ✓ |
| short_picks | action | ✓ | ✓ | — | ✓ | ✓ |
| short_picks | reassign | — | — | — | ✓ | ✓ |
| users | view | — | — | — | ✓ | ✓ |
| users | create / edit / delete | — | — | — | — | ✓ |
| roles | view / create / edit | — | — | — | — | ✓ |

### 4.3 Admin Override

Hardcoded in `utils/rbac.py`:
```python
if role == "admin":
    return True
```
Admin always has access regardless of what's stored in the `role_permissions` table.

### 4.4 Permission Storage

- **DB Table:** `role_permissions (role, module, action)` — unique constraint on all three
- **Fallback:** Hardcoded `_DEFAULTS` dict in `rbac.py` (mirrors seed data)
- **Cache:** 60-second TTL on `_get_permissions()` using `@st.cache_data`
- **Seeding:** `seed.py` inserts all permissions on first run (`_user_count == 0`)

---

## 5. Database Schema

### 5.1 `stores`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT NOT NULL | e.g. "Gurgaon" |
| store_code | TEXT NOT NULL | e.g. "S65", "DLF1" |

**Seed data:** 4 stores — S65 (Sector 65), DLF1 (DLF Phase 1), SRD (Sohna Road), MNS (Manesar)

---

### 5.2 `cx_users`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| name | TEXT NOT NULL | |
| email | TEXT | |
| phone | TEXT | |
| role | TEXT NOT NULL | agent \| cx_lead \| wh_user \| supervisor \| admin |
| is_active | INTEGER DEFAULT 1 | 0 = soft deleted |
| is_available | INTEGER DEFAULT 0 | Toggled by user in sidebar |

**Seed users:**
- Arjun Mehta (agent)
- Priya Nair (agent)
- Bhagwana Singh (cx_lead)
- Rajesh Kumar (wh_user)
- Vaibhav Gupta (supervisor)
- Ishaan Sindhu (admin)

---

### 5.3 `role_permissions`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| role | TEXT NOT NULL | |
| module | TEXT NOT NULL | |
| action | TEXT NOT NULL | |
| — | UNIQUE(role, module, action) | |

---

### 5.4 `returns`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | INTEGER PK AUTOINCREMENT | | |
| order_id | TEXT | NOT NULL | From CSV |
| customer_id | TEXT | NOT NULL | User ID from CSV |
| customer_name | TEXT | | Optional |
| customer_phone | TEXT | | |
| payment_method | TEXT | DEFAULT 'prepaid' | prepaid \| cod |
| agent_id | INTEGER | FK → cx_users | Who created/handled |
| type | TEXT | NOT NULL | return \| exchange |
| source | TEXT | NOT NULL | app \| chatbot \| admin_panel \| cx_portal |
| status | TEXT | DEFAULT 'pending_action' | See state machine §8.1 |
| refund_source | TEXT | | wallet \| source_refund \| cod_wallet (null if exchange) |
| reason | TEXT | | wrong_product \| damaged \| expired \| size_issue \| not_as_expected \| other |
| spoken_to_customer | TEXT | | yes \| no \| attempted |
| pitched_exchange | TEXT | | yes \| no \| na |
| pickup_slot | TEXT | | e.g. "26 Mar 2026, 10AM–12PM" |
| agent_notes | TEXT | | Free text |
| rejection_reason | TEXT | | Set on cx_lead_reject |
| store_id | INTEGER | FK → stores | Set at pickup stage |
| pidge_tracking_id | TEXT | | e.g. "PIDGE-A3F9C21E" |
| created_at | DATETIME | DEFAULT NOW | |
| updated_at | DATETIME | DEFAULT NOW | |

---

### 5.5 `return_items`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| return_id | INTEGER NOT NULL | FK → returns |
| item_name | TEXT NOT NULL | |
| item_sku | TEXT | |
| quantity | INTEGER DEFAULT 1 | |
| unit_price | REAL | MRP per unit |
| return_amount | REAL | Refundable amount |

---

### 5.6 `refunds`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| return_id | INTEGER | FK → returns (nullable) |
| order_id | TEXT NOT NULL | |
| customer_id | TEXT NOT NULL | |
| customer_phone | TEXT | |
| order_amount | REAL | Total order value |
| amount | REAL NOT NULL | Refund amount |
| method | TEXT NOT NULL | wallet \| source_refund \| cod_wallet |
| refund_type | TEXT | return_app \| admin_panel \| chatbot \| tnb \| oos \| cancelled_prepaid \| manual |
| coupon_code | TEXT | |
| notes | TEXT | |
| status | TEXT DEFAULT 'pending' | See state machine §8.2 |
| triggered_at | DATETIME | When created |
| completed_at | DATETIME | When marked complete |

---

### 5.7 `crm_calls`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| order_id | TEXT NOT NULL UNIQUE | |
| customer_id | TEXT | |
| customer_phone | TEXT | |
| customer_name | TEXT | |
| order_amount | REAL | |
| order_status | TEXT | rto_out_for_delivery \| rto_delivered \| cancelled \| failed \| undelivered \| pending |
| new_repeat | TEXT | new \| repeat |
| coupon_code | TEXT | |
| assigned_to | INTEGER | FK → cx_users (nullable = unassigned) |
| call_status | TEXT DEFAULT 'pending' | pending \| in_progress \| completed |
| reached_out | TEXT | yes \| no \| attempted |
| drop_off_reason | TEXT | See §6.7 for enum |
| reordered | TEXT | yes \| no |
| notes | TEXT | |
| assigned_at | DATETIME | |
| started_at | DATETIME | Set when agent opens detail panel |
| completed_at | DATETIME | Set on complete |

---

### 5.8 `short_pick_actions`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| order_id | TEXT NOT NULL UNIQUE | |
| customer_id | TEXT | |
| customer_phone | TEXT | |
| customer_name | TEXT | |
| order_amount | REAL | |
| payment_method | TEXT | |
| store_code | TEXT | |
| short_items | TEXT | Comma-separated item names |
| short_skus | TEXT | Comma-separated SKUs |
| short_item_count | INTEGER DEFAULT 0 | |
| assigned_to | INTEGER | FK → cx_users |
| action_status | TEXT DEFAULT 'pending' | pending \| in_progress \| completed |
| reached_out | TEXT | yes \| no \| attempted |
| customer_response | TEXT | See §6.8 for enum |
| resolution | TEXT | See §6.8 for enum |
| notes | TEXT | |
| synced_at | DATETIME | From OMS |
| started_at | DATETIME | |
| completed_at | DATETIME | |

---

## 6. Module Specifications

### 6.1 Authentication & Sidebar

#### Login
- **Page:** `app.py` (shown when `current_user` not in session state)
- **Fields:** User dropdown (sorted by role priority: admin → supervisor → cx_lead → agent → wh_user)
- **Behaviour:** Sets `st.session_state["current_user"]` with full user dict

#### Sidebar (when logged in)
- **Wordmark:** "ozi**CX**" in bold
- **Avatar:** Circular with user initials, coloured by role
- **Role badge:** Colour-coded pill (Admin=red, Supervisor=orange, CX Lead=purple, Agent=blue, WH=green)
- **Availability toggle:** "🟢 Available" / "⚫ Unavailable" button (calls `toggle_availability`)
  - Marking Available triggers `assign_calls_to_available_agents()` for round-robin assignment
- **Navigation:** All pages accessible to the role
- **Log Out:** Clears `current_user` from session state

#### Role Colours

| Role | Hex |
|------|-----|
| admin | #ef4444 |
| supervisor | #f97316 |
| cx_lead | #8b5cf6 |
| agent | #3b82f6 |
| wh_user | #10b981 |

---

### 6.2 Dashboard

#### Admin / Supervisor / CX Lead View

**KPI Cards (4):**
| Card | Value Source |
|------|-------------|
| Open Returns | COUNT returns WHERE status NOT IN (completed, cancelled) |
| Open Refunds | COUNT refunds WHERE status NOT IN (completed, failed) |
| Open CRM Calls | COUNT crm_calls WHERE call_status != completed |
| Open Short Picks | COUNT short_pick_actions WHERE action_status != completed |

**Team Queue Table:**
| Column | Source |
|--------|--------|
| Agent | cx_users.name |
| Role | cx_users.role |
| Status | is_available → "🟢 Online" or "⚫ Offline" |
| Returns | COUNT open returns assigned to agent |
| Calls | COUNT open crm_calls assigned to agent |
| Short Picks | COUNT open short_pick_actions assigned to agent |

#### Agent View

**KPI Cards (4):** Same as above but filtered to `agent_id = current_user.id`

**Queue Sections (3 columns):**
- **Returns** — pending returns assigned to agent (up to 5), "Open" button deep-links to Returns module
- **CRM Calls** — pending calls assigned to agent (up to 5), deep-links to CRM Calling module
- **Short Picks** — pending short picks assigned to agent (up to 5), deep-links to Short Picks module

**Empty State:** Green "✓ All clear" card when queue is empty

**Deep-link mechanism:**
```python
st.session_state["selected_pending_action"] = return_id
st.switch_page("pages/1_Returns.py")
```

---

### 6.3 Orders

#### Data Loading

```python
# orders.csv — load columns:
["id", "user_id", "contact_person_number", "order_amount", "coupon_code",
 "coupon_discount_amount", "order_status", "created_at", "Is Return",
 "return_amount", "FINAL STORE", "NEW_REPEAT", "is_try_and_buy", "GrossAmount"]

# order_details.csv — load columns:
["order_id", "item_name", "item_sku", "price", "quantity", "is_return",
 "Return Amount", "store_id", "Brand", "SellingPriceX_Quantity",
 "discount_on_item", "is_rx", "isGift_Price", "Coupon Discount While Ordering"]
```

Both loaded with `@st.cache_data` (persist across page reruns).

#### Filters

| Filter | Type | Field |
|--------|------|-------|
| Search | text_input | order_id OR contact_person_number |
| Status | selectbox | order_status |
| Store | selectbox | FINAL STORE |
| Sort | selectbox | created_at DESC/ASC, order_amount DESC/ASC |
| Returns Only | checkbox | Is Return == 1 |

#### Table (st.dataframe)

Columns: Order ID, Phone, Amount (₹), Status, Store, Return, Date, Coupon
- Number format: `₹%.0f` for Amount
- Row selection: `selection_mode="single-row"`, `on_select="rerun"`
- Pagination: 50 rows per page, Prev/Next nav at top and bottom

#### Detail Panel (on row select)

**Header bar:** Close button | Order # | 📞 Phone | 🏪 Store | 🗓 Date | ₹ Amount | Status badge

**Info Cards Row:**
- **Order Info card** (left): Coupon code + discount, User ID, Store, New/Repeat/T&B tags
- **CX Actions card** (right): Context-dependent
  - If return exists → Show return status badge + "Go to Returns module"
  - If delivered + has permission → "↩ Return Item(s)" button
  - If other status → "Returns only for delivered orders"

**Return Form** (full-width, shown below info cards when initiated):

| Field | Type | Options |
|-------|------|---------|
| Select items | multiselect | From order_details CSV |
| Type | radio | return \| exchange |
| Payment | radio | prepaid \| cod |
| Spoken to customer | radio | yes \| no \| attempted |
| Pitched exchange | radio | yes \| no \| na |
| Return reason | selectbox | wrong_product \| damaged \| expired \| size_issue \| not_as_expected \| other |
| Refund source | selectbox | wallet / source_refund (prepaid) or cod_wallet (cod) — hidden for exchange |
| Pickup date | date_input | min = today |
| Pickup time | selectbox | 7 time slots |
| Notes | text_area | optional |

Submit → `create_return_with_approval()` → pending_approval status

**Items Table** (full-width, with store tabs):
- Grouped by `store_id` from order_details CSV
- Tab label = FINAL STORE name from orders CSV
- Columns: #, Item Details (name + brand), SKU (code pill), Qty, Price (MRP), Sell Price, Discount
- Return/Rx status shown as inline badge on item name

**Order Summary** (right-aligned card below items):
| Line | Calculation |
|------|-------------|
| Items Price | SUM(price × quantity) |
| Subtotal | SUM(SellingPriceX_Quantity) |
| Discount | SUM(discount_on_item) |
| Coupon Discount | coupon_discount_amount from orders.csv |
| Delivery Fee | 0 (not in CSV) |
| Gift Fee | SUM(isGift_Price) |
| **Total** | order_amount from orders.csv |
| Wallet Amount | 0 (not implemented) |
| **Payable Amount** | order_amount |

---

### 6.4 Customers

#### Customer List

Built by aggregating `orders.csv` by `user_id`:

```python
grp = df.groupby("user_id").agg(
    phone        = ("contact_person_number", "first"),
    total_orders = ("id", "count"),
    returns      = ("Is Return", "sum"),
    total_spent  = ("order_amount", "sum"),
    first_order  = ("created_at", "min"),
    last_repeat  = ("NEW_REPEAT", "last"),
)
```

**Table (st.dataframe):** User ID, Phone, Orders, Returns, Total Spent (₹), First Order, Type
**Search:** By phone or user_id
**Pagination:** 30 per page

#### Customer Profile Panel

| Section | Content |
|---------|---------|
| Header | Customer ID + phone, Close button |
| KPI chips (4) | Total Orders, Total Spent, Returns, Wallet Credits |
| Coupons Used | All unique coupon codes as pills |
| Order History | Expandable — last 10 orders (with "Show all" toggle) |
| Returns in CX System | Expandable — returns from DB linked to phone |
| CRM Calls | Expandable — calls from DB linked to phone |

---

### 6.5 Returns & Exchanges

#### Tabs
All · Pending Action · Pending Approval · Pending Pickup · Out for Pickup · Completed · Cancelled

Each tab header shows count in brackets.

#### Filters (in expandable section per tab)

| Filter | Type |
|--------|------|
| Customer name / phone | text_input |
| Store | selectbox (from stores table) |
| Agent | selectbox (from active cx_users) |
| Type | selectbox (all / return / exchange) |
| Source | selectbox (all / app / chatbot / admin_panel / cx_portal) |
| Payment | selectbox (all / prepaid / cod) |
| From date | date_input |
| To date | date_input |

#### Summary Metrics (per tab, above table)

| Metric | Calculation |
|--------|-------------|
| Total | COUNT filtered returns |
| Return Value | SUM total_return_value |
| Today | COUNT where created_at = today |
| Returns / Exchanges | COUNT type='return' / COUNT type='exchange' |

#### Table Columns

**Pending Action tab:** ID, Order, Customer, Store, Payment, Items, Value, Agent, Created, [Open]
**All other tabs:** ID, Order, Customer, **Type**, Store, Payment, Items, Value, Agent, Created, [Open]

#### Detail Panel — by Role and Status

**Status: `pending_action`** | Roles: agent, cx_lead, supervisor, admin

Form fields:

| Field | Type | Required |
|-------|------|----------|
| Type | radio (return / exchange) | ✓ |
| Spoken to customer | selectbox (yes/no/attempted) | ✓ |
| Pitched exchange | selectbox (yes/no/na) | ✓ |
| Return reason | selectbox (6 options) | ✓ |
| Refund source | selectbox (payment-method dependent) | ✓ if type=return |
| Pickup date | date_input (min=today) | ✓ |
| Pickup time slot | selectbox (7 options) | ✓ |
| Agent notes | text_area | — |

Submit → `agent_submit_return()` → status becomes `pending_approval`

---

**Status: `pending_approval`** | Roles: cx_lead, supervisor, admin

Shows read-only fields from above + two actions:
- **✓ Approve** → `cx_lead_approve()` → `pending_pickup`
- **✗ Reject** (expandable) → text_area for reason → `cx_lead_reject()` → `cancelled`

Agents see: "Submitted — awaiting CX Lead approval" + read-only fields

---

**Status: `pending_pickup`** | Roles: wh_user, supervisor, admin

- Read-only submitted fields
- Store selectbox (from stores table)
- **"Send to Pidge ↗"** → `wh_send_to_pidge()` → generates `PIDGE-{uuid8}` tracking ID → `out_for_pickup`

Others see: "Approved — waiting for warehouse to send to Pidge"

---

**Status: `out_for_pickup`**

All roles see: "Out for pickup. Pidge ID: `{id}`"

Admin/Supervisor only: **"Simulate Pidge Complete →"** button → `simulate_pidge_complete()` → `completed` + auto-creates refund if type=return

---

**Status: `completed` / `cancelled`**

Read-only. Completed shows success. Cancelled shows rejection reason.

#### Manual Create Modal (top-right button, permission: returns:create)

Same form as pending_action but also includes:
- Order ID input (with live CSV lookup for items)
- Customer phone + customer ID (manual input)
- Submits directly to `pending_approval`

---

### 6.6 Refunds

#### Tabs
All · Pending Approval · Pending · Processed · Completed · Failed

#### Filters

| Filter | Type |
|--------|------|
| Customer (name/phone) | text_input |
| Method | selectbox |
| Refund Type | selectbox |
| From / To date | date_input |

#### Summary Metrics

| Metric | Calculation |
|--------|-------------|
| Refunds | COUNT filtered |
| Total Amount | SUM amount |

#### Table Columns

ID, Order, Customer, Ord Amt, Refund, Method, Type, Return?, Status, [Open]

#### Detail Panel

**Left column:** Refund details (customer, amounts, method, type, coupon, notes, timestamps)
**Right column:** Linked return (if exists), current status badge, action buttons

**Actions by status:**

| Status | Role | Actions |
|--------|------|---------|
| pending_approval | cx_lead, supervisor, admin | ✅ Approve → `pending` \| ❌ Reject → `failed` |
| pending | cx_lead, supervisor, admin | 🔄 Mark Processed → `processed` |
| processed | cx_lead, supervisor, admin | ✔ Mark Completed → `completed` |

#### Manual Refund Form (top-right button, permission: refunds:create)

**Flow:**
1. Order ID entered (outside form for live lookup)
2. System fetches from `orders.csv`: customer phone, customer ID, order amount
3. All fields auto-displayed (read-only)
4. User inputs: Refund Method, Refund Type, Notes
5. Admin only (`refunds:override_amount`): editable number input for refund amount
6. Submit → `create_manual_refund()` → `pending_approval`

| Field | Type | Admin | Others |
|-------|------|-------|--------|
| Customer Phone | display only | read-only | read-only |
| Customer ID | display only | read-only | read-only |
| Order Amount | display only | read-only | read-only |
| Refund Amount | number_input | ✓ editable | locked = order_amount |
| Refund Method | selectbox | ✓ | ✓ |
| Refund Type | selectbox | ✓ | ✓ |
| Notes | text_area | ✓ | ✓ |

---

### 6.7 CRM Calling

#### Purpose
Retention outreach for orders with "bad" statuses: RTO, cancelled, failed, undelivered.

#### Tabs
All · Pending · In Progress · Completed

#### Filters (Pending tab only)

| Filter | Type |
|--------|------|
| Order Status | selectbox (All / RTO / Cancelled / Failed / etc.) |
| Date range | date_input (start of month to today default) |

#### Flexible Columns (user-selectable expander)
Optional: New/Repeat, Coupon Code, Assigned Agent (default: all selected)

#### Table Columns
ID, Order, Customer, Amount, Order Status, Call Status, [optional columns], [Open]

#### Summary Metrics
Total Calls, Order Value (sum), Completed (count)

#### Detail Panel

Auto-marks `in_progress` on open.

**Right column (read-only):** Order ID, customer name/phone, amount, order status badge, new/repeat, coupon, assigned agent, timestamps

**Reassign (admin/supervisor only):** Agent selectbox + "Save Assignment" button

**Left column — form:**

| Field | Type | Options |
|-------|------|---------|
| Reached out | radio | yes / no / attempted |
| Drop-off reason | selectbox | cx_unavailable, not_interested, price_too_expensive, bad_delivery, forgot_coupon, too_slow, product_quality, other |
| Reordered | radio | yes / no |
| Notes | text_area | optional |

Buttons: "💾 Save Draft" (save without completing) | "✓ Submit" (mark completed)

#### Auto-Assignment
When agent toggles "Available" in sidebar → `assign_calls_to_available_agents()` → distributes unassigned pending calls round-robin to online agents

---

### 6.8 Short Picks

#### Purpose
When warehouse short-picks (can't fulfil) an item, agents call the customer to offer resolution.

#### Data Sync
`utils/oms_sync.py → sync_short_picks_from_oms()` (stub in v1, returns count of new records)

#### Tabs
All · Pending · In Progress · Completed

#### Filters (Pending tab only)

| Filter | Type |
|--------|------|
| Store code | text_input |
| Date range | date_input |

#### Flexible Columns (user-selectable)
Optional: Payment Method, Store, Assigned Agent (default: Store + Assigned Agent)

#### Table Columns
ID, Order, Customer, Amount, Short Items (truncated at 30 chars), Count badge, Status, [optional], [Open]

#### Detail Panel

Auto-marks `in_progress` on open.

**Right column:** Order context, payment, store, assigned agent, timestamps, short-picked items list (name + SKU)

**Reassign (admin/supervisor only):** Agent selectbox + "Save Assignment"

**Admin edit:** Admin/Supervisor can edit completed actions (is_admin_edit flag)

**Left column — form:**

| Field | Type | Options |
|-------|------|---------|
| Reached out | radio | yes / no / attempted |
| Customer response | selectbox | Understood & Accepted, Upset, Wants Full Refund, Wants Replacement, No Response, Other |
| Resolution | selectbox | Refund Initiated, Replacement Arranged, Partial Refund, Customer Cancelled, No Action Needed, Other |
| Notes | text_area | optional |

Buttons: "💾 Save Draft" | "✓ Submit" (or "✓ Update" for admin edits)

---

### 6.9 User Management

**Access:** Admin only

#### User List
All active users with role badge, email, phone.

#### Create User Form
Fields: Name, Email, Phone, Role (selectbox)
Submit → `create_cx_user()`

#### Edit User (inline)
Fields: Name, Email, Phone, Role
Triggered by "Edit" button per row

#### Delete / Deactivate
Sets `is_active = 0` (soft delete)
**Constraint:** Cannot deactivate yourself

---

## 7. Data Sources

### 7.1 orders.csv

| Column | Type | Notes |
|--------|------|-------|
| id | string | Order ID |
| user_id | string | Customer ID |
| contact_person_number | string | Phone |
| order_amount | float | Final payable amount |
| coupon_code | string | Applied coupon |
| coupon_discount_amount | float | Discount applied |
| order_status | string | delivered / cancelled / failed / etc. |
| created_at | datetime | |
| Is Return | int | 1 = has return |
| return_amount | float | |
| FINAL STORE | string | Store name |
| NEW_REPEAT | string | NEW / REPEAT |
| is_try_and_buy | int | 1 = T&B order |
| GrossAmount | float | Pre-discount amount |

### 7.2 order_details.csv

| Column | Type | Notes |
|--------|------|-------|
| order_id | string | FK to orders.csv |
| item_name | string | |
| item_sku | string | |
| price | float | MRP per unit |
| quantity | int | |
| SellingPriceX_Quantity | float | (sell price) × quantity |
| discount_on_item | float | MRP - sell price per item |
| is_return | int | 1 = item returned |
| is_rx | int | 1 = prescription item |
| store_id | int | Numeric store ID (maps to FINAL STORE) |
| Brand | string | Brand name |
| Return Amount | float | Refundable per item |
| isGift_Price | float | Gift wrapping fee |
| Coupon Discount While Ordering | float | Per-item coupon breakdown |

### 7.3 Data Loading

```python
@st.cache_data(show_spinner=False)
def load_orders(path: str) -> pd.DataFrame:
    # Loads ORDERS_COLS, casts types, caches

@st.cache_data(show_spinner=False)
def load_order_details(path: str) -> pd.DataFrame:
    # Loads DETAILS_COLS, casts types, caches
```

Cache is invalidated on CSV re-upload (`load_orders.clear()`).

---

## 8. Status Flows & State Machines

### 8.1 Returns

```
         [CSV / Admin / App]
                 │
         ┌───────▼────────┐
         │ pending_action  │  ← Agent fills form (type, reason, pickup slot, etc.)
         └───────┬────────┘
                 │ agent_submit_return()
         ┌───────▼────────┐
         │pending_approval │  ← CX Lead / Supervisor / Admin reviews
         └──┬─────────┬───┘
     approve│         │reject (+ reason)
         ┌──▼──────┐  └──────────────┐
         │ pending │                 │
         │ _pickup │         ┌───────▼────┐
         └────┬────┘         │ cancelled  │
              │ wh_send_to_pidge()
         ┌────▼───────────┐
         │ out_for_pickup │  ← Pidge has picked up
         └────┬───────────┘
              │ simulate_pidge_complete()
         ┌────▼──────┐
         │ completed │  → if type=return: auto-creates refund
         └───────────┘

[Manual Create via CX Portal] → skips pending_action → straight to pending_approval
```

### 8.2 Refunds

```
         [Manual / Auto from completed return]
                        │
         ┌──────────────▼────────────┐
         │     pending_approval       │  ← CX Lead / Admin reviews
         └──────┬─────────┬──────────┘
         approve│         │reject
         ┌──────▼──┐  ┌───▼───┐
         │ pending │  │ failed│
         └──────┬──┘  └───────┘
                │ process_refund()
         ┌──────▼────┐
         │ processed │  ← Payment gateway processing
         └──────┬────┘
                │ complete_refund()
         ┌──────▼────┐
         │ completed │
         └───────────┘
```

### 8.3 CRM Calls / Short Picks

```
         [OMS sync / seeded]
                │
         ┌──────▼──────┐
         │   pending    │  ← Unassigned or assigned to agent
         └──────┬───────┘
                │ Auto-marked on panel open (start_crm_call / start_short_pick)
         ┌──────▼──────────┐
         │  in_progress     │  ← Agent working, can save drafts
         └──────┬───────────┘
                │ complete_crm_call / complete_short_pick_action
         ┌──────▼────┐
         │ completed │
         └───────────┘
```

---

## 9. API / Query Reference

### 9.1 Returns

```python
get_returns(
    status_filter: str | None,
    store_id: int | None,
    agent_id: int | None,
    customer_search: str | None,
    date_from: str | None,
    date_to: str | None,
    type_filter: str | None,
    source_filter: str | None,
    payment_filter: str | None,
) -> list[sqlite3.Row]
# Returns rows with: id, order_id, customer_id, customer_name, customer_phone,
#   payment_method, type, source, status, refund_source, reason, spoken_to_customer,
#   pitched_exchange, pickup_slot, agent_notes, rejection_reason, store_id,
#   pidge_tracking_id, created_at, updated_at,
#   agent_name (JOIN), store_name (JOIN),
#   item_count (subquery), total_return_value (subquery)

get_return_by_id(return_id: int) -> sqlite3.Row | None

get_return_items(return_id: int) -> list[sqlite3.Row]
# Returns: id, return_id, item_name, item_sku, quantity, unit_price, return_amount

get_return_counts() -> dict[str, int]
# Keys: pending_action, pending_approval, pending_pickup, out_for_pickup, completed, cancelled

agent_submit_return(
    return_id: int,
    ret_type: str,
    spoken: str,
    pitched: str,
    reason: str,
    refund_source: str | None,
    pickup_slot: str,
    notes: str,
) -> None
# Sets status = pending_approval, fills all agent fields

cx_lead_approve(return_id: int) -> None
# status → pending_pickup, updated_at = NOW

cx_lead_reject(return_id: int, reason: str) -> None
# status → cancelled, rejection_reason = reason

wh_send_to_pidge(return_id: int, store_id: int, pidge_tracking_id: str) -> None
# status → out_for_pickup, store_id = store_id, pidge_tracking_id = id

simulate_pidge_complete(return_id: int) -> None
# status → completed
# If type == 'return': creates refund with status='pending', method=refund_source

create_return_with_approval(
    order_id: str,
    customer_id: str,
    customer_phone: str,
    payment_method: str,
    ret_type: str,
    items: list[dict],       # [{name, sku, qty, unit_price, return_amount}]
    spoken: str,
    pitched: str,
    reason: str,
    refund_source: str | None,
    pickup_slot: str,
    notes: str,
    agent_id: int | None,
    source: str,
) -> int                      # return_id

check_return_exists(order_id: str) -> dict | None
# Returns {id, status} if return exists for this order
```

### 9.2 Refunds

```python
get_refunds(
    status_filter: str | None,
    customer_search: str | None,
    date_from: str | None,
    date_to: str | None,
    method_filter: str | None,
    refund_type_filter: str | None,
) -> list[sqlite3.Row]
# Includes return context (return_status, return_type, return_reason) via LEFT JOIN

get_refund_by_id(refund_id: int) -> sqlite3.Row | None
# Includes return context

get_refund_counts() -> dict[str, int]
# Keys: pending_approval, pending, processed, completed, failed

create_manual_refund(
    order_id: str,
    customer_id: str,
    customer_phone: str,
    order_amount: float,
    amount: float,
    method: str,
    refund_type: str,
    coupon_code: str | None,
    notes: str | None,
) -> int                      # refund_id

approve_refund(refund_id: int) -> None
# pending_approval → pending

reject_refund(refund_id: int, reason: str) -> None
# → failed, appends reason to notes

process_refund(refund_id: int) -> None
# pending → processed

complete_refund(refund_id: int) -> None
# processed → completed, completed_at = NOW
```

### 9.3 CRM Calls

```python
get_crm_calls(
    call_status: str | None,
    assigned_to: int | None,
    order_status: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[sqlite3.Row]
# Includes assigned_agent_name via LEFT JOIN

get_crm_call_by_id(call_id: int) -> sqlite3.Row | None
get_crm_call_counts() -> dict[str, int]
start_crm_call(call_id: int) -> None           # → in_progress + started_at
save_crm_draft(call_id, reached_out, drop_off, reordered, notes) -> None
complete_crm_call(call_id, reached_out, drop_off, reordered, notes) -> None
reassign_crm_call(call_id: int, new_agent_id: int) -> None
get_crm_calls_for_customer(phone: str) -> list[sqlite3.Row]
get_crm_calls_for_agent(agent_id: int, limit: int = 5) -> list[sqlite3.Row]
```

### 9.4 Short Picks

```python
get_short_picks(
    action_status: str | None,
    assigned_to: int | None,
    store: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[sqlite3.Row]

get_short_pick_by_id(sp_id: int) -> sqlite3.Row | None
get_short_pick_counts() -> dict[str, int]
start_short_pick(sp_id: int) -> None           # → in_progress + started_at
save_short_pick_draft(sp_id, reached_out, response, resolution, notes) -> None
complete_short_pick_action(sp_id, reached_out, response, resolution, notes) -> None
reassign_short_pick(sp_id: int, new_agent_id: int) -> None
get_short_picks_for_agent(agent_id: int, limit: int = 5) -> list[sqlite3.Row]
```

### 9.5 Users & Availability

```python
get_cx_users(active_only: bool = True) -> list[sqlite3.Row]
get_cx_user_by_id(user_id: int) -> sqlite3.Row | None
create_cx_user(name, email, phone, role) -> int
update_cx_user(user_id, name, email, phone, role) -> None
delete_cx_user(user_id: int) -> None          # Sets is_active = 0
toggle_availability(user_id: int, is_available: bool) -> None
assign_calls_to_available_agents() -> None    # Round-robin unassigned pending calls
get_stores() -> list[sqlite3.Row]
```

### 9.6 Dashboard

```python
get_dashboard_stats_admin() -> dict
# Keys: open_returns, open_refunds, open_crm_calls, open_short_picks

get_dashboard_stats_agent(agent_id: int) -> dict
# Keys: my_returns, my_refunds, my_calls, my_short_picks

get_agent_queue_summary() -> list[sqlite3.Row]
# One row per active user: name, role, is_available, open_returns, open_calls, open_short_picks

get_returns_for_agent(agent_id: int, limit: int = 5) -> list[sqlite3.Row]
get_crm_calls_for_agent(agent_id: int, limit: int = 5) -> list[sqlite3.Row]
get_short_picks_for_agent(agent_id: int, limit: int = 5) -> list[sqlite3.Row]
```

---

## 10. UI Design System

### 10.1 Streamlit Config (`.streamlit/config.toml`)

```toml
[theme]
primaryColor               = "#6d28d9"
backgroundColor            = "#ffffff"
secondaryBackgroundColor   = "#f8f5ff"
textColor                  = "#1e1e2e"
font                       = "sans serif"
```

### 10.2 Global CSS (injected in `app.py`)

| Element | Style |
|---------|-------|
| Font | Inter, -apple-system |
| Sidebar background | `linear-gradient(180deg, #1e1b4b 0%, #2e1065 100%)` |
| Sidebar nav default | `#e8d5e8` (mauve), `font-weight: 500` |
| Sidebar nav active | white text, `rgba(180,130,180,0.28)` background |
| Primary button | `linear-gradient(135deg, #6d28d9, #4f46e5)` |
| Input focus ring | `#6d28d9` |
| Active tab | `#6d28d9` border-bottom |
| KPI card | White card, 4px left border in accent colour |
| Detail containers | `border: 1px solid #ede9fe`, `border-radius: 14px`, purple shadow |

### 10.3 Status Colour Reference

**Returns:**
| Status | Hex |
|--------|-----|
| pending_action | #f0a500 |
| pending_approval | #e07b00 |
| pending_pickup | #1a73e8 |
| out_for_pickup | #7b1fa2 |
| completed | #2e7d32 |
| cancelled | #c62828 |

**Refunds:**
| Status | Hex |
|--------|-----|
| pending_approval | #7c3aed |
| pending | #f0a500 |
| processed | #0284c7 |
| completed | #2e7d32 |
| failed | #c62828 |

**Order Status:**
| Status | Hex |
|--------|-----|
| delivered | #2e7d32 |
| cancelled/canceled | #c62828 |
| failed | #991b1b |
| undelivered | #ea580c |
| pending | #f0a500 |
| confirmed | #1a73e8 |
| rto_out_for_delivery | #7b1fa2 |
| rto_delivered | #6d28d9 |

---

## 11. Session State & Navigation

### 11.1 Global Session Keys

| Key | Type | Notes |
|-----|------|-------|
| `current_user` | dict | Set on login, cleared on logout |

### 11.2 Per-Module Session Keys

| Key | Set By | Used By |
|-----|--------|---------|
| `selected_<status_key>` | Returns page / Dashboard | Returns detail panel per tab |
| `open_refund_<status_key>` | Refunds page | Refunds detail panel per tab |
| `order_selected` | Orders page | Orders detail panel |
| `cust_selected` | Customers page | Customer profile panel |
| `selected_<tab_status>` | CRM / Short Picks | Detail panels |
| `show_manual_create` | Returns page | Manual create modal visibility |
| `show_manual_refund` | Refunds page | Manual refund form visibility |
| `ret_form_<order_id>` | Orders page | Return form visibility per order |
| `ret_items` | Orders / Returns page | Manual items list state |
| `manual_ret_items` | Returns manual create | Manual items list state |
| `orders_page` | Orders page | Pagination page number |

### 11.3 Deep-Link Navigation (Dashboard → Module)

```python
# Returns queue item
st.session_state["selected_pending_action"] = return_id
st.switch_page("pages/1_Returns.py")

# CRM queue item
st.session_state["selected_pending"] = call_id
st.switch_page("pages/7_CRM_Calling.py")

# Short Picks queue item
st.session_state["selected_pending"] = sp_id
st.switch_page("pages/8_Short_Picks.py")
```

---

## 12. Test Cases

### 12.1 Authentication

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| A1 | Login success | User exists in DB | Select user from dropdown → click Login | Session state set, redirected to Dashboard |
| A2 | Page access denied | Logged in as agent | Navigate to Users page directly | "🚫 Access Denied" shown, page stops |
| A3 | Logout clears session | Logged in | Click Log Out | Returns to login screen, session cleared |
| A4 | Admin bypass | Logged in as admin | Access any page | Always allowed, no permission errors |
| A5 | Sidebar visibility | Logged in as wh_user | Check sidebar nav | Customers/Orders not shown or blocked |

---

### 12.2 Returns Module

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| R1 | View all returns | Agent logged in | Open Returns, "All" tab | Table renders with all returns |
| R2 | Filter by status | Any user | Select "Pending Action" tab | Only pending_action returns shown |
| R3 | Filter by store | Any user | Expand filters, select store | Table filters correctly |
| R4 | Filter by agent | Supervisor | Select agent in filter | Only that agent's returns shown |
| R5 | Date range filter | Any user | Set from/to dates | Returns filtered within date range |
| R6 | Open detail panel | Agent | Click Open on a pending_action return | Detail panel expands below row |
| R7 | Close detail panel | Panel open | Click Close | Panel collapses |
| R8 | Submit pending_action | Agent, return in pending_action | Fill all required fields → Submit for Approval | Status changes to pending_approval, panel closes |
| R9 | Validate required fields | Agent | Submit without picking reason | Error shown, no DB update |
| R10 | Approve return | CX Lead, return in pending_approval | Click ✓ Approve | Status → pending_pickup |
| R11 | Reject with reason | CX Lead, return in pending_approval | Open Reject expander, enter reason, confirm | Status → cancelled, rejection_reason saved |
| R12 | Reject without reason | CX Lead | Click Confirm Reject without text | Error: "Please enter a rejection reason" |
| R13 | Send to Pidge | WH User, return in pending_pickup | Select store → Send to Pidge | Status → out_for_pickup, Pidge ID generated |
| R14 | Simulate Pidge complete | Admin, return out_for_pickup and type=return | Click Simulate Pidge Complete | Status → completed, refund auto-created |
| R15 | Exchange no refund | Admin, out_for_pickup, type=exchange | Simulate Pidge complete | Status → completed, NO refund created |
| R16 | Type hidden in pending_action tab | Any user | View pending_action tab table | Type column absent |
| R17 | Type shown in pending_approval tab | Any user | View pending_approval tab | Type column present |
| R18 | Manual create return | Agent | Click "＋ Create Manual Return" | Modal opens, form renders |
| R19 | Manual create skips to pending_approval | Agent | Fill form and submit | Return created with status=pending_approval |
| R20 | Manual create without items | Agent | Submit without item name | Error: "Add at least one item" |
| R21 | Manual create without order ID | Agent | Submit without order ID | Error: "Enter an Order ID" |
| R22 | Dashboard deeplink | Agent | Click "Open" on returns queue item | Navigates to Returns, correct panel auto-opened |
| R23 | WH user cannot submit form | WH user, pending_action | Open detail panel | No form shown for wh_user |
| R24 | Store + Payment columns present | Any user | View any tab | Store and Payment columns visible |
| R25 | COD refund source | Agent | Select payment=COD, type=return | Only cod_wallet shown in refund source |
| R26 | Exchange no refund source | Agent | Select type=exchange | Refund source field hidden |

---

### 12.3 Refunds Module

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| RF1 | View all refunds | CX Lead | Open Refunds, All tab | Table shows all 34+ seeded records |
| RF2 | Status tab counts | Any user | Check tab headers | Counts match actual records |
| RF3 | Approve refund | CX Lead, pending_approval | Click ✅ Approve | Status → pending |
| RF4 | Reject refund | CX Lead, pending_approval | Enter reason → ❌ Reject | Status → failed |
| RF5 | Reject without reason | CX Lead | Click Reject without text | Error shown |
| RF6 | Process refund | CX Lead, pending | Click 🔄 Mark Processed | Status → processed |
| RF7 | Complete refund | CX Lead, processed | Click ✔ Mark Completed | Status → completed, completed_at set |
| RF8 | Manual refund form | CX Lead | Click ＋ Manual Refund | Form opens |
| RF9 | Order ID lookup | CX Lead | Enter valid order ID | Phone + amount auto-populated |
| RF10 | Invalid order ID | CX Lead | Enter non-existent order ID | Warning shown, submit blocked |
| RF11 | Admin override amount | Admin | Open manual refund | Editable amount field shown |
| RF12 | Non-admin cannot override | Agent | Open manual refund | Amount locked to order_amount |
| RF13 | Linked return shows | Any user | Open detail for return-linked refund | Return ID, status, type shown |
| RF14 | Agent cannot create | Agent | Check for ＋ Manual Refund button | Button not shown |
| RF15 | Method filter works | Any user | Filter by wallet | Only wallet refunds shown |

---

### 12.4 Orders Module

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| O1 | CSV loads | data/orders.csv exists | Open Orders page | Table renders with 50k orders |
| O2 | Search by order ID | Any user | Type order ID in search | Matching rows shown |
| O3 | Search by phone | Any user | Type phone number | Orders for that phone shown |
| O4 | Status filter | Any user | Select "delivered" | Only delivered orders shown |
| O5 | Store filter | Any user | Select store | Only that store's orders shown |
| O6 | Returns only filter | Any user | Check "Returns only" | Only Is Return=1 rows |
| O7 | Pagination works | Any user | Click Next | Next 50 rows shown |
| O8 | Click row to open | Any user | Click row in dataframe | Detail panel opens below |
| O9 | Store tab label correct | Any user | Open order with items | Tab shows store name e.g. "Gurgaon" |
| O10 | Items table renders | Any user, order with items | Open detail | Items with name, brand, SKU, qty, price, sell price, discount |
| O11 | No Status column | Any user | Look at items table | Status column absent; badges inline |
| O12 | Order summary shows | Any user, order with items | Open detail | Summary card with all 8 lines |
| O13 | Coupon discount in summary | Any user, order with coupon | Open detail | Coupon discount shows in summary |
| O14 | Return button shown | Admin, delivered order | Open detail panel | "↩ Return Item(s)" button visible |
| O15 | Return button hidden (non-delivered) | Admin, cancelled order | Open detail panel | Return button not shown |
| O16 | Return form opens full-width | Admin | Click Return Item(s) | Form opens below info cards, not cramped |
| O17 | Return submitted successfully | Admin, delivered order | Select items, fill form, submit | Success toast, RET-XXX created |
| O18 | Return already exists | Any user, order with return | Open detail | Return status badge shown, no new Return button |
| O19 | Item multiselect shows items | Any user, order with details | Click Return Item(s) | Items from order_details CSV in multiselect |

---

### 12.5 Customers Module

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| C1 | Customer list loads | CSV exists | Open Customers page | Aggregated customer list renders |
| C2 | Search by phone | Any user | Type phone | Matching customers shown |
| C3 | Search by user ID | Any user | Type user ID | Matching customer shown |
| C4 | Pagination | Any user | Navigate pages | 30 customers per page |
| C5 | Click row opens profile | Any user | Click row in dataframe | Profile panel opens below |
| C6 | KPI metrics correct | Any user | Open profile | Orders/Spent/Returns match CSV data |
| C7 | Coupons shown | Any user, customer with coupons | Open profile | Coupon pills displayed |
| C8 | Order history expands | Any user | Click Order History | Recent 10 orders shown |
| C9 | Show all toggle | Any user | Check "Show all" | All orders shown |
| C10 | Returns section appears | Any user, customer with DB returns | Open profile | Returns expander shows |
| C11 | CRM calls section appears | Any user, customer with calls | Open profile | CRM calls expander shows |
| C12 | Close profile | Any user | Click ✕ Close | Profile panel collapses |

---

### 12.6 CRM Calling Module

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| CR1 | View all calls | Agent | Open CRM Calling, All tab | Table renders |
| CR2 | Agent sees own calls | Agent | Open Pending tab | Only calls assigned to that agent |
| CR3 | Supervisor sees all | Supervisor | Open Pending tab | All pending calls regardless of agent |
| CR4 | Auto-in-progress | Agent | Open detail of pending call | Status → in_progress, started_at set |
| CR5 | Save draft | Agent | Fill form → Save Draft | Fields saved, status stays in_progress |
| CR6 | Complete call | Agent | Fill all fields → Submit | Status → completed, completed_at set |
| CR7 | Submit without fields | Agent | Click Submit with empty fields | Error: "Please fill all required fields" |
| CR8 | Reassign visible | Supervisor | Open detail of any call | Reassign selectbox + button shown |
| CR9 | Reassign works | Supervisor | Select new agent → Save | assigned_to updated in DB |
| CR10 | Reassign not visible | Agent | Open detail panel | No reassign section shown |
| CR11 | Availability auto-assigns | Agent | Toggle to Available | Unassigned calls distributed |
| CR12 | Optional columns work | Any user | Toggle column options | Table updates with/without columns |
| CR13 | Order status filter | Supervisor | Filter by "cancelled" | Only cancelled order calls shown |
| CR14 | Dashboard deeplink | Agent | Click Open in CRM queue | Navigates to CRM, panel auto-opened |

---

### 12.7 Short Picks Module

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| SP1 | View short picks | Any user | Open Short Picks | Seeded records render |
| SP2 | Auto-in-progress | Agent | Open pending panel | Status → in_progress |
| SP3 | Save draft | Agent | Fill form → Save Draft | Saved, stays in_progress |
| SP4 | Complete action | Agent | Fill all → Submit | Status → completed |
| SP5 | Admin edit completed | Admin | Open completed, edit | ✓ Update button shown, update works |
| SP6 | Reassign | Supervisor | Reassign to other agent | assigned_to updated |
| SP7 | Short items displayed | Any user | Open detail | Short item names + SKUs listed |
| SP8 | Item count badge | Any user | View table | Count badge shows correct number |

---

### 12.8 User Management

| # | Test | Precondition | Steps | Expected Result |
|---|------|-------------|-------|----------------|
| U1 | Admin can access | Admin | Open Users page | Page renders |
| U2 | Non-admin blocked | Agent | Navigate to Users | "🚫 Access Denied" |
| U3 | Create user | Admin | Fill form → Create | New user in DB, appears in list |
| U4 | Edit user | Admin | Click Edit → change role → Save | Role updated in DB |
| U5 | Deactivate user | Admin | Click Delete on other user | User removed from active list |
| U6 | Cannot deactivate self | Admin | Click Delete on own account | Error: "Cannot deactivate yourself" |

---

### 12.9 RBAC Edge Cases

| # | Test | Expected |
|---|------|---------|
| RBAC1 | WH user opens Returns | Can view, no action buttons on pending_action |
| RBAC2 | Agent opens pending_approval | Sees "Awaiting CX Lead approval", no Approve button |
| RBAC3 | Agent tries manual refund | "＋ Manual Refund" button absent |
| RBAC4 | Agent on completed return | Read-only view |
| RBAC5 | Admin on any module | Full access, all buttons visible |
| RBAC6 | DB permissions missing | Falls back to _DEFAULTS in rbac.py |
| RBAC7 | Admin override_amount | Amount input editable in manual refund |
| RBAC8 | Non-admin override_amount | Amount display-only, locked to order_amount |

---

### 12.10 Data Integrity

| # | Test | Expected |
|---|------|---------|
| DI1 | Return created → items saved | return_items table populated |
| DI2 | Pidge complete on return | Refund auto-created with correct amount |
| DI3 | Pidge complete on exchange | No refund created |
| DI4 | Approve refund updates status only | Other fields unchanged |
| DI5 | Reject refund appends reason to notes | Notes: "...| Rejected: {reason}" |
| DI6 | Duplicate order_id in crm_calls | UNIQUE constraint raises error |
| DI7 | Return items total_value | Matches SUM(return_amount) across items |
| DI8 | init_db idempotent | Safe to call multiple times |
| DI9 | Seed runs once | Only seeds when cx_users count = 0 |

---

## 13. Deployment

### 13.1 Streamlit Cloud

- **URL:** `ozi-cx.streamlit.app`
- **Repo:** `github.com/ishaansindhu3005/CX-dashboard`
- **Branch:** `main`
- **Entry point:** `app.py`
- **Python:** 3.11 (Streamlit Cloud default)

### 13.2 Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `DB_PATH` | `../ozi_cx.db` | Override to MySQL DSN for production |

### 13.3 Deployment Notes

- SQLite DB is **ephemeral** on Streamlit Cloud (resets on restart) — `seed.py` runs automatically on cold start (`_user_count == 0`)
- `data/orders.csv` (18MB) and `data/order_details.csv` (27MB) are tracked in git and available on Cloud
- `ozi_cx.db` is in `.gitignore` — never committed
- Streamlit Cloud triggers redeploy on every push to `main`

### 13.4 Production Migration Path

1. Provision MySQL instance (Cloud SQL / RDS)
2. Set `DB_PATH` env var to MySQL DSN
3. In `db/connection.py`: replace `sqlite3` with `mysql.connector`, change `?` → `%s`
4. Remove WAL pragma
5. Run `seed.py` once against MySQL to initialise

---

## 14. Known Gaps & Future Roadmap

### 14.1 Not Implemented in v1

| Feature | Notes |
|---------|-------|
| `pages/6_Roles.py` | Placeholder exists, no UI built |
| Real Pidge API | Currently simulated with UUID generation |
| Real OMS sync | `utils/oms_sync.py` is a stub |
| Wallet credit system | Returns `0` for all customers |
| Plotly charts | Imported, not used |
| Bulk actions | No multi-select on any table |
| Notifications | No push/email notifications |
| File attachments | No image/doc upload for returns |
| Call recording | No audio logging |
| Return barcode scanning | Not applicable for web |

### 14.2 Prioritised Backlog

| Priority | Feature | Module |
|----------|---------|--------|
| P0 | MySQL migration (persistent DB) | Infrastructure |
| P0 | Roles management UI | Roles (6_Roles.py) |
| P1 | Real Pidge API integration | Returns |
| P1 | OMS short-pick sync | Short Picks |
| P1 | Analytics tab (Plotly charts) | Dashboard |
| P2 | Bulk approve/reject returns | Returns |
| P2 | Wallet credit lookup | Customers |
| P2 | WhatsApp bot integration | CRM Calling |
| P3 | Delivery fee in order summary | Orders |
| P3 | Mobile-responsive layout | All |
| P3 | Export to CSV/Excel | Returns, Refunds |
| P3 | Audit log (who changed what) | All |

---

*End of PRD v1.0 — Ozi CX Dashboard*
