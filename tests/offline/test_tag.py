from pycomm3 import Tag


def test_tag_truthiness():
    assert Tag('tag', 100, 'DINT')
    assert not Tag('tag', None, None, None)
    assert not Tag('tag', None, None, 'Error')
    assert not Tag('tag', None, 'DINT', 'Error')
    assert not Tag('tag', 100, 'DINT', 'Error')


def test_tag_repr():
    _tag_repr = "Tag(tag='tag_name', value='string value', type='STRING', error=None)"
    assert _tag_repr == repr(Tag('tag_name', 'string value', 'STRING'))

    _tag = Tag('tag', 100, 'DINT')
    assert eval(repr(_tag)) == _tag
