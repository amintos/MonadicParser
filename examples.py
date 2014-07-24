from peg import *

# Parse an Operator expression

class BinaryAdd(object):
    """This is the AST-node we want to construct"""

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def evaluate(self):
        return (self.left + self.right) % 2

# Variables capture results on their way
l = Variable()
r = Variable()

# Item('x') matches element x. The | operator chains parsers.
# Using the >> notation we pipe this parser's result into a constructor:
digit = (item('1') | item('0')) >> Make(int)

op = item('+')

# Pipelining (>>) can also be used to bind Variables.
# Keywords in the Make expression binds constructor arguments
# to variable arguments:

add = ((digit >> l) + op + (digit >> r)) >> Make(BinaryAdd, left=l, right=r)

# Now we test our parser:

strings = '0+0', '0+1', '1+0', '1+1'

for string in strings:
    # Instantiation takes the input data as well as a starting position
    # and a starting "AST", which is None.
    
    for result, end in add(string, 0):

        # Why a for loop? Well, a grammar can have multiple valid
        # resolutions, so we return all of them. Parsing is lazy, so
        # we can just break this loop without wasting time.
        
        print string, '=', result.evaluate(), 'parsed until:', end

# And now everything with a grammar object.
# Grammars can use recursion, as a referred parsing rule may be
# defined later.

g = Grammar('expr')         # expr is the starting non-terminal

# we can add rules in arbitrary order. g['key'] is resolved in a lazy fashion.
g['expr'] = g['add'] >> Make(BinaryAdd, left = l, right = r)
g['add'] = (g['digit'] >> l) + item('+') + (g['digit'] >> r)
g['digit'] = (item('1') | item('0')) >> Make(int)


# An own extension (see readme.md before)

class Select(Unifiable):
    def __init__(self, one, another):
        self.one = one
        self.another = another

    def unify(self, value):
        for result in self.one.unify(value):
            yield result
        for result in self.another.unify(value):
            yield result

# Structured data

class X(object):
    def __init__(self):
        self.foo = 42

class Y(object):
    def __init__(self):
        self.bar = 21

v = Variable()

# structured parser using [] to re-parse
get_the_int = (type_of(X) & get('foo') | type_of(Y) & get('bar')) [ type_of(int) >> v]

for result, pos in get_the_int(X(), 0):
    print v.value

for result, pos in get_the_int(Y(), 0):
    print v.value

# Parse a list of lists

input = [[1, 2], [3, 4]]

dig = Set(range(10))
#dig = item(1) | item(2) | item(3) | item(4)

# Use the cut combinator -p to avoid recursing through every instantiation
line = -many(dig)
matrix = -many(element[line])

for result, pos in matrix(input, 0):
    print result