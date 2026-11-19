"""Interpret one restricted browser function as an allowlisted operation, never exec/eval."""
import ast


def parse_function(source, evidence):
    if not isinstance(source, str) or not 1 <= len(source) <= 4000:
        raise ValueError('Expected a bounded browser function')
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        raise ValueError('Invalid browser function syntax') from None
    # Some coder templates emit the single call body; normalize it before the same strict validation.
    if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
        source = 'def run(browser):\n' + '\n'.join('    ' + line for line in source.splitlines())
        tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError('Define only def run(browser)')
    function = tree.body[0]
    args = function.args
    if (function.name != 'run' or function.decorator_list or function.returns
            or args.posonlyargs or args.kwonlyargs or args.defaults or args.kw_defaults
            or args.vararg or args.kwarg or len(args.args) != 1
            or args.args[0].arg != 'browser' or args.args[0].annotation
            or len(function.body) != 1 or not isinstance(function.body[0], ast.Expr)):
        raise ValueError('Expected one browser operation in def run(browser)')
    call = function.body[0].value
    if (not isinstance(call, ast.Call) or call.keywords
            or not isinstance(call.func, ast.Attribute)
            or not isinstance(call.func.value, ast.Name) or call.func.value.id != 'browser'
            or call.func.attr not in ('click', 'scroll', 'observe', 'read_articles', 'screenshot')
            or not all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in call.args)):
        raise ValueError('Only literal-argument public browser operations are allowed')
    method = call.func.attr
    values = [a.value for a in call.args]
    targeted = method in ('click', 'scroll')
    if len(values) != (2 if targeted else 1) or values[-1] != evidence:
        raise ValueError('Browser function is not bound to the current page evidence')
    if targeted and (len(values[0]) > 40 or not values[0]):
        raise ValueError('Invalid observed candidate identifier')
    return {'action': method if targeted else 'read' if method == 'read_articles' else 'finish',
            'candidate': values[0] if targeted else None, 'evidence': evidence, 'python': source}
