MonadicParser
=============

This is a prototype implementation of Parsing Expression Grammars (PEG) using a lazy monad-style implementation.

## Example

### Combining parsers

Let's start with items. The item is the fundamental parser, it just matches a single element of a collection, e.g. character inside a string or any object inside a list.

```python
from peg import *

zero = item('0')
```

Parsers can be combined using either chaining (```+```) or alternative (```|```). Chained parsers are applied in order and the suffix left over by one parser is consumed by the next one. Alternatives evaluate both possible parsing paths, each parser starts with the same suffix. 

```python
bit = item('0') | item('1')
add = bit + item('+') + bit
```

### Transforming in-place

It would be nice to convert the results from the bit-Parser directly to an integer, so let's pass the parsed value into Python's builtin method using the Make modifier:

```python
bit = (item('0') | item('1')) >> Make(int)
```

Let's try that out:

```python
for result, pos in bit('1', 0):
    print result, pos
# 1 1
```

The ```pos``` variable will contain the position where parsing has finished. The parser resolves to exactly one instantiation, because the grammar is not ambiguous. The other argument is the starting position.

### Capturing results using variables

We use **variables** to extract multiple integers from our expression:

```python
l = Variable()
r = Variable()

add = (bit >> l) + item('+') + (bit >> r)
```

To see exactly how this evaluates, try:

```python
for result, pos in add('1+0', 0):
    print l.value, r.value
    
# 1 0
```

### Building/Evaluating the AST

Consider the case where we want our parsing results to be combined to some composite object (**Abstract Syntax Tree**) or evaluated to something else. For simplicity we do not evaluate to an AST but to the result immediately:
```python
def binary_add(left, right):
    return (left + right) % 2
```

We can bind the arguments of this method to our variables using the Make modifier. 
Make will unpack the variables transparently into the method's arguments.

```python
add = ((bit >> l) + item('+') + (bit >> r)) >> Make(binary_add, left=l, right=r)
```

Now we can try the following:

```python
for result, pos in add('1+1', 0):
    print result
    
# 0, that's the result of our method.
```

### Recursing and ealing with objects

The subscript combinator ```p[q]``` is a way of re-parsing the output of ```p``` with ```q```. If ```p``` just outputs a list (like the ```many``` or ```some``` combinators do), ```q``` may just use the parser semantics discussed above. However, many parsers will not yield parsable collections but single objects instead.

A single object can be parsed and returned using the ```this``` unit parser. So ```p[this]``` is the same as ```p```. There are some more parser combinators which use single-object semantics instead of indexable lists:

```python
get('x')    # Extract attribute x from the object being parsed
type_of(T)  # Return the parsed input iff it is an instance of T
at(i)       # Extract item i from an input collection
```

**Example:** Given two classes ```X``` (with an integer attribute ```foo```) and ```Y``` (with an integer attribute ```bar```). A parser which extracts the integer from either of these classes and checks for its type may looks like this:

```
class X(object):
    def __init__(self):
        self.foo = 42

class Y(object):
    def __init__(self):
        self.bar = 21
        
v = Variable()

# this is the parser:
get_the_int = (type_of(X) & get('foo') | 
               type_of(Y) & get('bar')) [ type_of(int) >> v]
               
# use it this way: 
for result, pos in get_the_int(X(), 0):
    print v.value
```

## Creating custom parsers

### Deriving a new expression type

An own parsing expression can be created by deriving a class from ```Expression``` and overriding ```def __call__(self, value, position)```. This example shows how to create a parser that parses an item if it is included in a specific set:

```python
class AnyOf(Expression):
	
    def __init__(self, choices):
        self.choices = choices
    
    def __call__(self, value, position):
        item = value[position]
        if value[position] in self.choices:
            # note that we have to yield the result and the NEXT position.
            yield item, position + 1   
```

**Not yielding anything** is considered failure and causes backtracking. **Yielding multiple times** causes the parser to backtrack to the next yield if the first did not lead to a full instantiation. Given this extension we can rewrite our bit-parser:

```python
bit = AnyOf('01') >> Make(int)
```

### Using monads

The parsing expressions are based on **monads**, which means there is a bind operator (represented by the power operator ```**```) taking a parser as left argument and a lambda expression as right argument. The lambda consumes each parsed value of the parser and returns a new parser depending on the value. There is also the ```Return(x)``` parser which yields just ```x```, and the ```zero``` parser which yields nothing.

With those operations we can easily write the any-of-parser as:

