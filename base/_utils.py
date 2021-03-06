"""
Utilities module (internal)

This module contains a number of tools that help with the interface for this
plugin. This contains things such as the multicase decorator, the matcher
class for querying and filtering lists of things, support for aliasing
functions, and a number of functional programming primitives (combinators).
"""

import six
from six.moves import builtins

import logging, types, weakref
import functools, operator, itertools
import sys, heapq, collections

import internal
import idaapi

__all__ = ['fbox','fboxed','funbox','finstance','fhasitem','fitemQ','fgetitem','fitem','fhasattr','fattributeQ','fgetattr','fattribute','fconstant','fpassthru','fdefault','fpass','fidentity','fid','first','second','third','last','fcompose','fdiscard','fcondition','fmap','flazy','fmemo','fpartial','fapply','fcurry','frpartial','freverse','freversed','fexc','fexception','fcatch','fcomplement','fnot','ilist','liter','ituple','titer','itake','iget','imap','ifilter','ichain','izip','count']

### functional programming primitives (FIXME: probably better to document these with examples)

# box any specified arguments
fbox = fboxed = lambda *a: a
# return a closure that executes `f` with the arguments unboxed.
funbox = lambda f, *a, **k: lambda *ap, **kp: f(*(a + builtins.reduce(operator.add, builtins.map(builtins.tuple, ap), ())), **builtins.dict(k.items() + kp.items()))
# return a closure that will check that `object` is an instance of `type`.
finstance = lambda *type: frpartial(builtins.isinstance, type)
# return a closure that will check if its argument has an item `key`.
fhasitem = fitemQ = lambda key: fcompose(fcatch(frpartial(operator.getitem, key)), iter, next, fpartial(operator.eq, None))
# return a closure that will get a particular element from an object
fgetitem = fitem = lambda item, *default: lambda object: default[0] if default and item not in object else object[item]
# return a closure that will check if its argument has an `attribute`.
fhasattr = fattributeQ = lambda attribute: frpartial(hasattr, attribute)
# return a closure that will get a particular attribute from an object
fgetattr = fattribute = lambda attribute, *default: lambda object: getattr(object, attribute, *default)
# return a closure that always returns `object`.
fconstant = fconst = falways = lambda object: lambda *a, **k: object
# a closure that returns its argument always
fpassthru = fpass = fidentity = fid = lambda object: object
# a closure that returns a default value if its object is false-y
fdefault = lambda default: lambda object: object or default
# return the first, second, or third item of a box.
first, second, third, last = operator.itemgetter(0), operator.itemgetter(1), operator.itemgetter(2), operator.itemgetter(-1)
# return a closure that executes a list of functions one after another from left-to-right
fcompose = lambda *f: builtins.reduce(lambda f1, f2: lambda *a: f1(f2(*a)), builtins.reversed(f))
# return a closure that executes function `f` whilst discarding any extra arguments
fdiscard = lambda f: lambda *a, **k: f()
# return a closure that executes function `crit` and then returns/executes `f` or `t` based on whether or not it's successful.
fcondition = fcond = lambda crit: lambda t, f: \
    lambda *a, **k: (t(*a, **k) if builtins.callable(t) else t) if crit(*a, **k) else (f(*a, **k) if builtins.callable(f) else f)
# return a closure that takes a list of functions to execute with the provided arguments
fmap = lambda *fa: lambda *a, **k: (f(*a, **k) for f in fa)
#lazy = lambda f, state={}: lambda *a, **k: state[(f, a, builtins.tuple(builtins.sorted(k.items())))] if (f, a, builtins.tuple(builtins.sorted(k.items()))) in state else state.setdefault((f, a, builtins.tuple(builtins.sorted(k.items()))), f(*a, **k))
#lazy = lambda f, *a, **k: lambda *ap, **kp: f(*(a+ap), **dict(k.items() + kp.items()))
# return a memoized closure that's lazy and only executes when evaluated
def flazy(f, *a, **k):
    sortedtuple, state = fcompose(builtins.sorted, builtins.tuple), {}
    def lazy(*ap, **kp):
        A, K = a+ap, sortedtuple(k.items() + kp.items())
        return state[(A, K)] if (A, K) in state else state.setdefault((A, K), f(*A, **builtins.dict(k.items()+kp.items())))
    return lazy
fmemo = flazy
# return a closure with the function's arglist partially applied
fpartial = functools.partial
# return a closure that applies the provided arguments to the function `f`.
fapply = lambda f, *a, **k: lambda *ap, **kp: f(*(a+ap), **builtins.dict(k.items() + kp.items()))
# return a closure that will use the specified arguments to call the provided function.
fcurry = lambda *a, **k: lambda f, *ap, **kp: f(*(a+ap), **builtins.dict(k.items() + kp.items()))
# return a closure that applies the initial arglist to the end of function `f`.
frpartial = lambda f, *a, **k: lambda *ap, **kp: f(*(ap + builtins.tuple(builtins.reversed(a))), **builtins.dict(k.items() + kp.items()))
# return a closure that applies the arglist to function `f` in reverse.
freversed = freverse = lambda f, *a, **k: lambda *ap, **kp: f(*builtins.reversed(a + ap), **builtins.dict(k.items() + kp.items()))
# return a closure that executes function `f` and includes the caught exception (or None) as the first element in the boxed result.
def fcatch(f, *a, **k):
    def fcatch(*a, **k):
        try: return builtins.None, f(*a, **k)
        except: return sys.exc_info()[1], builtins.None
    return functools.partial(fcatch, *a, **k)
