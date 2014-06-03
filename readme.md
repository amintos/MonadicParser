MonadicParser
=============

This is a prototype implementation of Parsing Expression Grammars (PEG) using a lazy monad-style implementation.

## Example

### Combining parsers

Let's start with items. The item is the fundamental parser, it just matches a single element of a collection, e.g. character inside a string or any object inside a list.

```python
from peg import *

zero = Item('0')
```

Parsers can be combined using either chaining (+) or alternative (|). Chained parsers are applied in order and the suffix left over by one parser is consumed by the next one. Alternatives evaluate both possible parsing paths, each parser starts with the same suffix.

```python
bit = Item('0') | Item('1')
add = bit + Item('+') + bit
```

### Transforming in-place

It would be nice to convert the results from the bit-Parser directly to an integer, so let's pass the parsed value into Python's builtin method using the Make modifier:

```python
bit = (Item('0') | Item('1')) >> Make(int)
```

Let's try that out:

```python
for result, pos in bit.instantiate('1', 0, None):
    print result
# <1 at 0>
```

The result is an InstantiatedExpression object with value '1' at position 0. The ```pos``` variable will contain the position where parsing has finished. The parser resolves to exactly one instantiation, because the grammar is not ambiguous. The other arguments are just the starting position and the previously parsed result in case the parser needs it.

### Capturing results using variables

Now how do we extract multiple integers from our expression? We use variables:

```python
l = Variable()
r = Variable()

add = (bit >> l) + Item('+') + (bit >> r)
```

To see exactly how this evaluates, try:

```python
for result, pos in add.instantiate('1+0', 0, None):
    print l.value, r.value
    
# 1 0
```

### Building/Evaluating the AST

Consider the case where we want our parsing results to be combined to some composite object (**Abstract Syntax Tree**) or evaluated to something else. For simplicity we do not evaluate to an AST but to the result immediately:
```python
def binary_add(left, right):
    return (left + right) % 2
```

We can bind the arguments of this method to our variables using the Make modifier. (Keep in mind that variables may be complex structures that do not magically resolve to their value, so the Make modifier unpacks them for us)

```python
add = ((bit >> l) + Item('+') + (bit >> r)) >> Make(binary_add, left=l, right=r)
```

Now we can try the following:

```python
for result, pos in add.instantiate('1+1', 0, None):
    print result
    
# 0, that's the result of our method.
```

## Creating custom parsers

An own parsing expression can be created by deriving a class from ```Expression``` and overriding ```def instantiate(self, value, position, before)```. This example shows how to create a parser that parses an item if it is included in a specific set:

```python
class AnyOf(Expression):
	
    def __init__(self, choices):
        self.choices = choices
    
    def instantiate(self, value, position, previous):
        item = value[position]
        if value[position] in self.choices:
            # note that we have to yield the result and the NEXT position.
            yield ItemInstance(item, position), position + 1   
```

**Not yielding anything** is considered failure and causes backtracking. **Yielding multiple times** causes the parser to backtrack to the next yield if the first did not lead to a full instantiation. Given this extension we can rewrite our bit-parser:

```python
bit = AnyOf('01') >> Make(int)
```