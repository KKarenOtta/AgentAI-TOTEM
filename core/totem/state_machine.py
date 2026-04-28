from enum import Enum


class State(str, Enum):
    IDLE = "idle"
    PRESENCE = "presence"
    GREETING = "greeting"
    INTERACTION = "interaction"
    RECOMMENDATION = "recommendation"
    HANDOFF = "handoff"
    COMPLETED = "completed"


class Event(str, Enum):
    PRESENCE_DETECTED = "presence_detected"
    GREETING_DONE = "greeting_done"
    USER_MESSAGE = "user_message"
    ANSWER_READY = "answer_ready"
    RECOMMEND = "recommend"
    HANDOFF = "handoff"
    END = "end"


TRANSITIONS = {
    (State.IDLE, Event.PRESENCE_DETECTED): State.PRESENCE,
    (State.PRESENCE, Event.GREETING_DONE): State.GREETING,
    (State.GREETING, Event.USER_MESSAGE): State.INTERACTION,
    (State.INTERACTION, Event.ANSWER_READY): State.RECOMMENDATION,
    (State.RECOMMENDATION, Event.HANDOFF): State.HANDOFF,
    (State.HANDOFF, Event.END): State.COMPLETED,
}