fexc = fexception = fcatch
# boolean inversion of the result of a function
fcomplement = fnot = frpartial(fcompose, operator.not_)
# converts a list to an iterator, or an iterator to a list
ilist, liter = fcompose(builtins.list, builtins.iter), fcompose(builtins.iter, builtins.list)
# converts a tuple to an iterator, or an iterator to a tuple
ituple, titer = fcompose(builtins.tuple, builtins.iter), fcompose(builtins.iter, builtins.tuple)
# take `count` number of elements from an iterator
itake = lambda count: fcompose(builtins.iter, fmap(*(builtins.next,)*count), builtins.tuple)
# get the `nth` element from an iterator
iget = lambda count: fcompose(builtins.iter, fmap(*(builtins.next,)*(count)), builtins.tuple, operator.itemgetter(-1))
# copy from itertools
imap, ifilter, ichain, izip = itertools.imap, itertools.ifilter, itertools.chain, itertools.izip
# count number of elements of a container
count = fcompose(builtins.iter, builtins.list, builtins.len)

# cheap pattern-like matching
class Pattern(object):
    '''Base class for fake pattern matching against a tuple.'''
    def __eq__(self, other):
        return self.__cmp__(other) == 0
    __call__ = __eq__
    def __repr__(self):
        return 'Pattern()'
class PatternAny(Pattern):
    '''Object for matching against anything it is compared against.'''
    def __cmp__(self, other):
        return 0
    def __repr__(self):
        return "{:s}({:s})".format('Pattern', '*')
class PatternAnyType(Pattern):
    '''Object for matching against any type it is compared against.'''
    def __init__(self, other):
        self.type = other
    def __cmp__(self, other):
        return 0 if isinstance(other, self.type) else -1
    def __repr__(self):
        return "{:s}({:s})".format('Pattern', '|'.join(n.__name__ for n in self.type) if hasattr(self.type, '__iter__') else self.type.__name__)