```python
def any_of(choices):
    return element ** (lambda r: Return(r) if r in choices else zero)
```

If you have a look at ```expressions.py``` you will notice that many basic combinators and recursors are implemented this way.

### Unification and the >> operator

The semantics of modifiers attached via the ```>>``` operator can be explained using the concept of unification. The left term is made similar to the right term and each possible instantiation which could be unified is yielded back.

If a **variable** gets unified, it first accepts every term and stores it. Whenever the same variable is used again, it only unifies with terms which in turn unify with the value stored in the variable.

```python
# this will parse 'aa' and leave the last match in x,
# because 'a' unifies with 'a'
x = Variable()
p = (item('a') >> x) + (item('a') >> x)   

# this will never parse
x = Variable()
p = (item('a') >> x) + (item('b') >> x)  
```

```Make``` produces a unified result by invoking the given factory method. 

It is possible to add unifying extensions to the framework, for example a unifier which selects any of two variables. This can be achieved by overriding ```unify```to yield back the unification result of both arguments.

```python
class Select(Unifiable):
    def __init__(self, one, another):
        self.one = one
        self.another = another

    def unify(self, value):
        for result in self.one.unify(value):
            yield result
        for result in self.another.unify(value):
            yield result
```

With this expression it is now possible to write a grammar which matches any triples of letters 'a', 'b' and 'c' as long as the last element matches either the first or the second:

```python
x = Variable()
y = Variable()
abc = item('a') | item('b') | item('c')

# Store first match in x, second match in y,
# then only accept x or y again:
p = (abc >> x) + (abc >> y) + (abc >> Select(x, y))

# this will work (also with 'aaa', 'aba', 'abb', ...)
for r, i in p('aca', 0):
	print x, y
 
# this won't work (also not with 'abc') 
for r, i in p('aab', 0):
	print x, y
```

The current implementation is not progressed very far, so unification is limited. It is not possible to recursively unify sequences containing items and variables due to some simplification.

# How about monads?

The foundation of these parser expressions is a so called ***monad with addition***. A monad in an object-oriented context can be seen as a wrapper around some (hidden) data which supports two operations: ```return(x)``` just puts the wrapper around x. The bind operation ```m.bind(lambda x: new_wrapper)``` exposes every data item inside ```m``` to the bound function and re-assembles the wrappers given by that function.

In case of **lists**, the **return** operation just maps ```x``` to ```[x]``` while the **bind** operation is also known as *flat-map*: it puts every element of the list into a function which results in a new list for every item. These mapped lists are then concatenated to form a single flattened list again. 

In a **parser** world, we want a parser to represent a *"list of possible parse results"* at the given input (and position). These lists should be lazy, so instead of assembling and concatenating lists we use **Python generators** and just ```yield``` each parse result. Concatenation is achieved by successively yielding from two generators. The **return** operation would then just create a parser which consumes no input and yields the (single) given result. The **bind** operation ```p.bind(func)``` should put each result of a sub-parser into ```func``` and continue parsing with all the parsers resulting from ```func```. The result of the **bind** operation is encapsulated in a parser itself to *stay in the monad*.

Given such a definition of **bind** and **return** we can start to combine parsers in the form of:

```python
def combine(p, q, ...):
    return p.bind(lambda result1:
                  q.bind(lambda result2:
                  ...
                         Return(computation_with_results)))
                  
# one example: a parser which parses one element and only continues if
# the element satisfies a given predicate. 
# (zero is the parser which always fails.)

def when(predicate):
    return element.bind(lambda r: Return(r) if predicate(r) else zero)
```

It should be obvious now why **return** is called **return** in the context of monads: It consumes the terminal value of some nested **bind** operations and wraps it back in the monad, so it can be bound again. Also ```p.bind(Return)``` does the same as ```p```, it just yields all results of ```p```. ```Return(a).bind(f)``` does the same as ```f(a)```, because it just puts its wrapped value ```a``` into f.

In this implementation, ```bind``` is replaced by the ```**``` operator for convenience. This operator is also the only operator in Python which associates to the right: ```a ** b ** c == a ** (b ** c)```, which is necessary for monads. 

For a more mathematical definition, see the documentation of ```expressions.py``` and look at the implementations of ```chain, when, item, many``` and ```some```, which use this concept.

```python
"""
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

    Zero(), also Expression.zero
        being the unit element of addition/branching.
        
        Laws:
        p | Zero() == p                         # right unit property
        Zero() | p == p                         # left unit property

"""
```

