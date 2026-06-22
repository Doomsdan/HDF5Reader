from gui_stats import aggregate_request_stats, filter_request_rows


def test_aggregate_request_stats_counts_parameters_and_customers():
    rows = [
        ("Alice", "Ta_2m,rh_2m"),
        ("Bob", "Ta_2m"),
        ("Alice", " Ta_2m, ,G "),
    ]

    parameter_usage, parameter_customers, customer_requests = (
        aggregate_request_stats(rows)
    )

    assert parameter_usage == [
        ("Ta_2m", 3),
        ("G", 1),
        ("rh_2m", 1),
    ]
    assert parameter_customers == [
        ("Ta_2m", "Alice", 2),
        ("G", "Alice", 1),
        ("rh_2m", "Alice", 1),
        ("Ta_2m", "Bob", 1),
    ]
    assert customer_requests == [("Alice", 2), ("Bob", 1)]


def test_aggregate_request_stats_counts_requests_without_parameters():
    parameter_usage, parameter_customers, customer_requests = (
        aggregate_request_stats([("Alice", None), ("Alice", "")])
    )

    assert parameter_usage == []
    assert parameter_customers == []
    assert customer_requests == [("Alice", 2)]


def test_filter_request_rows_supports_multiple_customers_and_parameters():
    rows = [
        ("Alice", "Ta_2m,rh_2m"),
        ("Bob", "Ta_2m,G"),
        ("Charlie", "rh_2m"),
    ]

    assert filter_request_rows(
        rows,
        customers={"Alice", "Bob"},
        parameters={"rh_2m", "G"},
    ) == [("Alice", "rh_2m"), ("Bob", "G")]
