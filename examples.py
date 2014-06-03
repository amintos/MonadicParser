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
digit = (Item('1') | Item('0')) >> Make(int)

op = Item('+')

# Pipelining (>>) can also be used to bind Variables.
# Keywords in the Make expression binds constructor arguments
# to variable arguments:

add = ((digit >> l) + op + (digit >> r)) >> Make(BinaryAdd, left=l, right=r)

# Now we test our parser:

strings = '0+0', '0+1', '1+0', '1+1'

for string in strings:
    # Instantiation takes the input data as well as a starting position
    # and a starting "AST", which is None.
    
    for result, end in add.instantiate(string, 0, None):

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
g['add'] = (g['digit'] >> l) + Item('+') + (g['digit'] >> r)
g['digit'] = (Item('1') | Item('0')) >> Make(int)


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
