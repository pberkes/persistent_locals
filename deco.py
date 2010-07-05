import new
import byteplay as bp
import inspect
import sys

# persistent_locals2 has been co-authored with Andrea Maffezzoli
class persistent_locals2(object):
    """Function decorator to expose local variables after execution.

    Modify the function such that, at the exit of the function
    (regular exit or exceptions), the local dictionary is copied to a
    function attribute 'locals'.
    """
    
    def __init__(self, func):
        self._locals = {}
        self.func = func
        
    def __call__(self, *args, **kwargs):
        def tracer(frame, event, arg):
            if event=='return':
                self._locals = frame.f_locals
                
        # tracer is activated on next call, return or exception
        sys.setprofile(tracer)
        try:
            # trace the function call
            res = self.func(*args, **kwargs)
        finally:
            # disable tracer
            sys.setprofile(None)
        return res

    def clear_locals(self):
        self._locals = {}

    @property
    def locals(self):
        return self._locals

def persistent_locals(f):
    """Function decorator to expose local variables after execution.

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

    # ### add try...finally statement around code
    finally_label = bp.Label()
    # try:
    code_before = (bp.SETUP_FINALLY, finally_label)
    #     [original code here]
    # finally:
    code_after = [(finally_label, None),
                  # self._locals = locals().copy()
                  (bp.LOAD_GLOBAL, 'locals'),
                  (bp.CALL_FUNCTION, 0),
                  (bp.LOAD_ATTR, 'copy'),
                  (bp.CALL_FUNCTION, 0),
                  (bp.LOAD_FAST, 'self'),
                  (bp.STORE_ATTR, '_locals'),
                  #   del self._locals['self']
                  (bp.LOAD_FAST, 'self'),
                  (bp.LOAD_ATTR, '_locals'),
                  (bp.LOAD_CONST, 'self'),
                  (bp.DELETE_SUBSCR, None),
                  (bp.END_FINALLY, None),
                  (bp.LOAD_CONST, None),
                  (bp.RETURN_VALUE, None)]
    
    f_code.code.insert(0, code_before)
    f_code.code.extend(code_after)

    # ### re-assemble
    f_code.args =  ('self',) + f_code.args
    func = new.function(f_code.to_code(), f.func_globals, f.func_name,
                        f.func_defaults, f.func_closure)
                        
    return  PersistentLocalsFunction(func)


class PersistentLocalsFunction(object):
    """Wrapper class for 'persistent_locals' decorator.

    See the __doc__ attribute of the instances for help about
    the wrapped function.
    """
    def __init__(self, func):
        self._locals = {}
        
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
        return self._func(*args, **kwargs)
    
    @property
    def locals(self):
        return self._locals
