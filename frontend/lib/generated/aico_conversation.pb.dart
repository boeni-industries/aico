// This is a generated file - do not edit.
//
// Generated from aico_conversation.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'aico_conversation.pbenum.dart';
import 'google/protobuf/timestamp.pb.dart' as $0;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'aico_conversation.pbenum.dart';

/// Conversation message
/// Represents a single message in the conversation, including content and analysis.
/// See emotion_sim_msg.md for field semantics and examples.
class ConversationMessage extends $pb.GeneratedMessage {
  factory ConversationMessage({
    $0.Timestamp? timestamp,
    $core.String? source,
    $core.String? messageId,
    $core.String? userId,
    Message? message,
    MessageAnalysis? analysis,
  }) {
    final result = create();
    if (timestamp != null) result.timestamp = timestamp;
    if (source != null) result.source = source;
    if (messageId != null) result.messageId = messageId;
    if (userId != null) result.userId = userId;
    if (message != null) result.message = message;
    if (analysis != null) result.analysis = analysis;
    return result;
  }

  ConversationMessage._();

  factory ConversationMessage.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ConversationMessage.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ConversationMessage',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOM<$0.Timestamp>(1, _omitFieldNames ? '' : 'timestamp',
        subBuilder: $0.Timestamp.create)
    ..aOS(2, _omitFieldNames ? '' : 'source')
    ..aOS(3, _omitFieldNames ? '' : 'messageId')
    ..aOS(4, _omitFieldNames ? '' : 'userId')
    ..aOM<Message>(5, _omitFieldNames ? '' : 'message',
        subBuilder: Message.create)
    ..aOM<MessageAnalysis>(6, _omitFieldNames ? '' : 'analysis',
        subBuilder: MessageAnalysis.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ConversationMessage clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ConversationMessage copyWith(void Function(ConversationMessage) updates) =>
      super.copyWith((message) => updates(message as ConversationMessage))
          as ConversationMessage;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ConversationMessage create() => ConversationMessage._();
  @$core.override
  ConversationMessage createEmptyInstance() => create();
  static $pb.PbList<ConversationMessage> createRepeated() =>
      $pb.PbList<ConversationMessage>();
  @$core.pragma('dart2js:noInline')
  static ConversationMessage getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ConversationMessage>(create);
  static ConversationMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $0.Timestamp get timestamp => $_getN(0);
  @$pb.TagNumber(1)
  set timestamp($0.Timestamp value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasTimestamp() => $_has(0);
  @$pb.TagNumber(1)
  void clearTimestamp() => $_clearField(1);
  @$pb.TagNumber(1)
  $0.Timestamp ensureTimestamp() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get source => $_getSZ(1);
  @$pb.TagNumber(2)
  set source($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSource() => $_has(1);
  @$pb.TagNumber(2)
  void clearSource() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get messageId => $_getSZ(2);
  @$pb.TagNumber(3)
  set messageId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasMessageId() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessageId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get userId => $_getSZ(3);
  @$pb.TagNumber(4)
  set userId($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasUserId() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserId() => $_clearField(4);

  @$pb.TagNumber(5)
  Message get message => $_getN(4);
  @$pb.TagNumber(5)
  set message(Message value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasMessage() => $_has(4);
  @$pb.TagNumber(5)
  void clearMessage() => $_clearField(5);
  @$pb.TagNumber(5)
  Message ensureMessage() => $_ensure(4);

  @$pb.TagNumber(6)
  MessageAnalysis get analysis => $_getN(5);
  @$pb.TagNumber(6)
  set analysis(MessageAnalysis value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasAnalysis() => $_has(5);
  @$pb.TagNumber(6)
  void clearAnalysis() => $_clearField(6);
  @$pb.TagNumber(6)
  MessageAnalysis ensureAnalysis() => $_ensure(5);
}

/// Message content and metadata
/// Contains the actual text, type, conversation information, and turn number for the conversation message.
/// Fields:
/// - text: Actual message content (string)
/// - type: Message type (user_input, system_response, etc.)
/// - conversation_id: Conversation identifier
/// - turn_number: Sequential turn number in conversation
/// See emotion_sim_msg.md for examples.
class Message extends $pb.GeneratedMessage {
  factory Message({
    $core.String? text,
    Message_MessageType? type,
    $core.String? conversationId,
    $core.int? turnNumber,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (type != null) result.type = type;
    if (conversationId != null) result.conversationId = conversationId;
    if (turnNumber != null) result.turnNumber = turnNumber;
    return result;
  }

  Message._();

  factory Message.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Message.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Message',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..aE<Message_MessageType>(2, _omitFieldNames ? '' : 'type',
        enumValues: Message_MessageType.values)
    ..aOS(3, _omitFieldNames ? '' : 'conversationId')
    ..aI(4, _omitFieldNames ? '' : 'turnNumber')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Message clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Message copyWith(void Function(Message) updates) =>
      super.copyWith((message) => updates(message as Message)) as Message;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Message create() => Message._();
  @$core.override
  Message createEmptyInstance() => create();
  static $pb.PbList<Message> createRepeated() => $pb.PbList<Message>();
  @$core.pragma('dart2js:noInline')
  static Message getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Message>(create);
  static Message? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  /// Message type: user_input, system_response, system_notification, thinking_aloud, internal_reflection
  @$pb.TagNumber(2)
  Message_MessageType get type => $_getN(1);
  @$pb.TagNumber(2)
  set type(Message_MessageType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get conversationId => $_getSZ(2);
  @$pb.TagNumber(3)
  set conversationId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasConversationId() => $_has(2);
  @$pb.TagNumber(3)
  void clearConversationId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get turnNumber => $_getIZ(3);
  @$pb.TagNumber(4)
  set turnNumber($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTurnNumber() => $_has(3);
  @$pb.TagNumber(4)
  void clearTurnNumber() => $_clearField(4);
}

/// Analysis of the message
/// Contains detected user intent, urgency, and whether a response is expected.
/// Fields:
/// - intent: Detected user intent (string)
/// - urgency: Message urgency level (low, medium, high, critical)
/// - requires_response: Whether response is expected (boolean)
/// See emotion_sim_msg.md for examples.
class MessageAnalysis extends $pb.GeneratedMessage {
  factory MessageAnalysis({
    $core.String? intent,
    MessageAnalysis_Urgency? urgency,
    $core.bool? requiresResponse,
  }) {
    final result = create();
    if (intent != null) result.intent = intent;
    if (urgency != null) result.urgency = urgency;
    if (requiresResponse != null) result.requiresResponse = requiresResponse;
    return result;
  }

  MessageAnalysis._();

  factory MessageAnalysis.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MessageAnalysis.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MessageAnalysis',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'intent')
    ..aE<MessageAnalysis_Urgency>(2, _omitFieldNames ? '' : 'urgency',
        enumValues: MessageAnalysis_Urgency.values)
    ..aOB(3, _omitFieldNames ? '' : 'requiresResponse')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageAnalysis clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageAnalysis copyWith(void Function(MessageAnalysis) updates) =>
      super.copyWith((message) => updates(message as MessageAnalysis))
          as MessageAnalysis;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MessageAnalysis create() => MessageAnalysis._();
  @$core.override
  MessageAnalysis createEmptyInstance() => create();
  static $pb.PbList<MessageAnalysis> createRepeated() =>
      $pb.PbList<MessageAnalysis>();
  @$core.pragma('dart2js:noInline')
  static MessageAnalysis getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MessageAnalysis>(create);
  static MessageAnalysis? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get intent => $_getSZ(0);
  @$pb.TagNumber(1)
  set intent($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasIntent() => $_has(0);
  @$pb.TagNumber(1)
  void clearIntent() => $_clearField(1);

  @$pb.TagNumber(2)
  MessageAnalysis_Urgency get urgency => $_getN(1);
  @$pb.TagNumber(2)
  set urgency(MessageAnalysis_Urgency value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasUrgency() => $_has(1);
  @$pb.TagNumber(2)
  void clearUrgency() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.bool get requiresResponse => $_getBF(2);
  @$pb.TagNumber(3)
  set requiresResponse($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasRequiresResponse() => $_has(2);
  @$pb.TagNumber(3)
  void clearRequiresResponse() => $_clearField(3);
}

/// Broader conversation context
/// Represents the overall context for the conversation, including current state and recent history.
/// Fields:
/// - timestamp: Timestamp of context snapshot
/// - source: Source module/component
/// - context: Current conversation context
/// - recent_history: Historical context for pattern recognition
/// See emotion_sim_msg.md for examples.
class ConversationContext extends $pb.GeneratedMessage {
  factory ConversationContext({
    $0.Timestamp? timestamp,
    $core.String? source,
    Context? context,
    RecentHistory? recentHistory,
  }) {
    final result = create();
    if (timestamp != null) result.timestamp = timestamp;
    if (source != null) result.source = source;
    if (context != null) result.context = context;
    if (recentHistory != null) result.recentHistory = recentHistory;
    return result;
  }

  ConversationContext._();

  factory ConversationContext.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ConversationContext.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ConversationContext',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOM<$0.Timestamp>(1, _omitFieldNames ? '' : 'timestamp',
        subBuilder: $0.Timestamp.create)
    ..aOS(2, _omitFieldNames ? '' : 'source')
    ..aOM<Context>(3, _omitFieldNames ? '' : 'context',
        subBuilder: Context.create)
    ..aOM<RecentHistory>(4, _omitFieldNames ? '' : 'recentHistory',
        subBuilder: RecentHistory.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ConversationContext clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ConversationContext copyWith(void Function(ConversationContext) updates) =>
      super.copyWith((message) => updates(message as ConversationContext))
          as ConversationContext;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ConversationContext create() => ConversationContext._();
  @$core.override
  ConversationContext createEmptyInstance() => create();
  static $pb.PbList<ConversationContext> createRepeated() =>
      $pb.PbList<ConversationContext>();
  @$core.pragma('dart2js:noInline')
  static ConversationContext getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ConversationContext>(create);
  static ConversationContext? _defaultInstance;

  @$pb.TagNumber(1)
  $0.Timestamp get timestamp => $_getN(0);
  @$pb.TagNumber(1)
  set timestamp($0.Timestamp value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasTimestamp() => $_has(0);
  @$pb.TagNumber(1)
  void clearTimestamp() => $_clearField(1);
  @$pb.TagNumber(1)
  $0.Timestamp ensureTimestamp() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get source => $_getSZ(1);
  @$pb.TagNumber(2)
  set source($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSource() => $_has(1);
  @$pb.TagNumber(2)
  void clearSource() => $_clearField(2);

  @$pb.TagNumber(3)
  Context get context => $_getN(2);
  @$pb.TagNumber(3)
  set context(Context value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasContext() => $_has(2);
  @$pb.TagNumber(3)
  void clearContext() => $_clearField(3);
  @$pb.TagNumber(3)
  Context ensureContext() => $_ensure(2);

  @$pb.TagNumber(4)
  RecentHistory get recentHistory => $_getN(3);
  @$pb.TagNumber(4)
  set recentHistory(RecentHistory value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasRecentHistory() => $_has(3);
  @$pb.TagNumber(4)
  void clearRecentHistory() => $_clearField(4);
  @$pb.TagNumber(4)
  RecentHistory ensureRecentHistory() => $_ensure(3);
}

/// Current conversation context
/// Contains details about the current topic, phase, session duration, relationship phase, time context, and crisis indicators.
/// Fields:
/// - current_topic: Current conversation topic (string)
/// - conversation_phase: Phase of current conversation
/// - session_duration_minutes: Length of current session
/// - relationship_phase: Current relationship development stage
/// - time_context: Temporal/situational context
/// - crisis_indicators: Whether crisis situation detected (boolean)
/// See emotion_sim_msg.md for details.
class Context extends $pb.GeneratedMessage {
  factory Context({
    $core.String? currentTopic,
    $core.String? conversationPhase,
    $core.int? sessionDurationMinutes,
    $core.String? relationshipPhase,
    $core.String? timeContext,
    $core.bool? crisisIndicators,
  }) {
    final result = create();
    if (currentTopic != null) result.currentTopic = currentTopic;
    if (conversationPhase != null) result.conversationPhase = conversationPhase;
    if (sessionDurationMinutes != null)
      result.sessionDurationMinutes = sessionDurationMinutes;
    if (relationshipPhase != null) result.relationshipPhase = relationshipPhase;
    if (timeContext != null) result.timeContext = timeContext;
    if (crisisIndicators != null) result.crisisIndicators = crisisIndicators;
    return result;
  }

  Context._();

  factory Context.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Context.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Context',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'currentTopic')
    ..aOS(2, _omitFieldNames ? '' : 'conversationPhase')
    ..aI(3, _omitFieldNames ? '' : 'sessionDurationMinutes')
    ..aOS(4, _omitFieldNames ? '' : 'relationshipPhase')
    ..aOS(5, _omitFieldNames ? '' : 'timeContext')
    ..aOB(6, _omitFieldNames ? '' : 'crisisIndicators')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Context clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Context copyWith(void Function(Context) updates) =>
      super.copyWith((message) => updates(message as Context)) as Context;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Context create() => Context._();
  @$core.override
  Context createEmptyInstance() => create();
  static $pb.PbList<Context> createRepeated() => $pb.PbList<Context>();
  @$core.pragma('dart2js:noInline')
  static Context getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Context>(create);
  static Context? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get currentTopic => $_getSZ(0);
  @$pb.TagNumber(1)
  set currentTopic($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasCurrentTopic() => $_has(0);
  @$pb.TagNumber(1)
  void clearCurrentTopic() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get conversationPhase => $_getSZ(1);
  @$pb.TagNumber(2)
  set conversationPhase($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasConversationPhase() => $_has(1);
  @$pb.TagNumber(2)
  void clearConversationPhase() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get sessionDurationMinutes => $_getIZ(2);
  @$pb.TagNumber(3)
  set sessionDurationMinutes($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasSessionDurationMinutes() => $_has(2);
  @$pb.TagNumber(3)
  void clearSessionDurationMinutes() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get relationshipPhase => $_getSZ(3);
  @$pb.TagNumber(4)
  set relationshipPhase($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasRelationshipPhase() => $_has(3);
  @$pb.TagNumber(4)
  void clearRelationshipPhase() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get timeContext => $_getSZ(4);
  @$pb.TagNumber(5)
  set timeContext($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasTimeContext() => $_has(4);
  @$pb.TagNumber(5)
  void clearTimeContext() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.bool get crisisIndicators => $_getBF(5);
  @$pb.TagNumber(6)
  set crisisIndicators($core.bool value) => $_setBool(5, value);
  @$pb.TagNumber(6)
  $core.bool hasCrisisIndicators() => $_has(5);
  @$pb.TagNumber(6)
  void clearCrisisIndicators() => $_clearField(6);
}

/// Recent conversation history
/// Contains historical context for pattern recognition, including last topics and emotional trajectory.
/// Fields:
/// - last_topics: Recent conversation topics (string[])
/// - emotional_trajectory: Emotional progression (string[])
/// See emotion_sim_msg.md for details.
class RecentHistory extends $pb.GeneratedMessage {
  factory RecentHistory({
    $core.Iterable<$core.String>? lastTopics,
    $core.Iterable<$core.String>? emotionalTrajectory,
  }) {
    final result = create();
    if (lastTopics != null) result.lastTopics.addAll(lastTopics);
    if (emotionalTrajectory != null)
      result.emotionalTrajectory.addAll(emotionalTrajectory);
    return result;
  }

  RecentHistory._();

  factory RecentHistory.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory RecentHistory.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'RecentHistory',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..pPS(1, _omitFieldNames ? '' : 'lastTopics')
    ..pPS(2, _omitFieldNames ? '' : 'emotionalTrajectory')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  RecentHistory clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  RecentHistory copyWith(void Function(RecentHistory) updates) =>
      super.copyWith((message) => updates(message as RecentHistory))
          as RecentHistory;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static RecentHistory create() => RecentHistory._();
  @$core.override
  RecentHistory createEmptyInstance() => create();
  static $pb.PbList<RecentHistory> createRepeated() =>
      $pb.PbList<RecentHistory>();
  @$core.pragma('dart2js:noInline')
  static RecentHistory getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<RecentHistory>(create);
  static RecentHistory? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<$core.String> get lastTopics => $_getList(0);

  @$pb.TagNumber(2)
  $pb.PbList<$core.String> get emotionalTrajectory => $_getList(1);
}

/// Response generation request
class ResponseRequest extends $pb.GeneratedMessage {
  factory ResponseRequest({
    $0.Timestamp? timestamp,
    $core.String? source,
    $core.String? threadId,
    $core.String? inputMessageId,
    ResponseParameters? parameters,
  }) {
    final result = create();
    if (timestamp != null) result.timestamp = timestamp;
    if (source != null) result.source = source;
    if (threadId != null) result.threadId = threadId;
    if (inputMessageId != null) result.inputMessageId = inputMessageId;
    if (parameters != null) result.parameters = parameters;
    return result;
  }

  ResponseRequest._();

  factory ResponseRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ResponseRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ResponseRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOM<$0.Timestamp>(1, _omitFieldNames ? '' : 'timestamp',
        subBuilder: $0.Timestamp.create)
    ..aOS(2, _omitFieldNames ? '' : 'source')
    ..aOS(3, _omitFieldNames ? '' : 'threadId')
    ..aOS(4, _omitFieldNames ? '' : 'inputMessageId')
    ..aOM<ResponseParameters>(5, _omitFieldNames ? '' : 'parameters',
        subBuilder: ResponseParameters.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ResponseRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ResponseRequest copyWith(void Function(ResponseRequest) updates) =>
      super.copyWith((message) => updates(message as ResponseRequest))
          as ResponseRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ResponseRequest create() => ResponseRequest._();
  @$core.override
  ResponseRequest createEmptyInstance() => create();
  static $pb.PbList<ResponseRequest> createRepeated() =>
      $pb.PbList<ResponseRequest>();
  @$core.pragma('dart2js:noInline')
  static ResponseRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ResponseRequest>(create);
  static ResponseRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $0.Timestamp get timestamp => $_getN(0);
  @$pb.TagNumber(1)
  set timestamp($0.Timestamp value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasTimestamp() => $_has(0);
  @$pb.TagNumber(1)
  void clearTimestamp() => $_clearField(1);
  @$pb.TagNumber(1)
  $0.Timestamp ensureTimestamp() => $_ensure(0);

  @$pb.TagNumber(2)
  $core.String get source => $_getSZ(1);
  @$pb.TagNumber(2)
  set source($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSource() => $_has(1);
  @$pb.TagNumber(2)
  void clearSource() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get threadId => $_getSZ(2);
  @$pb.TagNumber(3)
  set threadId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasThreadId() => $_has(2);
  @$pb.TagNumber(3)
  void clearThreadId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get inputMessageId => $_getSZ(3);
  @$pb.TagNumber(4)
  set inputMessageId($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasInputMessageId() => $_has(3);
  @$pb.TagNumber(4)
  void clearInputMessageId() => $_clearField(4);

  @$pb.TagNumber(5)
  ResponseParameters get parameters => $_getN(4);
  @$pb.TagNumber(5)
  set parameters(ResponseParameters value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasParameters() => $_has(4);
  @$pb.TagNumber(5)
  void clearParameters() => $_clearField(5);
  @$pb.TagNumber(5)
  ResponseParameters ensureParameters() => $_ensure(4);
}

/// Parameters for response generation
class ResponseParameters extends $pb.GeneratedMessage {
  factory ResponseParameters({
    $core.double? emotionalAlignment,
    $core.String? responseStyle,
    $core.Iterable<$core.String>? includeTopics,
    $core.Iterable<$core.String>? avoidTopics,
    $core.int? maxLength,
    $core.double? creativity,
  }) {
    final result = create();
    if (emotionalAlignment != null)
      result.emotionalAlignment = emotionalAlignment;
    if (responseStyle != null) result.responseStyle = responseStyle;
    if (includeTopics != null) result.includeTopics.addAll(includeTopics);
    if (avoidTopics != null) result.avoidTopics.addAll(avoidTopics);
    if (maxLength != null) result.maxLength = maxLength;
    if (creativity != null) result.creativity = creativity;
    return result;
  }

  ResponseParameters._();

  factory ResponseParameters.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ResponseParameters.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ResponseParameters',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aD(1, _omitFieldNames ? '' : 'emotionalAlignment',
        fieldType: $pb.PbFieldType.OF)
    ..aOS(2, _omitFieldNames ? '' : 'responseStyle')
    ..pPS(3, _omitFieldNames ? '' : 'includeTopics')
    ..pPS(4, _omitFieldNames ? '' : 'avoidTopics')
    ..aI(5, _omitFieldNames ? '' : 'maxLength')
    ..aD(6, _omitFieldNames ? '' : 'creativity', fieldType: $pb.PbFieldType.OF)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ResponseParameters clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ResponseParameters copyWith(void Function(ResponseParameters) updates) =>
      super.copyWith((message) => updates(message as ResponseParameters))
          as ResponseParameters;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ResponseParameters create() => ResponseParameters._();
  @$core.override
  ResponseParameters createEmptyInstance() => create();
  static $pb.PbList<ResponseParameters> createRepeated() =>
      $pb.PbList<ResponseParameters>();
  @$core.pragma('dart2js:noInline')
  static ResponseParameters getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ResponseParameters>(create);
  static ResponseParameters? _defaultInstance;

  @$pb.TagNumber(1)
  $core.double get emotionalAlignment => $_getN(0);
  @$pb.TagNumber(1)
  set emotionalAlignment($core.double value) => $_setFloat(0, value);
  @$pb.TagNumber(1)
  $core.bool hasEmotionalAlignment() => $_has(0);
  @$pb.TagNumber(1)
  void clearEmotionalAlignment() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get responseStyle => $_getSZ(1);
  @$pb.TagNumber(2)
  set responseStyle($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasResponseStyle() => $_has(1);
  @$pb.TagNumber(2)
  void clearResponseStyle() => $_clearField(2);

  @$pb.TagNumber(3)
  $pb.PbList<$core.String> get includeTopics => $_getList(2);

  @$pb.TagNumber(4)
  $pb.PbList<$core.String> get avoidTopics => $_getList(3);

  @$pb.TagNumber(5)
  $core.int get maxLength => $_getIZ(4);
  @$pb.TagNumber(5)
  set maxLength($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasMaxLength() => $_has(4);
  @$pb.TagNumber(5)
  void clearMaxLength() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.double get creativity => $_getN(5);
  @$pb.TagNumber(6)
  set creativity($core.double value) => $_setFloat(5, value);
  @$pb.TagNumber(6)
  $core.bool hasCreativity() => $_has(5);
  @$pb.TagNumber(6)
  void clearCreativity() => $_clearField(6);
}

/// Streaming chunk for real-time API responses
class StreamingResponse extends $pb.GeneratedMessage {
  factory StreamingResponse({
    $core.String? requestId,
    $core.String? content,
    $core.String? accumulatedContent,
    $core.bool? done,
    $fixnum.Int64? timestamp,
    $core.String? contentType,
  }) {
    final result = create();
    if (requestId != null) result.requestId = requestId;
    if (content != null) result.content = content;
    if (accumulatedContent != null)
      result.accumulatedContent = accumulatedContent;
    if (done != null) result.done = done;
    if (timestamp != null) result.timestamp = timestamp;
    if (contentType != null) result.contentType = contentType;
    return result;
  }

  StreamingResponse._();

  factory StreamingResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory StreamingResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'StreamingResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.conversation'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..aOS(3, _omitFieldNames ? '' : 'accumulatedContent')
    ..aOB(4, _omitFieldNames ? '' : 'done')
    ..aInt64(5, _omitFieldNames ? '' : 'timestamp')
    ..aOS(6, _omitFieldNames ? '' : 'contentType')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StreamingResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StreamingResponse copyWith(void Function(StreamingResponse) updates) =>
      super.copyWith((message) => updates(message as StreamingResponse))
          as StreamingResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static StreamingResponse create() => StreamingResponse._();
  @$core.override
  StreamingResponse createEmptyInstance() => create();
  static $pb.PbList<StreamingResponse> createRepeated() =>
      $pb.PbList<StreamingResponse>();
  @$core.pragma('dart2js:noInline')
  static StreamingResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<StreamingResponse>(create);
  static StreamingResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get requestId => $_getSZ(0);
  @$pb.TagNumber(1)
  set requestId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRequestId() => $_has(0);
  @$pb.TagNumber(1)
  void clearRequestId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get accumulatedContent => $_getSZ(2);
  @$pb.TagNumber(3)
  set accumulatedContent($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasAccumulatedContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearAccumulatedContent() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.bool get done => $_getBF(3);
  @$pb.TagNumber(4)
  set done($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasDone() => $_has(3);
  @$pb.TagNumber(4)
  void clearDone() => $_clearField(4);

  @$pb.TagNumber(5)
  $fixnum.Int64 get timestamp => $_getI64(4);
  @$pb.TagNumber(5)
  set timestamp($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasTimestamp() => $_has(4);
  @$pb.TagNumber(5)
  void clearTimestamp() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get contentType => $_getSZ(5);
  @$pb.TagNumber(6)
  set contentType($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasContentType() => $_has(5);
  @$pb.TagNumber(6)
  void clearContentType() => $_clearField(6);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
