"""wx event types shared by the pyOBD UI and background worker."""

import wx


EVT_RESULT_ID = 1000
EVT_DTC_ID = 1001
EVT_STATUS_ID = 1002
EVT_TESTS_ID = 1003
EVT_GRAPH_ID = 1035
EVT_GRAPH_VALUE_ID = 1036
EVT_CLOSE_ID = 1037
EVT_INSERT_FREEZEFRAME_ROW_ID = 1042
EVT_FREEZEFRAME_RESULT_ID = 1043
EVT_DASHBOARD_VALUES_ID = 1107


def EVT_RESULT(window, handler, event_id):
    window.Connect(-1, -1, event_id, handler)


class DataEvent(wx.PyEvent):
    event_type = None

    def __init__(self, data):
        super().__init__()
        self.SetEventType(self.event_type)
        self.data = data


def _event_class(name, event_type):
    return type(name, (DataEvent,), {"event_type": event_type})


ResultEvent = _event_class("ResultEvent", EVT_RESULT_ID)
FreezeframeResultEvent = _event_class("FreezeframeResultEvent", EVT_FREEZEFRAME_RESULT_ID)
InsertFreezeframeRowEvent = _event_class("InsertFreezeframeRowEvent", EVT_INSERT_FREEZEFRAME_ROW_ID)
GraphValueEvent = _event_class("GraphValueEvent", EVT_GRAPH_VALUE_ID)
GraphEvent = _event_class("GraphEvent", EVT_GRAPH_ID)
DTCEvent = _event_class("DTCEvent", EVT_DTC_ID)
StatusEvent = _event_class("StatusEvent", EVT_STATUS_ID)
CloseEvent = _event_class("CloseEvent", EVT_CLOSE_ID)
TestEvent = _event_class("TestEvent", EVT_TESTS_ID)
DashboardValuesEvent = _event_class("DashboardValuesEvent", EVT_DASHBOARD_VALUES_ID)

