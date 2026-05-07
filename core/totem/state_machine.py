from __future__ import annotations
from enum import Enum


class State(str, Enum):
    IDLE = "idle"
    PRESENCE_DETECTED = "presence_detected"
    SESSION_STARTED = "session_started"
    GREETING = "greeting"
    INTERACTING = "interacting"
    RECOMMENDING = "recommending"
    FINISHED = "finished"
    TIMEOUT = "timeout"


class Event(str, Enum):
    PRESENCE_DETECTED = "presence_detected"
    SESSION_STARTED = "session_started"
    GREETING_DONE = "greeting_done"
    USER_MESSAGE = "user_message"
    ANSWER_READY = "answer_ready"
    SESSION_END = "session_end"
    TIMEOUT = "timeout"


TRANSITIONS = {
    (State.IDLE, Event.PRESENCE_DETECTED): State.PRESENCE_DETECTED,
    (State.PRESENCE_DETECTED, Event.SESSION_STARTED): State.SESSION_STARTED,
    (State.SESSION_STARTED, Event.GREETING_DONE): State.GREETING,
    (State.GREETING, Event.USER_MESSAGE): State.INTERACTING,
    (State.INTERACTING, Event.ANSWER_READY): State.RECOMMENDING,
    (State.RECOMMENDING, Event.USER_MESSAGE): State.INTERACTING,
    (State.RECOMMENDING, Event.SESSION_END): State.FINISHED,
    (State.INTERACTING, Event.TIMEOUT): State.TIMEOUT,
}
