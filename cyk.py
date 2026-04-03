"""
cyk.py - CYK Algorithm, CNF Conversion, Tree Building, Derivations
Complete module handling all CFG processing.
"""

from copy import deepcopy

# ═══════════════════════════════════════════════════════════════
# CNF CONVERSION
# ═══════════════════════════════════════════════════════════════

def convert_to_cnf(grammar):
    """Convert CFG to Chomsky Normal Form with step tracking."""
    steps = []
    prods = deepcopy(grammar['productions'])
    nts = set(grammar['non_terminals'])
    terms = set(grammar['terminals'])
    start = grammar['start_symbol']

    steps.append({'title': 'Original Grammar', 'description': 'As entered.',
                  'productions': fmt(prods)})

    # Step 1: New start
    ns = start + '0'
    new_p = {}
    new_p[ns] = [[start]]
    for k, v in prods.items():
        new_p[k] = [list(r) for r in v]
    prods = new_p
    nts.add(ns)
    start = ns
    steps.append({'title': 'Step 1: New Start Symbol',
                  'description': f'Added {ns} → {grammar["start_symbol"]}.',
                  'productions': fmt(prods)})

    # Step 2: Remove ε-productions
    nullable = set()
    changed = True
    while changed:
        changed = False
        for lhs, alts in prods.items():
            if lhs in nullable:
                continue
            for rhs in alts:
                if rhs == ['ε'] or all(s in nullable for s in rhs):
                    nullable.add(lhs)
                    changed = True
                    break

    new_p2 = {}
    for lhs, alts in prods.items():
        new_alts = []
        for rhs in alts:
            if rhs == ['ε']:
                continue
            combos = _null_combos(rhs, nullable)
            for c in combos:
                if c and c not in new_alts:
                    new_alts.append(c)
        if new_alts:
            new_p2[lhs] = new_alts
    if grammar['start_symbol'] in nullable:
        if start not in new_p2:
            new_p2[start] = []
        if ['ε'] not in new_p2[start]:
            new_p2[start].append(['ε'])
    prods = new_p2
    steps.append({'title': 'Step 2: Remove ε-productions',
                  'description': f'Nullable: {{{", ".join(sorted(nullable))}}}.',
                  'productions': fmt(prods)})

    # Step 3: Remove unit productions
    changed = True
    while changed:
        changed = False
        for lhs in list(prods.keys()):
            new_alts = []
            for rhs in prods.get(lhs, []):
                if len(rhs) == 1 and rhs[0] in nts and rhs[0] != lhs:
                    changed = True
                    for br in prods.get(rhs[0], []):
                        if br not in new_alts:
                            new_alts.append(br)
                else:
                    if rhs not in new_alts:
                        new_alts.append(rhs)
            prods[lhs] = new_alts
    steps.append({'title': 'Step 3: Remove Unit Productions',
                  'description': 'Replaced A → B with productions of B.',
                  'productions': fmt(prods)})

    # Step 4: Isolate terminals
    tc = 0
    tmap = {}
    for lhs in list(prods.keys()):
        new_alts = []
        for rhs in prods[lhs]:
            if len(rhs) <= 1:
                new_alts.append(rhs)
                continue
            nr = []
            for s in rhs:
                if s in terms:
                    if s not in tmap:
                        nm = f'T_{s}_{tc}'
                        tc += 1
                        tmap[s] = nm
                        nts.add(nm)
                        prods[nm] = [[s]]
                    nr.append(tmap[s])
                else:
                    nr.append(s)
            new_alts.append(nr)
        prods[lhs] = new_alts
    steps.append({'title': 'Step 4: Isolate Terminals',
                  'description': 'Replaced terminals in mixed rules.',
                  'productions': fmt(prods)})

    # Step 5: Binary rules
    bc = 0
    for lhs in list(prods.keys()):
        new_alts = []
        for rhs in prods[lhs]:
            if len(rhs) <= 2:
                new_alts.append(rhs)
                continue
            rem = list(rhs)
            first = rem[0]
            rem = rem[1:]
            nn = f'B_{bc}'
            bc += 1
            nts.add(nn)
            new_alts.append([first, nn])
            while len(rem) > 2:
                nextnn = f'B_{bc}'
                bc += 1
                nts.add(nextnn)
                prods[nn] = [[rem[0], nextnn]]
                rem = rem[1:]
                nn = nextnn
            prods[nn] = [rem]
        prods[lhs] = new_alts
    steps.append({'title': 'Step 5: Binary Rules',
                  'description': 'Converted long rules to binary chains.',
                  'productions': fmt(prods)})

    cnf = {'start_symbol': start, 'non_terminals': sorted(nts),
           'terminals': sorted(terms), 'productions': prods}
    return cnf, steps


# ═══════════════════════════════════════════════════════════════
# CYK PARSING
# ═══════════════════════════════════════════════════════════════

