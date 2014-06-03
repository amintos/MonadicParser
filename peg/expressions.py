from instantiations import *

class Expression(object):
    """Base class for parsing expressions"""

    @staticmethod
    def lift(value):
        """Make sure atomic values are constant expressions"""
        if isinstance(value, Expression):
            return value
        else:
            return Constant(value)

    def instantiate(self, value, position, before):
        raise NotImplemented

    def __add__(self, other):
        return Chain(self, other)

    def __or__(self, other):
        return Alternative(self, other)

    def __rshift__(self, other):
        return Unify(self, other)

    def __xor__(self, other):
        return Locate(self, other)


class Reference(Expression):
    """Lazy reference to a grammar rule. Detects infinite recursion."""

    def __init__(self, grammar, key):
        self.grammar = grammar
        self.key = key

    def instantiate(self, value, position, before):
        if not self.ensure_progress(position, len(value)):
            print "Warning: Instantiation of rule '%s' may be infinite. Tracking back." % self.key
            return
        self.grammar.history.append((position, self))
        for result, next_pos in self.grammar.rules[self.key].instantiate(value, position, before):
            yield result, next_pos
        self.grammar.history.pop()

    def ensure_progress(self, pos, size):
        for prev_pos, rule in reversed(self.grammar.history):
            if rule is self and pos == prev_pos and pos < size:
                return False
        return True


class Grammar(Expression):
    """Collection of named rules."""

    def __init__(self, start):
        """Instantiate grammar. start = name of the starting non-terminal"""
        self.rules = {}
        self.start = start
        self.history = []

    def __setitem__(self, key, value):
        """Define a non-terminal"""
        self.rules[key] = value >> Label(key)

    def __getitem__(self, item):
        """Refer to a non-terminal. The resolution can be defined later (lazy)"""
        return Reference(self, item)

    def instantiate(self, value, position=0, before=None):
        """Instantiate grammar on a given collection"""
        for result, next_pos in self.rules[self.start].instantiate(value, position, before):
            yield result, next_pos


class Chain(Expression):
    """Chains two expressions. Results are combined using the combined_with method."""

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def instantiate(self, value, position, before):
        for left_value, p1 in self.left.instantiate(value, position, before):
            for right_value, p2 in self.right.instantiate(value, p1, left_value):
                # Any of the expressions may yield the empty instantiation.
                if left_value is Empty:
                    if right_value is Empty:
                        yield Empty, p2
                    yield right_value, p2
                elif right_value is Empty:
                    yield left_value, p2
                else:
                    # If two expressions yield an instantiation, call their
                    # (polymorphic) combinator.
                    yield (left_value.combined_with(right_value), p2)


class Unify(Expression):
    """Pipes an expression's instantiation into a Unifiable instance.
    Returns the unified/transformed instantiation"""

    def __init__(self, expression, pattern):
        self.expression = expression
        self.pattern = pattern

    def instantiate(self, value, position, before):
        for parse_result, p1 in self.expression.instantiate(value, position, before):
            for unify_result in self.pattern.unify(parse_result):
                yield unify_result, p1


class Alternative(Expression):
    """Non-deterministically branches instantiation along two expressions"""

    def __init__(self, one, another):
        self.one = one
        self.another = another

    def instantiate(self, value, position, before):
        for result, rest in self.one.instantiate(value, position, before):
            yield result, rest
        for result, rest in self.another.instantiate(value, position, before):
            yield result, rest


class Return(Expression):
    """Matches end of input. Instantiates to an End instance or fails."""

    def instantiate(self, value, position, before):
        if position == len(value):
            yield (End(position), position)

    def __add__(self, other):
        raise Exception("Trying to place anything behind end-of-match.")

    def __repr__(self):
        return "Return"

    def unpack(self):
        return None


class Item(Expression):
    """Matches a Unifiable or constant against an input item, yields ItemInstance."""

    def __init__(self, match):
        self.match = Unifiable.lift(match)

    def instantiate(self, value, position, before):
        if position < len(value):
            for match in self.match.unify(value[position]):
                yield (ItemInstance(match, position), position + 1)

    def __repr__(self):
        return "Item(%s)" % self.value


class Anything(Expression):
    """Skips an item"""

    def instantiate(self, value, position, before):
        yield (ItemInstance(value[position], position), position + 1)
AnyItem = Anything()


class Ahead(Expression):
    """Look-ahead expression. Yields the empty instantiation of look-ahead succeeds."""

    def __init__(self, expression):
        self.expression = expression

    def instantiate(self, value, position, before):
        for result, next_pos in self.expression.instantiate(value, position, before):
            yield Empty, position
            break


class Locate(Expression):
    """Extracts the position of the current match and unifies it.
    Example:   position = Variable(); parser = Locate(Item('x'), position)"""

    def __init__(self, expression, match):
        self.expression = expression
        self.match = match

    def instantiate(self, value, position, before):
        for result, next_pos in self.expression.instantiate(value, position, before):
            for _ in self.match.unify(result.pos):
                yield result, next_pos




class Repeat(Expression):
    """Greedy repeated expression. Will only yield the (recursively) first match.
    WARNING: Will not unbind variables!
    Call unbind() every time a variable has been bound inside a Repeat(...)"""

    def __init__(self, what, once=True):
        self.what = what
        self.once = once

    def instantiate(self, value, position, before):
        result, next_pos, next_before = Empty, position, before
        try:
            while True:
                next_result, next_pos = self.what.instantiate(value, next_pos, next_before).next()
                result = result.combined_with(next_result)
                next_before = result
        except StopIteration:
            if not self.once or result is not Empty:
                yield result, next_pos


class RepeatBack(Expression):
    """Backtracking repeated expression. Will yield all instantiations.
    WARNING: Uses stack depth proportional to the longest instantiation!"""

    def __init__(self, what):
        self.what = what

    def instantiate(self, value, position, before):
        for result, p1 in self.what.instantiate(value, position, before):
            continues = False
            for next_result, p2 in self.instantiate(value, p1, result):
                continues = True
                yield result.combined_with(next_result), p2
            if not continues:
                yield result, p1