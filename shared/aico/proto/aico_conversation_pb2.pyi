import datetime

from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ConversationMessage(_message.Message):
    __slots__ = ("timestamp", "source", "message_id", "user_id", "message", "analysis")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ANALYSIS_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    source: str
    message_id: str
    user_id: str
    message: Message
    analysis: MessageAnalysis
    def __init__(self, timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source: _Optional[str] = ..., message_id: _Optional[str] = ..., user_id: _Optional[str] = ..., message: _Optional[_Union[Message, _Mapping]] = ..., analysis: _Optional[_Union[MessageAnalysis, _Mapping]] = ...) -> None: ...

class Message(_message.Message):
    __slots__ = ("text", "type", "conversation_id", "turn_number")
    class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[Message.MessageType]
        USER_INPUT: _ClassVar[Message.MessageType]
        SYSTEM_RESPONSE: _ClassVar[Message.MessageType]
        SYSTEM_NOTIFICATION: _ClassVar[Message.MessageType]
        THINKING_ALOUD: _ClassVar[Message.MessageType]
        INTERNAL_REFLECTION: _ClassVar[Message.MessageType]
        AICO_INITIATED: _ClassVar[Message.MessageType]
    UNKNOWN: Message.MessageType
    USER_INPUT: Message.MessageType
    SYSTEM_RESPONSE: Message.MessageType
    SYSTEM_NOTIFICATION: Message.MessageType
    THINKING_ALOUD: Message.MessageType
    INTERNAL_REFLECTION: Message.MessageType
    AICO_INITIATED: Message.MessageType
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    TURN_NUMBER_FIELD_NUMBER: _ClassVar[int]
    text: str
    type: Message.MessageType
    conversation_id: str
    turn_number: int
    def __init__(self, text: _Optional[str] = ..., type: _Optional[_Union[Message.MessageType, str]] = ..., conversation_id: _Optional[str] = ..., turn_number: _Optional[int] = ...) -> None: ...

class MessageAnalysis(_message.Message):
    __slots__ = ("intent", "urgency", "requires_response")
    class Urgency(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[MessageAnalysis.Urgency]
        LOW: _ClassVar[MessageAnalysis.Urgency]
        MEDIUM: _ClassVar[MessageAnalysis.Urgency]
        HIGH: _ClassVar[MessageAnalysis.Urgency]
        CRITICAL: _ClassVar[MessageAnalysis.Urgency]
    UNKNOWN: MessageAnalysis.Urgency
    LOW: MessageAnalysis.Urgency
    MEDIUM: MessageAnalysis.Urgency
    HIGH: MessageAnalysis.Urgency
    CRITICAL: MessageAnalysis.Urgency
    INTENT_FIELD_NUMBER: _ClassVar[int]
    URGENCY_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    intent: str
    urgency: MessageAnalysis.Urgency
    requires_response: bool
    def __init__(self, intent: _Optional[str] = ..., urgency: _Optional[_Union[MessageAnalysis.Urgency, str]] = ..., requires_response: bool = ...) -> None: ...

class ConversationContext(_message.Message):
    __slots__ = ("timestamp", "source", "context", "recent_history")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    RECENT_HISTORY_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    source: str
    context: Context
    recent_history: RecentHistory
    def __init__(self, timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source: _Optional[str] = ..., context: _Optional[_Union[Context, _Mapping]] = ..., recent_history: _Optional[_Union[RecentHistory, _Mapping]] = ...) -> None: ...

class Context(_message.Message):
    __slots__ = ("current_topic", "conversation_phase", "session_duration_minutes", "relationship_phase", "time_context", "crisis_indicators")
    CURRENT_TOPIC_FIELD_NUMBER: _ClassVar[int]
    CONVERSATION_PHASE_FIELD_NUMBER: _ClassVar[int]
    SESSION_DURATION_MINUTES_FIELD_NUMBER: _ClassVar[int]
    RELATIONSHIP_PHASE_FIELD_NUMBER: _ClassVar[int]
    TIME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    CRISIS_INDICATORS_FIELD_NUMBER: _ClassVar[int]
    current_topic: str
    conversation_phase: str
    session_duration_minutes: int
    relationship_phase: str
    time_context: str
    crisis_indicators: bool
    def __init__(self, current_topic: _Optional[str] = ..., conversation_phase: _Optional[str] = ..., session_duration_minutes: _Optional[int] = ..., relationship_phase: _Optional[str] = ..., time_context: _Optional[str] = ..., crisis_indicators: bool = ...) -> None: ...

class RecentHistory(_message.Message):
    __slots__ = ("last_topics", "emotional_trajectory")
    LAST_TOPICS_FIELD_NUMBER: _ClassVar[int]
    EMOTIONAL_TRAJECTORY_FIELD_NUMBER: _ClassVar[int]
    last_topics: _containers.RepeatedScalarFieldContainer[str]
    emotional_trajectory: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, last_topics: _Optional[_Iterable[str]] = ..., emotional_trajectory: _Optional[_Iterable[str]] = ...) -> None: ...

class ResponseRequest(_message.Message):
    __slots__ = ("timestamp", "source", "thread_id", "input_message_id", "parameters")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    THREAD_ID_FIELD_NUMBER: _ClassVar[int]
    INPUT_MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    source: str
    thread_id: str
    input_message_id: str
    parameters: ResponseParameters
    def __init__(self, timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source: _Optional[str] = ..., thread_id: _Optional[str] = ..., input_message_id: _Optional[str] = ..., parameters: _Optional[_Union[ResponseParameters, _Mapping]] = ...) -> None: ...

class ResponseParameters(_message.Message):
    __slots__ = ("emotional_alignment", "response_style", "include_topics", "avoid_topics", "max_length", "creativity")
    EMOTIONAL_ALIGNMENT_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_STYLE_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_TOPICS_FIELD_NUMBER: _ClassVar[int]
    AVOID_TOPICS_FIELD_NUMBER: _ClassVar[int]
    MAX_LENGTH_FIELD_NUMBER: _ClassVar[int]
    CREATIVITY_FIELD_NUMBER: _ClassVar[int]
    emotional_alignment: float
    response_style: str
    include_topics: _containers.RepeatedScalarFieldContainer[str]
    avoid_topics: _containers.RepeatedScalarFieldContainer[str]
    max_length: int
    creativity: float
    def __init__(self, emotional_alignment: _Optional[float] = ..., response_style: _Optional[str] = ..., include_topics: _Optional[_Iterable[str]] = ..., avoid_topics: _Optional[_Iterable[str]] = ..., max_length: _Optional[int] = ..., creativity: _Optional[float] = ...) -> None: ...

class StreamingResponse(_message.Message):
    __slots__ = ("request_id", "content", "accumulated_content", "done", "timestamp", "content_type")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ACCUMULATED_CONTENT_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    content: str
    accumulated_content: str
    done: bool
    timestamp: int
    content_type: str
    def __init__(self, request_id: _Optional[str] = ..., content: _Optional[str] = ..., accumulated_content: _Optional[str] = ..., done: bool = ..., timestamp: _Optional[int] = ..., content_type: _Optional[str] = ...) -> None: ...
