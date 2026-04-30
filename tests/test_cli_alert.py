from i2c_rasp import cli


class FakeSink:
    def __init__(self):
        self.calls = []

    def show_page(self, page, flash=False):
        self.calls.append((tuple(page), flash))


class FakeBuzzer:
    def __init__(self):
        self.on_count = 0
        self.off_count = 0

    def on(self):
        self.on_count += 1

    def off(self):
        self.off_count += 1


def test_show_page_with_alert_blinks_and_doubles_time(monkeypatch):
    sink = FakeSink()
    buzzer = FakeBuzzer()
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(cli, "sleep", fake_sleep)

    cli._show_page_with_alert(sink, buzzer, ["a"], alert=True, page_seconds=1.0, once=False)

    assert buzzer.on_count == 1
    assert buzzer.off_count == 1
    assert len(sink.calls) >= 4
    assert sink.calls[0][1] is True
    assert any(flash is False for _, flash in sink.calls)
    assert sum(sleeps) == 2.0


def test_show_page_with_alert_once_does_not_sleep():
    sink = FakeSink()
    buzzer = FakeBuzzer()

    cli._show_page_with_alert(sink, buzzer, ["a"], alert=True, page_seconds=1.0, once=True)

    assert sink.calls == [(("a",), True)]
    assert buzzer.on_count == 1
    assert buzzer.off_count == 1
