from peg import *
import unittest

class ItemTest(unittest.TestCase):

    def test_item(self):
        word = 'a'
        expr = Item('a')
        ok = False
        for result, pos in expr.instantiate(word, 0, None):
            self.assertEqual(1, pos)
            self.assertEqual('a', result.unpack())
            ok = True
        self.assertTrue(ok)
        
class ChainTest(unittest.TestCase):

    def test_addition(self):
        word = 'ab'
        expr = Item('a') + Item('b')
        ok = False
        for result, pos in expr.instantiate(word, 0, None):
            a, b = result.unpack()
            self.assertEqual('a', a)
            self.assertEqual('b', b)

if __name__ == '__main__':
    unittest.main()
