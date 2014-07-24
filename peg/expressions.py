"""
Monad of PEG-Like Expressions
-----------------------------

Expressions are callables, taking a value and a position. Calling parses
the (indexable) value at the given position and yields pairs
(result, next_position) for each possible interpretation.

Expressions form a monad with

    Return(x)
        consuming no input and yielding only x.
        
    Bind(x, f), also x ** f
        applying f to each result from parser x. f should return a new
        Expression which is evaluated for each suffix left over by x.
        
        Laws:
                         p ** Return == p       # right unit property
                      Return(a) ** f == f(a)
        p ** (lambda a: (f(a) ** g)) == (p ** (lambda a: f(a))) ** g

    Branch(p, q), also p | q
        being the addition in the monad. Follows both parsing paths.
        
        Laws:
        (p | q) | r  == p | (q | r)             # associativity
        (p | q) ** f == (p ** f) | (q ** f)     # distributivity over binding

    Zero(), also zero
        being the unit element of addition/branching.
        
        Laws:
        p | Zero() == p                         # right unit property
        Zero() | p == p                         # left unit property

The following additional expressions are present:

    Basics
    ------

    element
        Consumes the next element and returns it.

    item(x)
        Consumes just x and returns it.

    chain(p, q)
        Apply parser p followed by parser q. Returns q's result.

    when(p, cond)
        Apply p but filter results by cond. cond should be a lambda
        expression taking p's result as input and return a bool.

    many(p)
        Non-greedy star. Apply p zero or more times, backtrack as needed.

    some(p)
        Non-greedy plus. Apply p one or more times, backtracking as needed.


    Recursors
    ---------

    star(p)
        Greedy star. (Not guaranteed to unbind variables!)
        Apply parser p zero or more times. Returns list of matches.
        
    plus(p)
        Greedy plus. (Not guaranteed to unbind variables!)
        Apply parser p one or more times. Return non-empty list of matches.


    Grammars
    --------

    g.Grammar(start_symbol)
        Defines a grammar which maps symbols (strings) to parser expressions.

    g[symbol] = parser
        Defines a named parser in g.

    g[symbol]
        Refers to a named parser in g.

    Symbols use **late binding** so that in order to refer to a symbol
    the symbol itself does not need to be defined.
        
    g(data)
        Applys g[starting_symbol] to the given data.


    Filters
    -------

    p >> f
        puts the results of p through f. f should have a 'unify' method
        which accepts output values of p and yields transformed values.

    There are multiple filters:

    Variable()
        creates a filter which stores the value for subsequent parsers.
        If it has a value stored and is forced to bind against a different
        value, it will fail and yield nothing. Variables expose their
        current value via unpack():

        v = Variable()
        for result in (p >> v)(input):
            print v.unpack()
        
    Make(method, [arg=var [,arg=var[, ...]])
        consumes a transformation method and yields the transformed
        result. Can auto-unpack variables into method arguments.

        Example 1:

        p >> Make(int)

        Example 2:

        v = Variable()
        w = Variable()
        ((p >> v) + (q >> w)) >> Make(some_class, x=v, y=w)

    Label(symbol)
        just labels a parsed result with symbol.
        
        
"""

from instantiations import *

class Expression(object):
    """Base class for parsing expressions"""
    
    def __call__(self, value, position):
        raise NotImplementedError

    def __add__(self, other):
        return chain(self, other)

    def __or__(self, other):
        return Branch(self, other)

    def __rshift__(self, other):
        return Unify(self, other)

    def __xor__(self, other):
        return Locate(self, other)

    def __pow__(self, other):
        """Bind operator in a monad of parsers"""
        return Bind(self, other)


class Bind(Expression):
    """Resulting parser of the monadic bind operator.
    'expr' is the parser to which we bind the 'each' method for each result.
    'each' is expected to take the parsed result and return a new parser."""

    def __init__(self, expr, each):
        self.expr = expr
        self.each = each

    def __call__(self, value, position):
        for r1, p1 in self.expr(value, position):   
            for r2, p2 in self.each(r1)(value, p1):
                yield r2, p2


class Return(Expression):
    """The returning element of the monad. Does not consume input,
    yields only the result"""

    def __init__(self, result):
        self.result = result

    def __call__(self, value, position):
        yield self.result, position


class Zero(Expression):
    """The monad's zero element. Signals parsing failure."""
    
    def __call__(self, value, position):
        return
        yield   # the "empty generator pattern"
zero = Zero()

class Branch(Expression):
    """The monad's addition. Yields results from both given parsers."""

    def __init__(self, p, q):
        self.p = p
        self.q = q

    def __call__(self, value, position):
        import itertools
        for result, pos in itertools.chain(self.p(value, position),
                                           self.q(value, position)):
            yield result, pos
            

