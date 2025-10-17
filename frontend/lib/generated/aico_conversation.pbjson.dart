// This is a generated file - do not edit.
//
// Generated from aico_conversation.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use conversationMessageDescriptor instead')
const ConversationMessage$json = {
  '1': 'ConversationMessage',
  '2': [
    {
      '1': 'timestamp',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'timestamp'
    },
    {'1': 'source', '3': 2, '4': 1, '5': 9, '10': 'source'},
    {'1': 'message_id', '3': 3, '4': 1, '5': 9, '10': 'messageId'},
    {'1': 'user_id', '3': 4, '4': 1, '5': 9, '10': 'userId'},
    {
      '1': 'message',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.aico.conversation.Message',
      '10': 'message'
    },
    {
      '1': 'analysis',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.aico.conversation.MessageAnalysis',
      '10': 'analysis'
    },
  ],
};

/// Descriptor for `ConversationMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List conversationMessageDescriptor = $convert.base64Decode(
    'ChNDb252ZXJzYXRpb25NZXNzYWdlEjgKCXRpbWVzdGFtcBgBIAEoCzIaLmdvb2dsZS5wcm90b2'
    'J1Zi5UaW1lc3RhbXBSCXRpbWVzdGFtcBIWCgZzb3VyY2UYAiABKAlSBnNvdXJjZRIdCgptZXNz'
    'YWdlX2lkGAMgASgJUgltZXNzYWdlSWQSFwoHdXNlcl9pZBgEIAEoCVIGdXNlcklkEjQKB21lc3'
    'NhZ2UYBSABKAsyGi5haWNvLmNvbnZlcnNhdGlvbi5NZXNzYWdlUgdtZXNzYWdlEj4KCGFuYWx5'
    'c2lzGAYgASgLMiIuYWljby5jb252ZXJzYXRpb24uTWVzc2FnZUFuYWx5c2lzUghhbmFseXNpcw'
    '==');

@$core.Deprecated('Use messageDescriptor instead')
const Message$json = {
  '1': 'Message',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {
      '1': 'type',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.aico.conversation.Message.MessageType',
      '10': 'type'
    },
    {'1': 'conversation_id', '3': 3, '4': 1, '5': 9, '10': 'conversationId'},
    {'1': 'turn_number', '3': 4, '4': 1, '5': 5, '10': 'turnNumber'},
  ],
  '4': [Message_MessageType$json],
};

@$core.Deprecated('Use messageDescriptor instead')
const Message_MessageType$json = {
  '1': 'MessageType',
  '2': [
    {'1': 'UNKNOWN', '2': 0},
    {'1': 'USER_INPUT', '2': 1},
    {'1': 'SYSTEM_RESPONSE', '2': 2},
    {'1': 'SYSTEM_NOTIFICATION', '2': 3},
    {'1': 'THINKING_ALOUD', '2': 4},
    {'1': 'INTERNAL_REFLECTION', '2': 5},
  ],
};

/// Descriptor for `Message`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List messageDescriptor = $convert.base64Decode(
    'CgdNZXNzYWdlEhIKBHRleHQYASABKAlSBHRleHQSOgoEdHlwZRgCIAEoDjImLmFpY28uY29udm'
    'Vyc2F0aW9uLk1lc3NhZ2UuTWVzc2FnZVR5cGVSBHR5cGUSJwoPY29udmVyc2F0aW9uX2lkGAMg'
    'ASgJUg5jb252ZXJzYXRpb25JZBIfCgt0dXJuX251bWJlchgEIAEoBVIKdHVybk51bWJlciKFAQ'
    'oLTWVzc2FnZVR5cGUSCwoHVU5LTk9XThAAEg4KClVTRVJfSU5QVVQQARITCg9TWVNURU1fUkVT'
    'UE9OU0UQAhIXChNTWVNURU1fTk9USUZJQ0FUSU9OEAMSEgoOVEhJTktJTkdfQUxPVUQQBBIXCh'
    'NJTlRFUk5BTF9SRUZMRUNUSU9OEAU=');

@$core.Deprecated('Use messageAnalysisDescriptor instead')
const MessageAnalysis$json = {
  '1': 'MessageAnalysis',
  '2': [
    {'1': 'intent', '3': 1, '4': 1, '5': 9, '10': 'intent'},
    {
      '1': 'urgency',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.aico.conversation.MessageAnalysis.Urgency',
      '10': 'urgency'
    },
    {
      '1': 'requires_response',
      '3': 3,
      '4': 1,
      '5': 8,
      '10': 'requiresResponse'
    },
  ],
  '4': [MessageAnalysis_Urgency$json],
};

@$core.Deprecated('Use messageAnalysisDescriptor instead')
const MessageAnalysis_Urgency$json = {
  '1': 'Urgency',
  '2': [
    {'1': 'UNKNOWN', '2': 0},
    {'1': 'LOW', '2': 1},
    {'1': 'MEDIUM', '2': 2},
    {'1': 'HIGH', '2': 3},
    {'1': 'CRITICAL', '2': 4},
  ],
};

