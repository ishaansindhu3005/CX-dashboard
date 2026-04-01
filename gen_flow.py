#!/usr/bin/env python3
"""Generate Ozi CX Dashboard end-to-end flow diagram as SVG."""

W, H = 1440, 1860

C = {
    'bg':     '#f8f5ff',
    'dark':   '#1e1b4b',
    'purple': '#6d28d9',
    'lpurple':'#ede9fe',
    'border': '#c4b5fd',
    'agent':  '#3b82f6', 'abg': '#dbeafe',
    'lead':   '#8b5cf6', 'lbg': '#f3e8ff',
    'wh':     '#10b981', 'wbg': '#d1fae5',
    'sup':    '#f97316', 'sbg': '#ffedd5',
    'adm':    '#ef4444', 'admb':'#fee2e2',
    'sys':    '#64748b', 'sysbg':'#f1f5f9',
    'cust':   '#ca8a04', 'custbg':'#fef9c3',
    'txt':    '#1e1e2e',
    'muted':  '#9ca3af',
    'white':  '#ffffff',
    'ok':     '#10b981',
    'err':    '#ef4444',
    'line':   '#d1d5db',
}

def e(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def rect(x,y,w,h,fill,stroke=None,rx=8,sw=1.5,dash=None,op=1):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="{rx}"'
    if stroke: s += f' stroke="{stroke}" stroke-width="{sw}"'
    if dash: s += f' stroke-dasharray="{dash}"'
    if op!=1: s += f' opacity="{op}"'
    return s+'/>',

def T(x,y,t,sz=12,fill='#1e1e2e',bold=False,a='middle',b='middle'):
    fw = '600' if bold else 'normal'
    return f'<text x="{x}" y="{y}" font-size="{sz}" fill="{fill}" font-weight="{fw}" text-anchor="{a}" dominant-baseline="{b}">{e(t)}</text>'

def line(x1,y1,x2,y2,color='#d1d5db',sw=1,dash=None):
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"'
    if dash: s += f' stroke-dasharray="{dash}"'
    return s+'/>'

def arrow_h(x1,y,x2,color='#9ca3af',sw=1.5,marker='arr'):
    return f'<line x1="{x1}" y1="{y}" x2="{x2-2}" y2="{y}" stroke="{color}" stroke-width="{sw}" marker-end="url(#{marker})"/>'

def arrow_v(x,y1,y2,color='#9ca3af',sw=1.5,marker='arr'):
    return f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2-2}" stroke="{color}" stroke-width="{sw}" marker-end="url(#{marker})"/>'

def pill(x,y,w,h,bg,border,label,sz=11):
    return [
        *rect(x,y,w,h,bg,border,rx=h//2,sw=1.5),
        T(x+w//2,y+h//2,label,sz=sz,fill=border,bold=True),
    ]

def card(x,y,w,h,bg,border,lines,bold_first=True):
    """Multi-line card."""
    els = [*rect(x,y,w,h,bg,border,rx=8,sw=1.5)]
    n = len(lines)
    pad = 10
    usable = h - 2*pad
    step = usable // max(n,1)
    for i,ln in enumerate(lines):
        cy = y + pad + i*step + step//2
        bld = bold_first and i==0
        sz = 11 if bld else 10
        els.append(T(x+w//2, cy, ln, sz=sz, fill=C['txt'] if not bld else border, bold=bld))
    return els

# ── Build SVG ──────────────────────────────────────────────────────────────

parts = []

# SVG root + defs
parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     font-family="'Segoe UI',system-ui,Arial,sans-serif">
<defs>
  <marker id="arr"     markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#9ca3af"/></marker>
  <marker id="arr_p"   markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#6d28d9"/></marker>
  <marker id="arr_ok"  markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#10b981"/></marker>
  <marker id="arr_err" markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#ef4444"/></marker>
  <marker id="arr_b"   markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#3b82f6"/></marker>
  <marker id="arr_g"   markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#10b981"/></marker>
  <marker id="arr_o"   markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#f97316"/></marker>
  <filter id="sh"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#1e1b4b" flood-opacity="0.07"/></filter>
</defs>''')

def emit(*els):
    for el in els:
        if isinstance(el,(list,tuple)):
            for e2 in el:
                parts.append(e2)
        else:
            parts.append(el)

# Background
emit(*rect(0,0,W,H,C['bg'],rx=0))

# ── HEADER ────────────────────────────────────────────────────
emit(*rect(0,0,W,68,C['dark'],rx=0))
emit(T(W//2,24,'Ozi CX Dashboard — End-to-End Operational Flow',sz=20,fill=C['white'],bold=True))
emit(T(W//2,48,'v1.0 · March 2026 · All 9 Modules · 5 Roles',sz=12,fill='#c4b5fd'))

# ── LEGEND ─────────────────────────────────────────────────────
LY = 80
roles = [
    ('Customer',           C['cust'],  C['custbg']),
    ('CX Agent',           C['agent'], C['abg']),
    ('CX Lead',            C['lead'],  C['lbg']),
    ('Warehouse User',     C['wh'],    C['wbg']),
    ('Supervisor / Admin', C['sup'],   C['sbg']),
    ('System (Auto)',      C['sys'],   C['sysbg']),
]
PW, PH, PG = 170, 28, 12
total_pw = len(roles)*PW + (len(roles)-1)*PG
lx = (W - total_pw)//2
for i,(lbl,col,bg) in enumerate(roles):
    px = lx + i*(PW+PG)
    emit(*rect(px,LY,PW,PH,bg,col,rx=14,sw=1.5))
    emit(*rect(px+10,LY+8,12,12,col,rx=3))
    emit(T(px+PW//2+5, LY+14, lbl, sz=10.5, fill=col, bold=True))

# ── MODULE OVERVIEW SECTION ─────────────────────────────────────
MY = 120
emit(*rect(0,MY,W,8,'#e9d5ff',rx=0))
emit(T(24, MY+26, '❶  Module Overview', sz=14, fill=C['dark'], bold=True, a='start'))

mods = [
    ('Dashboard',         'Personal queue & team KPIs',           C['purple'], C['lpurple']),
    ('Orders',            'Order lookup, detail, initiate return', C['agent'],  C['abg']),
    ('Customers',         '360° profile: orders, returns, calls',  C['agent'],  C['abg']),
    ('Returns & Exchanges','5-stage lifecycle with approval gate',  C['lead'],   C['lbg']),
    ('Refunds',           'Auto + manual · 3-step approval',       C['lead'],   C['lbg']),
    ('CRM Calling',       'Retention calls for RTO/failed orders', C['sup'],    C['sbg']),
    ('Short Picks',       'WH→CX handoff for unfulfilled items',   C['wh'],     C['wbg']),
    ('User Management',   'Create/edit/deactivate team (Admin)',    C['adm'],    C['admb']),
    ('Auth & RBAC',       '5 roles, permissions, availability',    C['sys'],    C['sysbg']),
]

MW, MH, MGX, MGY = 428, 58, 18, 10
MX0 = 24
MYS = MY + 40

for i,(name,desc,col,bg) in enumerate(mods):
    row, col_i = divmod(i,3)
    mx = MX0 + col_i*(MW+MGX)
    my = MYS + row*(MH+MGY)
    emit(*rect(mx,my,MW,MH,bg,col,rx=8,sw=1))
    emit(T(mx+MW//2, my+20, name, sz=12.5, fill=col, bold=True))
    emit(T(mx+MW//2, my+39, desc, sz=10.5, fill=C['txt']))

# ── SECTION 2: RETURNS & EXCHANGE LIFECYCLE ─────────────────────
SY = MYS + 3*(MH+MGY) + 20
emit(*rect(0,SY,W,8,'#c4b5fd',rx=0))
emit(T(24, SY+22, '❷  Returns & Exchange Lifecycle  (Core Flow)', sz=14, fill=C['dark'], bold=True, a='start'))
emit(T(W-24, SY+22, 'Roles: Agent → CX Lead → Warehouse → System', sz=11, fill=C['muted'], a='end'))

# Swimlane
SLY = SY + 42   # top of swimlane
LABEL_W = 128
COL_W   = (W - LABEL_W) // 5  # 5 stages
ROW_H   = 96

stages = ['① Trigger','② Pending\nAction','③ Pending\nApproval','④ Pending\nPickup','⑤ Out for Pickup\n→ Complete']
stage_colors = [C['custbg'],C['abg'],C['lbg'],C['wbg'],C['sysbg']]
stage_borders= [C['cust'],  C['agent'],C['lead'],C['wh'],C['sys']]

# Stage header row
emit(*rect(0,SLY,W,36,C['dark'],rx=0))
emit(*rect(0,SLY,LABEL_W,36,'#2d2b5e',rx=0))
emit(T(LABEL_W//2, SLY+18, 'Actor', sz=11, fill='#c4b5fd', bold=True))
for i,stg in enumerate(stages):
    sx = LABEL_W + i*COL_W
    emit(T(sx+COL_W//2, SLY+18, stg.replace('\n',' · '), sz=11, fill=C['white'], bold=True))
    if i>0:
        emit(line(sx,SLY,sx,SLY+36,color='#3d3b6e'))

# Swimlane rows
rows = [
    ('Customer',         C['cust'],  C['custbg']),
    ('CX Agent',         C['agent'], C['abg']),
    ('CX Lead',          C['lead'],  C['lbg']),
    ('Warehouse\nUser',  C['wh'],    C['wbg']),
    ('System\n(Auto)',   C['sys'],   C['sysbg']),
]

# Row backgrounds + labels
for ri,(lbl,col,bg) in enumerate(rows):
    ry = SLY + 36 + ri*ROW_H
    # Alternating row tint
    emit(*rect(LABEL_W, ry, W-LABEL_W, ROW_H, bg, rx=0, op=0.35))
    emit(*rect(0, ry, LABEL_W, ROW_H, bg, col, rx=0, sw=0))
    emit(*rect(0, ry, LABEL_W, ROW_H, 'none', col, rx=0, sw=0.5))
    for ll in lbl.split('\n'):
        idx = lbl.split('\n').index(ll)
        emit(T(LABEL_W//2, ry+ROW_H//2 + (idx-len(lbl.split('\n'))//2)*14, ll, sz=11, fill=col, bold=True))
    # Column separator lines
    for i in range(1,5):
        sx = LABEL_W + i*COL_W
        emit(line(sx, ry, sx, ry+ROW_H, color='#ddd6fe', sw=0.8))
    emit(line(0, ry+ROW_H, W, ry+ROW_H, color='#e5e7eb', sw=0.8))

# Cell content: (row, col, lines, bg, border)
pad = 8
CW = COL_W - 2*pad  # inner card width
CH = ROW_H - 2*pad  # inner card height

def cell(row_i, col_i, lines, bg=None, border=None, bold_first=True):
    rx = LABEL_W + col_i*COL_W + pad
    ry = SLY + 36 + row_i*ROW_H + pad
    bg2   = bg     or rows[row_i][2]
    bord2 = border or rows[row_i][1]
    return card(rx, ry, CW, CH, bg2, bord2, lines, bold_first)

# Row 0: Customer
emit(*cell(0,0,['Order issue arises','Wrong product / damaged', 'Missing item / RTO']))
emit(*cell(0,1,['Customer contacts','via App / WhatsApp','or CX calls proactively']))
emit(*cell(0,2,['Customer waits','No action needed']))
emit(*cell(0,3,['Customer waits','Rider pickup scheduled']))
emit(*cell(0,4,['Rider collects item','↩ Refund / Exchange','issued to customer']))

# Row 1: CX Agent
emit(*cell(1,0,['Agent sees return','in Pending Action queue','on Dashboard']))
emit(*cell(1,1,['Agent fills form:','Type · Reason · Refund source','Pickup date/time · Notes']))
emit(*cell(1,2,['Agent sees read-only view','Status: Awaiting CX Lead','Cannot edit or approve']))
emit(*cell(1,3,['Agent notified','Return approved','Waiting for WH dispatch']))
emit(*cell(1,4,['Agent sees Pidge ID','No further action','unless reassigned']))

# Row 2: CX Lead
emit(*cell(2,0,['CX Lead monitors','Pending Approval queue','on Dashboard']))
emit(*cell(2,1,['No action in this stage']))
emit(*cell(2,2,['CX Lead reviews:','Agent notes + reason','→ Approve or Reject']))
emit(*cell(2,3,['Return visible in','Pending Pickup queue','No action for CX Lead']))
emit(*cell(2,4,['Auto-notified on','Completion · Refund created','if type = Return']))

# Row 3: Warehouse
emit(*cell(3,0,['WH has no action','at trigger']))
emit(*cell(3,1,['WH has no action']))
emit(*cell(3,2,['WH has no action','in this stage']))
emit(*cell(3,3,['WH selects store','Clicks Send to Pidge ↗','Pidge ID generated']))
emit(*cell(3,4,['Pidge rider assigned','Rider collects return','WH marks RTO complete']))

# Row 4: System
emit(*cell(4,0,['Return record created','status = pending_action','Assigned to agent']))
emit(*cell(4,1,['Form validated','Return updated to','status = pending_approval']))
emit(*cell(4,2,['On Approve → pending_pickup','On Reject → cancelled','Rejection reason logged']))
emit(*cell(4,3,['PIDGE-XXXXXXXX ID','generated · status =','out_for_pickup']))
emit(*cell(4,4,['On complete:','Auto-create Refund record','status = pending_approval']))

# Stage transition arrows (middle of header row = SLY+18)
for i in range(4):
    ax = LABEL_W + (i+1)*COL_W - pad
    emit(arrow_h(ax-COL_W+pad*2, SLY+18, ax+pad, C['white'], sw=2, marker='arr'))

# Reject branch from col 2 (CX Lead) — downward to cancelled
REJ_X = LABEL_W + 3*COL_W - pad//2
REJ_Y = SLY + 36 + 2*ROW_H + ROW_H//2
REJ_BY = SLY + 36 + 5*ROW_H + 8  # below last row
emit(*rect(LABEL_W+2*COL_W+pad, REJ_BY, COL_W*2-pad*2, 36, C['admb'], C['adm'], rx=8, sw=1.5))
emit(T(LABEL_W+3*COL_W, REJ_BY+18, '✗  Rejected → CANCELLED  (rejection reason logged)', sz=11, fill=C['err'], bold=True))
emit(arrow_v(REJ_X, REJ_Y+CH//2, REJ_BY, C['err'], sw=1.5, marker='arr_err'))

SL_BOTTOM = SLY + 36 + 5*ROW_H + 36 + 18  # bottom of swimlane inc reject

# ── SECTION 3: REFUNDS ──────────────────────────────────────────
RFY = SL_BOTTOM + 22
emit(*rect(0,RFY,W,8,'#c4b5fd',rx=0))
emit(T(24, RFY+22, '❸  Refund Flow', sz=14, fill=C['dark'], bold=True, a='start'))
emit(T(W-24, RFY+22, 'Auto-triggered on Return complete  |  or Manual creation by CX Lead', sz=11, fill=C['muted'], a='end'))

RF_STAGES = [
    ('Auto-Created\n(Return done)', 'System creates refund\nwhen return = completed\n— OR —\nCX Lead creates manually', C['sysbg'], C['sys']),
    ('Pending\nApproval',           'CX Lead reviews:\nmethod, amount, type\nApprove or Reject',       C['lbg'],   C['lead']),
    ('Pending',                     'Approved · waiting for\npayment system to process\nWallet or Source refund', C['sbg'],   C['sup']),
    ('Processed',                   'Payment initiated\nby finance / system\nMark when confirmed',     C['abg'],   C['agent']),
    ('Completed',                   'Customer receives\nrefund to wallet\nor original source',          C['wbg'],   C['wh']),
]

RF_W  = (W - 48) // len(RF_STAGES) - 10
RF_H  = 90
RF_Y0 = RFY + 42
RF_GAP= 12

for i,(stg,desc,bg,col) in enumerate(RF_STAGES):
    rx = 24 + i*(RF_W+RF_GAP)
    emit(*rect(rx, RF_Y0, RF_W, RF_H, bg, col, rx=8, sw=1.5))
    lines = stg.split('\n')
    emit(T(rx+RF_W//2, RF_Y0+17, lines[0], sz=12, fill=col, bold=True))
    if len(lines)>1:
        emit(T(rx+RF_W//2, RF_Y0+30, lines[1], sz=10, fill=col, bold=True))
    for j,dl in enumerate(desc.split('\n')):
        emit(T(rx+RF_W//2, RF_Y0+50+j*13, dl, sz=10, fill=C['txt']))
    if i<len(RF_STAGES)-1:
        ax = rx+RF_W+2
        emit(arrow_h(ax, RF_Y0+RF_H//2, ax+RF_GAP+2, C['muted'], marker='arr'))

# COD note
emit(T(24, RF_Y0+RF_H+14, '⚠  COD orders → Wallet credit only (no source refund possible). Admin can override refund amount. Rejected refunds → Failed.', sz=10.5, fill=C['muted'], a='start'))

# ── SECTION 4: CRM CALLING ──────────────────────────────────────
CY = RF_Y0 + RF_H + 42
emit(*rect(0,CY,W,8,'#c4b5fd',rx=0))
emit(T(24, CY+22, '❹  CRM Calling Flow  (Retention)', sz=14, fill=C['dark'], bold=True, a='start'))
emit(T(W-24, CY+22, 'Triggered for: RTO · Cancelled · Failed · Undelivered orders', sz=11, fill=C['muted'], a='end'))

CR_STAGES = [
    ('Failed Order\nDetected',      'RTO / Cancelled\nFailed / Undelivered\norder in system',              C['admb'],  C['adm']),
    ('Auto-Assigned\nto Agent',     'Agent marks Available\nin sidebar toggle\nRound-robin distribution',  C['sysbg'], C['sys']),
    ('In Progress',                 'Agent opens call\nStatus → In Progress\nAgent calls customer',        C['abg'],   C['agent']),
    ('Save Draft\n(if needed)',      'Agent saves progress\nCan return and continue\nStatus stays active',  C['sbg'],   C['sup']),
    ('Completed',                   'Outcome logged:\nReached / Not reached\nDrop-off reason · Reordered', C['wbg'],   C['wh']),
]

CR_W  = (W - 48) // len(CR_STAGES) - 10
CR_H  = 90
CR_Y0 = CY + 42

for i,(stg,desc,bg,col) in enumerate(CR_STAGES):
    rx = 24 + i*(CR_W+RF_GAP)
    emit(*rect(rx, CR_Y0, CR_W, CR_H, bg, col, rx=8, sw=1.5))
    lines = stg.split('\n')
    emit(T(rx+CR_W//2, CR_Y0+17, lines[0], sz=12, fill=col, bold=True))
    if len(lines)>1:
        emit(T(rx+CR_W//2, CR_Y0+30, lines[1], sz=10, fill=col, bold=True))
    for j,dl in enumerate(desc.split('\n')):
        emit(T(rx+CR_W//2, CR_Y0+50+j*13, dl, sz=10, fill=C['txt']))
    if i<len(CR_STAGES)-1:
        ax = rx+CR_W+2
        emit(arrow_h(ax, CR_Y0+CR_H//2, ax+RF_GAP+2, C['muted'], marker='arr'))

emit(T(24, CR_Y0+CR_H+14, '⚠  Supervisor / Admin can reassign calls. Draft → In Progress (not reset). Completing a call logs drop-off reason and reorder flag.', sz=10.5, fill=C['muted'], a='start'))

# ── SECTION 5: SHORT PICKS ──────────────────────────────────────
SPY = CR_Y0 + CR_H + 44
emit(*rect(0,SPY,W,8,'#c4b5fd',rx=0))
emit(T(24, SPY+22, '❺  Short Picks Flow  (Warehouse → CX)', sz=14, fill=C['dark'], bold=True, a='start'))
emit(T(W-24, SPY+22, 'Triggered when warehouse cannot fulfil one or more items in an order', sz=11, fill=C['muted'], a='end'))

SP_STAGES = [
    ('WH Short-Pick\nFlagged',      'Warehouse cannot\nfulfil item(s)\nOMS → creates record',            C['wbg'],   C['wh']),
    ('Pending\nAssignment',         'Record in Pending queue\nAuto or manual assign\nto CX agent',        C['sysbg'], C['sys']),
    ('In Progress',                 'Agent opens record\nStatus → In Progress\nAgent calls customer',     C['abg'],   C['agent']),
    ('Resolution\nLogged',          'Customer response noted\nResolution selected:\nRefund / Replace / Cancel',C['lbg'],C['lead']),
    ('Completed',                   'Action logged with\noutcome + notes\nAdmin can edit if needed',       C['wbg'],   C['wh']),
]

SP_W  = (W - 48) // len(SP_STAGES) - 10
SP_H  = 90
SP_Y0 = SPY + 42

for i,(stg,desc,bg,col) in enumerate(SP_STAGES):
    rx = 24 + i*(SP_W+RF_GAP)
    emit(*rect(rx, SP_Y0, SP_W, SP_H, bg, col, rx=8, sw=1.5))
    lines = stg.split('\n')
    emit(T(rx+SP_W//2, SP_Y0+17, lines[0], sz=12, fill=col, bold=True))
    if len(lines)>1:
        emit(T(rx+SP_W//2, SP_Y0+30, lines[1], sz=10, fill=col, bold=True))
    for j,dl in enumerate(desc.split('\n')):
        emit(T(rx+SP_W//2, SP_Y0+50+j*13, dl, sz=10, fill=C['txt']))
    if i<len(SP_STAGES)-1:
        ax = rx+SP_W+2
        emit(arrow_h(ax, SP_Y0+SP_H//2, ax+RF_GAP+2, C['muted'], marker='arr'))

emit(T(24, SP_Y0+SP_H+14, '⚠  Resolution options: Refund Initiated · Replacement Arranged · Partial Refund · Customer Cancelled · No Action Needed. Supervisor can reassign.', sz=10.5, fill=C['muted'], a='start'))

# ── SECTION 6: V2 ROADMAP STRIP ─────────────────────────────────
V2Y = SP_Y0 + SP_H + 44
emit(*rect(0,V2Y,W,8,'#c4b5fd',rx=0))
emit(T(24, V2Y+22, '❻  v2 Roadmap — Integration Gaps', sz=14, fill=C['dark'], bold=True, a='start'))

gaps = [
    ('Pidge Webhook',      'Real RTO status\nfrom Pidge API'),
    ('OMS Sync',           'Auto short-pick\ncreation from OMS'),
    ('Razorpay',           'Webhook confirms\nactual disbursement'),
    ('WhatsApp Notifs',    'Customer updates\non return/pickup'),
    ('Coupon Tool',        'Create ₹100/₹250\ncoupons in-dashboard'),
    ('Analytics',          'Agent performance\nreports & charts'),
    ('Shift Scheduling',   'Calendar planner\nfor team leads'),
    ('Mobile View',        'Responsive layout\nfor WH staff'),
]

G_W  = (W - 48 - 7*10) // 8
G_H  = 72
G_Y0 = V2Y + 42

for i,(title,desc) in enumerate(gaps):
    gx = 24 + i*(G_W+10)
    emit(*rect(gx, G_Y0, G_W, G_H, C['bg'], C['border'], rx=8, sw=1, dash='5,3'))
    emit(T(gx+G_W//2, G_Y0+20, title, sz=11, fill=C['purple'], bold=True))
    for j,dl in enumerate(desc.split('\n')):
        emit(T(gx+G_W//2, G_Y0+38+j*14, dl, sz=10, fill=C['muted']))

# ── FOOTER ──────────────────────────────────────────────────────
FY = G_Y0 + G_H + 24
emit(*rect(0,FY,W,H-FY,C['dark'],rx=0))
emit(T(W//2, FY+18, 'Ozi CX Dashboard · Internal Tool · Gurugram · Built March 2026 · PM: Ishaan Sindhu', sz=11, fill='#c4b5fd'))
emit(T(W//2, FY+36, 'Roles: Admin · Supervisor · CX Lead · CX Agent · Warehouse User  |  Data: 50k+ orders · SQLite DB · Streamlit', sz=10, fill='#7c6fa0'))

# Dynamically set height
actual_H = FY + 56
parts[0] = parts[0].replace(f'height="{H}"', f'height="{actual_H}"').replace(f'0 0 {W} {H}', f'0 0 {W} {actual_H}')

# Close SVG
parts.append('</svg>')

svg = '\n'.join(parts)
with open('flow_diagram.svg', 'w') as f:
    f.write(svg)

print(f"Generated flow_diagram.svg ({W}x{actual_H}px, {len(svg):,} bytes)")

# ── Auto-generate PNG ────────────────────────────────────────────
import subprocess, os, sys
from PIL import Image
import numpy as np

svg_path = os.path.abspath('flow_diagram.svg')
png_tmp  = svg_path + '.png'
png_out  = os.path.abspath('flow_diagram.png')

# Render at 2× the diagram width so text stays sharp
render_size = W * 2

result = subprocess.run(
    ['qlmanage', '-t', '-s', str(render_size), '-o', os.path.dirname(svg_path), svg_path],
    capture_output=True, text=True
)
if result.returncode != 0 or not os.path.exists(png_tmp):
    print("⚠  PNG generation failed — SVG is still valid and can be opened directly.")
    print(result.stderr[:300])
    sys.exit(0)

img = Image.open(png_tmp)
arr = np.array(img)
non_white = (arr < 240).any(axis=2).any(axis=1)
last_row  = int(non_white.nonzero()[0][-1]) + 10
cropped   = img.crop((0, 0, img.width, last_row))
cropped.save(png_out, optimize=True)
os.remove(png_tmp)
print(f"Generated flow_diagram.png  ({cropped.width}×{cropped.height}px, {os.path.getsize(png_out)//1024}KB)")
