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

import 'package:protobuf/protobuf.dart' as $pb;

class Message_MessageType extends $pb.ProtobufEnum {
  static const Message_MessageType UNKNOWN =
      Message_MessageType._(0, _omitEnumNames ? '' : 'UNKNOWN');
  static const Message_MessageType USER_INPUT =
      Message_MessageType._(1, _omitEnumNames ? '' : 'USER_INPUT');
  static const Message_MessageType SYSTEM_RESPONSE =
      Message_MessageType._(2, _omitEnumNames ? '' : 'SYSTEM_RESPONSE');
  static const Message_MessageType SYSTEM_NOTIFICATION =
      Message_MessageType._(3, _omitEnumNames ? '' : 'SYSTEM_NOTIFICATION');
  static const Message_MessageType THINKING_ALOUD =
      Message_MessageType._(4, _omitEnumNames ? '' : 'THINKING_ALOUD');
  static const Message_MessageType INTERNAL_REFLECTION =
      Message_MessageType._(5, _omitEnumNames ? '' : 'INTERNAL_REFLECTION');

  static const $core.List<Message_MessageType> values = <Message_MessageType>[
    UNKNOWN,
    USER_INPUT,
    SYSTEM_RESPONSE,
    SYSTEM_NOTIFICATION,
    THINKING_ALOUD,
    INTERNAL_REFLECTION,
  ];

  static final $core.List<Message_MessageType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 5);
  static Message_MessageType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const Message_MessageType._(super.value, super.name);
}

class MessageAnalysis_Urgency extends $pb.ProtobufEnum {
  static const MessageAnalysis_Urgency UNKNOWN =
      MessageAnalysis_Urgency._(0, _omitEnumNames ? '' : 'UNKNOWN');
  static const MessageAnalysis_Urgency LOW =
      MessageAnalysis_Urgency._(1, _omitEnumNames ? '' : 'LOW');
  static const MessageAnalysis_Urgency MEDIUM =
      MessageAnalysis_Urgency._(2, _omitEnumNames ? '' : 'MEDIUM');
  static const MessageAnalysis_Urgency HIGH =
      MessageAnalysis_Urgency._(3, _omitEnumNames ? '' : 'HIGH');
  static const MessageAnalysis_Urgency CRITICAL =
      MessageAnalysis_Urgency._(4, _omitEnumNames ? '' : 'CRITICAL');

  static const $core.List<MessageAnalysis_Urgency> values =
      <MessageAnalysis_Urgency>[
    UNKNOWN,
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL,
  ];

  static final $core.List<MessageAnalysis_Urgency?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 4);
  static MessageAnalysis_Urgency? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const MessageAnalysis_Urgency._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