/// Descriptor for `MessageAnalysis`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List messageAnalysisDescriptor = $convert.base64Decode(
    'Cg9NZXNzYWdlQW5hbHlzaXMSFgoGaW50ZW50GAEgASgJUgZpbnRlbnQSRAoHdXJnZW5jeRgCIA'
    'EoDjIqLmFpY28uY29udmVyc2F0aW9uLk1lc3NhZ2VBbmFseXNpcy5VcmdlbmN5Ugd1cmdlbmN5'
    'EisKEXJlcXVpcmVzX3Jlc3BvbnNlGAMgASgIUhByZXF1aXJlc1Jlc3BvbnNlIkMKB1VyZ2VuY3'
    'kSCwoHVU5LTk9XThAAEgcKA0xPVxABEgoKBk1FRElVTRACEggKBEhJR0gQAxIMCghDUklUSUNB'
    'TBAE');

@$core.Deprecated('Use conversationContextDescriptor instead')
const ConversationContext$json = {
  '1': 'ConversationContext',
  '2': [
    {
      '1': 'timestamp',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'timestamp'
    },
    {'1': 'source', '3': 2, '4': 1, '5': 9, '10': 'source'},
    {
      '1': 'context',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.aico.conversation.Context',
      '10': 'context'
    },
    {
      '1': 'recent_history',
      '3': 4,
      '4': 1,
      '5': 11,
      '6': '.aico.conversation.RecentHistory',
      '10': 'recentHistory'
    },
  ],
};

/// Descriptor for `ConversationContext`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List conversationContextDescriptor = $convert.base64Decode(
    'ChNDb252ZXJzYXRpb25Db250ZXh0EjgKCXRpbWVzdGFtcBgBIAEoCzIaLmdvb2dsZS5wcm90b2'
    'J1Zi5UaW1lc3RhbXBSCXRpbWVzdGFtcBIWCgZzb3VyY2UYAiABKAlSBnNvdXJjZRI0Cgdjb250'
    'ZXh0GAMgASgLMhouYWljby5jb252ZXJzYXRpb24uQ29udGV4dFIHY29udGV4dBJHCg5yZWNlbn'
    'RfaGlzdG9yeRgEIAEoCzIgLmFpY28uY29udmVyc2F0aW9uLlJlY2VudEhpc3RvcnlSDXJlY2Vu'
    'dEhpc3Rvcnk=');

@$core.Deprecated('Use contextDescriptor instead')
const Context$json = {
  '1': 'Context',
  '2': [
    {'1': 'current_topic', '3': 1, '4': 1, '5': 9, '10': 'currentTopic'},
    {
      '1': 'conversation_phase',
      '3': 2,
      '4': 1,
      '5': 9,
      '10': 'conversationPhase'
    },
    {
      '1': 'session_duration_minutes',
      '3': 3,
      '4': 1,
      '5': 5,
      '10': 'sessionDurationMinutes'
    },
    {
      '1': 'relationship_phase',
      '3': 4,
      '4': 1,
      '5': 9,
      '10': 'relationshipPhase'
    },
    {'1': 'time_context', '3': 5, '4': 1, '5': 9, '10': 'timeContext'},
    {
      '1': 'crisis_indicators',
      '3': 6,
      '4': 1,
      '5': 8,
      '10': 'crisisIndicators'
    },
  ],
};

/// Descriptor for `Context`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List contextDescriptor = $convert.base64Decode(
    'CgdDb250ZXh0EiMKDWN1cnJlbnRfdG9waWMYASABKAlSDGN1cnJlbnRUb3BpYxItChJjb252ZX'
    'JzYXRpb25fcGhhc2UYAiABKAlSEWNvbnZlcnNhdGlvblBoYXNlEjgKGHNlc3Npb25fZHVyYXRp'
    'b25fbWludXRlcxgDIAEoBVIWc2Vzc2lvbkR1cmF0aW9uTWludXRlcxItChJyZWxhdGlvbnNoaX'
    'BfcGhhc2UYBCABKAlSEXJlbGF0aW9uc2hpcFBoYXNlEiEKDHRpbWVfY29udGV4dBgFIAEoCVIL'
    'dGltZUNvbnRleHQSKwoRY3Jpc2lzX2luZGljYXRvcnMYBiABKAhSEGNyaXNpc0luZGljYXRvcn'
    'M=');

@$core.Deprecated('Use recentHistoryDescriptor instead')
const RecentHistory$json = {
  '1': 'RecentHistory',
  '2': [
    {'1': 'last_topics', '3': 1, '4': 3, '5': 9, '10': 'lastTopics'},
    {
      '1': 'emotional_trajectory',
      '3': 2,
      '4': 3,
      '5': 9,
      '10': 'emotionalTrajectory'
    },
  ],
};

/// Descriptor for `RecentHistory`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List recentHistoryDescriptor = $convert.base64Decode(
    'Cg1SZWNlbnRIaXN0b3J5Eh8KC2xhc3RfdG9waWNzGAEgAygJUgpsYXN0VG9waWNzEjEKFGVtb3'
    'Rpb25hbF90cmFqZWN0b3J5GAIgAygJUhNlbW90aW9uYWxUcmFqZWN0b3J5');