### decorators
class multicase(object):
    """
    A lot of magic is in this class which allows one to define multiple cases
    for a single function.
    """
    CO_OPTIMIZED                = 0x00001
    CO_NEWLOCALS                = 0x00002
    CO_VARARGS                  = 0x00004
    CO_VARKEYWORDS              = 0x00008
    CO_NESTED                   = 0x00010
    CO_VARGEN                   = 0x00020
    CO_NOFREE                   = 0x00040
    CO_COROUTINE                = 0x00080
    CO_ITERABLE                 = 0x00100
    CO_GENERATOR_ALLOWED        = 0x01000
    CO_FUTURE_DIVISION          = 0x02000
    CO_FUTURE_ABSOLUTE_IMPORT   = 0x04000
    CO_FUTURE_WITH_STATEMENT    = 0x08000
    CO_FUTURE_PRINT_FUNCTION    = 0x10000
    CO_FUTURE_UNICODE_LITERALS  = 0x20000
    CO_FUTURE_BARRY_AS_BDFL     = 0x40000
    CO_FUTURE_GENERATOR_STOP    = 0x80000

    cache_name = '__multicase_cache__'

    def __new__(cls, *other, **t_args):
        '''Decorate a case of a function with the specified types.'''
        def result(wrapped):
            # extract the FunctionType and its arg types
            cons, func = cls.reconstructor(wrapped), cls.ex_function(wrapped)
            args, defaults, (star, starstar) = cls.ex_args(func)
            s_args = 1 if isinstance(wrapped, (classmethod, types.MethodType)) else 0

            # determine if the user included the previous function
            if len(other):
                ok, prev = True, other[0]
            # ..otherwise we just figure it out by looking in the caller's locals
            elif func.func_name in sys._getframe().f_back.f_locals:
                ok, prev = True, sys._getframe().f_back.f_locals[func.func_name]
            # ..otherwise, first blood and we're not ok.
            else:
                ok = False

            # so, a wrapper was found and we need to steal its cache
            res = ok and cls.ex_function(prev)
            if ok and hasattr(res, cls.cache_name):
                cache = getattr(res, cls.cache_name)
            # ..otherwise, we just create a new one.
            else:
                cache = []
                res = cls.new_wrapper(func, cache)
                res.__module__ = getattr(wrapped, '__module__', getattr(func, '__module__', '__main__'))

            # calculate the priority by trying to match the most first
            argtuple = s_args, args, defaults, (star, starstar)
            priority = len(args) - s_args - len(t_args) + (len(args) and (next((float(i) for i, a in enumerate(args[s_args:]) if a in t_args), 0) / len(args))) + sum(0.3 for _ in filter(None, (star, starstar)))

            # check to see if our func is already in the cache
            current = tuple(t_args.get(_, None) for _ in args), (star, starstar)
            for i, (p, (_, t, a)) in enumerate(cache):
                if p != priority: continue
                # verify that it actually matches the entry
                if current == (tuple(t.get(_, None) for _ in a[1]), a[3]):
                    # yuuup, update it.
                    cache[i] = (priority, (func, t_args, argtuple))
                    res.__doc__ = cls.document(func.__name__, [n for _, n in cache])
                    return cons(res)
                continue

            # everything is ok...so should be safe to add it
            heapq.heappush(cache, (priority, (func, t_args, argtuple)))

            # now we can update the docs
            res.__doc__ = cls.document(func.__name__, [n for _, n in cache])

            # ..and then restore the wrapper to its former glory
            return cons(res)

        # validate type arguments
        for n, t in t_args.iteritems():
            if not isinstance(t, (types.TypeType, types.TupleType)) and t not in {callable}:
                error_keywords = ("{:s}={!s}".format(n, t.__name__ if isinstance(t, types.TypeType) or t in {callable} else '|'.join(t_.__name__ for t_ in t) if hasattr(t, '__iter__') else "{!r}".format(t)) for n, t in t_args.iteritems())
                raise internal.exceptions.InvalidParameterError(u"@{:s}({:s}) : The value ({!s}) specified for parameter \"{:s}\" is not a supported type.".format('.'.join(('internal', __name__, cls.__name__)), ', '.join(error_keywords), t, string.escape(n, '"')))
            continue

        # validate arguments containing original callable
        try:
            for c in other:
                cls.ex_function(c)
        except:
            error_keywords = ("{:s}={!s}".format(n, t.__name__ if isinstance(t, types.TypeType) or t in {callable} else '|'.join(t_.__name__ for t_ in t) if hasattr(t, '__iter__') else "{!r}".format(t)) for n, t in t_args.iteritems())
            raise internal.exceptions.InvalidParameterError(u"@{:s}({:s}) : The specified callable{:s} {!r} {:s} not of a valid type.".format('.'.join(('internal', __name__, cls.__name__)), ', '.join(error_keywords), '' if len(other) == 1 else 's', other, 'is' if len(other) == 1 else 'are'))

        # throw an exception if we were given an unexpected number of arguments
        if len(other) > 1:
            error_keywords = ("{:s}={!s}".format(n, t.__name__ if isinstance(t, types.TypeType) or t in {callable} else '|'.join(t_.__name__ for t_ in t) if hasattr(t, '__iter__') else "{!r}".format(t)) for n, t in t_args.iteritems())
            raise internal.exceptions.InvalidParameterError(u"@{:s}({:s}) : More than one callable ({:s}) was specified to add a case to. Refusing to add cases to more than one callable.".format('.'.join(('internal', __name__, cls.__name__)), ', '.join(error_keywords), ', '.join("\"{:s}\"".format(string.escape(c.co_name if isinstance(c, types.CodeType) else c.__name__, '"')) for c in other)))
        return result

    @classmethod
    def document(cls, name, cache):
        '''Generate documentation for a multicased function.'''
        res = []
        for func, types, _ in cache:
            doc = (func.__doc__ or '').split('\n')
            if len(doc) > 1:
                res.append("{:s} ->".format(cls.prototype(func, types)))
                res.extend("{: >{padding:d}s}".format(n, padding=len(name)+len(n)+1) for n in map(operator.methodcaller('strip'), doc))
            elif len(doc) == 1:
                res.append(cls.prototype(func, types) + (" -> {:s}".format(doc[0]) if len(doc[0]) else ''))
            continue
        return '\n'.join(res)

    @classmethod
    def prototype(cls, func, parameters={}):
        '''Generate a prototype for an instance of a function.'''
        args, defaults, (star, starstar) = cls.ex_args(func)
        argsiter = ("{:s}={:s}".format(n, parameters[n].__name__ if isinstance(parameters[n], types.TypeType) or parameters[n] in {callable} else '|'.join(t.__name__ for t in parameters[n]) if hasattr(parameters[n], '__iter__') else "{!r}".format(parameters[n])) if parameters.has_key(n) else n for n in args)
        res = (argsiter, ("*{:s}".format(star),) if star else (), ("**{:s}".format(starstar),) if starstar else ())
        return "{:s}({:s})".format(func.func_name, ', '.join(itertools.chain(*res)))

    @classmethod
    def match(cls, (args, kwds), heap):
        '''Given the specified `args` and `kwds`, find the correct function according to its types.'''
        # FIXME: yep, done in O(n) time.
        for f, ts, (sa, af, defaults, (argname, kwdname)) in heap:
            # populate our arguments
            ac, kc = (n for n in args), dict(kwds)

            # skip some args in our tuple
            map(next, (ac,)*sa)

            # build the argument tuple using the generator, kwds, or our defaults.
            a = []
            try:
                for n in af[sa:]:
                    try: a.append(next(ac))
                    except StopIteration: a.append(kc.pop(n) if n in kc else defaults.pop(n))
            except KeyError: pass
            finally: a = tuple(a)

            # now anything left in ac or kc goes in the wildcards. if there aren't any, then this iteration doesn't match.
            wA, wK = list(ac), dict(kc)
            if (not argname and len(wA)) or (not kwdname and wK):
                continue

            # if our perceived argument length doesn't match, then this iteration doesn't match either
            if len(a) != len(af[sa:]):
                continue

            # figure out how to match the types by checking if it's a regular type or it's a callable
            predicateF = lambda t: callable if t == callable else (lambda v: isinstance(v, t))

            # now we can finally start checking that the types match
            if any(not predicateF(ts[t])(v) for t, v in zip(af[sa:], a) if t in ts):
                continue

            # we should have a match
            return f, (tuple(args[:sa]) + a, wA, wK)

        error_arguments = [n.__class__.__name__ for n in args]
        error_keywords = ["{:s}={!s}".format(n, kwds[n].__class__.__name__) for n in kwds]
        raise internal.exceptions.UnknownPrototypeError(u"@multicase.call({:s}{:s}): The requested argument types do not match any of the available prototypes. The prototypes that are available are: {:s}.".format(', '.join(error_arguments) if args else '*()', ", {:s}".format(', '.join(error_keywords)) if error_keywords else '', ', '.join(cls.prototype(f, t) for f, t, _ in heap)))

    @classmethod
    def new_wrapper(cls, func, cache):
        '''Create a new wrapper that will determine the correct function to call.'''
        # define the wrapper...
        def F(*arguments, **keywords):
            heap = [res for _, res in heapq.nsmallest(len(cache), cache)]
            f, (a, w, k) = cls.match((arguments[:], keywords), heap)
            return f(*arguments, **keywords)
            #return f(*(arguments + tuple(w)), **keywords)

        # swap out the original code object with our wrapper's
        f, c = F, F.func_code
        cargs = c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags, \
                c.co_code, c.co_consts, c.co_names, c.co_varnames, \
                c.co_filename, '.'.join((func.__module__, func.func_name)), \
                c.co_firstlineno, c.co_lnotab, c.co_freevars, c.co_cellvars
        newcode = types.CodeType(*cargs)
        res = types.FunctionType(newcode, f.func_globals, f.func_name, f.func_defaults, f.func_closure)
        res.func_name, res.func_doc = func.func_name, func.func_doc

        # assign the specified cache to it
        setattr(res, cls.cache_name, cache)
        # ...and finally add a default docstring
        setattr(res, '__doc__', '')
        return res

    @classmethod
    def ex_function(cls, object):
        '''Extract the actual function type from a callable.'''
        if isinstance(object, types.FunctionType):
            return object
        elif isinstance(object, types.MethodType):
            return object.im_func
        elif isinstance(object, types.CodeType):
            res, = (n for n in gc.get_referrers(c) if n.func_name == c.co_name and isinstance(n, types.FunctionType))
            return res
        elif isinstance(object, (staticmethod, classmethod)):
            return object.__func__
        raise internal.exceptions.InvalidTypeOrValueError(object)

    @classmethod
    def reconstructor(cls, n):
        '''Return a closure that returns the original callable type for a function.'''
        if isinstance(n, types.FunctionType):
            return lambda f: f
        if isinstance(n, types.MethodType):
            return lambda f: types.MethodType(f, n.im_self, n.im_class)
        if isinstance(n, (staticmethod, classmethod)):
            return lambda f: type(n)(f)
        if isinstance(n, types.InstanceType):
            return lambda f: types.InstanceType(type(n), dict(f.__dict__))
        if isinstance(n, (types.TypeType, types.ClassType)):
            return lambda f: type(n)(n.__name__, n.__bases__, dict(f.__dict__))
        raise internal.exceptions.InvalidTypeOrValueError(type(n))

    @classmethod
    def ex_args(cls, f):
        '''Extract the arguments from a function.'''
        c = f.func_code
        varnames_count, varnames_iter = c.co_argcount, iter(c.co_varnames)
        args = tuple(itertools.islice(varnames_iter, varnames_count))
        res = { a : v for v, a in zip(reversed(f.func_defaults or []), reversed(args)) }
        try: starargs = next(varnames_iter) if c.co_flags & cls.CO_VARARGS else ""
        except StopIteration: starargs = ""
        try: kwdargs = next(varnames_iter) if c.co_flags & cls.CO_VARKEYWORDS else ""
        except StopIteration: kwdargs = ""
        return args, res, (starargs, kwdargs)

    @classmethod
    def generatorQ(cls, func):
        '''Returns true if `func` is a generator.'''
        func = cls.ex_function(func)
        return bool(func.func_code.co_flags & CO_VARGEN)

