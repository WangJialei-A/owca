from unittest.mock import patch, call, mock_open
from owca.testing import create_open_mock


def test_create_open_mock_autocreated():
    with patch('builtins.open', create_open_mock({
            '/some/path.txt': 'foo',
            })) as mocks:
        assert open('/some/path.txt').read() == 'foo'
        open('/some/path.txt', 'w').write('bar')
        mocks['/some/path.txt'].assert_has_calls(
            [call().write('bar')])


def test_create_open_mock_manually():
    my_own_mock_open = mock_open(read_data='foo')
    with patch('builtins.open', create_open_mock({
            '/some/path.txt': my_own_mock_open
            })):
        assert open('/some/path.txt').read() == 'foo'
        open('/some/path.txt', 'w').write('bar')
        my_own_mock_open.assert_has_calls(
            [call().write('bar')])
