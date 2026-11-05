"""wxPython adapter for the framework-neutral event sink."""

import wx

from app_events import (
    CloseEvent,
    DashboardValuesEvent,
    DTCEvent,
    FreezeframeResultEvent,
    GraphEvent,
    GraphValueEvent,
    InsertFreezeframeRowEvent,
    ResultEvent,
    StatusEvent,
    TestEvent,
)
from debugEvent import DebugEvent
from event_sink import AppEvent, EventChannel


class WxEventSink:
    _EVENT_TYPES = {
        EventChannel.RESULT: ResultEvent,
        EventChannel.DTC: DTCEvent,
        EventChannel.STATUS: StatusEvent,
        EventChannel.TEST: TestEvent,
        EventChannel.GRAPH: GraphEvent,
        EventChannel.GRAPH_VALUE: GraphValueEvent,
        EventChannel.CLOSE: CloseEvent,
        EventChannel.INSERT_FREEZE_FRAME_ROW: InsertFreezeframeRowEvent,
        EventChannel.FREEZE_FRAME_RESULT: FreezeframeResultEvent,
        EventChannel.DASHBOARD_VALUES: DashboardValuesEvent,
        EventChannel.DEBUG: DebugEvent,
    }

    def __init__(self, window):
        self._window = window

    def publish(self, event: AppEvent) -> None:
        event_type = self._EVENT_TYPES.get(event.channel)
        if event_type is not None:
            wx.PostEvent(self._window, event_type(event.payload))
