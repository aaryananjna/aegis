"""A tick reaches the detector every settings.tick_s seconds, even in silence (CONTRACTS v2.1,
caption section: "A also calls the detector's tick every 1.0 s")."""
import time

import pytest

from aegis_server.config import settings
from helpers import is_type, recv_until

FAST_TICK_S = 0.05


def test_default_tick_is_one_second():
    assert settings.tick_s == 1.0


@pytest.fixture
def fast_tick():
    # Settings is a frozen dataclass and other modules hold a reference to the same object,
    # so change it in place rather than swapping it out, and put it back afterwards.
    original = settings.tick_s
    object.__setattr__(settings, "tick_s", FAST_TICK_S)
    yield FAST_TICK_S
    object.__setattr__(settings, "tick_s", original)


@pytest.mark.xfail(strict=False, reason="not implemented yet")
def test_ticks_reach_the_detector_in_silence(client, new_call, detector_spy, fast_tick):
    new_call()  # nobody connects and nobody speaks
    time.sleep(20 * fast_tick)
    ticks = detector_spy.names("tick")
    assert 10 <= len(ticks) <= 30  # about one per tick_s, with slack for a slow CI box
    times = [args[0] for args in ticks]
    assert times == sorted(times)  # now_s never goes backwards
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert sum(gaps) / len(gaps) == pytest.approx(fast_tick, rel=0.5)


@pytest.mark.xfail(strict=False, reason="not implemented yet")
def test_ticks_stop_after_the_call_ends(client, new_call, detector_spy, fast_tick):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        cap.send_json({"type": "end"})
        recv_until(elder, is_type("call_ended"))
    time.sleep(2 * fast_tick)  # let a tick already in flight land
    count = len(detector_spy.names("tick"))
    time.sleep(10 * fast_tick)
    assert len(detector_spy.names("tick")) == count
