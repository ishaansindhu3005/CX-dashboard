# Ozi CX Dashboard — Product & Business Flow Document

> **Version:** 1.0 · **Date:** March 2026 · **Author:** Ishaan Sindhu, Ozi · **Status:** Production (v1)

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Objective](#objective)
- [Functional Requirements](#functional-requirements)
  - [Module 1 — Authentication & Access Control](#module-1--authentication--access-control)
  - [Module 2 — Dashboard (Home)](#module-2--dashboard-home)
  - [Module 3 — Orders](#module-3--orders)
  - [Module 4 — Customers](#module-4--customers-phase-2)
  - [Module 5 — Returns & Exchanges](#module-5--returns--exchanges)
  - [Module 6 — Refunds](#module-6--refunds)
  - [Module 7 — CRM Calling](#module-7--crm-calling)
  - [Module 8 — Short Picks](#module-8--short-picks)
  - [Module 9 — User Management](#module-9--user-management-admin-only)
- [Goals & Success Metrics](#goals--success-metrics)
- [Non-Functional Requirements](#non-functional-requirements)
- [Analytics & Events](#analytics--events)
- [Test Cases](#test-cases)
- [Rollout Plan](#rollout-plan)
- [Known Gaps & v2 Items](#known-gaps--v2-items)

---

## Problem Statement

### 1. Operational Fragmentation

Ozi's CX team manages all post-order customer issues across a patchwork of unconnected tools — WhatsApp groups, PhP Admin Panel, Pidge (delivery ops), Razorpay (payments), and a Google Sheet. Every return, refund, and retention call requires an agent to switch between 4–5 tabs with no single source of truth.

- No audit trail on return approvals, pending returns, or action bias by CX agent against a return.
- Agents, leads, and leadership have no real-time visibility into the status of a return after handoff.
- Refunds are initiated inconsistently — sometimes via Admin Panel, sometimes manually via finance over WhatsApp — with no structured approval gate.
- No logging system for outbound retention calls, so the same customer can be called multiple times, or never at all.

### 2. Warehouse–CX Coordination Is Manual

When a warehouse short-picks an order (cannot fulfil an item), there is no structured handoff to CX. The warehouse team messages on WhatsApp, CX calls the customer, but none of this is logged. The customer may not get a call, or may receive multiple calls.

### 3. No Unified Customer View

An agent handling a complaint has to search three separate systems to answer: *"Has this customer returned before? Did they have a CRM call? What coupons have they used?"* This slows resolution and affects service quality.

---

## Objective

Build an **internal multi-role CX management dashboard** for Ozi that:

1. Centralises all post-order workflows (returns, exchanges, refunds, calls, short picks) into one tool.
2. Enforces a structured approval hierarchy — agents submit, CX Leads approve, warehouse dispatches — with a full audit trail.
3. Gives every CX role a personalised view of their work queue so they start each shift knowing exactly what to do.
4. Provides supervisors and admins with a real-time operational health view across the entire team.

---

## Functional Requirements

---

### Module 1 — Authentication & Access Control

**What it does:** Controls who can log in and what they can see and do.

**User-facing behaviour:**

Users have a login/password-based login similar to OMS. Inside the CX dashboard, admins can add users and assign them roles and permissions. Once logged in, the sidebar shows:

- The Ozi CX wordmark.
- The agent's initials in a circular avatar, colour-coded by role:
  - 🔴 Admin · 🟠 Supervisor · 🟣 CX Lead · 🔵 Agent
- A role badge (e.g. `Supervisor`).
- An **availability toggle** — agents mark themselves Available or Unavailable for the shift. When marked Available, unassigned calls and short pick cases are automatically distributed via round-robin.
- Navigation to all modules they have access to.
- A logout button.

**Permission rules:**

| Action | Minimum Role Required |
|---|---|
| Approve or reject a return | CX Lead |
| Send a return to Pidge | Warehouse User |
| Create or deactivate users | Admin |
| Override refund amount | Admin |
| Initiate a return from Orders | Agent |
| Approve their own submission | ❌ Not permitted |

---

### Module 2 — Dashboard (Home)

**What it does:** Gives each user a personalised operational view when they open the app.

#### Supervisor / Admin / CX Lead View

Four KPI cards at the top:

| Card | What it shows |
|---|---|
| Open Returns | Total active returns not yet completed or cancelled |
| Open Refunds | Total refunds not yet completed or failed |
| Open CRM Calls | Total retention calls not yet completed |
| Open Short Picks | Total short-pick actions not yet completed |

Below the KPIs: a **team queue table** showing every CX agent — their availability status, and how many open returns, calls, and short picks are assigned to them. Supervisors use this to spot overloaded agents and redistribute work.

#### Agent View

Same four KPI cards, scoped to the agent's own workload. Below that, three side-by-side work queues:

- **My Returns** — up to 5 returns assigned to this agent needing action.
- **My CRM Calls** — up to 5 pending retention calls assigned to this agent.
- **My Short Picks** — up to 5 short-pick actions assigned to this agent.

All Order IDs are clickable and open into the respective order details page within the relevant module.

Empty queue = green **✓ All clear** card. This is the agent's daily task list.

---

### Module 3 — Orders

**What it does:** A unified order lookup tool. Agents can search any order, see all its details, and initiate a return directly from here.

> **Note:** Can import and replicate OMS orders flow here. Interface is fine for our use-case; only the return via admin panel flow needs to be included.

#### CX Actions Card (right)

| Order State | What the card shows |
|---|---|
| Return already exists | Return status badge + link to Returns module |
| Delivered, no return | **↩ Return Item(s)** button |
| Not yet delivered | "Returns are only for delivered orders" message |

#### Return Initiation Form

Appears full-width below the info row when the agent clicks **Return Item(s)**. The agent can:

- Select which items to return.
- Specify return vs. exchange.
- Select payment method (prepaid vs. COD).
- Enter the reason, pickup date/time slot, and notes.

Submitting creates a return in the Returns module at the **Pending Approval** stage.

#### Items Table (below, grouped by store)

Columns: Item name + brand (with return/Rx badge if applicable) · SKU · Quantity · MRP price · Selling price · Discount.

#### Order Summary Card

| Line | What it represents |
|---|---|
| Items Price | Full MRP value of all items |
| Subtotal | Total selling price after item-level discounts |
| Discount | Total item-level discount |
| Coupon Discount | Coupon applied at checkout |
| Delivery Fee | Delivery charge (₹0 if free delivery) |
| Gift Fee | Gift wrapping fee if opted in |
| **Total** | Final order amount charged |
| Wallet Amount | Wallet balance used |
| **Payable Amount** | Amount actually collected from customer |

---

### Module 4 — Customers *(Phase 2)*

**What it does:** A 360° customer profile tool. Agents can look up any customer by phone or user ID and see their full history across orders, returns, calls, and coupons.

#### Customer List

- Search by phone or user ID.
- Table columns: User ID · Phone · Total Orders · Returns · Total Spent · First Order Date · Customer Type (New/Repeat).

#### Customer Profile Panel

Four KPI chips:

- Total Orders placed.
- Total Amount Spent (₹).
- Total Returns initiated.
- Wallet Credits received (completed wallet/COD wallet refunds from the system).

**Order History:** All past orders (expandable) — Order ID, Date, Amount, Status, Store, Return flag.

**Returns in System:** All returns logged against this customer's phone — Return ID, status, type (return/exchange), date.

**CRM Calls:** All retention calls logged against this customer — Order ID, call status, drop-off reason.

---

### Module 5 — Returns & Exchanges

**What it does:** The core operational hub for the returns and exchange lifecycle. Every return flows through a structured multi-stage process, each stage owned by a different role.

#### Stages & Ownership

| Stage | What's happening | Who acts |
|---|---|---|
| Pending Action | Return flagged; agent needs to fill in details | Agent |
| Pending Approval | Details submitted; waiting for CX Lead to approve | CX Lead / Supervisor |
| Pickup Status | Pending at WH for allocation to Pidge / rider en route | No action needed |
| Completed | Item collected; refund triggered | — |
| Cancelled | Rejected by CX Lead, or rejected by customer (via Pidge order status) | — |

**Tabs:** One tab per stage with a count badge. An **All** tab shows everything.

#### Filters

- Customer name or phone.
- Store (which dark store the order came from).
- Agent assigned to the return.
- Return type (return vs. exchange).
- Return source (app / chatbot / admin panel / CX portal).
- Payment method (prepaid vs. COD).
- Date range (from / to).

**Summary metrics above the table:** Total count · Total return value · Count created today · Returns vs. exchanges breakdown.

#### What Each Role Sees in the Detail Panel

**Agent — Pending Action**

Fills in the return form:

- Return type (return or exchange).
- Whether they spoke to the customer (yes / no / attempted).
- Whether they pitched an exchange before proceeding (yes / no / N/A).
- Return reason: wrong product / damaged / expired / size issue / not as expected / other.
- Refund source — prepaid: wallet credit or original source; COD: wallet only; hidden if exchange.
- Pickup date and preferred time slot (7 slots; minimum today).
- Internal notes.

Submitting moves the return to **Pending Approval**.

**CX Lead — Pending Approval**

Sees all form details submitted by the agent (read-only). Return IDs here originate from:
- Pending Action tab (chatbot/app-routed orders).
- Entries created in the Orders page.
- Manual return button at the top of Returns.

CX Lead can either:
- ✅ **Approve** → moves to **Pending Pickup**.
- ❌ **Reject** → must provide a written reason → moves to **Cancelled**.

Agents see a *"Submitted — awaiting CX Lead approval"* message and cannot edit the return.

**Pickup Status — All roles**

Shows the Pidge tracking ID if one exists. If no Pidge order exists, shows a **Pending at WH** flag. No action needed from any user. Admin/Supervisor can simulate Pidge completion in v1 (real integration in v2), which marks the return **Completed** and auto-triggers a refund.

**Manual Return Creation — CX Lead and above**

A **Create Return** button at the top right lets CX Leads manually create a return (entering Order ID, customer details, and all fields) without the agent submission step. Used for edge cases (expired return window, non-app returns, admin-initiated refunds). Submits directly to **Pending Approval**.

> Only Admin, Supervisor, and CX Lead can create manual returns.

---

### Module 6 — Refunds

**What it does:** Tracks every refund from creation to completion, with a 3-step approval and processing flow. Refunds can be auto-created (triggered when a return completes) or manually created by CX Leads.

#### Refund Stages

| Stage | What's happening | Who acts |
|---|---|---|
| Pending | Waiting to be processed by finance/system | CX Lead / Supervisor |
| Processed | Payment initiated | CX Lead / Supervisor |
| Completed | Refund confirmed delivered to customer | — |
| Failed | Rejected or failed during processing | — |

**Refund types tracked:** App return · Chatbot return · Admin panel return · TnB refund · RTO refund · Manual (OOS, cancelled refunds).

**Refund methods tracked:** Wallet credit · Source refund (original payment method).

#### Key Rules

- COD orders can only receive wallet credits — no source refund possible (cash was never collected).
- Prepaid orders get a choice: wallet credit or original source refund.
- Refund amount is locked to the order amount for all roles **except Admin** (who can override).

> **Note on flow:** Most refunds are automated and will land directly in **Refund Processed** (if CX has already selected refund source) or in **Pending** (if CX received the WhatsApp message but hasn't selected a source). Only manual refunds without any system entry land in Pending as actionable items for the finance team.
>
> In the Pending refunds detail panel, Admin/Supervisor can fill in refund details (refund status, RRN, payment ID). Once submitted, the refund moves to the **Completed** tab.

#### Filters

Customer phone/name · Refund method · Refund type · Date range.

**Summary metrics:** Total refund count · Total refund amount.

#### Table Columns

Refund ID · Order ID · Customer · Order Amount · Refund Amount · Method · Type · Linked Return · Status.

#### Detail Panel

- **Left:** Full refund details — customer, amounts, method, type, any linked coupon, notes, timestamps.
- **Right:** Linked return (if auto-triggered), current status, and action buttons.

#### Manual Refund Creation — CX Lead and above

Enter an Order ID → system auto-fills customer phone, customer ID, and order amount (read-only). The CX Lead selects refund method, type, and adds notes. Admin can change the refund amount. Submits to **Pending**.

> Only Admin, Supervisor, and CX Lead can create manual refunds.

---

### Module 7 — CRM Calling

**What it does:** A structured retention call management system. When orders fail (RTO, cancelled, undelivered, failed payment), CX agents call customers to re-engage them. Every call is logged with outcome and reason.

**Why this exists:** Without this, agents work off a spreadsheet or WhatsApp list with no standard process, no logging, and no visibility into whether a customer was reached or what happened.

#### Call Stages

| Stage | What's happening |
|---|---|
| Pending | Call not yet attempted |
| In Progress | Agent has opened the call record and is working on it |
| Completed | Call logged with outcome |

**Auto-assignment:** When an agent marks themselves Available in the sidebar, unassigned pending calls are automatically distributed to them using round-robin logic. No supervisor needs to manually assign.

#### Filters (Pending tab)

- Order status: RTO / Cancelled / Failed / Undelivered / RTO_undelivered / Confirmed / Pending / etc.
- Date range (defaults to current month).

**Optional columns** (agent-selectable): New/Repeat flag · Coupon Code · Assigned Agent.

**Summary metrics:** Total calls · Total order value · Count completed.

#### Detail Panel

**Right column — context (read-only):**

- Order ID, customer name and phone, order amount, order status badge.
- Coupon code applied (if any).
- Assigned agent and timestamps.
- Admin/Supervisor: reassign dropdown.

**Left column — agent form:**

- **Reached out:** Yes / No / Attempted.
- **Drop-off reason:** CX unavailable · Not interested · Price too expensive · Bad delivery experience · Forgot coupon · Too slow · Product quality · Other.
- **Reordered:** Yes / No *(Phase 2: auto-driven by system — checks for new order against user ID/phone within 24 hours).*
- **Notes:** Free text.

**Two submission options:**

- 💾 **Save Draft** — saves progress without marking call complete. Agent can return to it.
- ✅ **Submit** — marks the call Completed.

---

### Module 8 — Short Picks

**What it does:** When a warehouse cannot fulfil one or more items in an order (short pick), a task is created for a CX agent to call the customer, explain the situation, and offer a resolution (refund, replacement, or cancellation).

**Why this exists:** Currently, warehouse staff message CX on WhatsApp when a short pick happens. There is no tracking of whether the customer was called, what was offered, or how it was resolved. Short picks can go unaddressed.

#### Short-Pick Stages

| Stage | What's happening |
|---|---|
| Pending | Short pick flagged; not yet assigned or actioned |
| In Progress | Agent has opened the record and is working on it |
| Completed | Resolution logged |

> **Sync with OMS:** In v1, a sync function stub exists. In production, short-pick records will auto-flow from the OMS when a warehouse confirms a short pick.

#### Filters (Pending tab)

Store code · Date range.

**Optional columns** (agent-selectable): Payment Method · Store · Assigned Agent.

**Table columns:** ID · Order ID · Customer · Amount · Short-picked Items (truncated preview) · Item count badge · Status.

#### Detail Panel

**Right column — context (read-only):**

- Full order context, payment method, store.
- List of short-picked items with name and SKU.
- Assigned agent, timestamps.
- Admin/Supervisor: reassign dropdown.

**Left column — agent form:**

- **Reached out:** Yes / No / Attempted.
- **Customer response:** Understood & Accepted / Upset / Wants Full Refund / Wants Replacement / No Response / Other.
- **Resolution:** Refund Initiated / Replacement Arranged / Partial Refund / Customer Cancelled / No Action Needed / Other.
- **Reordered:** Yes / No *(Phase 2: auto-driven by system).*
- **Notes:** Free text.

**Two submission options:**

- 💾 **Save Draft.**
- ✅ **Submit** — marks Completed.

> Admin/Supervisor can edit a completed record (flagged with an admin-edit marker for audit purposes).

---

### Module 9 — User Management *(Admin Only)*

**What it does:** Allows the Admin to manage the CX team roster inside the dashboard itself.

**User list:** All active team members with their role badge, email, and phone.

**Create user:** Admin fills in first and last name, email, phone number, username and password, and assigns a role. User is immediately active and can log in.

**Edit user:** Inline — Admin can update name, email, phone, and role for any user.

**Deactivate user:** Soft delete — marks the user inactive (they disappear from the team list and cannot log in). Admins cannot deactivate themselves.

---

## Goals & Success Metrics

### North Star Metric

> **Resolution Time** — average time from return/complaint creation to final resolution (refund completed or exchange dispatched).
>
> 🎯 Target: Reduce average resolution time by **70%** within 30 days of go-live.

### Primary Success Metrics

| Metric | Target |
|---|---|
| % of returns with full audit trail | 100% (vs. 0% today) |
| % of retention calls logged with outcome | 100% (vs. ~0% today) |
| % of short picks resolved within 24 hours | >90% (vs. unmeasurable today) |
| Returns stuck in Pending Action >24 hours | <10% |
| Average return-to-refund cycle time | <72 hours |
| Total refunds processed via system vs. total revenue | <2% of total net revenue |

### Secondary Success Metrics

**Operational:**
- Agent utilisation — are all agents handling roughly equal workloads?
- Approval bottleneck rate — how often do returns sit in Pending Approval for >4 hours?
- Refund failure rate — refunds that fail and need re-initiation.

**Quality:**
- Exchange pitch rate — what % of return-eligible cases did the agent pitch exchange first?
- Resolution mix — returns vs. exchanges vs. coupon resolutions over time.

**Customer:**
- Customers with >1 return in 30 days (repeat returners, potential abuse signals).
- Wallet credit accumulation per customer (customers being over-compensated).

### Guardrail Metrics

- No increase in escalations reaching Ishaan or Vaibhav directly (system should absorb this).
- No refunds processed outside the dashboard (compliance).
- Agent login rate >80% on all working days.

---

## Non-Functional Requirements

### Access Control

- All pages enforce role-based permissions server-side — there is no "view source and bypass" risk.
- Admin override is hardcoded (not DB-configurable) so a DB compromise cannot grant admin access to a non-admin.

### Data Integrity

- Returns and refunds are linked — a refund auto-created by a completed return is permanently linked to that return record.
- **Soft deletes only** — no records are permanently deleted. Admins deactivate users; returns are cancelled, not deleted.
- All status transitions are append-only in terms of audit — timestamps are recorded at each transition.

---

## Analytics & Events

### Return Events

| Event | Trigger |
|---|---|
| Return Created | Agent submits a return form (any source) |
| Return Approved | CX Lead clicks Approve |
| Return Rejected | CX Lead clicks Reject (with reason) |
| Return Sent to Pidge | Warehouse clicks Send to Pidge |
| Return Completed | Pidge confirms pickup |
| Return Cancelled | CX Lead rejects OR admin cancels |
| Manual Return Created | CX Lead uses Create Return form |

### Refund Events

| Event | Trigger |
|---|---|
| Refund Auto-Created | Return reaches Completed status |
| Refund Manually Created | CX Lead uses Create Refund form |
| Refund Approved | CX Lead clicks Approve |
| Refund Rejected | CX Lead clicks Reject |
| Refund Marked Processed | CX Lead marks Processed |
| Refund Completed | CX Lead marks Completed |
| Refund Failed | CX Lead marks Failed |

### CRM Calling Events

| Event | Trigger |
|---|---|
| Call Auto-Assigned | Agent marks Available → round-robin assigns |
| Call In Progress | Agent opens call detail panel |
| Call Draft Saved | Agent clicks Save Draft |
| Call Completed | Agent clicks Submit |
| Call Reassigned | Supervisor reassigns to different agent |

### Short Pick Events

| Event | Trigger |
|---|---|
| Short Pick Created | OMS sync (v2) or manual entry |
| Short Pick In Progress | Agent opens detail panel |
| Short Pick Draft Saved | Agent clicks Save Draft |
| Short Pick Completed | Agent clicks Submit |
| Short Pick Edited | Admin edits a completed record |

### System Events

| Event | Trigger |
|---|---|
| Agent Login | User selects name and logs in |
| Agent Marked Available | Sidebar toggle switched on |
| Agent Marked Unavailable | Sidebar toggle switched off |
| User Created | Admin creates new user |
| User Deactivated | Admin soft-deletes a user |

---

## Test Cases

### Authentication & Access Control

| ID | Scenario | Expected Behaviour |
|---|---|---|
| AUTH-01 | Agent logs in | Sees Dashboard, Orders, Customers, Returns, Refunds, CRM Calling, Short Picks. Does not see User Management. |
| AUTH-02 | Warehouse User logs in | Sees Dashboard, Returns, Refunds, CRM Calling, Short Picks. Does not see Orders or Customers. |
| AUTH-03 | Admin logs in | Sees all modules including User Management. |
| AUTH-04 | Agent tries to access a pending_approval return | Sees form fields as read-only. No Approve/Reject buttons visible. |
| AUTH-05 | CX Lead tries to access User Management by URL | Page shows access denied error. |
| AUTH-06 | Agent marks themselves Available | Unassigned pending calls are distributed to them (round-robin). |
| AUTH-07 | Admin deactivates their own account | System blocks with error: "Cannot deactivate yourself." |

### Dashboard

| ID | Scenario | Expected Behaviour |
|---|---|---|
| DASH-01 | Agent logs in with 3 pending returns, 2 calls | Dashboard shows 3 My Returns items, 2 My CRM Calls items, 0 My Short Picks. |
| DASH-02 | Agent clicks "Open" on a queue return | Deep-links to Returns module with that return already open. |
| DASH-03 | Supervisor view with 0 open items | All 4 KPI cards show 0. Team queue shows all agents with 0 workloads. |
| DASH-04 | Agent has no tasks | All 3 queue columns show green "✓ All clear" card. |

### Orders

| ID | Scenario | Expected Behaviour |
|---|---|---|
| ORD-01 | Agent searches by phone number | Table filters to all orders for that phone. |
| ORD-02 | Agent searches for a non-existent order ID | Table shows 0 results. |
| ORD-03 | Agent opens a delivered order with no existing return | CX Actions card shows "↩ Return Item(s)" button. |
| ORD-04 | Agent opens an order not yet delivered | CX Actions card shows "Returns only for delivered orders." No button. |
| ORD-05 | Agent opens an order that already has a return | CX Actions card shows the return status badge and a link to Returns module. |
| ORD-06 | Agent submits return form from Orders module | New return appears in Returns → Pending Approval tab with correct order ID and items. |
| ORD-07 | Order with a coupon — Order Summary | Coupon Discount line shows the correct coupon amount. Total matches order_amount from CSV. |
| ORD-08 | Order with gift wrapping | Gift Fee line shows non-zero value. |
| ORD-09 | COD order opened | Return form shows only "Wallet" as refund source option. |
| ORD-10 | Store tab label | Tab shows the store name (e.g. "Gurgaon"), not a numeric store ID. |

### Customers

| ID | Scenario | Expected Behaviour |
|---|---|---|
| CUST-01 | Search by phone — customer found | Profile panel shows correct total orders, spent, returns, and coupons. |
| CUST-02 | Search for phone not in CSV | Table shows 0 results. |
| CUST-03 | Customer with completed wallet refunds | Wallet Credits chip shows correct sum. |
| CUST-04 | Customer with no coupons ever used | Coupons Used section shows "None used." |
| CUST-05 | Customer with >10 orders | Order History shows last 10; "Show all" expander reveals rest. |
| CUST-06 | Customer with returns in the CX system | Returns section shows all linked returns with status. |
| CUST-07 | Customer with logged CRM calls | CRM Calls section shows all calls with drop-off reason. |

### Returns & Exchanges

| ID | Scenario | Expected Behaviour |
|---|---|---|
| RET-01 | Agent submits return form (all fields filled) | Return moves to Pending Approval. Submission form becomes read-only. |
| RET-02 | Agent tries to submit with missing required field | Form shows validation error. Return not created. |
| RET-03 | Agent submits exchange type | Refund Source field is hidden (not required for exchanges). |
| RET-04 | Agent submits COD order return | Refund Source shows only "Wallet" (no source refund). |
| RET-05 | CX Lead approves a return | Return moves to Pending Pickup. Agent sees "Approved — waiting for warehouse" message. |
| RET-06 | CX Lead rejects a return | Return moves to Cancelled. Rejection reason is recorded and displayed. |
| RET-07 | CX Lead rejects without entering reason | System blocks rejection. Reason is required. |
| RET-08 | Warehouse sends to Pidge | Return moves to Out for Pickup. Pidge tracking ID (PIDGE-XXXXXXXX) is generated and shown. |
| RET-09 | Return reaches Completed (type = return) | A refund record is automatically created in Refunds → Pending Approval. |
| RET-10 | Return reaches Completed (type = exchange) | No refund is auto-created. |
| RET-11 | Pending Action tab count | Badge count reflects actual number of pending_action returns. |
| RET-12 | Filter by store | Returns table filters correctly to only that store's returns. |
| RET-13 | Filter by date range | Returns outside date range are excluded. |
| RET-14 | Manual create by CX Lead | New return appears at Pending Approval (skips Pending Action stage). |
| RET-15 | Agent views completed return | Read-only view. No action buttons. Success message shown. |
| RET-16 | Agent views cancelled return | Read-only view. Rejection reason shown in red. |

### Refunds

| ID | Scenario | Expected Behaviour |
|---|---|---|
| REF-01 | Auto-created refund (from completed return) | Refund appears in Pending Approval with correct order amount, customer, and method. |
| REF-02 | CX Lead approves refund | Status moves to Pending. |
| REF-03 | CX Lead rejects refund | Status moves to Failed. |
| REF-04 | CX Lead marks Processed | Status moves to Processed. |
| REF-05 | CX Lead marks Completed | Status moves to Completed. |
| REF-06 | Manual refund — CX Lead enters Order ID | System auto-fills customer phone, ID, and order amount (read-only). |
| REF-07 | Manual refund — Admin creates | Refund Amount field is editable. Admin sets a custom amount. |
| REF-08 | Manual refund — non-Admin creates | Refund Amount field is locked to order amount. Cannot be changed. |
| REF-09 | COD order manual refund | Refund Method shows only Wallet options. |
| REF-10 | Filter by refund type | Table shows only selected type (e.g. only "undelivered" refunds). |

### CRM Calling

| ID | Scenario | Expected Behaviour |
|---|---|---|
| CRM-01 | Agent marks Available with unassigned calls | Pending calls distributed via round-robin. Count visible on Dashboard. |
| CRM-02 | Agent opens a pending call | Status automatically moves to In Progress. |
| CRM-03 | Agent saves draft | Call status remains In Progress. Form fields are saved. Agent can return and continue. |
| CRM-04 | Agent submits call with "Not Reached" | Reordered = No by default. Call marked Completed with notes. |
| CRM-05 | Supervisor reassigns call to different agent | Call appears in the new agent's My CRM Calls queue on their Dashboard. |
| CRM-06 | Filter by order status = RTO | Table shows only RTO-status orders. |
| CRM-07 | Agent tries to reassign a call | Reassign section is not visible to agents (supervisor-only). |
| CRM-08 | All calls completed | Dashboard CRM queue shows "✓ All clear" for agent. |

### Short Picks

| ID | Scenario | Expected Behaviour |
|---|---|---|
| SP-01 | Agent opens a pending short pick | Status moves to In Progress automatically. |
| SP-02 | Agent submits resolution | Status moves to Completed. Resolution and customer response logged. |
| SP-03 | Agent saves draft | Status remains In Progress. Form saved. |
| SP-04 | Supervisor reassigns short pick | New agent sees it in their Dashboard queue. |
| SP-05 | Admin edits a completed short pick | Edited record is flagged with admin-edit marker in the audit trail. |
| SP-06 | Agent tries to edit a completed short pick | Edit option not shown to agents. |
| SP-07 | Filter by store code | Only short picks from that store's orders shown. |

### User Management

| ID | Scenario | Expected Behaviour |
|---|---|---|
| USR-01 | Admin creates a new agent | New user appears in login dropdown. Can immediately log in. |
| USR-02 | Admin changes a user's role from Agent to Supervisor | User's permissions update immediately on next login. |
| USR-03 | Admin deactivates a user | User disappears from login dropdown and team queue. Existing records preserved. |
| USR-04 | Admin tries to deactivate themselves | System blocks with error message. |
| USR-05 | Supervisor tries to access User Management | Access denied page. Cannot create or deactivate users. |

---

## Rollout Plan

### Phase 0 — Internal Pilot *(Week 1–2)*

**Audience:** Ishaan + 2 agents (Bhawana, Himani)

**Goal:** Validate that the return flow works end-to-end in a real shift scenario.

Exit criteria:
- Returns can be created, approved, and dispatched without using WhatsApp.
- Refunds are created correctly when returns complete.
- CRM calls are logged with outcome.
- No data loss on app restart.

### Phase 1 — Full Team Onboarding *(Week 3–4)*

**Audience:** All CX agents.

**Goal:** All CX operations run through the dashboard. WhatsApp used only for communication, not approvals or tracking.

Actions:
- Training session for agents (30 min).
- Training session for CX Lead / Warehouse (20 min).
- Supervisor/Ishaan monitors Dashboard team queue daily.

Success check (end of Week 4):
- >80% of returns logged in the system.
- >80% of retention calls logged with outcome.
- <5 returns still handled on WhatsApp (exceptions allowed for unusual cases).

### Phase 2 — Process Lock-in *(Week 5–8)*

**Goal:** WhatsApp approvals fully eliminated. 100% compliance.

Actions:
- Ishaan spot-checks WhatsApp groups for any approvals that should be in the dashboard.
- Weekly review of Dashboard metrics: resolution time trend, agent utilisation, approval bottleneck.
- Feedback from agents on UX friction points — minor fixes shipped weekly.

### Phase 3 — Production Migration *(Month 3+)*

**Goal:** Move from SQLite (ephemeral on cloud restart) to MySQL (persistent). Replace CSV with live OMS/order API feeds.

Actions:
- Backend team sets up MySQL instance.
- DB layer swapped (only data layer changes — no UI changes required).
- OMS short-pick sync activated (real API, not stub).
- Pidge webhook integration activated for real return pickup tracking.

---

## Known Gaps & v2 Items

| Gap | Current State | v2 Plan |
|---|---|---|
| Pidge integration | Simulated ("Simulate Pidge Complete" button) | Real webhook from Pidge on RTO status |
| OMS short-pick sync | Stub function | Real OMS API integration |
| Payment gateway | Refunds marked "Completed" manually | Razorpay webhook confirms actual disbursement |
| WhatsApp notifications | Not built | Notify customer on return approval + pickup via WhatsApp API |
| Coupon validation in-dashboard | Not built | Create and validate ₹100/₹250 coupons directly in dashboard |
| CX performance reports | Not built | Tabular + chart view of agent resolution times, approval rates, call outcomes by week |
| Shift scheduling | Not built | Calendar-based shift planner for team leads |
| Mobile view | Not supported | Responsive layout for warehouse staff on phones |
| Freshchat / Callyser integration | External | Log incoming chats and calls as CX cases inside the dashboard |
| Returns to Pidge via OMS | Manual | Overhaul return visibility on OMS as well |

---