class alias(object):
    def __new__(cls, other, klass=None):
        cons, func = multicase.reconstructor(other), multicase.ex_function(other)
        if isinstance(other, types.MethodType) or klass:
            module = (func.__module__, klass or other.im_self.__name__)
        else:
            module = (func.__module__,)
        document = "Alias for `{:s}`.".format('.'.join(module + (func.func_name,)))
        res = cls.new_wrapper(func, document)
        return cons(res)

    @classmethod
    def new_wrapper(cls, func, document):
        # build the wrapper...
        def fn(*arguments, **keywords):
            return func(*arguments, **keywords)
        res = functools.update_wrapper(fn, func)
        res.__doc__ = document
        return res

### matcher class helper

# FIXME: figure out how to match against a bounds_t in a non-hacky way
class matcher(object):
    """
    An object that allows one to match or filter a list of things in an
    sort of elegant way.
    """

    def __init__(self):
        self.__predicate__ = {}
    def __attrib__(self, *attribute):
        if not attribute:
            return lambda n: n
        res = [(operator.attrgetter(a) if isinstance(a, basestring) else a) for a in attribute]
        return lambda o: tuple(x(o) for x in res) if len(res) > 1 else res[0](o)
    def attribute(self, type, *attribute):
        attr = self.__attrib__(*attribute)
        self.__predicate__[type] = lambda v: fcompose(attr, functools.partial(functools.partial(operator.eq, v)))
    def mapping(self, type, function, *attribute):
        attr = self.__attrib__(*attribute)
        mapper = fcompose(attr, function)
        self.__predicate__[type] = lambda v: fcompose(mapper, functools.partial(operator.eq, v))
    def boolean(self, type, function, *attribute):
        attr = self.__attrib__(*attribute)
        self.__predicate__[type] = lambda v: fcompose(attr, functools.partial(function, v))
    def predicate(self, type, *attribute):
        attr = self.__attrib__(*attribute)
        self.__predicate__[type] = functools.partial(fcompose, attr)
    def match(self, type, value, iterable):
        matcher = self.__predicate__[type](value)
        return itertools.ifilter(matcher, iterable)

