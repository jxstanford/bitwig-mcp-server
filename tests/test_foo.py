from bitwig_mcp_server.foo import foo


def test_foo():
    assert foo("foo") == "foo"
