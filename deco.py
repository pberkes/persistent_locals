import new
import byteplay as bp
import inspect

class PersistentLocalsFunction(object):
    """Wrapper class for 'persistent_locals' decorator.

    See the __doc__ attribute of the instances for help about
    the wrapped function.
    """
    def __init__(self, func):
        self.locals = {}
        
        # make function an instance method
        self._func = new.instancemethod(func, self, PersistentLocalsFunction)
        
        # create nice-looking doc string for the class
        signature = inspect.getargspec(func)
        signature[0].pop(0) # remove 'self' argument
        signature = inspect.formatargspec(*signature)
        
        docprefix = func.func_name + signature
        docpostfix = """
        
This function has been decorated with the 'persistent_locals'
decorator. You can access the dictionary of the variables in the inner
scope of the function via the 'locals' attribute.

For more information about the original function, query the self._func
attribute.
        """
        default_doc = '<no docstring>'
        self.__doc__ = (docprefix + '\n\n' + (func.__doc__ or default_doc)
                        + docpostfix)
        
    def __call__(self, *args, **kwargs):
        res = self._func(*args, **kwargs)
        del self.locals['self']
        return res

def persistent_locals(f):
    """Makes local variables static.

    Modify the function such that, at the exit of the function
    (regular exit or exceptions), the local dictionary is copied to a
    function attribute 'locals'.

    This decorator wraps the function in a callable object, and
    modifies its bytecode by adding an external try...finally
    statement as follows:

    def f(self, *args, **kwargs):
        try:
            ... old code ...
        finally:
            self.locals = locals().copy()
            del self.locals['self']
    """

    # ### disassemble f
    f_code = bp.Code.from_code(f.func_code)
    
    #print '--------', f.func_name
    #print 'before'
    #print f_code.code

    # ### add try...finally statement around code
    finally_label = bp.Label()
    # try:
    code_before = (bp.SETUP_FINALLY, finally_label)
    #     [original code here]
    # finally:
    code_after = [(finally_label, None),
                  # _selfref.locals = locals().copy()
                  (bp.LOAD_GLOBAL, 'locals'),
                  (bp.CALL_FUNCTION, 0),
                  (bp.LOAD_ATTR, 'copy'),
                  (bp.CALL_FUNCTION, 0),
                  #   del _selfref.locals['_selfref']
                  (bp.LOAD_FAST, 'self'),
                  (bp.STORE_ATTR, 'locals'),
                  (bp.END_FINALLY, None),
                  (bp.LOAD_CONST, None),
                  (bp.RETURN_VALUE, None)]
    
    f_code.code.insert(0, code_before)
    f_code.code.extend(code_after)
    
    #print 'after'
    #print f_code.code

    # ### re-assemble
    f_code.args =  ('self',) + f_code.args
    func = new.function(f_code.to_code(), f.func_globals, f.func_name,
                        f.func_defaults, f.func_closure)
                        
    return  PersistentLocalsFunction(func)


def persistent_locals_with_kwarg(f):
    """Makes local variables static.

    Modify the function such that, at the exit of the function
    (regular exit or exceptions), the local dictionary is copied to the
    function attribute 'locals'.

    The decorator modifies the bytecode of the function by adding an
    external try...finally statement as follows:

    def f(*args, **kwargs):
        try:
            ... old code ...
        finally:
            f.locals = locals().copy()

    In order to be able to keep a consistent self-reference, the decorator
    adds a new keyword argument to the function, _selfref. The signature
    of a function
    f(x, y='default', **kwargs)
    would thus change to
    f(x, y='default', _selfref=f, **kwargs)

    The decorator will not work if an *args argument is defined.
    """

    # #### disassemble f
    
    f_code = bp.Code.from_code(f.func_code)
    
    #print '--------', f.func_name
    #print 'before'
    #print f_code.code

    # #### add try...finally statement around code
    
    finally_label = bp.Label()
    # try:
    code_before = (bp.SETUP_FINALLY, finally_label) 
    #     [original code here]
    # finally:
    code_after = [(finally_label, None),
                  # _selfref.locals = locals().copy()
                  (bp.LOAD_GLOBAL, 'locals'),
                  (bp.CALL_FUNCTION, 0),
                  (bp.LOAD_ATTR, 'copy'),
                  (bp.CALL_FUNCTION, 0),
                  (bp.LOAD_FAST, '_selfref'),
                  (bp.STORE_ATTR, 'locals'),
                  #   del _selfref.locals['_selfref']
                  (bp.LOAD_FAST, '_selfref'),
                  (bp.LOAD_ATTR, 'locals'),
                  (bp.LOAD_CONST, '_selfref'),
                  (bp.DELETE_SUBSCR, None),
                  (bp.END_FINALLY, None),
                  (bp.LOAD_CONST, None),
                  (bp.RETURN_VALUE, None)]
                  
    f_code.code.insert(0, code_before)
    f_code.code.extend(code_after)
    
    # print 'after'
    # print f_code.code
    
    # #### reassemble
    if f_code.varargs:
        raise Exception('The function defines an *args argument, which is not' +
                        ' supported by the persistent_locals decorator.')

    if f_code.varkwargs:
        f_code.args = f_code.args[:-1] + ('_selfref',) + f_code.args[-1:]
    else:
        f_code.args = f_code.args + ('_selfref',)

    newf = new.function(f_code.to_code(), f.func_globals, f.func_name,
                        f.func_defaults, f.func_closure)
    if newf.func_defaults is None:
        newf.func_defaults = (newf,)
    else:
        newf.func_defaults = newf.func_defaults + (newf,)
    newf.locals = {}

    return newf