### character processing (escaping and unescaping)
class character(object):
    """
    This namespace is responsible for performing actions on individual
    characters such as detecting printability or encoding them in a
    form that can be evaluated.
    """
    class const(object):
        ''' Constants '''
        import string as _string, unicodedata as _unicodedata

        backslash = '\\'

        # character mappings to escaped versions
        mappings = {
            '\a' : r'\a',
            '\b' : r'\b',
            '\t' : r'\t',
            '\n' : r'\n',
            '\v' : r'\v',
            '\f' : r'\f',
            '\r' : r'\r',
            '\0' : r'\0',
            '\1' : r'\1',
            '\2' : r'\2',
            '\3' : r'\3',
            '\4' : r'\4',
            '\5' : r'\5',
            '\6' : r'\6',
            # '\7' : r'\7',     # this is the same as '\a'
        }

        # inverse mappings of characters plus the '\7 -> '\a' byte
        inverse = { v : k for k, v in itertools.chain([('\7', r'\7')], six.iteritems(mappings)) }

        # whitespace characters as a set
        whitespace = { ch for ch in _string.whitespace }

        # printable characters as a set
        printable = { ch for ch in _string.printable } - whitespace

        # hexadecimal digits as a lookup
        hexadecimal = { ch : i for i, ch in enumerate(_string.hexdigits[:0x10]) }

    @classmethod
    def asciiQ(cls, ch):
        '''Returns whether an ascii character is printable or not.'''
        return operator.contains(cls.const.printable, ch)

    @classmethod
    def unicodeQ(cls, ch):
        '''Returns whether a unicode character is printable or not.'''
        cat = cls.const._unicodedata.category(ch)
        return cat[0] != 'C'

    @classmethod
    def whitespaceQ(cls, ch):
        '''Returns whether a character represents whitespace or not.'''
        return operator.contains(cls.const.whitespace, ch)

    @classmethod
    def mapQ(cls, ch):
        '''Returns whether a character is mappable or not.'''
        return operator.contains(cls.const.mappings, ch)

    @classmethod
    def map(cls, ch):
        '''Given a mappable character, return the string that emits it.'''
        return operator.getitem(cls.const.mappings, ch)

    @classmethod
    def hexQ(cls, ch):
        '''Returns whether a character is a hex digit or not.'''
        return operator.contains(cls.const.hexadecimal, ch)

    @classmethod
    def to_hex(cls, integer):
        '''Given an integer, return the hex digit that it represents.'''
        if integer >= 0 and integer < 0x10:
            return six.int2byte(integer + 0x30) if integer < 10 else six.int2byte(integer + 0x57)
        raise ValueError

    @classmethod
    def of_hex(cls, digit):
        '''Given a hex digit, return it as an integer.'''
        return operator.getitem(cls.const.hexadecimal, digit.lower())

    @classmethod
    def escape(cls, result):
        '''Return a generator that escapes all non-printable characters and sends them to `result`.'''

        # begin processing any input that is fed to us
        while True:
            ch = (yield)
            n = six.byte2int(ch)

            # check if character has an existing escape mapping
            if cls.mapQ(ch):
                for ch in cls.map(ch):
                    result.send(ch)

            # check if character is a backslash
            elif operator.contains(cls.const.backslash, ch):
                result.send(cls.const.backslash)
                result.send(ch)

            # check if character is printable (unicode)
            elif isinstance(ch, unicode) and cls.unicodeQ(ch):
                result.send(ch)

            # check if character is printable (ascii)
            elif isinstance(ch, str) and cls.asciiQ(ch):
                result.send(ch)

            # check if character is a single-byte ascii
            elif n < 0x100:
                result.send(cls.const.backslash)
                result.send('x')
                result.send(cls.to_hex((n & 0xf0) / 0x10))
                result.send(cls.to_hex((n & 0x0f) / 0x01))

            # check that character is an unprintable unicode character
            elif n < 0x10000:
                result.send(cls.const.backslash)
                result.send('u')
                result.send(cls.to_hex((n & 0xf000) / 0x1000))
                result.send(cls.to_hex((n & 0x0f00) / 0x0100))
                result.send(cls.to_hex((n & 0x00f0) / 0x0010))
                result.send(cls.to_hex((n & 0x000f) / 0x0001))

            # maybe the character is an unprintable long-unicode character
            elif n < 0x110000:
                result.send(cls.const.backslash)
                result.send('U')
                result.send(cls.to_hex((n & 0x00000000) / 0x10000000))
                result.send(cls.to_hex((n & 0x00000000) / 0x01000000))
                result.send(cls.to_hex((n & 0x00100000) / 0x00100000))
                result.send(cls.to_hex((n & 0x000f0000) / 0x00010000))
                result.send(cls.to_hex((n & 0x0000f000) / 0x00001000))
                result.send(cls.to_hex((n & 0x00000f00) / 0x00000100))
                result.send(cls.to_hex((n & 0x000000f0) / 0x00000010))
                result.send(cls.to_hex((n & 0x0000000f) / 0x00000001))

            # if we're here, then we have no idea what kind of character it is
            else:
                raise internal.exceptions.InvalidFormatError(u"{:s}.unescape({!s}) : Unable to determine how to escape the current character code ({:#x}).".format('.'.join(('internal', __name__, cls.__name__)), result, n))

            continue
        return

    @classmethod
    def unescape(cls, result):
        '''Return a generator that reads characters from an escaped string, unescapes/evaluates them, and then the unescaped character to `result`.'''

        # enter our processing loop for each character
        while True:
            ch = (yield)

            # okay, we got a backslash, so let's go...
            if ch == cls.const.backslash:
                t = (yield)

                # check if our character is in our inverse mappings
                if operator.contains(cls.const.inverse, cls.const.backslash + t):
                    ch = operator.getitem(cls.const.inverse, cls.const.backslash + t)
                    result.send(ch)

                # check if our character is a backslash
                elif operator.contains(cls.const.backslash, t):
                    result.send(cls.const.backslash)

                # check if the 'x' prefix is specified, which represents a hex digit
                elif t == 'x':
                    hb, lb = (yield), (yield)
                    if any(not cls.hexQ(b) for b in {hb, lb}):
                        raise internal.exceptions.InvalidFormatError(u"{:s}.unescape({!s}) : Expected the next two characters ('{:s}', '{:s}') to be hex digits for an ascii character.".format('.'.join(('internal', __name__, cls.__name__)), result, string.escape(hb, '\''), string.escape(lb, '\'')))

                    # convert the two hex digits into their integral forms
                    h, l = map(cls.of_hex, (hb.lower(), lb.lower()))

                    # coerce the digits into an ascii character and send the character to our result
                    result.send(six.int2byte(
                        h * 0x10 |
                        l * 0x01 |
                    0))

                # if we find a 'u' prefix, then we have a unicode character
                elif t == 'u':
                    hwb, lwb, hb, lb = (yield), (yield), (yield), (yield)
                    if any(not cls.hexQ(b) for b in {hwb, lwb, hb, lb}):
                        raise internal.exceptions.InvalidFormatError(u"{:s}.unescape({!s}) : Expected the next four characters ('{:s}', '{:s}', '{:s}', '{:s}') to be hex digits for a unicode character.".format('.'.join(('internal', __name__, cls.__name__)), result, string.escape(hwb, '\''), string.escape(lwb, '\''), string.escape(hb, '\''), string.escape(lb, '\'')))

                    # convert the four hex digits into their integral forms
                    hw, lw, h, l = map(cls.of_hex, (hwb.lower(), lwb.lower(), hb.lower(), lb.lower()))

                    # coerce the digits into a unicode character and send the character to our result
                    result.send(six.unichr(
                        hw * 0x1000 |
                        lw * 0x0100 |
                        h  * 0x0010 |
                        l  * 0x0001 |
                    0))

                # if we find a 'U' prefix, then we have a long unicode character
                elif t == 'U':
                    hzb, lzb, Hwb, Lwb, hwb, lwb, hb, lb = (yield), (yield), (yield), (yield), (yield), (yield), (yield), (yield)
                    if any(not cls.hexQ(b) or cls.of_hex(b) for b in (hzb, lzb)):
                        raise internal.exceptions.InvalidFormatError(u"{:s}.unescape({!s}) : Expected the next two characters ('{:s}', '{:s}') to be zero for a long-unicode character.".format('.'.join(('internal', __name__, cls.__name__)), result, string.escape(hzb, '\''), string.escape(lzb, '\'')))
                    if any(not cls.hexQ(b) for b in {Hwb, Lwb, hwb, lwb, hb, lb}) or Hwb not in {'0', '1'}:
                        raise internal.exceptions.InvalidFormatError(u"{:s}.unescape({!s}) : Expected the next six characters ('{:s}', '{:s}', '{:s}', '{:s}', '{:s}', '{:s}') to be hex digits for a long-unicode character.".format('.'.join(('internal', __name__, cls.__name__)), result, string.escape(Hwb, '\''), string.escape(Lwb, '\''), string.escape(hwb, '\''), string.escape(lwb, '\''), string.escape(hb, '\''), string.escape(lb, '\'')))

                    # convert the six hex digits into their integral forms
                    Hw, Lw, hw, lw, h, l = map(cls.of_hex, (Hwb.lower(), Lwb.lower(), hwb.lower(), lwb.lower(), hb.lower(), lb.lower()))

                    # coerce the digits into a unicode character and send the character to our result
                    result.send(six.unichr(
                        Hw * 0x100000 |
                        Lw * 0x010000 |
                        hw * 0x001000 |
                        lw * 0x000100 |
                        h  * 0x000010 |
                        l  * 0x000001 |
                    0))

                else:
                    raise internal.exceptions.InvalidFormatError(u"{:s}.unescape({!s}) : An unknown character code was specified ('{:s}').".format('.'.join(('internal', __name__, cls.__name__)), result, string.escape(t, '\'')))

            # we haven't received a backslash, so there's nothing to unescape
            else:
                result.send(ch)

            continue
        return