@$core.Deprecated('Use responseRequestDescriptor instead')
const ResponseRequest$json = {
  '1': 'ResponseRequest',
  '2': [
    {
      '1': 'timestamp',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'timestamp'
    },
    {'1': 'source', '3': 2, '4': 1, '5': 9, '10': 'source'},
    {'1': 'thread_id', '3': 3, '4': 1, '5': 9, '10': 'threadId'},
    {'1': 'input_message_id', '3': 4, '4': 1, '5': 9, '10': 'inputMessageId'},
    {
      '1': 'parameters',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.aico.conversation.ResponseParameters',
      '10': 'parameters'
    },
  ],
};

/// Descriptor for `ResponseRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List responseRequestDescriptor = $convert.base64Decode(
    'Cg9SZXNwb25zZVJlcXVlc3QSOAoJdGltZXN0YW1wGAEgASgLMhouZ29vZ2xlLnByb3RvYnVmLl'
    'RpbWVzdGFtcFIJdGltZXN0YW1wEhYKBnNvdXJjZRgCIAEoCVIGc291cmNlEhsKCXRocmVhZF9p'
    'ZBgDIAEoCVIIdGhyZWFkSWQSKAoQaW5wdXRfbWVzc2FnZV9pZBgEIAEoCVIOaW5wdXRNZXNzYW'
    'dlSWQSRQoKcGFyYW1ldGVycxgFIAEoCzIlLmFpY28uY29udmVyc2F0aW9uLlJlc3BvbnNlUGFy'
    'YW1ldGVyc1IKcGFyYW1ldGVycw==');

@$core.Deprecated('Use responseParametersDescriptor instead')
const ResponseParameters$json = {
  '1': 'ResponseParameters',
  '2': [
    {
      '1': 'emotional_alignment',
      '3': 1,
      '4': 1,
      '5': 2,
      '10': 'emotionalAlignment'
    },
    {'1': 'response_style', '3': 2, '4': 1, '5': 9, '10': 'responseStyle'},
    {'1': 'include_topics', '3': 3, '4': 3, '5': 9, '10': 'includeTopics'},
    {'1': 'avoid_topics', '3': 4, '4': 3, '5': 9, '10': 'avoidTopics'},
    {'1': 'max_length', '3': 5, '4': 1, '5': 5, '10': 'maxLength'},
    {'1': 'creativity', '3': 6, '4': 1, '5': 2, '10': 'creativity'},
  ],
};

/// Descriptor for `ResponseParameters`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List responseParametersDescriptor = $convert.base64Decode(
    'ChJSZXNwb25zZVBhcmFtZXRlcnMSLwoTZW1vdGlvbmFsX2FsaWdubWVudBgBIAEoAlISZW1vdG'
    'lvbmFsQWxpZ25tZW50EiUKDnJlc3BvbnNlX3N0eWxlGAIgASgJUg1yZXNwb25zZVN0eWxlEiUK'
    'DmluY2x1ZGVfdG9waWNzGAMgAygJUg1pbmNsdWRlVG9waWNzEiEKDGF2b2lkX3RvcGljcxgEIA'
    'MoCVILYXZvaWRUb3BpY3MSHQoKbWF4X2xlbmd0aBgFIAEoBVIJbWF4TGVuZ3RoEh4KCmNyZWF0'
    'aXZpdHkYBiABKAJSCmNyZWF0aXZpdHk=');

@$core.Deprecated('Use streamingResponseDescriptor instead')
const StreamingResponse$json = {
  '1': 'StreamingResponse',
  '2': [
    {'1': 'request_id', '3': 1, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'content', '3': 2, '4': 1, '5': 9, '10': 'content'},
    {
      '1': 'accumulated_content',
      '3': 3,
      '4': 1,
      '5': 9,
      '10': 'accumulatedContent'
    },
    {'1': 'done', '3': 4, '4': 1, '5': 8, '10': 'done'},
    {
      '1': 'timestamp',
      '3': 5,
      '4': 1,
      '5': 3,
      '9': 0,
      '10': 'timestamp',
      '17': true
    },
    {'1': 'content_type', '3': 6, '4': 1, '5': 9, '10': 'contentType'},
  ],
  '8': [
    {'1': '_timestamp'},
  ],
};

/// Descriptor for `StreamingResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List streamingResponseDescriptor = $convert.base64Decode(
    'ChFTdHJlYW1pbmdSZXNwb25zZRIdCgpyZXF1ZXN0X2lkGAEgASgJUglyZXF1ZXN0SWQSGAoHY2'
    '9udGVudBgCIAEoCVIHY29udGVudBIvChNhY2N1bXVsYXRlZF9jb250ZW50GAMgASgJUhJhY2N1'
    'bXVsYXRlZENvbnRlbnQSEgoEZG9uZRgEIAEoCFIEZG9uZRIhCgl0aW1lc3RhbXAYBSABKANIAF'
    'IJdGltZXN0YW1wiAEBEiEKDGNvbnRlbnRfdHlwZRgGIAEoCVILY29udGVudFR5cGVCDAoKX3Rp'
    'bWVzdGFtcA==');
