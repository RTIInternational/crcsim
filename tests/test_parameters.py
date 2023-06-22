import pytest

from crcsim.parameters import StepFunction


def test_step_mismatch():
    """
    Passing lists whose lengths don't match should raise an exception.
    """

    with pytest.raises(ValueError):
        StepFunction(x=[1, 2, 3], y=[10, 20])


def test_step_unsorted():
    """
    Passing x values that aren't sorted should raise an exception.
    """

    with pytest.raises(ValueError):
        StepFunction(x=[1, 3, 2], y=[10, 30, 20])


def test_step_reverse_sorted():
    """
    Passing x values that are sorted in decreasing order should raise an
    exception.
    """

    with pytest.raises(ValueError):
        StepFunction(x=[3, 2, 1], y=[30, 20, 10])


def test_step_defined_x():
    """
    Evaluating the step function at a value that is in the defined x values
    should return the corresponding defined y value.
    """

    f = StepFunction(x=[1, 2, 3], y=[10, 20, 30])
    assert f(1) == 10
    assert f(2) == 20
    assert f(3) == 30


def test_step_interpolate():
    """
    Evaluating the step function at a value that falls between a pair of defined
    x values should produce the same result as evaluating it at the smaller of
    the pair.
    """

    f = StepFunction(x=[1, 2, 3], y=[10, 20, 30])
    assert f(1.1) == f(1)
    assert f(2.2) == f(2)


def test_step_extrapolate_low():
    """
    Evaluating the step function at a value that is smaller than the smallest
    defined x value should raise an exception.
    """

    f = StepFunction(x=[1, 2, 3], y=[10, 20, 30])
    with pytest.raises(ValueError):
        f(0)


def test_step_extrapolate_high():
    """
    Evaluating the step function at a value that is larger than the largest
    defined x value should produce the same result as evaluating it at the
    largest defined x value.
    """

    f = StepFunction(x=[1, 2, 3], y=[10, 20, 30])
    assert f(5) == f(3)
