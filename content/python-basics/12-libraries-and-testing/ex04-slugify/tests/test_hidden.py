import pytest


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("already-a-slug", "already-a-slug"),
        ("ALL CAPS", "all-caps"),
        ("10 Tips -- for -- Beginners", "10-tips-for-beginners"),
        ("", ""),
        ("x", "x"),
    ],
)
def test_more_titles(title, slug):
    from main import slugify

    assert slugify(title) == slug, f"slugify({title!r}) gave {slugify(title)!r}, expected {slug!r}"
