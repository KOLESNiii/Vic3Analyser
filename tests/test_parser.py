from vic3analyser.ingest.parser import as_list, coerce_scalar, parse


def test_simple_assignments():
    d = parse('a = 1\nb = 2.5\nc = "hello world"\nd = yes\ne = no')
    assert d == {"a": 1, "b": 2.5, "c": "hello world", "d": True, "e": False}


def test_dates_stay_strings():
    d = parse("start = 1836.1.1")
    assert d["start"] == "1836.1.1"


def test_negative_and_scientific_like():
    d = parse("x = -3\ny = -2.75")
    assert d["x"] == -3
    assert d["y"] == -2.75


def test_nested_map():
    d = parse(
        """
        building = {
            type = "building_steel_mills"
            level = 4
            cash_reserves = 1200.5
        }
        """
    )
    assert d["building"]["type"] == "building_steel_mills"
    assert d["building"]["level"] == 4
    assert d["building"]["cash_reserves"] == 1200.5


def test_scalar_array():
    d = parse("nums = { 1 2 3 4 }")
    assert d["nums"] == [1, 2, 3, 4]


def test_array_of_blocks():
    d = parse(
        """
        owned = {
            { x = 1 }
            { x = 2 }
        }
        """
    )
    assert d["owned"] == [{"x": 1}, {"x": 2}]


def test_duplicate_keys_collapse_to_list():
    d = parse(
        """
        building = { id = 1 }
        building = { id = 2 }
        building = { id = 3 }
        """
    )
    assert isinstance(d["building"], list)
    assert [b["id"] for b in d["building"]] == [1, 2, 3]


def test_as_list_helper():
    single = parse("building = { id = 7 }")
    assert len(as_list(single["building"])) == 1
    assert as_list(None) == []


def test_comments_ignored():
    d = parse("# a comment\na = 1 # trailing\nb = 2")
    assert d == {"a": 1, "b": 2}


def test_empty_block():
    d = parse("x = {}")
    assert d["x"] == {}


def test_comparison_operators_in_triggers():
    # game-def trigger style; we don't evaluate, just shouldn't crash
    d = parse(
        """
        trigger = {
            gdp > 1000
            literacy_rate >= 0.5
        }
        """
    )
    assert isinstance(d["trigger"], dict)
    assert d["trigger"]["gdp"] == 1000
    assert d["trigger"]["literacy_rate"] == 0.5


def test_production_method_like():
    d = parse(
        """
        production_method_steel_1 = {
            building_modifiers = {
                workforce_scaled = {
                    goods_input_iron_add = 30
                    goods_output_steel_add = 25
                }
            }
        }
        """
    )
    pm = d["production_method_steel_1"]["building_modifiers"]["workforce_scaled"]
    assert pm["goods_input_iron_add"] == 30
    assert pm["goods_output_steel_add"] == 25


def test_coerce_scalar():
    assert coerce_scalar("yes") is True
    assert coerce_scalar("42") == 42
    assert coerce_scalar('"q"') == "q"
    assert coerce_scalar("1836.2.1") == "1836.2.1"