def cyk_parse(cnf, s):
    """Run CYK algorithm. Returns accepted, table, back_pointers, table_display."""
    prods = cnf['productions']
    start = cnf['start_symbol']
    n = len(s)

    if n == 0:
        alts = prods.get(start, [])
        ok = any(r == ['ε'] for r in alts)
        return {
            'accepted': ok,
            'table': [[set()]],
            'back_pointers': [[{}]],
            'table_display': [[sorted({start}) if ok else []]]
        }

    table = [[set() for _ in range(n)] for _ in range(n)]
    bp = [[{} for _ in range(n)] for _ in range(n)]

    # Length 1
    for i in range(n):
        for lhs, alts in prods.items():
            for rhs in alts:
                if len(rhs) == 1 and rhs[0] == s[i]:
                    table[i][i].add(lhs)
                    bp[i][i].setdefault(lhs, []).append({'type': 'terminal', 'char': s[i]})

    # Length 2..n
    for ln in range(2, n + 1):
        for i in range(n - ln + 1):
            j = i + ln - 1
            for k in range(i, j):
                for B in table[i][k]:
                    for C in table[k + 1][j]:
                        for A, alts in prods.items():
                            for rhs in alts:
                                if len(rhs) == 2 and rhs[0] == B and rhs[1] == C:
                                    table[i][j].add(A)
                                    bp[i][j].setdefault(A, []).append(
                                        {'type': 'split', 'k': k, 'B': B, 'C': C})

    td = []
    for ln in range(1, n + 1):
        row = []
        for i in range(n):
            j = i + ln - 1
            row.append(sorted(table[i][j]) if j < n else None)
        td.append(row)

    return {'accepted': start in table[0][n - 1], 'table': table,
            'back_pointers': bp, 'table_display': td}


def count_trees(bp, start, n, cap=100):
    """Count parse trees for ambiguity detection."""
    if n == 0:
        return 1 if start in bp[0][0] else 0
    memo = {}

    def go(nt, i, j):
        key = (nt, i, j)
        if key in memo:
            return memo[key]
        entries = bp[i][j].get(nt, [])
        total = 0
        for e in entries:
            if e['type'] == 'terminal':
                total += 1
            else:
                total += go(e['B'], i, e['k']) * go(e['C'], e['k'] + 1, j)
            if total >= cap:
                break
        memo[key] = min(total, cap)
        return memo[key]

    return go(start, 0, n - 1)


# ═══════════════════════════════════════════════════════════════
# PARSE TREE
# ═══════════════════════════════════════════════════════════════

_nid = 0


def reset_ids():
    global _nid
    _nid = 0


def _next_id():
    global _nid
    _nid += 1
    return _nid


def build_tree(bp, sym, i, j, s):
    """Build parse tree from back-pointers."""
    entries = bp[i][j].get(sym, [])
    if not entries:
        return None
    e = entries[0]
    nid = _next_id()

    if e['type'] == 'terminal':
        return {'id': nid, 'name': sym, 'terminal': False, 'epsilon': False,
                'children': [{'id': _next_id(), 'name': e['char'],
                              'terminal': True, 'epsilon': False, 'children': []}]}
    if e['type'] == 'epsilon':
        return {'id': nid, 'name': sym, 'terminal': False, 'epsilon': False,
                'children': [{'id': _next_id(), 'name': 'ε',
                              'terminal': False, 'epsilon': True, 'children': []}]}

    left = build_tree(bp, e['B'], i, e['k'], s)
    right = build_tree(bp, e['C'], e['k'] + 1, j, s)
    ch = [c for c in [left, right] if c]
    return {'id': nid, 'name': sym, 'terminal': False, 'epsilon': False, 'children': ch}


def simplify(node, orig_nts):
    """Collapse CNF auxiliary nodes back to original grammar structure."""
    if not node:
        return None
    if node.get('terminal') or node.get('epsilon'):
        return dict(node)

    kids = [simplify(c, orig_nts) for c in node.get('children', [])]
    kids = [c for c in kids if c]

    is_orig = node['name'] in orig_nts

    if not is_orig:
        if len(kids) == 1 and kids[0].get('terminal'):
            return kids[0]
        return {'_flat': True, 'children': kids, **node}

    flat = []
    for c in kids:
        if c and c.get('_flat'):
            flat.extend(c.get('children', []))
        else:
            flat.append(c)

    # Collapse S0 → S
    if node['name'].endswith('0') and len(flat) == 1:
        base = node['name'][:-1]
        if base in orig_nts and flat[0]['name'] == base:
            return {**flat[0], 'id': node['id']}

    return {**node, '_flat': False, 'children': flat}


def clean(node):
    """Remove internal keys."""
    if not node:
        return
    node.pop('_flat', None)
    for c in node.get('children', []):
        clean(c)


# ═══════════════════════════════════════════════════════════════
# DERIVATIONS
# ═══════════════════════════════════════════════════════════════

def leftmost_derivation(tree):
    """Generate leftmost derivation steps."""
    if not tree:
        return []
    order = []
    _collect_lm(tree, order)
    return _derive(tree, order)


def rightmost_derivation(tree):
    """Generate rightmost derivation steps."""
    if not tree:
        return []
    order = []
    _collect_rm(tree, order)
    return _derive(tree, order)