class Element(Expression):
    """Parser for just the next element"""
    
    def __call__(self, value, position):
        if position < len(value):
            yield value[position], position + 1
element = Element() 

        
def chain(p1, p2):
    """Apply both parsers in order, return the most recent result"""
    return p1 ** (lambda result: p2)

def when(predicate):
    """Parse an element when it satisfies the predicate"""
    return element ** (lambda r: Return(r) if predicate(r) else zero)

def item(c):
    """Parse an element matching exactly c"""
    return when(lambda r: r == c)

def many(p):
    """Apply a parser zero or more times"""
    return some(p) | Return([])

def some(p):
    """Apply a parser one or more times"""
    return p ** (lambda a:
                 many(p) ** (lambda aa:
                             Return([a] + aa)))

class Set(Expression):
    """Sets represent classes of acceptable items.
    They optimize certain combinators by mapping them onto set arithmetics"""

    def __init__(self, choices):
        self.choices = choices if isinstance(choices, Set) else set(choices)

    def __or__(self, other):
        if isinstance(other, Set):
            return Set(self.choices | other.choices)
        else:
            return Expression.__or__(self, other)

    def __and__(self, other):
        if isinstance(other, Set):
            return Set(self.choices & other.choices)
        else:
            raise TypeError("& only applies to Set expressions")

    def __xor__(self, other):
        if isinstance(other, Set):
            return Set(self.choices ^ other.choices)
        else:
            return Expression.__xor__(self, other)

    def __sub__(self, other):
        if isinstance(other, Set):
            return Set(self.choices - other.choices)
        else:
            raise TypeError("& only applies to Set expressions")

    def __call__(self, value, position):
        if value[position] in self.choices:
            yield value


class Reference(Expression):
    """Lazy reference to a grammar rule. Detects infinite recursion."""

    def __init__(self, grammar, key):
        self.grammar = grammar
        self.key = key
        self._pos = 0

    def __call__(self, value, position):
        self._pos = position
        if not self.ensure_progress(position, len(value)):
            print "Warning: Instantiation of rule '%s' may be infinite. Tracking back." % self.key
            return
        with self:
            parse_rule = self.grammar.rules[self.key]
            for result, next_pos in parse_rule(value, position):
                yield result, next_pos

    def ensure_progress(self, pos, size):
        for prev_pos, rule in reversed(self.grammar.history):
            if rule is self and pos == prev_pos and pos < size:
                return False
        return True

    def __enter__(self):
        self.grammar.history.append((self._pos, self))

    def __exit__(self, *args):
        self.grammar.history.pop()
        self._pos = 0

class Grammar(Expression):
    """Collection of named rules."""

    def __init__(self, start):
        """Instantiate grammar. start = name of the starting non-terminal"""
        self.rules = {}
        self.start = start
        self.history = []

    def __setitem__(self, key, value):
        """Define a non-terminal"""
        self.rules[key] = value

    def __getitem__(self, item):
        """Refer to a non-terminal. The resolution can be defined later (lazy)"""
        return Reference(self, item)

    def __call__(self, value, position=0):
        """Instantiate grammar on a given collection"""
        for result, next_pos in self.rules[self.start](value, position):
            yield result, next_pos


class Unify(Expression):
    """Pipes an expression's instantiation into a Unifiable instance.
    Returns the unified/transformed instantiation"""

    def __init__(self, expression, pattern):
        self.expression = expression
        self.pattern = pattern

    def __call__(self, value, position):
        for parse_result, p1 in self.expression(value, position):
            for unify_result in self.pattern.unify(parse_result):
                yield unify_result, p1
                

class EndOfInput(Expression):
    """Matches end of input. Instantiates to an End instance or fails."""

    def __call__(self, value, position):
        if position == len(value):
            yield End(position), position


class Repeat(Expression):
    """Greedy repeated expression. Will only yield the (recursively) first match.
    WARNING: Will not unbind variables!
    Call unbind() every time a variable has been bound inside a Repeat(...)"""

    def __init__(self, what, once=True):
        self.what = what
        self.once = once

    def __call__(self, value, position):
        result, next_pos = [], position
        generator = None
        try:
            while True:
                generator = self.what(value, next_pos)
                next_result, next_pos = generator.next()
                result.append(next_result)
                next_before = result
                generator.close()
        except StopIteration:
            if not self.once or result:
                yield result, next_pos
        finally:
            if generator:
                generator.close()

def star(p):
    """Greedy star"""
    return Repeat(p, False)

def plus(p):
    """Greedy plus"""
    return Repeat(p, True)
