"""
app.py - Flask server for CFG Parser & Derivation Tree Generator
All rendering is server-side, zero JavaScript.
"""

from flask import Flask, render_template, request
from cfg_parser import parse_grammar, validate_string
from cyk import (
    convert_to_cnf, cyk_parse, count_trees,
    build_tree, simplify, clean, render_svg,
    leftmost_derivation, rightmost_derivation, reset_ids
)

app = Flask(__name__, template_folder='templates', static_folder='static')

EXAMPLES = [
    {'name': 'aⁿbⁿ', 'grammar': 'S -> aSb | ε', 'string': 'aabb',
     'description': 'Balanced strings aⁿbⁿ'},
    {'name': 'Arithmetic', 'grammar': 'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | a',
     'string': 'a+a*a', 'description': 'Arithmetic expressions'},
    {'name': 'Palindromes', 'grammar': 'S -> aSa | bSb | a | b | ε',
     'string': 'abba', 'description': 'Palindromes over {a,b}'},
    {'name': 'a⁺b⁺', 'grammar': 'S -> AB\nA -> aA | a\nB -> bB | b',
     'string': 'aabb', 'description': 'One or more a then b'},
    {'name': 'Ambiguous', 'grammar': 'S -> S + S | S * S | a',
     'string': 'a+a*a', 'description': 'Shows ambiguity'},
    {'name': 'Simple', 'grammar': 'S -> aSb | ab', 'string': 'aaabbb',
     'description': 'aⁿbⁿ without ε'},
]


def hl(text):
    """Highlight symbols in a sentential form — returns safe HTML."""
    if text == 'ε':
        return '<span class="sE">ε</span>'
    r = ''
    i = 0
    while i < len(text):
        c = text[i]
        if 'A' <= c <= 'Z':
            nt = c
            i += 1
            while i < len(text) and (text[i] == "'" or '0' <= text[i] <= '9' or text[i] == '_'):
                nt += text[i]
                i += 1
            r += f'<span class="sN">{nt}</span>'
        elif c == 'ε':
            r += '<span class="sE">ε</span>'
            i += 1
        else:
            r += f'<span class="sT">{c}</span>'
            i += 1
    return r


app.jinja_env.filters['hl'] = hl


@app.route('/', methods=['GET', 'POST'])
def index():
    ctx = {'examples': EXAMPLES, 'gt': '', 'st': '', 'res': None,
           'errs': None, 'cnf_steps': None, 'svg': '', 'cs': ''}

    if request.method == 'POST':
        action = request.form.get('action', 'parse')

        if action == 'example':
            idx = int(request.form.get('idx', 0))
            ex = EXAMPLES[idx % len(EXAMPLES)]
            ctx['gt'] = ex['grammar']
            ctx['st'] = ex['string']
            raw, inp = ex['grammar'], ex['string']
            action = 'parse'
        else:
            raw = request.form.get('grammar', '').strip()
            inp = request.form.get('string', '').strip()
            ctx['gt'] = raw
            ctx['st'] = inp

        if action in ('parse', 'example'):
            if not raw:
                ctx['errs'] = ['Please enter a grammar.']
                return render_template('index.html', **ctx)

            grammar, errors = parse_grammar(raw)
            if not grammar:
                ctx['errs'] = errors
                return render_template('index.html', **ctx)

            ok, msg = validate_string(inp, grammar)
            if not ok:
                ctx['errs'] = [msg]
                return render_template('index.html', **ctx)

            try:
                cnf, cnf_steps = convert_to_cnf(grammar)
                ctx['cs'] = cnf['start_symbol']
                result = cyk_parse(cnf, inp)
                accepted = result['accepted']

                res = {'accepted': accepted, 'inp': inp or 'ε',
                       'cyk': result['table_display'],
                       'amb': False, 'tc': 1, 'lm': [], 'rm': []}

                if accepted:
                    reset_ids()
                    n = len(inp)
                    bp = result['back_pointers']

                    if n > 0:
                        raw_tree = build_tree(bp, cnf['start_symbol'], 0, n - 1, inp)
                    else:
                        raw_tree = {
                            'id': 1, 'name': cnf['start_symbol'],
                            'terminal': False, 'epsilon': False,
                            'children': [{'id': 2, 'name': 'ε',
                                         'terminal': False, 'epsilon': True, 'children': []}]
                        }

                    orig_nts = set(grammar['non_terminals'])
                    tree = simplify(raw_tree, orig_nts)
                    clean(tree)
                    ctx['svg'] = render_svg(tree)

                    res['lm'] = leftmost_derivation(tree)
                    res['rm'] = rightmost_derivation(tree)

                    tc = count_trees(bp, cnf['start_symbol'], n)
                    res['amb'] = tc > 1
                    res['tc'] = min(tc, 100)

                ctx['res'] = res
                warnings = [e for e in errors if e.startswith('Warning')]
                if warnings:
                    ctx['errs'] = warnings

            except Exception as ex:
                ctx['errs'] = [f'Processing error: {str(ex)}']
                return render_template('index.html', **ctx)

        elif action == 'cnf':
            if not raw:
                ctx['errs'] = ['Please enter a grammar first.']
                return render_template('index.html', **ctx)
            grammar, errors = parse_grammar(raw)
            if not grammar:
                ctx['errs'] = errors
                return render_template('index.html', **ctx)
            try:
                _, steps = convert_to_cnf(grammar)
                ctx['cnf_steps'] = steps
            except Exception as ex:
                ctx['errs'] = [f'CNF conversion error: {str(ex)}']

    return render_template('index.html', **ctx)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
