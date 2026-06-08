from safety import validate_read_only_query


def test_select_query_is_allowed():
    result = validate_read_only_query("SELECT * FROM students LIMIT 5")

    assert result.is_safe


def test_drop_query_is_blocked():
    result = validate_read_only_query("DROP TABLE students")

    assert not result.is_safe
    assert result.message == "Unsafe SQL operation detected."


def test_semicolon_chaining_is_blocked():
    result = validate_read_only_query("SELECT * FROM students; SELECT * FROM fees")

    assert not result.is_safe


def test_insert_keyword_is_blocked_even_in_cte_position():
    result = validate_read_only_query("INSERT INTO students (name) VALUES ('Bad')")

    assert not result.is_safe