def _collect_lm(node, result):
    if not node or node.get('terminal') or node.get('epsilon'):
        return
    if node.get('children'):
        result.append(node)
        for c in node['children']:
            _collect_lm(c, result)


def _collect_rm(node, result):
    if not node or node.get('terminal') or node.get('epsilon'):
        return
    if node.get('children'):
        result.append(node)
        for c in reversed(node['children']):
            _collect_rm(c, result)


def _derive(tree, order):
    steps = []
    sent = [{'t': 'nt', 's': tree['name'], 'id': tree['id']}]
    steps.append(_render(sent))

    for node in order:
        idx = None
        for i, tok in enumerate(sent):
            if tok['t'] == 'nt' and tok['id'] == node['id']:
                idx = i
                break
        if idx is None:
            continue

        repl = []
        for c in node.get('children', []):
            if c.get('terminal'):
                repl.append({'t': 'term', 's': c['name']})
            elif c.get('epsilon'):
                pass
            else:
                repl.append({'t': 'nt', 's': c['name'], 'id': c['id']})

        sent = sent[:idx] + repl + sent[idx + 1:]
        steps.append(_render(sent))

    return steps


def _render(sent):
    if not sent:
        return 'ε'
    return ''.join(t['s'] for t in sent)


# ═══════════════════════════════════════════════════════════════
# SVG TREE RENDERING (pure Python, no JS)
# ═══════════════════════════════════════════════════════════════

def render_svg(tree):
    """Generate SVG string for parse tree."""
    if not tree:
        return '<p style="color:#64748b;text-align:center;padding:40px;">No tree.</p>'

    R = 22
    LH = 78
    GAP = 14
    PAD = 45
    FS = 12

    layout = _layout(tree, R, GAP)
    depth = _depth(tree)
    w = layout['w'] + PAD * 2
    h = (depth + 1) * LH + PAD * 2

    edges = []
    nodes = []

    def draw(nd, ly, ox, d):
        cx = ox + ly['x'] + PAD
        cy = d * LH + PAD + R

        if nd.get('epsilon'):
            fill, stk, tc = '#fbbf24', '#d97706', '#451a03'
        elif nd.get('terminal'):
            fill, stk, tc = '#6ee7b7', '#059669', '#064e3b'
        else:
            fill, stk, tc = '#818cf8', '#4f46e5', '#eef2ff'

        if nd.get('children') and ly.get('ch'):
            for ci, cl in enumerate(ly['ch']):
                ccx = ox + cl['x'] + PAD
                ccy = (d + 1) * LH + PAD + R
                my = (cy + ccy) / 2
                edges.append(
                    f'<path d="M{cx} {cy+R} C{cx} {my},{ccx} {my},{ccx} {ccy-R}" '
                    f'fill="none" stroke="#475569" stroke-width="2" opacity=".55"/>')

        nodes.append(
            f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{fill}" stroke="{stk}" stroke-width="2.5"/>')

        label = nd.get('name', '?').replace('&', '&amp;').replace('<', '&lt;')
        fw = '700' if nd.get('terminal') or nd.get('epsilon') else '600'
        nodes.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" '
            f'fill="{tc}" font-size="{FS}" font-weight="{fw}" '
            f'font-family="\'JetBrains Mono\',monospace">{label}</text>')

        if nd.get('children') and ly.get('ch'):
            for ci, cl in enumerate(ly['ch']):
                draw(nd['children'][ci], cl, ox, d + 1)

    draw(tree, layout, 0, 0)

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" style="max-width:100%;height:auto;">'
            f'{"".join(edges)}{"".join(nodes)}</svg>')


def _layout(nd, r, gap):
    if not nd or not nd.get('children'):
        return {'x': 0, 'w': r * 2 + gap, 'ch': []}
    chs = [_layout(c, r, gap) for c in nd['children']]
    tw = max(sum(c['w'] for c in chs), r * 2 + gap)
    cur = 0
    for c in chs:
        c['x'] = cur + c['w'] / 2
        cur += c['w']
    mid = (chs[0]['x'] + chs[-1]['x']) / 2
    for c in chs:
        c['x'] = c['x'] - mid + tw / 2
    return {'x': tw / 2, 'w': tw, 'ch': chs}


def _depth(nd):
    if not nd or not nd.get('children'):
        return 0
    return 1 + max(_depth(c) for c in nd['children'])


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _null_combos(rhs, nullable):
    ni = [i for i, s in enumerate(rhs) if s in nullable]
    k = len(ni)
    results = []
    for mask in range(1 << k):
        exc = {ni[b] for b in range(k) if mask & (1 << b)}
        combo = [rhs[i] for i in range(len(rhs)) if i not in exc]
        if combo and combo not in results:
            results.append(combo)
    return results


def fmt(prods):
    lines = []
    for lhs, alts in prods.items():
        rhs = ' | '.join(''.join(a) for a in alts)
        lines.append(f"{lhs} → {rhs}")
    return '\n'.join(lines)
