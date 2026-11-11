import pytest


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Hello, World!", "hello-world"),
        ("  Python   3.13 is out ", "python-3-13-is-out"),
        ("C++ & C#", "c-c"),
        ("!!!", ""),
    ],
)
def test_slugify(title, slug):
    from main import slugify

    assert slugify(title) == slug, f"slugify({title!r}) gave {slugify(title)!r}, expected {slug!r}"
