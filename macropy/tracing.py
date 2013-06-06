
from macropy.core.macros import *
from macropy.core.quotes import macros, q, u
import ast
import copy

macros = Macros()

@macros.expose()
def wrap(printer, txt, x):
    string = txt + " -> " + repr(x)
    printer(string)
    return x

@macros.expose()
def wrap_simple(printer, txt, x):
    string = txt
    printer(string)
    return x

@macros.expr()
def log(tree, exact_src, hygienic_names, **kw):
    new_tree = q[name[hygienic_names("wrap")](log, u[exact_src(tree)], ast[tree])]
    return new_tree

@macros.expr()
def show_expanded(tree, expand_macros, hygienic_names, **kw):
    expanded_tree = expand_macros(tree)
    new_tree = q[wrap_simple(log, u[unparse_ast(expanded_tree)], ast[expanded_tree])]
    return new_tree

@macros.block()
def show_expanded(tree, expand_macros, **kw):

    new_tree = []
    for stmt in tree:
        new_stmt = expand_macros(stmt)

        with q as code:
            log(u[unparse_ast(new_stmt)])
        new_tree.append(code)
        new_tree.append(new_stmt)

    return new_tree

def trace_walk_func(tree, exact_src, hygienic_names):

    @Walker
    def trace_walk(tree, stop, **kw):

        if isinstance(tree, expr) and \
                tree._fields != () and \
                type(tree) is not Num and \
                type(tree) is not Str and \
                type(tree) is not Name:

            try:
                literal_eval(tree)
                stop()
                return tree
            except ValueError:
                txt = exact_src(tree)
                trace_walk.walk_children(tree)

                wrapped = q[wrap(log, u[txt], ast[tree])]
                stop()
                return wrapped

        elif isinstance(tree, stmt):
            txt = exact_src(tree)
            trace_walk.walk_children(tree)
            with q as code:
                log(u[txt])
            stop()
            return [code, tree]

    return trace_walk.recurse(tree)
@macros.expr()
def trace(tree, exact_src, hygienic_names, **kw):
    ret = trace_walk_func(tree, exact_src, hygienic_names)
    return ret

@macros.block()
def trace(tree, exact_src, hygienic_names, **kw):
    ret = trace_walk_func(tree, exact_src, hygienic_names)
    return ret


def _require_transform(tree, exact_src, hygienic_names):
    ret = trace_walk_func(copy.deepcopy(tree), exact_src, hygienic_names)
    trace_walk_func(copy.deepcopy(tree), exact_src, hygienic_names)
    new = q[ast[tree] or handle(lambda log: ast[ret])]
    return new

@macros.expose()
def handle(thunk):
    out = []
    thunk(out.append)
    raise AssertionError("Require Failed\n" + "\n".join(out))

@macros.expr()
def require(tree, exact_src, hygienic_names, **kw):
    return _require_transform(tree, exact_src, hygienic_names)

@macros.block()
def require(tree, exact_src, hygienic_names, **kw):
    for expr in tree:
        expr.value = _require_transform(expr.value, exact_src, hygienic_names)

    return tree

@macros.expose_unhygienic()
def log(x):
    print(x)
