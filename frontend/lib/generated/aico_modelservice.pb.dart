// This is a generated file - do not edit.
//
// Generated from aico_modelservice.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'google/protobuf/timestamp.pb.dart' as $0;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

/// Health check request
class HealthRequest extends $pb.GeneratedMessage {
  factory HealthRequest() => create();

  HealthRequest._();

  factory HealthRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory HealthRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'HealthRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HealthRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HealthRequest copyWith(void Function(HealthRequest) updates) =>
      super.copyWith((message) => updates(message as HealthRequest))
          as HealthRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static HealthRequest create() => HealthRequest._();
  @$core.override
  HealthRequest createEmptyInstance() => create();
  static $pb.PbList<HealthRequest> createRepeated() =>
      $pb.PbList<HealthRequest>();
  @$core.pragma('dart2js:noInline')
  static HealthRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<HealthRequest>(create);
  static HealthRequest? _defaultInstance;
}

/// Conversation completions request
class CompletionsRequest extends $pb.GeneratedMessage {
  factory CompletionsRequest({
    $core.String? model,
    $core.Iterable<ConversationMessage>? messages,
    $core.bool? stream,
    $core.double? temperature,
    $core.int? maxTokens,
    $core.double? topP,
    $core.String? system,
  }) {
    final result = create();
    if (model != null) result.model = model;
    if (messages != null) result.messages.addAll(messages);
    if (stream != null) result.stream = stream;
    if (temperature != null) result.temperature = temperature;
    if (maxTokens != null) result.maxTokens = maxTokens;
    if (topP != null) result.topP = topP;
    if (system != null) result.system = system;
    return result;
  }

  CompletionsRequest._();

  factory CompletionsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CompletionsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CompletionsRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..pPM<ConversationMessage>(2, _omitFieldNames ? '' : 'messages',
        subBuilder: ConversationMessage.create)
    ..aOB(3, _omitFieldNames ? '' : 'stream')
    ..aD(4, _omitFieldNames ? '' : 'temperature')
    ..aI(5, _omitFieldNames ? '' : 'maxTokens')
    ..aD(6, _omitFieldNames ? '' : 'topP')
    ..aOS(7, _omitFieldNames ? '' : 'system')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CompletionsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CompletionsRequest copyWith(void Function(CompletionsRequest) updates) =>
      super.copyWith((message) => updates(message as CompletionsRequest))
          as CompletionsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CompletionsRequest create() => CompletionsRequest._();
  @$core.override
  CompletionsRequest createEmptyInstance() => create();
  static $pb.PbList<CompletionsRequest> createRepeated() =>
      $pb.PbList<CompletionsRequest>();
  @$core.pragma('dart2js:noInline')
  static CompletionsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CompletionsRequest>(create);
  static CompletionsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbList<ConversationMessage> get messages => $_getList(1);

