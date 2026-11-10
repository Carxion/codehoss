from dojo_checks import assert_image, docker


def test_image_works():
    assert_image("words:1")
    assert docker("run", "--rm", "words:1") == "9 unique words"
