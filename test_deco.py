import unittest
import deco


@deco.persistent_locals
def _globalfunc(x):
    z = 2*x
    return z

_a = 2
@deco.persistent_locals
def _globaldependent(x):
    z = x + _a
    return z

@deco.persistent_locals
def _toberemoved(x):
    z = 2*x
    return z

class TestPersistLocals(unittest.TestCase):
    def test_outer_scope(self):
        _globalfunc(2)
        self.assertEqual(_globalfunc.locals['x'], 2)
        self.assertEqual(_globalfunc.locals['z'], 4)

    def test_global_name_removed(self):
        global _toberemoved
        f = _toberemoved
        f(2) # should pass
        del _toberemoved
        f(2) # might fail if 'f' looks for a global name '_toberemoved'

    def test_globals_are_flexible(self):
        global _a
        self.assertEqual(_globaldependent(2), 4)
        _a = 3
        self.assertEqual(_globaldependent(2), 5)
        
    def test_inner_scope(self):
        @deco.persistent_locals
        def is_sum_lt_prod(a,b,c):
            sum = a+b+c
            prod = a*b*c
            return sum<prod

        self.assertEqual(is_sum_lt_prod.locals, {})
        is_sum_lt_prod(2,3,4)
        self.assertEqual(set(is_sum_lt_prod.locals.keys()),
                         set(['a','b','c','sum','prod']))
        self.assertEqual(is_sum_lt_prod.locals['sum'], 2+3+4)
        self.assertEqual(is_sum_lt_prod.locals['prod'], 2*3*4)

    def test_args(self):
        @deco.persistent_locals
        def f(x, *args):
            return x, args

        x, args = f(2,3,4)
        self.assertEqual(x, 2)
        self.assertEqual(args, (3,4))
        self.assertEqual(f.locals['x'], 2)
        self.assertEqual(f.locals['args'], (3,4))

if __name__ == '__main__':
    unittest.main()
    
