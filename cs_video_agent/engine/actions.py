"""动作注册表合并入口。"""

from cs_video_agent.engine.actions_net import HANDLERS as _NET, SPECS as _NET_SPECS
from cs_video_agent.engine.actions_os import HANDLERS as _OS, SPECS as _OS_SPECS
from cs_video_agent.engine.actions_pay import HANDLERS as _PAY, SPECS as _PAY_SPECS
from cs_video_agent.engine.actions_text import HANDLERS as _TEXT, SPECS as _TEXT_SPECS

ACTION_HANDLERS = {**_TEXT, **_NET, **_OS, **_PAY}
ACTION_SPECS = {**_TEXT_SPECS, **_NET_SPECS, **_OS_SPECS, **_PAY_SPECS}


def get_handler(name):
    try:
        return ACTION_HANDLERS[name]
    except KeyError:
        raise KeyError(
            f"unknown action {name!r}; known actions: {sorted(ACTION_HANDLERS)}"
        ) from None
