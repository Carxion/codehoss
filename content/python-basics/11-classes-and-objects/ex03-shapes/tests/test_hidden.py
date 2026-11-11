import pytest


def test_rectangle_and_circle():
    from main import Circle, Rectangle

    assert Rectangle(2, 4.5).describe() == "rectangle with area 9.00"
    assert Circle(1).describe() == "circle with area 3.14"
    assert round(Circle(2).area(), 4) == 12.5664


def test_family_tree():
    from main import Circle, Rectangle, Shape, Square

    assert issubclass(Rectangle, Shape) and issubclass(Circle, Shape), (
        "Rectangle and Circle should inherit from Shape"
    )
    assert issubclass(Square, Rectangle), "Square should inherit from Rectangle"


def test_shape_area_is_left_to_children():
    from main import Shape

    with pytest.raises(NotImplementedError):
        Shape("blob").area()


def test_describe_is_written_once():
    from main import Circle, Rectangle, Shape, Square

    for child in (Rectangle, Circle, Square):
        assert "describe" not in vars(child), (
            f"{child.__name__} has its own describe(); write it once in Shape and inherit it"
        )
    assert "describe" in vars(Shape)