### string casting, escaping and emitting
class string(object):
    """
    IDA takes ascii strings and internally encodes them as UTF8. So
    this class aims to normalize all of these strings by converting
    them into a `unicode` type.
    """

    @classmethod
    def of(cls, string):
        '''Return a string from IDA in a format that is consistent'''
        return None if string is None else string.decode('utf8') if isinstance(string, str) else string

    @classmethod
    def to(cls, string):
        '''Convert a string into a form that IDA will accept.'''
        return None if string is None else string.encode('utf8') if isinstance(string, unicode) else string

    # dictionary for mapping control characters to their correct forms
    mapping = {
        '\n' : r'\n',
         ' ' : r' ',
    }

    @classmethod
    def escape(cls, string, quote=''):
        """Escape the characters in `string` specified by `quote`.

        Handles both unicode and ascii. Defaults to escaping only
        the unprintable characters.
        """

        # construct a list for anything that gets transformed
        res = internal.interface.collect_t(list, lambda agg, value: agg + [value])

        # instantiate our generator for escaping unprintables in the string
        transform = character.escape(res); next(transform)

        # iterate through each character, sending everything to res
        for ch in iter(string or ''):

            # check if character is a user-specified quote or a backslash
            if any(operator.contains(set, ch) for set in (quote, '\\')):
                res.send('\\')
                res.send(ch)

            # check if character has an escape mapping to use
            elif operator.contains(cls.mapping, ch):
                map(res.send, cls.mapping[ch])

            # otherwise we can just send it to transform to escape it
            else:
                transform.send(ch)
            continue

        # figure out the correct function that determines how to join the res
        fjoin = (unicode() if isinstance(string, unicode) else str()).join

        return fjoin(res.get())

    @classmethod
    def repr(cls, item):
        """Given an item, return the `repr()` of it whilst ensuring that a proper ascii string is returned.

        All unicode strings are encoded to UTF-8 in order to guarantee
        the resulting string can be emitted.
        """
        if isinstance(item, basestring):
            res = cls.escape(item, '\'')
            if all(six.byte2int(ch) < 0x100 for ch in item):
                return "'{:s}'".format(res)
            return u"u'{:s}'".format(res)
        elif isinstance(item, tuple):
            res = map(cls.repr, item)
            return "({:s}{:s})".format(', '.join(res), ',' if len(item) == 1 else '')
        elif isinstance(item, list):
            res = map(cls.repr, item)
            return "[{:s}]".format(', '.join(res))
        elif isinstance(item, set):
            res = map(cls.repr, item)
            return "set([{:s}])".format(', '.join(res))
        elif isinstance(item, dict):
            res = ("{:s}: {:s}".format(cls.repr(k), cls.repr(v)) for k, v in six.iteritems(item))
            return "{{{:s}}}".format(', '.join(res))
        return repr(item)

    @classmethod
    def kwargs(cls, kwds):
        '''Format a dictionary (from kwargs) so that it can be emitted to a user as part of a message.'''
        res = []
        for key, value in six.iteritems(kwds):
            k, v = cls.escape(key), cls.repr(value)
            res.append("{:s}={!s}".format(*(item.encode('utf8') if isinstance(item, unicode) else item for item in (k, v))))
        return ', '.join(res).decode('utf8')

    @classmethod
    def decorate_arguments(cls, *names):
        '''Given a list of argument names, decode them into unicode strings.'''
        return transform(cls.of, *names)

