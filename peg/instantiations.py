class Unifiable(object):
    """Base class for matching parser results"""

    @staticmethod
    def lift(value):
        if isinstance(value, Unifiable):
            return value
        else:
            return Constant(value)

    def unify(self, value):
        if self == value:
            yield self


class Any(Unifiable):
    """Accept any parse result"""

    def unify(self, value):
        yield value
Any = Any()


class Nothing(Unifiable):
    """Reject any parse result"""

    def unify(self, value):
        pass
Nothing = Nothing()


class InstantiatedExpression(Unifiable):
    """Base class for instantiated expressions"""

    def unpack(self):
        """Expose the underlying value to be passed to a secondary parser"""
        raise NotImplemented

    def combined_with(self, other):
        return Sequence([self, other])

    def combined_with_item(self, other):
        return Sequence([other, self])

    def combined_with_sequence(self, other):
        return Sequence(other.items + [self])


class Empty(InstantiatedExpression):
    """The empty instantiation which signals success but no value"""

    def combined_with(self, other):
        return other

    def __repr__(self):
        return "Empty"

    def unpack(self):
        return None

    def combined_with_sequence(self, other):
        return other

    def combined_with_item(self, other):
        return other

Empty = Empty()


class End(InstantiatedExpression):
    """Signals end of input"""

    def __init__(self, pos):
        self.pos = pos

    def unify(self, value):
        if isinstance(value, End):
            yield value

    def combined_with_sequence(self, other):
        return other

    def combined_with_item(self, other):
        return other

    def __repr__(self):
        return "<End at %s>" % self.pos

    def unpack(self):
        return None


class Constant(Unifiable):

    def __init__(self, value):
        self.value = value

    def unify(self, value):
        if self.value == value:
            yield self.value

    def __repr__(self):
        return "Constant(%s)" % repr(self.value)

    def unpack(self):
        return self.value


class ItemInstance(InstantiatedExpression):
    """Instantiation of a matched item. Carries the position of its match."""

    def __init__(self, value, pos):
        self.value = value
        self.pos = pos

    def __repr__(self):
        return "<%s at %s>" % (self.value, self.pos)

    def combined_with(self, other):
        return other.combined_with_item(self)

    def unify(self, value):
        if hasattr(value, 'value') and self.value == value.value:
            yield value
        elif self.value == value:
            yield value

    def unpack(self):
        return self.value


class Variable(Unifiable):
    """Captures the matched value. Matches only the captured value again."""

    def __init__(self):
        self.bound = False
        self.value = None

    def bind_to(self, value):
        self.value = value
        self.bound = True

    def unbind(self):
        self.value = None
        self.bound = False

    def unify(self, value):
        if self.bound:
            if isinstance(self.value, Unifiable):
                for unified in self.value.unify(value):
                    yield unified
            elif isinstance(value, Unifiable):
                for unified in value.unify(self):
                    yield unified
            else:
                if self.value == value:
                    yield value
        else:
            self.bind_to(value)
            yield value
            self.unbind()

    def unpack(self):
        if isinstance(self.value, Unifiable):
            return self.value.unpack()
        else:
            return self.value

    def __repr__(self):
        return "<Variable bound to %s>" % repr(self.value) if self.bound else "<Unbound variable>"



class Sequence(InstantiatedExpression):
    """Instantiation of multiple chained items"""

    def __init__(self, items):
        self.pos = items[0].pos
        self.items = items

    def combined_with(self, other):
        return other.combined_with_sequence(self)

    def combined_with_item(self, other):
        return Sequence([other] + self.items)

    def combined_with_sequence(self, other):
        return Sequence(other.items + self.items)

    def __repr__(self):
        return "Sequence(%s)" % self.items

    def unify(self, value):
        if isinstance(value, Sequence):
            if len(self.items) == len(value.items):
                try:
                    for i in xrange(len(self.items)):
                        self.items[i].unify(value.items[i]).next()
                    yield value
                except StopIteration:
                    print "!"
                    return

    def unpack(self):
        return [item.unpack() for item in self.items]


class Result(InstantiatedExpression):
    """Instantiation wrapper with a label attached"""

    def __init__(self, result, label):
        self.result = result
        self.label = label

    def __repr__(self):
        return "<%s: %s>" % (self.label, self.result)

    def unpack(self):
        return self.result.unpack()


class Label(Unifiable):
    """Labels the current instantiation.
    Example:  Item(x) >> Label('x') """

    def __init__(self, label):
        self.label = label

    def unify(self, value):
        yield Result(value, self.label)


class Make(Unifiable):
    """Call a factory/class constructor with given variables.
    Example:
    
    ((p >> f) + (q >> g)) >> Make(MyClass, foo=f, bar=b)
    
    will instantiate MyClass for each possible parsing result using:
    
    MyClass(foo=f.value, bar=b.value)
    """
    
    def __init__(self, factory, **kwargs):
        self.factory = factory
        self.args = kwargs

    def unify(self, value):
        kwargs = {}
        for key, var in self.args.iteritems():
            if var.bound:
                kwargs[key] = var.unpack()
        yield self.factory(**kwargs)
