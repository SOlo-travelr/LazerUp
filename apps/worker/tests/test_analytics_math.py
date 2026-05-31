"""Unit tests for the deterministic scoring math (no DB/network)."""

from analytics.mathx import (
    acceleration,
    clamp,
    log_damp,
    mean,
    minmax,
    sigmoid,
    stdev,
    zscores,
)


def test_acceleration_positive_growth():
    assert acceleration(20, 10) > 0


def test_acceleration_handles_zero_prior():
    # eps prevents division by zero and tames tiny bases.
    assert acceleration(5, 0, eps=1.0) == 5.0


def test_log_damp_is_signed_and_monotonic():
    assert log_damp(0) == 0
    assert log_damp(3) > 0
    assert log_damp(-3) < 0
    assert log_damp(10) > log_damp(3)


def test_sigmoid_range_and_midpoint():
    assert sigmoid(0) == 0.5
    assert 0 < sigmoid(-50) < 0.5
    assert 0.5 < sigmoid(50) < 1


def test_zscores_zero_when_no_spread():
    assert zscores([4, 4, 4]) == [0.0, 0.0, 0.0]


def test_zscores_centered():
    z = zscores([1, 2, 3])
    assert abs(mean(z)) < 1e-9
    assert z[0] < 0 < z[2]


def test_minmax_scales_to_unit_interval():
    assert minmax([0, 5, 10]) == [0.0, 0.5, 1.0]
    assert minmax([7, 7]) == [0.5, 0.5]


def test_stdev_and_clamp():
    assert stdev([2, 4, 4, 4, 5, 5, 7, 9]) == 2.0
    assert clamp(1.5) == 1.0
    assert clamp(-0.5) == 0.0
    assert clamp(0.3) == 0.3