  @$pb.TagNumber(3)
  $core.bool get stream => $_getBF(2);
  @$pb.TagNumber(3)
  set stream($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasStream() => $_has(2);
  @$pb.TagNumber(3)
  void clearStream() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.double get temperature => $_getN(3);
  @$pb.TagNumber(4)
  set temperature($core.double value) => $_setDouble(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTemperature() => $_has(3);
  @$pb.TagNumber(4)
  void clearTemperature() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.int get maxTokens => $_getIZ(4);
  @$pb.TagNumber(5)
  set maxTokens($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasMaxTokens() => $_has(4);
  @$pb.TagNumber(5)
  void clearMaxTokens() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.double get topP => $_getN(5);
  @$pb.TagNumber(6)
  set topP($core.double value) => $_setDouble(5, value);
  @$pb.TagNumber(6)
  $core.bool hasTopP() => $_has(5);
  @$pb.TagNumber(6)
  void clearTopP() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get system => $_getSZ(6);
  @$pb.TagNumber(7)
  set system($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasSystem() => $_has(6);
  @$pb.TagNumber(7)
  void clearSystem() => $_clearField(7);
}

/// Streaming chunk message for real-time completions
class StreamingChunk extends $pb.GeneratedMessage {
  factory StreamingChunk({
    $core.String? requestId,
    $core.String? content,
    $core.String? accumulatedContent,
    $core.bool? done,
    $core.String? model,
    $fixnum.Int64? timestamp,
    $core.String? contentType,
  }) {
    final result = create();
    if (requestId != null) result.requestId = requestId;
    if (content != null) result.content = content;
    if (accumulatedContent != null)
      result.accumulatedContent = accumulatedContent;
    if (done != null) result.done = done;
    if (model != null) result.model = model;
    if (timestamp != null) result.timestamp = timestamp;
    if (contentType != null) result.contentType = contentType;
    return result;
  }

  StreamingChunk._();

  factory StreamingChunk.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory StreamingChunk.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'StreamingChunk',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..aOS(3, _omitFieldNames ? '' : 'accumulatedContent')
    ..aOB(4, _omitFieldNames ? '' : 'done')
    ..aOS(5, _omitFieldNames ? '' : 'model')
    ..aInt64(6, _omitFieldNames ? '' : 'timestamp')
    ..aOS(7, _omitFieldNames ? '' : 'contentType')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StreamingChunk clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StreamingChunk copyWith(void Function(StreamingChunk) updates) =>
      super.copyWith((message) => updates(message as StreamingChunk))
          as StreamingChunk;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static StreamingChunk create() => StreamingChunk._();
  @$core.override
  StreamingChunk createEmptyInstance() => create();
  static $pb.PbList<StreamingChunk> createRepeated() =>
      $pb.PbList<StreamingChunk>();
  @$core.pragma('dart2js:noInline')
  static StreamingChunk getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<StreamingChunk>(create);
  static StreamingChunk? _defaultInstance;

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
  $core.String get model => $_getSZ(4);
  @$pb.TagNumber(5)
  set model($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasModel() => $_has(4);
  @$pb.TagNumber(5)
  void clearModel() => $_clearField(5);

  @$pb.TagNumber(6)
  $fixnum.Int64 get timestamp => $_getI64(5);
  @$pb.TagNumber(6)
  set timestamp($fixnum.Int64 value) => $_setInt64(5, value);
  @$pb.TagNumber(6)
  $core.bool hasTimestamp() => $_has(5);
  @$pb.TagNumber(6)
  void clearTimestamp() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get contentType => $_getSZ(6);
  @$pb.TagNumber(7)
  set contentType($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasContentType() => $_has(6);
  @$pb.TagNumber(7)
  void clearContentType() => $_clearField(7);
}

/// Available models request
class ModelsRequest extends $pb.GeneratedMessage {
  factory ModelsRequest() => create();

  ModelsRequest._();

  factory ModelsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ModelsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ModelsRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelsRequest copyWith(void Function(ModelsRequest) updates) =>
      super.copyWith((message) => updates(message as ModelsRequest))
          as ModelsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ModelsRequest create() => ModelsRequest._();
  @$core.override
  ModelsRequest createEmptyInstance() => create();
  static $pb.PbList<ModelsRequest> createRepeated() =>
      $pb.PbList<ModelsRequest>();
  @$core.pragma('dart2js:noInline')
  static ModelsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ModelsRequest>(create);
  static ModelsRequest? _defaultInstance;
}

/// Model info request
class ModelInfoRequest extends $pb.GeneratedMessage {
  factory ModelInfoRequest({
    $core.String? model,
  }) {
    final result = create();
    if (model != null) result.model = model;
    return result;
  }

  ModelInfoRequest._();

  factory ModelInfoRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ModelInfoRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ModelInfoRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelInfoRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelInfoRequest copyWith(void Function(ModelInfoRequest) updates) =>
      super.copyWith((message) => updates(message as ModelInfoRequest))
          as ModelInfoRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ModelInfoRequest create() => ModelInfoRequest._();
  @$core.override
  ModelInfoRequest createEmptyInstance() => create();
  static $pb.PbList<ModelInfoRequest> createRepeated() =>
      $pb.PbList<ModelInfoRequest>();
  @$core.pragma('dart2js:noInline')
  static ModelInfoRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ModelInfoRequest>(create);
  static ModelInfoRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);
}

/// Embeddings request
class EmbeddingsRequest extends $pb.GeneratedMessage {
  factory EmbeddingsRequest({
    $core.String? model,
    $core.String? prompt,
  }) {
    final result = create();
    if (model != null) result.model = model;
    if (prompt != null) result.prompt = prompt;
    return result;
  }

  EmbeddingsRequest._();

  factory EmbeddingsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EmbeddingsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EmbeddingsRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..aOS(2, _omitFieldNames ? '' : 'prompt')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EmbeddingsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EmbeddingsRequest copyWith(void Function(EmbeddingsRequest) updates) =>
      super.copyWith((message) => updates(message as EmbeddingsRequest))
          as EmbeddingsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EmbeddingsRequest create() => EmbeddingsRequest._();
  @$core.override
  EmbeddingsRequest createEmptyInstance() => create();
  static $pb.PbList<EmbeddingsRequest> createRepeated() =>
      $pb.PbList<EmbeddingsRequest>();
  @$core.pragma('dart2js:noInline')
  static EmbeddingsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EmbeddingsRequest>(create);
  static EmbeddingsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get prompt => $_getSZ(1);
  @$pb.TagNumber(2)
  set prompt($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasPrompt() => $_has(1);
  @$pb.TagNumber(2)
  void clearPrompt() => $_clearField(2);
}

/// NER request
class NerRequest extends $pb.GeneratedMessage {
  factory NerRequest({
    $core.String? text,
    $core.Iterable<$core.String>? entityTypes,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (entityTypes != null) result.entityTypes.addAll(entityTypes);
    return result;
  }

  NerRequest._();

  factory NerRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory NerRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'NerRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..pPS(2, _omitFieldNames ? '' : 'entityTypes')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  NerRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  NerRequest copyWith(void Function(NerRequest) updates) =>
      super.copyWith((message) => updates(message as NerRequest)) as NerRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static NerRequest create() => NerRequest._();
  @$core.override
  NerRequest createEmptyInstance() => create();
  static $pb.PbList<NerRequest> createRepeated() => $pb.PbList<NerRequest>();
  @$core.pragma('dart2js:noInline')
  static NerRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<NerRequest>(create);
  static NerRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbList<$core.String> get entityTypes => $_getList(1);
}

/// Intent classification request
class IntentClassificationRequest extends $pb.GeneratedMessage {
  factory IntentClassificationRequest({
    $core.String? text,
    $core.String? model,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (model != null) result.model = model;
    return result;
  }

  IntentClassificationRequest._();

  factory IntentClassificationRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory IntentClassificationRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'IntentClassificationRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..aOS(2, _omitFieldNames ? '' : 'model')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  IntentClassificationRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  IntentClassificationRequest copyWith(
          void Function(IntentClassificationRequest) updates) =>
      super.copyWith(
              (message) => updates(message as IntentClassificationRequest))
          as IntentClassificationRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static IntentClassificationRequest create() =>
      IntentClassificationRequest._();
  @$core.override
  IntentClassificationRequest createEmptyInstance() => create();
  static $pb.PbList<IntentClassificationRequest> createRepeated() =>
      $pb.PbList<IntentClassificationRequest>();
  @$core.pragma('dart2js:noInline')
  static IntentClassificationRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<IntentClassificationRequest>(create);
  static IntentClassificationRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get model => $_getSZ(1);
  @$pb.TagNumber(2)
  set model($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasModel() => $_has(1);
  @$pb.TagNumber(2)
  void clearModel() => $_clearField(2);
}

/// Sentiment analysis request
class SentimentRequest extends $pb.GeneratedMessage {
  factory SentimentRequest({
    $core.String? text,
  }) {
    final result = create();
    if (text != null) result.text = text;
    return result;
  }

  SentimentRequest._();

  factory SentimentRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory SentimentRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SentimentRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SentimentRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SentimentRequest copyWith(void Function(SentimentRequest) updates) =>
      super.copyWith((message) => updates(message as SentimentRequest))
          as SentimentRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SentimentRequest create() => SentimentRequest._();
  @$core.override
  SentimentRequest createEmptyInstance() => create();
  static $pb.PbList<SentimentRequest> createRepeated() =>
      $pb.PbList<SentimentRequest>();
  @$core.pragma('dart2js:noInline')
  static SentimentRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SentimentRequest>(create);
  static SentimentRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);
}

/// Service status request
class StatusRequest extends $pb.GeneratedMessage {
  factory StatusRequest() => create();

  StatusRequest._();

  factory StatusRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory StatusRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'StatusRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StatusRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StatusRequest copyWith(void Function(StatusRequest) updates) =>
      super.copyWith((message) => updates(message as StatusRequest))
          as StatusRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static StatusRequest create() => StatusRequest._();
  @$core.override
  StatusRequest createEmptyInstance() => create();
  static $pb.PbList<StatusRequest> createRepeated() =>
      $pb.PbList<StatusRequest>();
  @$core.pragma('dart2js:noInline')
  static StatusRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<StatusRequest>(create);
  static StatusRequest? _defaultInstance;
}

/// Ollama management requests
class OllamaStatusRequest extends $pb.GeneratedMessage {
  factory OllamaStatusRequest() => create();

  OllamaStatusRequest._();

  factory OllamaStatusRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaStatusRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaStatusRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaStatusRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaStatusRequest copyWith(void Function(OllamaStatusRequest) updates) =>
      super.copyWith((message) => updates(message as OllamaStatusRequest))
          as OllamaStatusRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaStatusRequest create() => OllamaStatusRequest._();
  @$core.override
  OllamaStatusRequest createEmptyInstance() => create();
  static $pb.PbList<OllamaStatusRequest> createRepeated() =>
      $pb.PbList<OllamaStatusRequest>();
  @$core.pragma('dart2js:noInline')
  static OllamaStatusRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaStatusRequest>(create);
  static OllamaStatusRequest? _defaultInstance;
}

class OllamaModelsRequest extends $pb.GeneratedMessage {
  factory OllamaModelsRequest() => create();

  OllamaModelsRequest._();

  factory OllamaModelsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaModelsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaModelsRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaModelsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaModelsRequest copyWith(void Function(OllamaModelsRequest) updates) =>
      super.copyWith((message) => updates(message as OllamaModelsRequest))
          as OllamaModelsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaModelsRequest create() => OllamaModelsRequest._();
  @$core.override
  OllamaModelsRequest createEmptyInstance() => create();
  static $pb.PbList<OllamaModelsRequest> createRepeated() =>
      $pb.PbList<OllamaModelsRequest>();
  @$core.pragma('dart2js:noInline')
  static OllamaModelsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaModelsRequest>(create);
  static OllamaModelsRequest? _defaultInstance;
}

class OllamaPullRequest extends $pb.GeneratedMessage {
  factory OllamaPullRequest({
    $core.String? model,
  }) {
    final result = create();
    if (model != null) result.model = model;
    return result;
  }

  OllamaPullRequest._();

  factory OllamaPullRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaPullRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaPullRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaPullRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaPullRequest copyWith(void Function(OllamaPullRequest) updates) =>
      super.copyWith((message) => updates(message as OllamaPullRequest))
          as OllamaPullRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaPullRequest create() => OllamaPullRequest._();
  @$core.override
  OllamaPullRequest createEmptyInstance() => create();
  static $pb.PbList<OllamaPullRequest> createRepeated() =>
      $pb.PbList<OllamaPullRequest>();
  @$core.pragma('dart2js:noInline')
  static OllamaPullRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaPullRequest>(create);
  static OllamaPullRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);
}

class OllamaRemoveRequest extends $pb.GeneratedMessage {
  factory OllamaRemoveRequest({
    $core.String? model,
  }) {
    final result = create();
    if (model != null) result.model = model;
    return result;
  }

  OllamaRemoveRequest._();

  factory OllamaRemoveRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaRemoveRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaRemoveRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaRemoveRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaRemoveRequest copyWith(void Function(OllamaRemoveRequest) updates) =>
      super.copyWith((message) => updates(message as OllamaRemoveRequest))
          as OllamaRemoveRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaRemoveRequest create() => OllamaRemoveRequest._();
  @$core.override
  OllamaRemoveRequest createEmptyInstance() => create();
  static $pb.PbList<OllamaRemoveRequest> createRepeated() =>
      $pb.PbList<OllamaRemoveRequest>();
  @$core.pragma('dart2js:noInline')
  static OllamaRemoveRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaRemoveRequest>(create);
  static OllamaRemoveRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);
}

class OllamaServeRequest extends $pb.GeneratedMessage {
  factory OllamaServeRequest() => create();

  OllamaServeRequest._();

  factory OllamaServeRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaServeRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaServeRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaServeRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaServeRequest copyWith(void Function(OllamaServeRequest) updates) =>
      super.copyWith((message) => updates(message as OllamaServeRequest))
          as OllamaServeRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaServeRequest create() => OllamaServeRequest._();
  @$core.override
  OllamaServeRequest createEmptyInstance() => create();
  static $pb.PbList<OllamaServeRequest> createRepeated() =>
      $pb.PbList<OllamaServeRequest>();
  @$core.pragma('dart2js:noInline')
  static OllamaServeRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaServeRequest>(create);
  static OllamaServeRequest? _defaultInstance;
}

class OllamaShutdownRequest extends $pb.GeneratedMessage {
  factory OllamaShutdownRequest() => create();

  OllamaShutdownRequest._();

  factory OllamaShutdownRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaShutdownRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaShutdownRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaShutdownRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaShutdownRequest copyWith(
          void Function(OllamaShutdownRequest) updates) =>
      super.copyWith((message) => updates(message as OllamaShutdownRequest))
          as OllamaShutdownRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaShutdownRequest create() => OllamaShutdownRequest._();
  @$core.override
  OllamaShutdownRequest createEmptyInstance() => create();
  static $pb.PbList<OllamaShutdownRequest> createRepeated() =>
      $pb.PbList<OllamaShutdownRequest>();
  @$core.pragma('dart2js:noInline')
  static OllamaShutdownRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaShutdownRequest>(create);
  static OllamaShutdownRequest? _defaultInstance;
}

/// Health check response
class HealthResponse extends $pb.GeneratedMessage {
  factory HealthResponse({
    $core.bool? success,
    $core.String? status,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (status != null) result.status = status;
    if (error != null) result.error = error;
    return result;
  }

  HealthResponse._();

  factory HealthResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory HealthResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'HealthResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'status')
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HealthResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HealthResponse copyWith(void Function(HealthResponse) updates) =>
      super.copyWith((message) => updates(message as HealthResponse))
          as HealthResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static HealthResponse create() => HealthResponse._();
  @$core.override
  HealthResponse createEmptyInstance() => create();
  static $pb.PbList<HealthResponse> createRepeated() =>
      $pb.PbList<HealthResponse>();
  @$core.pragma('dart2js:noInline')
  static HealthResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<HealthResponse>(create);
  static HealthResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get status => $_getSZ(1);
  @$pb.TagNumber(2)
  set status($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasStatus() => $_has(1);
  @$pb.TagNumber(2)
  void clearStatus() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Conversation completions response
class CompletionsResponse extends $pb.GeneratedMessage {
  factory CompletionsResponse({
    $core.bool? success,
    CompletionResult? result,
    $core.String? error,
  }) {
    final result$ = create();
    if (success != null) result$.success = success;
    if (result != null) result$.result = result;
    if (error != null) result$.error = error;
    return result$;
  }

  CompletionsResponse._();

  factory CompletionsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CompletionsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CompletionsResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOM<CompletionResult>(2, _omitFieldNames ? '' : 'result',
        subBuilder: CompletionResult.create)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CompletionsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CompletionsResponse copyWith(void Function(CompletionsResponse) updates) =>
      super.copyWith((message) => updates(message as CompletionsResponse))
          as CompletionsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CompletionsResponse create() => CompletionsResponse._();
  @$core.override
  CompletionsResponse createEmptyInstance() => create();
  static $pb.PbList<CompletionsResponse> createRepeated() =>
      $pb.PbList<CompletionsResponse>();
  @$core.pragma('dart2js:noInline')
  static CompletionsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CompletionsResponse>(create);
  static CompletionsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  CompletionResult get result => $_getN(1);
  @$pb.TagNumber(2)
  set result(CompletionResult value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasResult() => $_has(1);
  @$pb.TagNumber(2)
  void clearResult() => $_clearField(2);
  @$pb.TagNumber(2)
  CompletionResult ensureResult() => $_ensure(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Available models response
class ModelsResponse extends $pb.GeneratedMessage {
  factory ModelsResponse({
    $core.bool? success,
    $core.Iterable<ModelInfo>? models,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (models != null) result.models.addAll(models);
    if (error != null) result.error = error;
    return result;
  }

  ModelsResponse._();

  factory ModelsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ModelsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ModelsResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..pPM<ModelInfo>(2, _omitFieldNames ? '' : 'models',
        subBuilder: ModelInfo.create)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelsResponse copyWith(void Function(ModelsResponse) updates) =>
      super.copyWith((message) => updates(message as ModelsResponse))
          as ModelsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ModelsResponse create() => ModelsResponse._();
  @$core.override
  ModelsResponse createEmptyInstance() => create();
  static $pb.PbList<ModelsResponse> createRepeated() =>
      $pb.PbList<ModelsResponse>();
  @$core.pragma('dart2js:noInline')
  static ModelsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ModelsResponse>(create);
  static ModelsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbList<ModelInfo> get models => $_getList(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Model info response
class ModelInfoResponse extends $pb.GeneratedMessage {
  factory ModelInfoResponse({
    $core.bool? success,
    ModelDetails? details,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (details != null) result.details = details;
    if (error != null) result.error = error;
    return result;
  }

  ModelInfoResponse._();

  factory ModelInfoResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ModelInfoResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ModelInfoResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOM<ModelDetails>(2, _omitFieldNames ? '' : 'details',
        subBuilder: ModelDetails.create)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelInfoResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelInfoResponse copyWith(void Function(ModelInfoResponse) updates) =>
      super.copyWith((message) => updates(message as ModelInfoResponse))
          as ModelInfoResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ModelInfoResponse create() => ModelInfoResponse._();
  @$core.override
  ModelInfoResponse createEmptyInstance() => create();
  static $pb.PbList<ModelInfoResponse> createRepeated() =>
      $pb.PbList<ModelInfoResponse>();
  @$core.pragma('dart2js:noInline')
  static ModelInfoResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ModelInfoResponse>(create);
  static ModelInfoResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  ModelDetails get details => $_getN(1);
  @$pb.TagNumber(2)
  set details(ModelDetails value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasDetails() => $_has(1);
  @$pb.TagNumber(2)
  void clearDetails() => $_clearField(2);
  @$pb.TagNumber(2)
  ModelDetails ensureDetails() => $_ensure(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Embeddings response
class EmbeddingsResponse extends $pb.GeneratedMessage {
  factory EmbeddingsResponse({
    $core.bool? success,
    $core.Iterable<$core.double>? embedding,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (embedding != null) result.embedding.addAll(embedding);
    if (error != null) result.error = error;
    return result;
  }

  EmbeddingsResponse._();

  factory EmbeddingsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EmbeddingsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EmbeddingsResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..p<$core.double>(2, _omitFieldNames ? '' : 'embedding', $pb.PbFieldType.KD)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EmbeddingsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EmbeddingsResponse copyWith(void Function(EmbeddingsResponse) updates) =>
      super.copyWith((message) => updates(message as EmbeddingsResponse))
          as EmbeddingsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EmbeddingsResponse create() => EmbeddingsResponse._();
  @$core.override
  EmbeddingsResponse createEmptyInstance() => create();
  static $pb.PbList<EmbeddingsResponse> createRepeated() =>
      $pb.PbList<EmbeddingsResponse>();
  @$core.pragma('dart2js:noInline')
  static EmbeddingsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EmbeddingsResponse>(create);
  static EmbeddingsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbList<$core.double> get embedding => $_getList(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// NER response
class NerResponse extends $pb.GeneratedMessage {
  factory NerResponse({
    $core.bool? success,
    $core.Iterable<$core.MapEntry<$core.String, EntityList>>? entities,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (entities != null) result.entities.addEntries(entities);
    if (error != null) result.error = error;
    return result;
  }

  NerResponse._();

  factory NerResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory NerResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'NerResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..m<$core.String, EntityList>(2, _omitFieldNames ? '' : 'entities',
        entryClassName: 'NerResponse.EntitiesEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OM,
        valueCreator: EntityList.create,
        valueDefaultOrMaker: EntityList.getDefault,
        packageName: const $pb.PackageName('aico.modelservice'))
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  NerResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  NerResponse copyWith(void Function(NerResponse) updates) =>
      super.copyWith((message) => updates(message as NerResponse))
          as NerResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static NerResponse create() => NerResponse._();
  @$core.override
  NerResponse createEmptyInstance() => create();
  static $pb.PbList<NerResponse> createRepeated() => $pb.PbList<NerResponse>();
  @$core.pragma('dart2js:noInline')
  static NerResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<NerResponse>(create);
  static NerResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbMap<$core.String, EntityList> get entities => $_getMap(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

class EntityList extends $pb.GeneratedMessage {
  factory EntityList({
    $core.Iterable<EntityWithConfidence>? entities,
  }) {
    final result = create();
    if (entities != null) result.entities.addAll(entities);
    return result;
  }

  EntityList._();

  factory EntityList.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EntityList.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EntityList',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..pPM<EntityWithConfidence>(1, _omitFieldNames ? '' : 'entities',
        subBuilder: EntityWithConfidence.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EntityList clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EntityList copyWith(void Function(EntityList) updates) =>
      super.copyWith((message) => updates(message as EntityList)) as EntityList;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EntityList create() => EntityList._();
  @$core.override
  EntityList createEmptyInstance() => create();
  static $pb.PbList<EntityList> createRepeated() => $pb.PbList<EntityList>();
  @$core.pragma('dart2js:noInline')
  static EntityList getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EntityList>(create);
  static EntityList? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<EntityWithConfidence> get entities => $_getList(0);
}

class EntityWithConfidence extends $pb.GeneratedMessage {
  factory EntityWithConfidence({
    $core.String? text,
    $core.double? confidence,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (confidence != null) result.confidence = confidence;
    return result;
  }

  EntityWithConfidence._();

  factory EntityWithConfidence.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EntityWithConfidence.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EntityWithConfidence',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..aD(2, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EntityWithConfidence clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EntityWithConfidence copyWith(void Function(EntityWithConfidence) updates) =>
      super.copyWith((message) => updates(message as EntityWithConfidence))
          as EntityWithConfidence;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EntityWithConfidence create() => EntityWithConfidence._();
  @$core.override
  EntityWithConfidence createEmptyInstance() => create();
  static $pb.PbList<EntityWithConfidence> createRepeated() =>
      $pb.PbList<EntityWithConfidence>();
  @$core.pragma('dart2js:noInline')
  static EntityWithConfidence getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EntityWithConfidence>(create);
  static EntityWithConfidence? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.double get confidence => $_getN(1);
  @$pb.TagNumber(2)
  set confidence($core.double value) => $_setFloat(1, value);
  @$pb.TagNumber(2)
  $core.bool hasConfidence() => $_has(1);
  @$pb.TagNumber(2)
  void clearConfidence() => $_clearField(2);
}

/// Intent classification response
class IntentClassificationResponse extends $pb.GeneratedMessage {
  factory IntentClassificationResponse({
    $core.bool? success,
    $core.String? predictedIntent,
    $core.double? confidence,
    $core.String? detectedLanguage,
    $core.double? inferenceTimeMs,
    $core.Iterable<IntentPrediction>? alternativePredictions,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (predictedIntent != null) result.predictedIntent = predictedIntent;
    if (confidence != null) result.confidence = confidence;
    if (detectedLanguage != null) result.detectedLanguage = detectedLanguage;
    if (inferenceTimeMs != null) result.inferenceTimeMs = inferenceTimeMs;
    if (alternativePredictions != null)
      result.alternativePredictions.addAll(alternativePredictions);
    if (metadata != null) result.metadata.addEntries(metadata);
    if (error != null) result.error = error;
    return result;
  }

  IntentClassificationResponse._();

  factory IntentClassificationResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory IntentClassificationResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'IntentClassificationResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'predictedIntent')
    ..aD(3, _omitFieldNames ? '' : 'confidence')
    ..aOS(4, _omitFieldNames ? '' : 'detectedLanguage')
    ..aD(5, _omitFieldNames ? '' : 'inferenceTimeMs')
    ..pPM<IntentPrediction>(6, _omitFieldNames ? '' : 'alternativePredictions',
        subBuilder: IntentPrediction.create)
    ..m<$core.String, $core.String>(7, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'IntentClassificationResponse.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('aico.modelservice'))
    ..aOS(8, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  IntentClassificationResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  IntentClassificationResponse copyWith(
          void Function(IntentClassificationResponse) updates) =>
      super.copyWith(
              (message) => updates(message as IntentClassificationResponse))
          as IntentClassificationResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static IntentClassificationResponse create() =>
      IntentClassificationResponse._();
  @$core.override
  IntentClassificationResponse createEmptyInstance() => create();
  static $pb.PbList<IntentClassificationResponse> createRepeated() =>
      $pb.PbList<IntentClassificationResponse>();
  @$core.pragma('dart2js:noInline')
  static IntentClassificationResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<IntentClassificationResponse>(create);
  static IntentClassificationResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get predictedIntent => $_getSZ(1);
  @$pb.TagNumber(2)
  set predictedIntent($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasPredictedIntent() => $_has(1);
  @$pb.TagNumber(2)
  void clearPredictedIntent() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.double get confidence => $_getN(2);
  @$pb.TagNumber(3)
  set confidence($core.double value) => $_setDouble(2, value);
  @$pb.TagNumber(3)
  $core.bool hasConfidence() => $_has(2);
  @$pb.TagNumber(3)
  void clearConfidence() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get detectedLanguage => $_getSZ(3);
  @$pb.TagNumber(4)
  set detectedLanguage($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasDetectedLanguage() => $_has(3);
  @$pb.TagNumber(4)
  void clearDetectedLanguage() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.double get inferenceTimeMs => $_getN(4);
  @$pb.TagNumber(5)
  set inferenceTimeMs($core.double value) => $_setDouble(4, value);
  @$pb.TagNumber(5)
  $core.bool hasInferenceTimeMs() => $_has(4);
  @$pb.TagNumber(5)
  void clearInferenceTimeMs() => $_clearField(5);

  @$pb.TagNumber(6)
  $pb.PbList<IntentPrediction> get alternativePredictions => $_getList(5);

  @$pb.TagNumber(7)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(6);

  @$pb.TagNumber(8)
  $core.String get error => $_getSZ(7);
  @$pb.TagNumber(8)
  set error($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasError() => $_has(7);
  @$pb.TagNumber(8)
  void clearError() => $_clearField(8);
}

class IntentPrediction extends $pb.GeneratedMessage {
  factory IntentPrediction({
    $core.String? intent,
    $core.double? confidence,
  }) {
    final result = create();
    if (intent != null) result.intent = intent;
    if (confidence != null) result.confidence = confidence;
    return result;
  }

  IntentPrediction._();

  factory IntentPrediction.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory IntentPrediction.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'IntentPrediction',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'intent')
    ..aD(2, _omitFieldNames ? '' : 'confidence')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  IntentPrediction clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  IntentPrediction copyWith(void Function(IntentPrediction) updates) =>
      super.copyWith((message) => updates(message as IntentPrediction))
          as IntentPrediction;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static IntentPrediction create() => IntentPrediction._();
  @$core.override
  IntentPrediction createEmptyInstance() => create();
  static $pb.PbList<IntentPrediction> createRepeated() =>
      $pb.PbList<IntentPrediction>();
  @$core.pragma('dart2js:noInline')
  static IntentPrediction getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<IntentPrediction>(create);
  static IntentPrediction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get intent => $_getSZ(0);
  @$pb.TagNumber(1)
  set intent($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasIntent() => $_has(0);
  @$pb.TagNumber(1)
  void clearIntent() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.double get confidence => $_getN(1);
  @$pb.TagNumber(2)
  set confidence($core.double value) => $_setDouble(1, value);
  @$pb.TagNumber(2)
  $core.bool hasConfidence() => $_has(1);
  @$pb.TagNumber(2)
  void clearConfidence() => $_clearField(2);
}

/// Sentiment analysis response
class SentimentResponse extends $pb.GeneratedMessage {
  factory SentimentResponse({
    $core.bool? success,
    $core.String? sentiment,
    $core.double? confidence,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (sentiment != null) result.sentiment = sentiment;
    if (confidence != null) result.confidence = confidence;
    if (error != null) result.error = error;
    return result;
  }

  SentimentResponse._();

  factory SentimentResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory SentimentResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SentimentResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'sentiment')
    ..aD(3, _omitFieldNames ? '' : 'confidence')
    ..aOS(4, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SentimentResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SentimentResponse copyWith(void Function(SentimentResponse) updates) =>
      super.copyWith((message) => updates(message as SentimentResponse))
          as SentimentResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SentimentResponse create() => SentimentResponse._();
  @$core.override
  SentimentResponse createEmptyInstance() => create();
  static $pb.PbList<SentimentResponse> createRepeated() =>
      $pb.PbList<SentimentResponse>();
  @$core.pragma('dart2js:noInline')
  static SentimentResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SentimentResponse>(create);
  static SentimentResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get sentiment => $_getSZ(1);
  @$pb.TagNumber(2)
  set sentiment($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSentiment() => $_has(1);
  @$pb.TagNumber(2)
  void clearSentiment() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.double get confidence => $_getN(2);
  @$pb.TagNumber(3)
  set confidence($core.double value) => $_setDouble(2, value);
  @$pb.TagNumber(3)
  $core.bool hasConfidence() => $_has(2);
  @$pb.TagNumber(3)
  void clearConfidence() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get error => $_getSZ(3);
  @$pb.TagNumber(4)
  set error($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasError() => $_has(3);
  @$pb.TagNumber(4)
  void clearError() => $_clearField(4);
}

/// Service status response
class StatusResponse extends $pb.GeneratedMessage {
  factory StatusResponse({
    $core.bool? success,
    ServiceStatus? status,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (status != null) result.status = status;
    if (error != null) result.error = error;
    return result;
  }

  StatusResponse._();

  factory StatusResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory StatusResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'StatusResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOM<ServiceStatus>(2, _omitFieldNames ? '' : 'status',
        subBuilder: ServiceStatus.create)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StatusResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  StatusResponse copyWith(void Function(StatusResponse) updates) =>
      super.copyWith((message) => updates(message as StatusResponse))
          as StatusResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static StatusResponse create() => StatusResponse._();
  @$core.override
  StatusResponse createEmptyInstance() => create();
  static $pb.PbList<StatusResponse> createRepeated() =>
      $pb.PbList<StatusResponse>();
  @$core.pragma('dart2js:noInline')
  static StatusResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<StatusResponse>(create);
  static StatusResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  ServiceStatus get status => $_getN(1);
  @$pb.TagNumber(2)
  set status(ServiceStatus value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasStatus() => $_has(1);
  @$pb.TagNumber(2)
  void clearStatus() => $_clearField(2);
  @$pb.TagNumber(2)
  ServiceStatus ensureStatus() => $_ensure(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Ollama management responses
class OllamaStatusResponse extends $pb.GeneratedMessage {
  factory OllamaStatusResponse({
    $core.bool? success,
    OllamaStatus? status,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (status != null) result.status = status;
    if (error != null) result.error = error;
    return result;
  }

  OllamaStatusResponse._();

  factory OllamaStatusResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaStatusResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaStatusResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOM<OllamaStatus>(2, _omitFieldNames ? '' : 'status',
        subBuilder: OllamaStatus.create)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaStatusResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaStatusResponse copyWith(void Function(OllamaStatusResponse) updates) =>
      super.copyWith((message) => updates(message as OllamaStatusResponse))
          as OllamaStatusResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaStatusResponse create() => OllamaStatusResponse._();
  @$core.override
  OllamaStatusResponse createEmptyInstance() => create();
  static $pb.PbList<OllamaStatusResponse> createRepeated() =>
      $pb.PbList<OllamaStatusResponse>();
  @$core.pragma('dart2js:noInline')
  static OllamaStatusResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaStatusResponse>(create);
  static OllamaStatusResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  OllamaStatus get status => $_getN(1);
  @$pb.TagNumber(2)
  set status(OllamaStatus value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasStatus() => $_has(1);
  @$pb.TagNumber(2)
  void clearStatus() => $_clearField(2);
  @$pb.TagNumber(2)
  OllamaStatus ensureStatus() => $_ensure(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

class OllamaModelsResponse extends $pb.GeneratedMessage {
  factory OllamaModelsResponse({
    $core.bool? success,
    $core.Iterable<ModelInfo>? models,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (models != null) result.models.addAll(models);
    if (error != null) result.error = error;
    return result;
  }

  OllamaModelsResponse._();

  factory OllamaModelsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaModelsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaModelsResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..pPM<ModelInfo>(2, _omitFieldNames ? '' : 'models',
        subBuilder: ModelInfo.create)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaModelsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaModelsResponse copyWith(void Function(OllamaModelsResponse) updates) =>
      super.copyWith((message) => updates(message as OllamaModelsResponse))
          as OllamaModelsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaModelsResponse create() => OllamaModelsResponse._();
  @$core.override
  OllamaModelsResponse createEmptyInstance() => create();
  static $pb.PbList<OllamaModelsResponse> createRepeated() =>
      $pb.PbList<OllamaModelsResponse>();
  @$core.pragma('dart2js:noInline')
  static OllamaModelsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaModelsResponse>(create);
  static OllamaModelsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbList<ModelInfo> get models => $_getList(1);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

class OllamaPullResponse extends $pb.GeneratedMessage {
  factory OllamaPullResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (message != null) result.message = message;
    if (error != null) result.error = error;
    return result;
  }

  OllamaPullResponse._();

  factory OllamaPullResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaPullResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaPullResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaPullResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaPullResponse copyWith(void Function(OllamaPullResponse) updates) =>
      super.copyWith((message) => updates(message as OllamaPullResponse))
          as OllamaPullResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaPullResponse create() => OllamaPullResponse._();
  @$core.override
  OllamaPullResponse createEmptyInstance() => create();
  static $pb.PbList<OllamaPullResponse> createRepeated() =>
      $pb.PbList<OllamaPullResponse>();
  @$core.pragma('dart2js:noInline')
  static OllamaPullResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaPullResponse>(create);
  static OllamaPullResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

class OllamaRemoveResponse extends $pb.GeneratedMessage {
  factory OllamaRemoveResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (message != null) result.message = message;
    if (error != null) result.error = error;
    return result;
  }

  OllamaRemoveResponse._();

  factory OllamaRemoveResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaRemoveResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaRemoveResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaRemoveResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaRemoveResponse copyWith(void Function(OllamaRemoveResponse) updates) =>
      super.copyWith((message) => updates(message as OllamaRemoveResponse))
          as OllamaRemoveResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaRemoveResponse create() => OllamaRemoveResponse._();
  @$core.override
  OllamaRemoveResponse createEmptyInstance() => create();
  static $pb.PbList<OllamaRemoveResponse> createRepeated() =>
      $pb.PbList<OllamaRemoveResponse>();
  @$core.pragma('dart2js:noInline')
  static OllamaRemoveResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaRemoveResponse>(create);
  static OllamaRemoveResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

class OllamaServeResponse extends $pb.GeneratedMessage {
  factory OllamaServeResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (message != null) result.message = message;
    if (error != null) result.error = error;
    return result;
  }

  OllamaServeResponse._();

  factory OllamaServeResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaServeResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaServeResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaServeResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaServeResponse copyWith(void Function(OllamaServeResponse) updates) =>
      super.copyWith((message) => updates(message as OllamaServeResponse))
          as OllamaServeResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaServeResponse create() => OllamaServeResponse._();
  @$core.override
  OllamaServeResponse createEmptyInstance() => create();
  static $pb.PbList<OllamaServeResponse> createRepeated() =>
      $pb.PbList<OllamaServeResponse>();
  @$core.pragma('dart2js:noInline')
  static OllamaServeResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaServeResponse>(create);
  static OllamaServeResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

class OllamaShutdownResponse extends $pb.GeneratedMessage {
  factory OllamaShutdownResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? error,
  }) {
    final result = create();
    if (success != null) result.success = success;
    if (message != null) result.message = message;
    if (error != null) result.error = error;
    return result;
  }

  OllamaShutdownResponse._();

  factory OllamaShutdownResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaShutdownResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaShutdownResponse',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaShutdownResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaShutdownResponse copyWith(
          void Function(OllamaShutdownResponse) updates) =>
      super.copyWith((message) => updates(message as OllamaShutdownResponse))
          as OllamaShutdownResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaShutdownResponse create() => OllamaShutdownResponse._();
  @$core.override
  OllamaShutdownResponse createEmptyInstance() => create();
  static $pb.PbList<OllamaShutdownResponse> createRepeated() =>
      $pb.PbList<OllamaShutdownResponse>();
  @$core.pragma('dart2js:noInline')
  static OllamaShutdownResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaShutdownResponse>(create);
  static OllamaShutdownResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Conversation message for completions
class ConversationMessage extends $pb.GeneratedMessage {
  factory ConversationMessage({
    $core.String? role,
    $core.String? content,
  }) {
    final result = create();
    if (role != null) result.role = role;
    if (content != null) result.content = content;
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
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'role')
    ..aOS(2, _omitFieldNames ? '' : 'content')
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
  $core.String get role => $_getSZ(0);
  @$pb.TagNumber(1)
  set role($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRole() => $_has(0);
  @$pb.TagNumber(1)
  void clearRole() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => $_clearField(2);
}

/// Completion result
class CompletionResult extends $pb.GeneratedMessage {
  factory CompletionResult({
    $core.String? model,
    $0.Timestamp? createdAt,
    ConversationMessage? message,
    $core.bool? done,
    $fixnum.Int64? totalDuration,
    $fixnum.Int64? loadDuration,
    $fixnum.Int64? promptEvalCount,
    $fixnum.Int64? promptEvalDuration,
    $fixnum.Int64? evalCount,
    $fixnum.Int64? evalDuration,
    $core.String? thinking,
  }) {
    final result = create();
    if (model != null) result.model = model;
    if (createdAt != null) result.createdAt = createdAt;
    if (message != null) result.message = message;
    if (done != null) result.done = done;
    if (totalDuration != null) result.totalDuration = totalDuration;
    if (loadDuration != null) result.loadDuration = loadDuration;
    if (promptEvalCount != null) result.promptEvalCount = promptEvalCount;
    if (promptEvalDuration != null)
      result.promptEvalDuration = promptEvalDuration;
    if (evalCount != null) result.evalCount = evalCount;
    if (evalDuration != null) result.evalDuration = evalDuration;
    if (thinking != null) result.thinking = thinking;
    return result;
  }

  CompletionResult._();

  factory CompletionResult.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CompletionResult.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CompletionResult',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..aOM<$0.Timestamp>(2, _omitFieldNames ? '' : 'createdAt',
        subBuilder: $0.Timestamp.create)
    ..aOM<ConversationMessage>(3, _omitFieldNames ? '' : 'message',
        subBuilder: ConversationMessage.create)
    ..aOB(4, _omitFieldNames ? '' : 'done')
    ..aInt64(5, _omitFieldNames ? '' : 'totalDuration')
    ..aInt64(6, _omitFieldNames ? '' : 'loadDuration')
    ..aInt64(7, _omitFieldNames ? '' : 'promptEvalCount')
    ..aInt64(8, _omitFieldNames ? '' : 'promptEvalDuration')
    ..aInt64(9, _omitFieldNames ? '' : 'evalCount')
    ..aInt64(10, _omitFieldNames ? '' : 'evalDuration')
    ..aOS(11, _omitFieldNames ? '' : 'thinking')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CompletionResult clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CompletionResult copyWith(void Function(CompletionResult) updates) =>
      super.copyWith((message) => updates(message as CompletionResult))
          as CompletionResult;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CompletionResult create() => CompletionResult._();
  @$core.override
  CompletionResult createEmptyInstance() => create();
  static $pb.PbList<CompletionResult> createRepeated() =>
      $pb.PbList<CompletionResult>();
  @$core.pragma('dart2js:noInline')
  static CompletionResult getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CompletionResult>(create);
  static CompletionResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);

  @$pb.TagNumber(2)
  $0.Timestamp get createdAt => $_getN(1);
  @$pb.TagNumber(2)
  set createdAt($0.Timestamp value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasCreatedAt() => $_has(1);
  @$pb.TagNumber(2)
  void clearCreatedAt() => $_clearField(2);
  @$pb.TagNumber(2)
  $0.Timestamp ensureCreatedAt() => $_ensure(1);

  @$pb.TagNumber(3)
  ConversationMessage get message => $_getN(2);
  @$pb.TagNumber(3)
  set message(ConversationMessage value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => $_clearField(3);
  @$pb.TagNumber(3)
  ConversationMessage ensureMessage() => $_ensure(2);

  @$pb.TagNumber(4)
  $core.bool get done => $_getBF(3);
  @$pb.TagNumber(4)
  set done($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasDone() => $_has(3);
  @$pb.TagNumber(4)
  void clearDone() => $_clearField(4);

  @$pb.TagNumber(5)
  $fixnum.Int64 get totalDuration => $_getI64(4);
  @$pb.TagNumber(5)
  set totalDuration($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasTotalDuration() => $_has(4);
  @$pb.TagNumber(5)
  void clearTotalDuration() => $_clearField(5);

  @$pb.TagNumber(6)
  $fixnum.Int64 get loadDuration => $_getI64(5);
  @$pb.TagNumber(6)
  set loadDuration($fixnum.Int64 value) => $_setInt64(5, value);
  @$pb.TagNumber(6)
  $core.bool hasLoadDuration() => $_has(5);
  @$pb.TagNumber(6)
  void clearLoadDuration() => $_clearField(6);

  @$pb.TagNumber(7)
  $fixnum.Int64 get promptEvalCount => $_getI64(6);
  @$pb.TagNumber(7)
  set promptEvalCount($fixnum.Int64 value) => $_setInt64(6, value);
  @$pb.TagNumber(7)
  $core.bool hasPromptEvalCount() => $_has(6);
  @$pb.TagNumber(7)
  void clearPromptEvalCount() => $_clearField(7);

  @$pb.TagNumber(8)
  $fixnum.Int64 get promptEvalDuration => $_getI64(7);
  @$pb.TagNumber(8)
  set promptEvalDuration($fixnum.Int64 value) => $_setInt64(7, value);
  @$pb.TagNumber(8)
  $core.bool hasPromptEvalDuration() => $_has(7);
  @$pb.TagNumber(8)
  void clearPromptEvalDuration() => $_clearField(8);

  @$pb.TagNumber(9)
  $fixnum.Int64 get evalCount => $_getI64(8);
  @$pb.TagNumber(9)
  set evalCount($fixnum.Int64 value) => $_setInt64(8, value);
  @$pb.TagNumber(9)
  $core.bool hasEvalCount() => $_has(8);
  @$pb.TagNumber(9)
  void clearEvalCount() => $_clearField(9);

  @$pb.TagNumber(10)
  $fixnum.Int64 get evalDuration => $_getI64(9);
  @$pb.TagNumber(10)
  set evalDuration($fixnum.Int64 value) => $_setInt64(9, value);
  @$pb.TagNumber(10)
  $core.bool hasEvalDuration() => $_has(9);
  @$pb.TagNumber(10)
  void clearEvalDuration() => $_clearField(10);

  @$pb.TagNumber(11)
  $core.String get thinking => $_getSZ(10);
  @$pb.TagNumber(11)
  set thinking($core.String value) => $_setString(10, value);
  @$pb.TagNumber(11)
  $core.bool hasThinking() => $_has(10);
  @$pb.TagNumber(11)
  void clearThinking() => $_clearField(11);
}

/// Model information
class ModelInfo extends $pb.GeneratedMessage {
  factory ModelInfo({
    $core.String? name,
    $core.String? model,
    $0.Timestamp? modifiedAt,
    $fixnum.Int64? size,
    $core.String? digest,
    ModelDetails? details,
  }) {
    final result = create();
    if (name != null) result.name = name;
    if (model != null) result.model = model;
    if (modifiedAt != null) result.modifiedAt = modifiedAt;
    if (size != null) result.size = size;
    if (digest != null) result.digest = digest;
    if (details != null) result.details = details;
    return result;
  }

  ModelInfo._();

  factory ModelInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ModelInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ModelInfo',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'name')
    ..aOS(2, _omitFieldNames ? '' : 'model')
    ..aOM<$0.Timestamp>(3, _omitFieldNames ? '' : 'modifiedAt',
        subBuilder: $0.Timestamp.create)
    ..aInt64(4, _omitFieldNames ? '' : 'size')
    ..aOS(5, _omitFieldNames ? '' : 'digest')
    ..aOM<ModelDetails>(6, _omitFieldNames ? '' : 'details',
        subBuilder: ModelDetails.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelInfo copyWith(void Function(ModelInfo) updates) =>
      super.copyWith((message) => updates(message as ModelInfo)) as ModelInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ModelInfo create() => ModelInfo._();
  @$core.override
  ModelInfo createEmptyInstance() => create();
  static $pb.PbList<ModelInfo> createRepeated() => $pb.PbList<ModelInfo>();
  @$core.pragma('dart2js:noInline')
  static ModelInfo getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ModelInfo>(create);
  static ModelInfo? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get name => $_getSZ(0);
  @$pb.TagNumber(1)
  set name($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasName() => $_has(0);
  @$pb.TagNumber(1)
  void clearName() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get model => $_getSZ(1);
  @$pb.TagNumber(2)
  set model($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasModel() => $_has(1);
  @$pb.TagNumber(2)
  void clearModel() => $_clearField(2);

  @$pb.TagNumber(3)
  $0.Timestamp get modifiedAt => $_getN(2);
  @$pb.TagNumber(3)
  set modifiedAt($0.Timestamp value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasModifiedAt() => $_has(2);
  @$pb.TagNumber(3)
  void clearModifiedAt() => $_clearField(3);
  @$pb.TagNumber(3)
  $0.Timestamp ensureModifiedAt() => $_ensure(2);

  @$pb.TagNumber(4)
  $fixnum.Int64 get size => $_getI64(3);
  @$pb.TagNumber(4)
  set size($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSize() => $_has(3);
  @$pb.TagNumber(4)
  void clearSize() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get digest => $_getSZ(4);
  @$pb.TagNumber(5)
  set digest($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasDigest() => $_has(4);
  @$pb.TagNumber(5)
  void clearDigest() => $_clearField(5);

  @$pb.TagNumber(6)
  ModelDetails get details => $_getN(5);
  @$pb.TagNumber(6)
  set details(ModelDetails value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasDetails() => $_has(5);
  @$pb.TagNumber(6)
  void clearDetails() => $_clearField(6);
  @$pb.TagNumber(6)
  ModelDetails ensureDetails() => $_ensure(5);
}

/// Detailed model information
class ModelDetails extends $pb.GeneratedMessage {
  factory ModelDetails({
    $core.String? parentModel,
    $core.String? format,
    $core.String? family,
    $core.Iterable<$core.String>? families,
    $fixnum.Int64? parameterSize,
    $fixnum.Int64? quantizationLevel,
  }) {
    final result = create();
    if (parentModel != null) result.parentModel = parentModel;
    if (format != null) result.format = format;
    if (family != null) result.family = family;
    if (families != null) result.families.addAll(families);
    if (parameterSize != null) result.parameterSize = parameterSize;
    if (quantizationLevel != null) result.quantizationLevel = quantizationLevel;
    return result;
  }

  ModelDetails._();

  factory ModelDetails.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ModelDetails.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ModelDetails',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'parentModel')
    ..aOS(2, _omitFieldNames ? '' : 'format')
    ..aOS(3, _omitFieldNames ? '' : 'family')
    ..pPS(4, _omitFieldNames ? '' : 'families')
    ..aInt64(5, _omitFieldNames ? '' : 'parameterSize')
    ..aInt64(6, _omitFieldNames ? '' : 'quantizationLevel')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelDetails clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ModelDetails copyWith(void Function(ModelDetails) updates) =>
      super.copyWith((message) => updates(message as ModelDetails))
          as ModelDetails;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ModelDetails create() => ModelDetails._();
  @$core.override
  ModelDetails createEmptyInstance() => create();
  static $pb.PbList<ModelDetails> createRepeated() =>
      $pb.PbList<ModelDetails>();
  @$core.pragma('dart2js:noInline')
  static ModelDetails getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ModelDetails>(create);
  static ModelDetails? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get parentModel => $_getSZ(0);
  @$pb.TagNumber(1)
  set parentModel($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasParentModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearParentModel() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get format => $_getSZ(1);
  @$pb.TagNumber(2)
  set format($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasFormat() => $_has(1);
  @$pb.TagNumber(2)
  void clearFormat() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get family => $_getSZ(2);
  @$pb.TagNumber(3)
  set family($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFamily() => $_has(2);
  @$pb.TagNumber(3)
  void clearFamily() => $_clearField(3);

  @$pb.TagNumber(4)
  $pb.PbList<$core.String> get families => $_getList(3);

  @$pb.TagNumber(5)
  $fixnum.Int64 get parameterSize => $_getI64(4);
  @$pb.TagNumber(5)
  set parameterSize($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasParameterSize() => $_has(4);
  @$pb.TagNumber(5)
  void clearParameterSize() => $_clearField(5);

  @$pb.TagNumber(6)
  $fixnum.Int64 get quantizationLevel => $_getI64(5);
  @$pb.TagNumber(6)
  set quantizationLevel($fixnum.Int64 value) => $_setInt64(5, value);
  @$pb.TagNumber(6)
  $core.bool hasQuantizationLevel() => $_has(5);
  @$pb.TagNumber(6)
  void clearQuantizationLevel() => $_clearField(6);
}

/// Service status information
class ServiceStatus extends $pb.GeneratedMessage {
  factory ServiceStatus({
    $core.String? version,
    $core.bool? ollamaRunning,
    $core.String? ollamaVersion,
    $core.int? loadedModelsCount,
    $core.Iterable<$core.String>? loadedModels,
  }) {
    final result = create();
    if (version != null) result.version = version;
    if (ollamaRunning != null) result.ollamaRunning = ollamaRunning;
    if (ollamaVersion != null) result.ollamaVersion = ollamaVersion;
    if (loadedModelsCount != null) result.loadedModelsCount = loadedModelsCount;
    if (loadedModels != null) result.loadedModels.addAll(loadedModels);
    return result;
  }

  ServiceStatus._();

  factory ServiceStatus.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ServiceStatus.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ServiceStatus',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..aOB(2, _omitFieldNames ? '' : 'ollamaRunning')
    ..aOS(3, _omitFieldNames ? '' : 'ollamaVersion')
    ..aI(4, _omitFieldNames ? '' : 'loadedModelsCount')
    ..pPS(5, _omitFieldNames ? '' : 'loadedModels')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ServiceStatus clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ServiceStatus copyWith(void Function(ServiceStatus) updates) =>
      super.copyWith((message) => updates(message as ServiceStatus))
          as ServiceStatus;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ServiceStatus create() => ServiceStatus._();
  @$core.override
  ServiceStatus createEmptyInstance() => create();
  static $pb.PbList<ServiceStatus> createRepeated() =>
      $pb.PbList<ServiceStatus>();
  @$core.pragma('dart2js:noInline')
  static ServiceStatus getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ServiceStatus>(create);
  static ServiceStatus? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.bool get ollamaRunning => $_getBF(1);
  @$pb.TagNumber(2)
  set ollamaRunning($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasOllamaRunning() => $_has(1);
  @$pb.TagNumber(2)
  void clearOllamaRunning() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get ollamaVersion => $_getSZ(2);
  @$pb.TagNumber(3)
  set ollamaVersion($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasOllamaVersion() => $_has(2);
  @$pb.TagNumber(3)
  void clearOllamaVersion() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get loadedModelsCount => $_getIZ(3);
  @$pb.TagNumber(4)
  set loadedModelsCount($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasLoadedModelsCount() => $_has(3);
  @$pb.TagNumber(4)
  void clearLoadedModelsCount() => $_clearField(4);

  @$pb.TagNumber(5)
  $pb.PbList<$core.String> get loadedModels => $_getList(4);
}

/// Ollama status information
class OllamaStatus extends $pb.GeneratedMessage {
  factory OllamaStatus({
    $core.bool? running,
    $core.String? version,
    $core.String? host,
    $core.int? port,
    $core.Iterable<$core.String>? loadedModels,
  }) {
    final result = create();
    if (running != null) result.running = running;
    if (version != null) result.version = version;
    if (host != null) result.host = host;
    if (port != null) result.port = port;
    if (loadedModels != null) result.loadedModels.addAll(loadedModels);
    return result;
  }

  OllamaStatus._();

  factory OllamaStatus.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory OllamaStatus.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OllamaStatus',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'aico.modelservice'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'running')
    ..aOS(2, _omitFieldNames ? '' : 'version')
    ..aOS(3, _omitFieldNames ? '' : 'host')
    ..aI(4, _omitFieldNames ? '' : 'port')
    ..pPS(5, _omitFieldNames ? '' : 'loadedModels')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaStatus clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OllamaStatus copyWith(void Function(OllamaStatus) updates) =>
      super.copyWith((message) => updates(message as OllamaStatus))
          as OllamaStatus;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static OllamaStatus create() => OllamaStatus._();
  @$core.override
  OllamaStatus createEmptyInstance() => create();
  static $pb.PbList<OllamaStatus> createRepeated() =>
      $pb.PbList<OllamaStatus>();
  @$core.pragma('dart2js:noInline')
  static OllamaStatus getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OllamaStatus>(create);
  static OllamaStatus? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get running => $_getBF(0);
  @$pb.TagNumber(1)
  set running($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRunning() => $_has(0);
  @$pb.TagNumber(1)
  void clearRunning() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get version => $_getSZ(1);
  @$pb.TagNumber(2)
  set version($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasVersion() => $_has(1);
  @$pb.TagNumber(2)
  void clearVersion() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get host => $_getSZ(2);
  @$pb.TagNumber(3)
  set host($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasHost() => $_has(2);
  @$pb.TagNumber(3)
  void clearHost() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get port => $_getIZ(3);
  @$pb.TagNumber(4)
  set port($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasPort() => $_has(3);
  @$pb.TagNumber(4)
  void clearPort() => $_clearField(4);

  @$pb.TagNumber(5)
  $pb.PbList<$core.String> get loadedModels => $_getList(4);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
