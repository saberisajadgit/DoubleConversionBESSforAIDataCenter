import pytest

from double_conversion_bess.profiles import read_profile


def test_per_unit_profile(tmp_path):
    path = tmp_path / "load.csv"
    path.write_text("Time_s,Load_pu\n0,0.8\n1,1\n")
    _, power = read_profile(path, base_power_w=5.16e6)
    assert power.tolist() == pytest.approx([4.128e6, 5.16e6])


def test_per_unit_requires_base(tmp_path):
    path = tmp_path / "load.csv"
    path.write_text("Time_s,Load_pu\n0,0.8\n1,1\n")
    with pytest.raises(ValueError, match="power base"):
        read_profile(path)


def test_valid_profile(tmp_path):
    path = tmp_path / "load.csv"
    path.write_text("time_s,power_w\n0,1000000\n1,2000000\n")
    time, power = read_profile(path)
    assert time.tolist() == [0, 1]
    assert power.tolist() == [1000000, 2000000]


@pytest.mark.parametrize("rows", [
    "0,1\n0,2\n", "1,1\n0,2\n", "0,1\n1,-2\n", "0,1\n1,nan\n", "0,1\n",
])
def test_invalid_profile(tmp_path, rows):
    path = tmp_path / "load.csv"
    path.write_text("time_s,power_w\n" + rows)
    with pytest.raises(ValueError):
        read_profile(path)
