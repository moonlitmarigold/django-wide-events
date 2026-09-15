from django_wide_events.event_blocks import EventBlock, TimerEventBlock
from django.http import HttpResponse
import time

class TestBlock(TimerEventBlock):

    namespace = "TestBlock"

    @classmethod
    def start(cls):
        return cls.from_kwargs(test=True, is_flase=False)

class TestBlock2(EventBlock):

    namespace = "OtherBlock"
    drop_none = True
    use_namespace_on_write = False

    @classmethod
    def start(cls):
        return cls.from_kwargs(other=True, non_value=None)

class TestParent(EventBlock):

    namespace = "test_block"
    parent = TestBlock

    @classmethod
    def start(cls):
        return cls.from_kwargs(other=True)

    def add_parent(self):
        self.set(parent=self.parent, path=self.path)

def test_event_block(request):
    block = TestBlock.start()

    TestBlock.current().set(is_flase=True)

    with block.timer("sleep"):
        time.sleep(0.01)

    with TestBlock.current().timer("sleep2"):
        time.sleep(0.01)

    TestBlock2.start()

    TestParent.start().add_parent()

    return HttpResponse("ok")