### wrapping functions with another caller whilst preserving the wrapped function
class wrap(object):
    """
    A lot of magic is in this class which allows one to do a proper wrap
    around a single callable.
    """

    CO_OPTIMIZED                = 0x00001
    CO_NEWLOCALS                = 0x00002
    CO_VARARGS                  = 0x00004
    CO_VARKEYWORDS              = 0x00008
    CO_NESTED                   = 0x00010
    CO_VARGEN                   = 0x00020
    CO_NOFREE                   = 0x00040
    CO_COROUTINE                = 0x00080
    CO_ITERABLE                 = 0x00100
    CO_GENERATOR_ALLOWED        = 0x01000
    CO_FUTURE_DIVISION          = 0x02000
    CO_FUTURE_ABSOLUTE_IMPORT   = 0x04000
    CO_FUTURE_WITH_STATEMENT    = 0x08000
    CO_FUTURE_PRINT_FUNCTION    = 0x10000
    CO_FUTURE_UNICODE_LITERALS  = 0x20000
    CO_FUTURE_BARRY_AS_BDFL     = 0x40000
    CO_FUTURE_GENERATOR_STOP    = 0x80000

    import opcode, compiler.consts as consts

    @classmethod
    def co_assemble(cls, operation, operand=None):
        '''Assembles the specified `operation` and `operand` into a code string.'''
        opcode = cls.opcode.opmap[operation]
        if operand is None:
            return six.int2byte(opcode)

        # if operand was defined, then encode it
        op1 = (operand & 0x00ff) / 0x0001
        op2 = (operand & 0xff00) / 0x0100
        return reduce(operator.add, map(six.int2byte, (opcode, op1, op2)), bytes())

    @classmethod
    def co_varargsQ(cls, co):
        '''Returns whether the provided code type, `co`, takes variable arguments.'''
        return bool(co.co_flags & cls.consts.CO_VARARGS)

    @classmethod
    def co_varkeywordsQ(cls, co):
        '''Returns whether the provided code type, `co`, takes variable keyword arguments.'''
        return bool(co.co_flags & cls.consts.CO_VARKEYWORDS)

    @classmethod
    def cell(cls, *args):
        '''Convert `args` into a ``cell`` tuple.'''
        return tuple(((lambda item: lambda : item)(arg).func_closure[0]) for arg in args)

    @classmethod
    def assemble(cls, function, wrapper, bound=False):
        """Assemble a ``types.CodeType`` that will execute `wrapper` with `F` as its first parameter.

        If `bound` is ``True``, then assume that the first parameter for `F` represents the instance it's bound to.
        """
        F, C, S = map(cls.extract, (function, wrapper, cls.assemble))
        Fc, Cc, Sc = map(operator.attrgetter('func_code'), (F, C, S))

        ## build the namespaces that we'll use
        Tc = cls.co_varargsQ(Fc), cls.co_varkeywordsQ(Fc)

        # first we'll build the globals that get passed to the wrapper
        Sargs = ('F', 'wrapper')
        Svals = (f if callable(f) else fo for f, fo in [(function, F), (wrapper, C)])

        # rip out the arguments from our target `F`
        Fargs = Fc.co_varnames[:Fc.co_argcount]
        Fwildargs = Fc.co_varnames[Fc.co_argcount : Fc.co_argcount + sum(Tc)]

        # combine them into tuples for looking up variables
        co_names, co_varnames = Sargs[:], Fargs[:] + Fwildargs[:]

        # free variables (that get passed to `C`)
        co_freevars = Sargs[:2]

        # constants for code type (which consist of just the self-doc)
        co_consts = (F.func_doc,)

        ## figure out some things for assembling the bytecode

        # first we'll grab the call instruction type to use
        call_ = {
            (False, False) : 'CALL_FUNCTION',
            (True, False)  : 'CALL_FUNCTION_VAR',
            (False, True)  : 'CALL_FUNCTION_KW',
            (True, True)   : 'CALL_FUNCTION_VAR_KW',
        }
        call = call_[Tc]

        # now we'll determine the flags to apply
        flags_ = {
            (False, False) : 0,
            (True, False)  : cls.CO_VARARGS,
            (False, True)  : cls.CO_VARKEYWORDS,
            (True, True)   : cls.CO_VARARGS | cls.CO_VARKEYWORDS
        }

        co_flags = cls.CO_NESTED | cls.CO_OPTIMIZED | cls.CO_NEWLOCALS | flags_[Tc]

        ## assemble the code type that gets turned into a function
        code_, co_stacksize = [], 0
        asm = code_.append

        # first we'll dereference our cellvar for `wrapper`
        asm(cls.co_assemble('LOAD_DEREF', co_freevars.index('wrapper')))
        co_stacksize += 1

        # include the original `F` as the first arg
        asm(cls.co_assemble('LOAD_DEREF', co_freevars.index('F')))
        co_stacksize += 1

        # now we can include all of the original arguments (cropped by +1 if bound)
        for n in Fargs[int(bound):]:
            asm(cls.co_assemble('LOAD_FAST', co_varnames.index(n)))
            co_stacksize += 1

        # include any wildcard arguments
        for n in Fwildargs:
            asm(cls.co_assemble('LOAD_FAST', co_varnames.index(n)))
            co_stacksize += 1

        # call `wrapper` with the correct call type (+1 for `F`, -1 if bound)
        asm(cls.co_assemble(call, len(Fargs) + 1 - int(bound)))

        # and then return its value
        asm(cls.co_assemble('RETURN_VALUE'))

        # combine it into a single code string
        co_code = bytes().join(code_)

        ## next we'll construct the code type based on what we have
        cargs = len(Fargs), len(co_names) + len(co_varnames) + len(co_freevars), \
                co_stacksize, co_flags, co_code, \
                co_consts, co_names, co_varnames, \
                Fc.co_filename, Fc.co_name, Fc.co_firstlineno, \
                bytes(), co_freevars

        func_code = types.CodeType(*cargs)

        ## and then turn it back into a function
        res = types.FunctionType(func_code, F.func_globals, F.func_name, F.func_defaults, cls.cell(*Svals))
        res.func_name, res.func_doc = F.func_name, F.func_doc

        return res

    def __new__(cls, callable, wrapper):
        '''Return a function similar to `callable` that calls `wrapper` with `callable` as the first argument.'''
        cons, f = cls.constructor(callable), cls.extract(callable)

        # create a wrapper for the function that'll execute `callable` with the function as its first argument, and the rest with any args
        res = cls.assemble(callable, wrapper, bound=isinstance(callable, (classmethod, types.MethodType)))
        res.__module__ = getattr(callable, '__module__', getattr(callable, '__module__', '__main__'))

        # now we re-construct it and then return it
        return cons(res)

    @classmethod
    def extract(cls, object):
        '''Extract a ``types.FunctionType`` from a callable.'''

        # `object` is already a function
        if isinstance(object, types.FunctionType):
            return object

        # if it's a method, then extract the function from its propery
        elif isinstance(object, types.MethodType):
            return object.im_func

        # if it's a code type, then walk through all of its referrers finding one that matches it
        elif isinstance(object, types.CodeType):
            res, = (n for n in gc.get_referrers(c) if n.func_name == c.co_name and isinstance(n, types.FunctionType))
            return res

        # if it's a property decorator, then they hide the function in an attribute
        elif isinstance(object, (staticmethod, classmethod)):
            return object.__func__

        # okay, no go. we have no idea what this is.
        raise internal.exceptions.InvalidTypeOrValueError(object)

    @classmethod
    def arguments(cls, f):
        '''Extract the arguments from a function `f`.'''
        c = f.func_code
        count, iterable = c.co_argcount, iter(c.co_varnames)
        args = tuple(itertools.islice(iterable, count))
        res = { a : v for v, a in zip(reversed(f.func_defaults or []), reversed(args)) }
        starargs = next(iterable, '') if c.co_flags & cls.CO_VARARGS else ''
        kwdargs = next(iterable, '') if c.co_flags & cls.CO_VARKEYWORDS else ''
        return args, res, (starargs, kwdargs)

    @classmethod
    def constructor(cls, callable):
        '''Return a closure that constructs the original `callable` type from a function.'''

        # `callable` is a function type, so just return a closure that returns it
        if isinstance(callable, types.FunctionType):
            return lambda func: func

        # if it's a method type, then we just need to extract the related properties to construct it
        elif isinstance(callable, types.MethodType):
            return lambda method, self=callable.im_self, cls=callable.im_class: types.MethodType(method, self, cls)

        # if it's a property decorator, we just need to pass the function as an argument to the decorator
        elif isinstance(callable, (staticmethod, classmethod)):
            return lambda method, mt=callable.__class__: mt(method)

        # if it's a method instance, then we just need to instantiate it so that it's bound
        elif isinstance(callable, types.InstanceType):
            return lambda method, mt=callable.__class__: types.InstanceType(mt, dict(method.__dict__))

        # otherwise if it's a class or a type, then we just need to create the object with its bases
        elif isinstance(n, (types.TypeType, types.ClassType)):
            return lambda method, t=callable.__class__, name=callable.__name__, bases=callable.__bases__: t(name, bases, dict(method.__dict__))

        # if we get here, then we have no idea what kind of type `callable` is
        raise internal.exceptions.InvalidTypeOrValueError(callable.__class__)

### function decorator for translating arguments belonging to a function
def transform(translate, *names):
    '''This applies the callable `translate` to any function arguments that match `names` in the decorated function.'''
    names = {name for name in names}
    def wrapper(F, *rargs, **rkwds):
        f = wrap.extract(F)
        argnames, defaults, (wildname, _) = wrap.arguments(f)

        # convert any positional arguments
        res = ()
        for value, argname in zip(rargs, argnames):
            res += (translate(value) if argname in names else value),

        # get the rest
        for value in rargs[len(res):]:
            res += (translate(value) if wildname in names else value,)

        # convert any keywords arguments
        kwds = dict(rkwds)
        for argname in six.viewkeys(rkwds) & names:
            kwds[argname] = translate(kwds[argname])
        return F(*res, **kwds)

    # decorater that wraps the function `F` with `wrapper`.
    def result(F):
        return wrap(F, wrapper)
    return result
