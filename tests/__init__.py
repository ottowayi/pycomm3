from math import isclose


def tag_only(tag):
    """
    simple function to remove the elements token from a tag name

    e.g. tag_only('tag_name{10}') -> 'tag_name'
    """
    if '{' in tag:
        return tag[:tag.find('{')]
    else:
        return tag


class REAL(float):
    """simple subclass of float so that tests can avoid floating point precision issues using =="""

    def __new__(cls, float_string, rel_tol=1e-6):
        return float.__new__(cls, float_string)

    def __init__(self, value, rel_tol=1e-6):
        float.__init__(value)
        self.rel_tol = rel_tol

    def __eq__(self, other):
        return isclose(self, other, rel_tol=self.rel_tol)

    def __repr__(self):
        return f'REAL({float.__repr__(self)}, {self.rel_tol})'
