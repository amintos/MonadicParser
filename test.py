from peg import *
import unittest

class ParseTest(unittest.TestCase):

    def assertParse(self, parser, value, expected_result, position):
        for result, pos in parser(value, 0):
            if result == expected_result:
                if pos == position:
                    pass
                else:
                    self.fail("Parser stopped at %s instead of %s" % (pos, position))
            else:
                self.fail("Parser yielded %s instead of %s" % (result, expected_result))
            break

    def assertFail(self, parser, value):
        for result, pos in parser(value, 0):
            self.fail("Parser is expected to fail")


class ElementTest(ParseTest):

    def test_element(self):
        self.assertParse(element, [42], 42, 1)

    def test_no_element(self):
        self.assertFail(element, [])


class ReturnTest(ParseTest):

    def test_return(self):
        self.assertParse(Return(42), [], 42, 0)


class MonadTest(ParseTest):

    def test_right_unit(self):
        self.assertParse(Return(42) ** Return, [], 42, 0)

    def test_first_monad_law(self):
        self.assertParse(Return(42) ** (lambda x: Return(x / 2)), [], 21, 0)

    def test_second_monad_law_1(self):
        self.assertParse(
            element ** (lambda a:  Return(a / 2) ** (lambda b: Return(b * 3))), [42],
            63, 1
        )

    def test_second_monad_law_2(self):
        self.assertParse(
            (element ** (lambda a: Return(a / 2))) ** (lambda b: Return(b * 3)), [42],
            63, 1
        )


class ZeroTest(ParseTest):

    def test_zero(self):
        self.assertFail(zero, [42])


class ItemTest(ParseTest):

    def test_item(self):
        self.assertParse(
            item('a'), 'a',
            'a', 1)

    def test_item_fail(self):
        self.assertFail(item('a'), 'b')

    def test_item_numeric(self):
        self.assertParse(
            item(42), [42],
            42, 1)


class ChainTest(ParseTest):
    #
    #   The current behaviour of parsing a chain is returning the sum
    #   if '+' is implemented and the last element otherwise.
    #
    def test_chain(self):
        self.assertParse(
            item('a') + item('b'), 'ab',
            'ab', 2)

    def test_chain_too_short(self):
        self.assertFail(item('a') + item('b'), 'a')

    def test_chain_no_match(self):
        self.assertFail(item('a') + item('b'), 'bb')



class BranchTest(ParseTest):

    def test_branch_1(self):
        self.assertParse(
            item('a') | item('b'), 'a',
            'a', 1
        )

    def test_branch_2(self):
        self.assertParse(
            item('a') | item('b'), 'b',
            'b', 1
        )

    def test_branch_fail(self):
        self.assertFail(item('a') | item('b'), 'c')


class BothTest(ParseTest):

    def test_both(self):
        self.assertParse(
            item(1) & item(1), [1],
            1, 1
        )

    def test_both_fail(self):
        self.assertParse(
            item(1) & item(0), [1],
            1, 1
        )


class RecurseTest(ParseTest):

    def test_inside(self):
        self.assertParse(
            element [ element + element ], [['a', 'b']],
            'ab', 1
        )


class CutTest(ParseTest):

    def test_cut(self):
        p = -(Return(21) | Return(42))
        count = 0
        for result, pos in p([], 0):
            count += 1
        self.assertEqual(1, count)

    def test_no_cut(self):
        p = Return(21) | Return(42)
        count = 0
        for result, pos in p([], 0):
            count += 1
        self.assertEqual(2, count)


class WhenTest(ParseTest):

    def test_even(self):
        self.assertParse(
            when(lambda x: x % 2 == 0), [42],
            42, 1)

    def test_not_even(self):
        self.assertFail(
            when(lambda x: x % 2 == 0), [21])


class SomeManyTest(ParseTest):

    def test_some(self):
        self.assertParse(
            some(item('a') | item('b')), 'ab',
            ['a', 'b'], 2
        )

    def test_many(self):
        self.assertParse(
            many(item('a') | item('b')), 'ab',
            ['a', 'b'], 2
        )

    def test_some_empty(self):
        self.assertFail(
            some(item('a') | item('b')), [])


class SetTest(ParseTest):

    def test_in_set(self):
        self.assertParse(
            Set(range(10)), [9],
            9, 1
        )

    def test_set_union(self):
        self.assertParse(
            many(Set([1]) | Set([2])), [1, 2, 1],
            [1, 2, 1], 3
        )

    def test_set_intersect_1(self):
        self.assertFail(
            Set([1,2,3]) & Set([2,3,4]), [1]
        )

    def test_set_intersect_2(self):
        self.assertParse(
            Set([1,2,3]) & Set([2,3,4]), [2],
            2, 1
        )


if __name__ == '__main__':
    unittest.main()
