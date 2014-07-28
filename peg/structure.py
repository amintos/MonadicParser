"""
Parser extensions for structured data like objects and collections.

Extensions
----------

p [ q ]     Continues to parse p's output with q. Return q's output.

this        The parser for the whole input instead of just the next element.
            Use p[this] instead of p[element] if p does not emit a list.

get('name') Continues parsing with input.name

at(i)       Continues parsing with input[i]

typeof(t)   Continues parsing if isinstance(input, t)
"""

from expressions import *


class This(Expression):
    """Parser for just the argument given to parse.
    Complements the element parser which operates on indexable collections."""

    def __call__(self, value, position):
        yield value, position


class Attribute(Expression):

    def __init__(self, parser, attr):
        self.parser = parser
        self.attr = attr

    def __call__(self, value, position):
        for result, pos in self.parser(value, position):
            try:
                yield getattr(result, self.attr), pos
            except AttributeError:
                pass

this = This()



def get(name):
    """Continue parsing with input.<name>"""
    return this ** (lambda value: Return(getattr(value, name)))


def at(index):
    """Continue parsing with input[index]"""
    return this ** (lambda value: Return(value[index]))


def type_of(atype):
    """Continue parsing with input if type matches atype"""
    return this ** (lambda value: Return(value) if isinstance(value, atype) else zero)