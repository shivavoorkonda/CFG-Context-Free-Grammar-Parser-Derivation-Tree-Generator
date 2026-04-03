"""
cfg_parser.py - Grammar Parsing Module
Parses CFG input, validates format, identifies terminals/non-terminals.
"""

import re


def parse_grammar(raw_text):
    """Parse raw grammar text into a structured dict."""
    errors = []
    productions = {}
    non_terminals = set()
    terminals = set()
    start_symbol = None

    lines = raw_text.strip().replace('\r\n', '\n').split('\n')
    lines = [l.strip() for l in lines if l.strip()]

    if not lines:
        return None, ["Grammar is empty. Enter at least one production rule."]

    for i, line in enumerate(lines, 1):
        match = re.match(r'^(.+?)\s*(?:→|->)\s*(.+)$', line)
        if not match:
            errors.append(f"Line {i}: Invalid format. Use 'A -> α | β'.")
            continue

        lhs = match.group(1).strip()
        rhs_raw = match.group(2).strip()

        if not re.match(r"^[A-Z][A-Z0-9']*$", lhs):
            errors.append(f'Line {i}: LHS "{lhs}" must start with uppercase (e.g. S, A, B).')
            continue

        if start_symbol is None:
            start_symbol = lhs
        non_terminals.add(lhs)

        alternatives = [a.strip() for a in rhs_raw.split('|')]
        rhs_list = []
        for alt in alternatives:
            if not alt:
                errors.append(f"Line {i}: Empty alternative. Use ε for epsilon.")
                continue
            symbols = tokenise(alt)
            rhs_list.append(symbols)

        if lhs in productions:
            productions[lhs].extend(rhs_list)
        else:
            productions[lhs] = rhs_list

    # Find terminals
    for alts in productions.values():
        for syms in alts:
            for s in syms:
                if s != 'ε' and s not in non_terminals:
                    terminals.add(s)

    real_errors = [e for e in errors if not e.startswith("Warning")]
    if real_errors:
        return None, errors

    return {
        'start_symbol': start_symbol,
        'non_terminals': sorted(non_terminals),
        'terminals': sorted(terminals),
        'productions': productions
    }, errors


def tokenise(rhs):
    """Tokenise RHS into symbols."""
    # Fast check for full string aliases
    if rhs.lower() in ('ε', 'epsilon', 'eps', 'e'):
        return ['ε']
    tokens = []
    i = 0
    while i < len(rhs):
        ch = rhs[i]
        if ch == ' ':
            i += 1
            continue
        if ch == 'ε' or ch == 'e' or ch == 'E':
            # Allow individual character 'e' to mean epsilon
            tokens.append('ε')
            i += 1

        elif 'A' <= ch <= 'Z':
            sym = ch
            i += 1
            while i < len(rhs) and (rhs[i] == "'" or '0' <= rhs[i] <= '9'):
                sym += rhs[i]
                i += 1
            tokens.append(sym)
        else:
            tokens.append(ch)
            i += 1
    return tokens


def validate_string(s, grammar):
    """Check string uses only terminal symbols."""
    if not s:
        return True, ""
    terminals = set(grammar['terminals'])
    for ch in s:
        if ch not in terminals:
            return False, f'Character "{ch}" is not a terminal. Terminals: {{{", ".join(sorted(terminals))}}}'
    return True, ""
