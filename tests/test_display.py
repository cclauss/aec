import datetime

from dateutil.tz import tzutc

from tools.display import as_table, pretty


def test_as_table():
    assert as_table([{'a': 1, 'b': 2}, {'b': 4, 'a': 3}], ['a', 'b']) == [['a', 'b'], ['1', '2'], ['3', '4']]


def test_as_table_infer_keys():
    assert as_table([{'a': 1, 'b': 2}, {'b': 4, 'a': 3}]) == [['a', 'b'], ['1', '2'], ['3', '4']]


def test_as_table_with_datetime():
    assert as_table([{'a': 1, 'b': datetime.datetime(2019, 8, 19, 6, 3, 6, tzinfo=tzutc())}], ['a', 'b']) == [
        ['a', 'b'], ['1', '2019-08-19 06:03:06+00:00']]


def test_as_table_with_none():
    assert as_table([{'a': 1, 'b': None}]) == [['a', 'b'], ['1', None], ['a', 'b']]


def test_pretty():
    table = [['a', 'b', 'c'], ['aaaaaaaaaa', 'b', 'c'], ['a', 'bbbbbbbbbb', 'c']]
    expected = (f"a           b           c  \n"
                f"aaaaaaaaaa  b           c  \n"
                f"a           bbbbbbbbbb  c  ")
    actual = pretty(table)
    assert actual == expected


def test_pretty_with_none():
    table = [['a', 'b', 'c'], [None, 'e', 'f']]
    expected = (f"a  b  c  \n"
                f"   e  f  ")
    actual = pretty(table)
    assert actual == expected