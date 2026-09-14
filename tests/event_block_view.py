from wide_events.event_blocks import EventBlock, TimerEventBlock
from django.http import HttpResponse
import time

class TestBlock(TimerEventBlock):

    namespace = "TestBlock"

    @classmethod
    def start(cls):
        return cls.from_kwargs(test=True, is_flase=False)


def test_event_block(request):
    block = TestBlock.start()

    TestBlock.current().set(is_flase=True)

    with block.timer("sleep"):
        time.sleep(1)

    with TestBlock.current().timer("sleep2"):
        time.sleep(1)

    return HttpResponse("ok")
