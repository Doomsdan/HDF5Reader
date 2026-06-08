from datetime import datetime, timedelta

import numpy as np

import times


def test_scalar_datetime_string_roundtrip():
    timestamp = "01.01.2040 12:30:15"

    parsed = times.str2datetime(timestamp)

    assert parsed == datetime(2040, 1, 1, 12, 30, 15)
    assert times.datetime2str(parsed) == timestamp


def test_unix_datetime_roundtrip_for_array():
    datetimes = np.array([
        datetime(1970, 1, 1, 0, 0, 0),
        datetime(1970, 1, 1, 0, 1, 0),
        datetime(1970, 1, 1, 1, 0, 0),
    ])

    timestamps = times.datetime2unix(datetimes)
    restored = times.unix2datetime(timestamps)

    np.testing.assert_allclose(timestamps, [0.0, 60.0, 3600.0])
    np.testing.assert_array_equal(restored, datetimes)


def test_regularize_interpolates_to_common_time_step():
    datetimes = np.array([
        datetime(2000, 1, 1, 0, 0),
        datetime(2000, 1, 1, 1, 30),
        datetime(2000, 1, 1, 2, 0),
        datetime(2000, 1, 1, 3, 0),
    ])
    values = np.array([0.0, 1.5, 2.0, 3.0])

    regular_values, regular_datetimes = times.regularize(values, datetimes)

    np.testing.assert_allclose(regular_values, [0.0, 1.0, 2.0, 3.0])
    np.testing.assert_array_equal(
        regular_datetimes,
        np.array([
            datetime(2000, 1, 1, 0, 0),
            datetime(2000, 1, 1, 1, 0),
            datetime(2000, 1, 1, 2, 0),
            datetime(2000, 1, 1, 3, 0),
        ]),
    )


def test_hour_distance_wraps_around_midnight():
    result = times.hour_distance(0, np.array([23, 0, 1]))

    np.testing.assert_allclose(result, [1.0, 0.0, 1.0])
