from i2c_rasp.display import _ping_pong_offset


def test_ping_pong_offset_goes_and_comes_back() -> None:
    seq = [_ping_pong_offset(frame, max_offset=3, step=1) for frame in range(8)]

    assert seq == [0, 1, 2, 3, 2, 1, 0, 1]
