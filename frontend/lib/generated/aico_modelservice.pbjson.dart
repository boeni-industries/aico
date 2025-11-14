// This is a generated file - do not edit.
//
// Generated from aico_modelservice.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use healthRequestDescriptor instead')
const HealthRequest$json = {
  '1': 'HealthRequest',
};

/// Descriptor for `HealthRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List healthRequestDescriptor =
    $convert.base64Decode('Cg1IZWFsdGhSZXF1ZXN0');

@$core.Deprecated('Use completionsRequestDescriptor instead')
const CompletionsRequest$json = {
  '1': 'CompletionsRequest',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
    {
      '1': 'messages',
      '3': 2,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.ConversationMessage',
      '10': 'messages'
    },
    {'1': 'stream', '3': 3, '4': 1, '5': 8, '10': 'stream'},
    {
      '1': 'temperature',
      '3': 4,
      '4': 1,
      '5': 1,
      '9': 0,
      '10': 'temperature',
      '17': true
    },
    {
      '1': 'max_tokens',
      '3': 5,
      '4': 1,
      '5': 5,
      '9': 1,
      '10': 'maxTokens',
      '17': true
    },
    {'1': 'top_p', '3': 6, '4': 1, '5': 1, '9': 2, '10': 'topP', '17': true},
    {'1': 'system', '3': 7, '4': 1, '5': 9, '9': 3, '10': 'system', '17': true},
  ],
  '8': [
    {'1': '_temperature'},
    {'1': '_max_tokens'},
    {'1': '_top_p'},
    {'1': '_system'},
  ],
};

/// Descriptor for `CompletionsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List completionsRequestDescriptor = $convert.base64Decode(
    'ChJDb21wbGV0aW9uc1JlcXVlc3QSFAoFbW9kZWwYASABKAlSBW1vZGVsEkIKCG1lc3NhZ2VzGA'
    'IgAygLMiYuYWljby5tb2RlbHNlcnZpY2UuQ29udmVyc2F0aW9uTWVzc2FnZVIIbWVzc2FnZXMS'
    'FgoGc3RyZWFtGAMgASgIUgZzdHJlYW0SJQoLdGVtcGVyYXR1cmUYBCABKAFIAFILdGVtcGVyYX'
    'R1cmWIAQESIgoKbWF4X3Rva2VucxgFIAEoBUgBUgltYXhUb2tlbnOIAQESGAoFdG9wX3AYBiAB'
    'KAFIAlIEdG9wUIgBARIbCgZzeXN0ZW0YByABKAlIA1IGc3lzdGVtiAEBQg4KDF90ZW1wZXJhdH'
    'VyZUINCgtfbWF4X3Rva2Vuc0IICgZfdG9wX3BCCQoHX3N5c3RlbQ==');

@$core.Deprecated('Use streamingChunkDescriptor instead')
const StreamingChunk$json = {
  '1': 'StreamingChunk',
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
    {'1': 'model', '3': 5, '4': 1, '5': 9, '10': 'model'},
    {
      '1': 'timestamp',
      '3': 6,
      '4': 1,
      '5': 3,
      '9': 0,
      '10': 'timestamp',
      '17': true
    },
    {'1': 'content_type', '3': 7, '4': 1, '5': 9, '10': 'contentType'},
  ],
  '8': [
    {'1': '_timestamp'},
  ],
};

/// Descriptor for `StreamingChunk`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List streamingChunkDescriptor = $convert.base64Decode(
    'Cg5TdHJlYW1pbmdDaHVuaxIdCgpyZXF1ZXN0X2lkGAEgASgJUglyZXF1ZXN0SWQSGAoHY29udG'
    'VudBgCIAEoCVIHY29udGVudBIvChNhY2N1bXVsYXRlZF9jb250ZW50GAMgASgJUhJhY2N1bXVs'
    'YXRlZENvbnRlbnQSEgoEZG9uZRgEIAEoCFIEZG9uZRIUCgVtb2RlbBgFIAEoCVIFbW9kZWwSIQ'
    'oJdGltZXN0YW1wGAYgASgDSABSCXRpbWVzdGFtcIgBARIhCgxjb250ZW50X3R5cGUYByABKAlS'
    'C2NvbnRlbnRUeXBlQgwKCl90aW1lc3RhbXA=');

@$core.Deprecated('Use modelsRequestDescriptor instead')
const ModelsRequest$json = {
  '1': 'ModelsRequest',
};

/// Descriptor for `ModelsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List modelsRequestDescriptor =
    $convert.base64Decode('Cg1Nb2RlbHNSZXF1ZXN0');

@$core.Deprecated('Use modelInfoRequestDescriptor instead')
const ModelInfoRequest$json = {
  '1': 'ModelInfoRequest',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
  ],
};

/// Descriptor for `ModelInfoRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List modelInfoRequestDescriptor = $convert
    .base64Decode('ChBNb2RlbEluZm9SZXF1ZXN0EhQKBW1vZGVsGAEgASgJUgVtb2RlbA==');

@$core.Deprecated('Use embeddingsRequestDescriptor instead')
const EmbeddingsRequest$json = {
  '1': 'EmbeddingsRequest',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
    {'1': 'prompt', '3': 2, '4': 1, '5': 9, '10': 'prompt'},
  ],
};

/// Descriptor for `EmbeddingsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List embeddingsRequestDescriptor = $convert.base64Decode(
    'ChFFbWJlZGRpbmdzUmVxdWVzdBIUCgVtb2RlbBgBIAEoCVIFbW9kZWwSFgoGcHJvbXB0GAIgAS'
    'gJUgZwcm9tcHQ=');

@$core.Deprecated('Use nerRequestDescriptor instead')
const NerRequest$json = {
  '1': 'NerRequest',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {'1': 'entity_types', '3': 2, '4': 3, '5': 9, '10': 'entityTypes'},
  ],
};

/// Descriptor for `NerRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List nerRequestDescriptor = $convert.base64Decode(
    'CgpOZXJSZXF1ZXN0EhIKBHRleHQYASABKAlSBHRleHQSIQoMZW50aXR5X3R5cGVzGAIgAygJUg'
    'tlbnRpdHlUeXBlcw==');

@$core.Deprecated('Use intentClassificationRequestDescriptor instead')
const IntentClassificationRequest$json = {
  '1': 'IntentClassificationRequest',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {'1': 'model', '3': 2, '4': 1, '5': 9, '9': 0, '10': 'model', '17': true},
  ],
  '8': [
    {'1': '_model'},
  ],
};

/// Descriptor for `IntentClassificationRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List intentClassificationRequestDescriptor =
    $convert.base64Decode(
        'ChtJbnRlbnRDbGFzc2lmaWNhdGlvblJlcXVlc3QSEgoEdGV4dBgBIAEoCVIEdGV4dBIZCgVtb2'
        'RlbBgCIAEoCUgAUgVtb2RlbIgBAUIICgZfbW9kZWw=');

@$core.Deprecated('Use sentimentRequestDescriptor instead')
const SentimentRequest$json = {
  '1': 'SentimentRequest',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
  ],
};

/// Descriptor for `SentimentRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List sentimentRequestDescriptor = $convert
    .base64Decode('ChBTZW50aW1lbnRSZXF1ZXN0EhIKBHRleHQYASABKAlSBHRleHQ=');

@$core.Deprecated('Use statusRequestDescriptor instead')
const StatusRequest$json = {
  '1': 'StatusRequest',
};

/// Descriptor for `StatusRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List statusRequestDescriptor =
    $convert.base64Decode('Cg1TdGF0dXNSZXF1ZXN0');

@$core.Deprecated('Use ollamaStatusRequestDescriptor instead')
const OllamaStatusRequest$json = {
  '1': 'OllamaStatusRequest',
};

/// Descriptor for `OllamaStatusRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaStatusRequestDescriptor =
    $convert.base64Decode('ChNPbGxhbWFTdGF0dXNSZXF1ZXN0');

@$core.Deprecated('Use ollamaModelsRequestDescriptor instead')
const OllamaModelsRequest$json = {
  '1': 'OllamaModelsRequest',
};

/// Descriptor for `OllamaModelsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaModelsRequestDescriptor =
    $convert.base64Decode('ChNPbGxhbWFNb2RlbHNSZXF1ZXN0');

@$core.Deprecated('Use ollamaPullRequestDescriptor instead')
const OllamaPullRequest$json = {
  '1': 'OllamaPullRequest',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
  ],
};

/// Descriptor for `OllamaPullRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaPullRequestDescriptor = $convert
    .base64Decode('ChFPbGxhbWFQdWxsUmVxdWVzdBIUCgVtb2RlbBgBIAEoCVIFbW9kZWw=');

@$core.Deprecated('Use ollamaRemoveRequestDescriptor instead')
const OllamaRemoveRequest$json = {
  '1': 'OllamaRemoveRequest',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
  ],
};

/// Descriptor for `OllamaRemoveRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaRemoveRequestDescriptor =
    $convert.base64Decode(
        'ChNPbGxhbWFSZW1vdmVSZXF1ZXN0EhQKBW1vZGVsGAEgASgJUgVtb2RlbA==');

@$core.Deprecated('Use ollamaServeRequestDescriptor instead')
const OllamaServeRequest$json = {
  '1': 'OllamaServeRequest',
};

/// Descriptor for `OllamaServeRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaServeRequestDescriptor =
    $convert.base64Decode('ChJPbGxhbWFTZXJ2ZVJlcXVlc3Q=');

@$core.Deprecated('Use ollamaShutdownRequestDescriptor instead')
const OllamaShutdownRequest$json = {
  '1': 'OllamaShutdownRequest',
};

/// Descriptor for `OllamaShutdownRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaShutdownRequestDescriptor =
    $convert.base64Decode('ChVPbGxhbWFTaHV0ZG93blJlcXVlc3Q=');

@$core.Deprecated('Use healthResponseDescriptor instead')
const HealthResponse$json = {
  '1': 'HealthResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'status', '3': 2, '4': 1, '5': 9, '10': 'status'},
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_error'},
  ],
};

/// Descriptor for `HealthResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List healthResponseDescriptor = $convert.base64Decode(
    'Cg5IZWFsdGhSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEhYKBnN0YXR1cxgCIA'
    'EoCVIGc3RhdHVzEhkKBWVycm9yGAMgASgJSABSBWVycm9yiAEBQggKBl9lcnJvcg==');

@$core.Deprecated('Use completionsResponseDescriptor instead')
const CompletionsResponse$json = {
  '1': 'CompletionsResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'result',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.CompletionResult',
      '9': 0,
      '10': 'result',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_result'},
    {'1': '_error'},
  ],
};

/// Descriptor for `CompletionsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List completionsResponseDescriptor = $convert.base64Decode(
    'ChNDb21wbGV0aW9uc1Jlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3MSQAoGcmVzdW'
    'x0GAIgASgLMiMuYWljby5tb2RlbHNlcnZpY2UuQ29tcGxldGlvblJlc3VsdEgAUgZyZXN1bHSI'
    'AQESGQoFZXJyb3IYAyABKAlIAVIFZXJyb3KIAQFCCQoHX3Jlc3VsdEIICgZfZXJyb3I=');

@$core.Deprecated('Use modelsResponseDescriptor instead')
const ModelsResponse$json = {
  '1': 'ModelsResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'models',
      '3': 2,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.ModelInfo',
      '10': 'models'
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_error'},
  ],
};

/// Descriptor for `ModelsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List modelsResponseDescriptor = $convert.base64Decode(
    'Cg5Nb2RlbHNSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEjQKBm1vZGVscxgCIA'
    'MoCzIcLmFpY28ubW9kZWxzZXJ2aWNlLk1vZGVsSW5mb1IGbW9kZWxzEhkKBWVycm9yGAMgASgJ'
    'SABSBWVycm9yiAEBQggKBl9lcnJvcg==');

@$core.Deprecated('Use modelInfoResponseDescriptor instead')
const ModelInfoResponse$json = {
  '1': 'ModelInfoResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'details',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.ModelDetails',
      '9': 0,
      '10': 'details',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_details'},
    {'1': '_error'},
  ],
};

/// Descriptor for `ModelInfoResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List modelInfoResponseDescriptor = $convert.base64Decode(
    'ChFNb2RlbEluZm9SZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEj4KB2RldGFpbH'
    'MYAiABKAsyHy5haWNvLm1vZGVsc2VydmljZS5Nb2RlbERldGFpbHNIAFIHZGV0YWlsc4gBARIZ'
    'CgVlcnJvchgDIAEoCUgBUgVlcnJvcogBAUIKCghfZGV0YWlsc0IICgZfZXJyb3I=');

@$core.Deprecated('Use embeddingsResponseDescriptor instead')
const EmbeddingsResponse$json = {
  '1': 'EmbeddingsResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'embedding', '3': 2, '4': 3, '5': 1, '10': 'embedding'},
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_error'},
  ],
};

/// Descriptor for `EmbeddingsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List embeddingsResponseDescriptor = $convert.base64Decode(
    'ChJFbWJlZGRpbmdzUmVzcG9uc2USGAoHc3VjY2VzcxgBIAEoCFIHc3VjY2VzcxIcCgllbWJlZG'
    'RpbmcYAiADKAFSCWVtYmVkZGluZxIZCgVlcnJvchgDIAEoCUgAUgVlcnJvcogBAUIICgZfZXJy'
    'b3I=');

@$core.Deprecated('Use nerResponseDescriptor instead')
const NerResponse$json = {
  '1': 'NerResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'entities',
      '3': 2,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.NerResponse.EntitiesEntry',
      '10': 'entities'
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '3': [NerResponse_EntitiesEntry$json],
  '8': [
    {'1': '_error'},
  ],
};

@$core.Deprecated('Use nerResponseDescriptor instead')
const NerResponse_EntitiesEntry$json = {
  '1': 'EntitiesEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {
      '1': 'value',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.EntityList',
      '10': 'value'
    },
  ],
  '7': {'7': true},
};

/// Descriptor for `NerResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List nerResponseDescriptor = $convert.base64Decode(
    'CgtOZXJSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEkgKCGVudGl0aWVzGAIgAy'
    'gLMiwuYWljby5tb2RlbHNlcnZpY2UuTmVyUmVzcG9uc2UuRW50aXRpZXNFbnRyeVIIZW50aXRp'
    'ZXMSGQoFZXJyb3IYAyABKAlIAFIFZXJyb3KIAQEaWgoNRW50aXRpZXNFbnRyeRIQCgNrZXkYAS'
    'ABKAlSA2tleRIzCgV2YWx1ZRgCIAEoCzIdLmFpY28ubW9kZWxzZXJ2aWNlLkVudGl0eUxpc3RS'
    'BXZhbHVlOgI4AUIICgZfZXJyb3I=');

@$core.Deprecated('Use entityListDescriptor instead')
const EntityList$json = {
  '1': 'EntityList',
  '2': [
    {
      '1': 'entities',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.EntityWithConfidence',
      '10': 'entities'
    },
  ],
};

/// Descriptor for `EntityList`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List entityListDescriptor = $convert.base64Decode(
    'CgpFbnRpdHlMaXN0EkMKCGVudGl0aWVzGAEgAygLMicuYWljby5tb2RlbHNlcnZpY2UuRW50aX'
    'R5V2l0aENvbmZpZGVuY2VSCGVudGl0aWVz');

@$core.Deprecated('Use entityWithConfidenceDescriptor instead')
const EntityWithConfidence$json = {
  '1': 'EntityWithConfidence',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {'1': 'confidence', '3': 2, '4': 1, '5': 2, '10': 'confidence'},
  ],
};

/// Descriptor for `EntityWithConfidence`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List entityWithConfidenceDescriptor = $convert.base64Decode(
    'ChRFbnRpdHlXaXRoQ29uZmlkZW5jZRISCgR0ZXh0GAEgASgJUgR0ZXh0Eh4KCmNvbmZpZGVuY2'
    'UYAiABKAJSCmNvbmZpZGVuY2U=');

@$core.Deprecated('Use intentClassificationResponseDescriptor instead')
const IntentClassificationResponse$json = {
  '1': 'IntentClassificationResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'predicted_intent', '3': 2, '4': 1, '5': 9, '10': 'predictedIntent'},
    {'1': 'confidence', '3': 3, '4': 1, '5': 1, '10': 'confidence'},
    {
      '1': 'detected_language',
      '3': 4,
      '4': 1,
      '5': 9,
      '10': 'detectedLanguage'
    },
    {'1': 'inference_time_ms', '3': 5, '4': 1, '5': 1, '10': 'inferenceTimeMs'},
    {
      '1': 'alternative_predictions',
      '3': 6,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.IntentPrediction',
      '10': 'alternativePredictions'
    },
    {
      '1': 'metadata',
      '3': 7,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.IntentClassificationResponse.MetadataEntry',
      '10': 'metadata'
    },
    {'1': 'error', '3': 8, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '3': [IntentClassificationResponse_MetadataEntry$json],
  '8': [
    {'1': '_error'},
  ],
};

@$core.Deprecated('Use intentClassificationResponseDescriptor instead')
const IntentClassificationResponse_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `IntentClassificationResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List intentClassificationResponseDescriptor = $convert.base64Decode(
    'ChxJbnRlbnRDbGFzc2lmaWNhdGlvblJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3'
    'MSKQoQcHJlZGljdGVkX2ludGVudBgCIAEoCVIPcHJlZGljdGVkSW50ZW50Eh4KCmNvbmZpZGVu'
    'Y2UYAyABKAFSCmNvbmZpZGVuY2USKwoRZGV0ZWN0ZWRfbGFuZ3VhZ2UYBCABKAlSEGRldGVjdG'
    'VkTGFuZ3VhZ2USKgoRaW5mZXJlbmNlX3RpbWVfbXMYBSABKAFSD2luZmVyZW5jZVRpbWVNcxJc'
    'ChdhbHRlcm5hdGl2ZV9wcmVkaWN0aW9ucxgGIAMoCzIjLmFpY28ubW9kZWxzZXJ2aWNlLkludG'
    'VudFByZWRpY3Rpb25SFmFsdGVybmF0aXZlUHJlZGljdGlvbnMSWQoIbWV0YWRhdGEYByADKAsy'
    'PS5haWNvLm1vZGVsc2VydmljZS5JbnRlbnRDbGFzc2lmaWNhdGlvblJlc3BvbnNlLk1ldGFkYX'
    'RhRW50cnlSCG1ldGFkYXRhEhkKBWVycm9yGAggASgJSABSBWVycm9yiAEBGjsKDU1ldGFkYXRh'
    'RW50cnkSEAoDa2V5GAEgASgJUgNrZXkSFAoFdmFsdWUYAiABKAlSBXZhbHVlOgI4AUIICgZfZX'
    'Jyb3I=');

@$core.Deprecated('Use intentPredictionDescriptor instead')
const IntentPrediction$json = {
  '1': 'IntentPrediction',
  '2': [
    {'1': 'intent', '3': 1, '4': 1, '5': 9, '10': 'intent'},
    {'1': 'confidence', '3': 2, '4': 1, '5': 1, '10': 'confidence'},
  ],
};

/// Descriptor for `IntentPrediction`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List intentPredictionDescriptor = $convert.base64Decode(
    'ChBJbnRlbnRQcmVkaWN0aW9uEhYKBmludGVudBgBIAEoCVIGaW50ZW50Eh4KCmNvbmZpZGVuY2'
    'UYAiABKAFSCmNvbmZpZGVuY2U=');

@$core.Deprecated('Use sentimentResponseDescriptor instead')
const SentimentResponse$json = {
  '1': 'SentimentResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'sentiment', '3': 2, '4': 1, '5': 9, '10': 'sentiment'},
    {'1': 'confidence', '3': 3, '4': 1, '5': 1, '10': 'confidence'},
    {'1': 'error', '3': 4, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_error'},
  ],
};

/// Descriptor for `SentimentResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List sentimentResponseDescriptor = $convert.base64Decode(
    'ChFTZW50aW1lbnRSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEhwKCXNlbnRpbW'
    'VudBgCIAEoCVIJc2VudGltZW50Eh4KCmNvbmZpZGVuY2UYAyABKAFSCmNvbmZpZGVuY2USGQoF'
    'ZXJyb3IYBCABKAlIAFIFZXJyb3KIAQFCCAoGX2Vycm9y');

@$core.Deprecated('Use statusResponseDescriptor instead')
const StatusResponse$json = {
  '1': 'StatusResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'status',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.ServiceStatus',
      '9': 0,
      '10': 'status',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_status'},
    {'1': '_error'},
  ],
};

/// Descriptor for `StatusResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List statusResponseDescriptor = $convert.base64Decode(
    'Cg5TdGF0dXNSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEj0KBnN0YXR1cxgCIA'
    'EoCzIgLmFpY28ubW9kZWxzZXJ2aWNlLlNlcnZpY2VTdGF0dXNIAFIGc3RhdHVziAEBEhkKBWVy'
    'cm9yGAMgASgJSAFSBWVycm9yiAEBQgkKB19zdGF0dXNCCAoGX2Vycm9y');

@$core.Deprecated('Use ollamaStatusResponseDescriptor instead')
const OllamaStatusResponse$json = {
  '1': 'OllamaStatusResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'status',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.OllamaStatus',
      '9': 0,
      '10': 'status',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_status'},
    {'1': '_error'},
  ],
};

/// Descriptor for `OllamaStatusResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaStatusResponseDescriptor = $convert.base64Decode(
    'ChRPbGxhbWFTdGF0dXNSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEjwKBnN0YX'
    'R1cxgCIAEoCzIfLmFpY28ubW9kZWxzZXJ2aWNlLk9sbGFtYVN0YXR1c0gAUgZzdGF0dXOIAQES'
    'GQoFZXJyb3IYAyABKAlIAVIFZXJyb3KIAQFCCQoHX3N0YXR1c0IICgZfZXJyb3I=');

@$core.Deprecated('Use ollamaModelsResponseDescriptor instead')
const OllamaModelsResponse$json = {
  '1': 'OllamaModelsResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'models',
      '3': 2,
      '4': 3,
      '5': 11,
      '6': '.aico.modelservice.ModelInfo',
      '10': 'models'
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_error'},
  ],
};

/// Descriptor for `OllamaModelsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaModelsResponseDescriptor = $convert.base64Decode(
    'ChRPbGxhbWFNb2RlbHNSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEjQKBm1vZG'
    'VscxgCIAMoCzIcLmFpY28ubW9kZWxzZXJ2aWNlLk1vZGVsSW5mb1IGbW9kZWxzEhkKBWVycm9y'
    'GAMgASgJSABSBWVycm9yiAEBQggKBl9lcnJvcg==');

@$core.Deprecated('Use ollamaPullResponseDescriptor instead')
const OllamaPullResponse$json = {
  '1': 'OllamaPullResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'message',
      '3': 2,
      '4': 1,
      '5': 9,
      '9': 0,
      '10': 'message',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_message'},
    {'1': '_error'},
  ],
};

/// Descriptor for `OllamaPullResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaPullResponseDescriptor = $convert.base64Decode(
    'ChJPbGxhbWFQdWxsUmVzcG9uc2USGAoHc3VjY2VzcxgBIAEoCFIHc3VjY2VzcxIdCgdtZXNzYW'
    'dlGAIgASgJSABSB21lc3NhZ2WIAQESGQoFZXJyb3IYAyABKAlIAVIFZXJyb3KIAQFCCgoIX21l'
    'c3NhZ2VCCAoGX2Vycm9y');

@$core.Deprecated('Use ollamaRemoveResponseDescriptor instead')
const OllamaRemoveResponse$json = {
  '1': 'OllamaRemoveResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'message',
      '3': 2,
      '4': 1,
      '5': 9,
      '9': 0,
      '10': 'message',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_message'},
    {'1': '_error'},
  ],
};

/// Descriptor for `OllamaRemoveResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaRemoveResponseDescriptor = $convert.base64Decode(
    'ChRPbGxhbWFSZW1vdmVSZXNwb25zZRIYCgdzdWNjZXNzGAEgASgIUgdzdWNjZXNzEh0KB21lc3'
    'NhZ2UYAiABKAlIAFIHbWVzc2FnZYgBARIZCgVlcnJvchgDIAEoCUgBUgVlcnJvcogBAUIKCghf'
    'bWVzc2FnZUIICgZfZXJyb3I=');

@$core.Deprecated('Use ollamaServeResponseDescriptor instead')
const OllamaServeResponse$json = {
  '1': 'OllamaServeResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'message',
      '3': 2,
      '4': 1,
      '5': 9,
      '9': 0,
      '10': 'message',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_message'},
    {'1': '_error'},
  ],
};

/// Descriptor for `OllamaServeResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaServeResponseDescriptor = $convert.base64Decode(
    'ChNPbGxhbWFTZXJ2ZVJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3MSHQoHbWVzc2'
    'FnZRgCIAEoCUgAUgdtZXNzYWdliAEBEhkKBWVycm9yGAMgASgJSAFSBWVycm9yiAEBQgoKCF9t'
    'ZXNzYWdlQggKBl9lcnJvcg==');

@$core.Deprecated('Use ollamaShutdownResponseDescriptor instead')
const OllamaShutdownResponse$json = {
  '1': 'OllamaShutdownResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {
      '1': 'message',
      '3': 2,
      '4': 1,
      '5': 9,
      '9': 0,
      '10': 'message',
      '17': true
    },
    {'1': 'error', '3': 3, '4': 1, '5': 9, '9': 1, '10': 'error', '17': true},
  ],
  '8': [
    {'1': '_message'},
    {'1': '_error'},
  ],
};

/// Descriptor for `OllamaShutdownResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaShutdownResponseDescriptor = $convert.base64Decode(
    'ChZPbGxhbWFTaHV0ZG93blJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3MSHQoHbW'
    'Vzc2FnZRgCIAEoCUgAUgdtZXNzYWdliAEBEhkKBWVycm9yGAMgASgJSAFSBWVycm9yiAEBQgoK'
    'CF9tZXNzYWdlQggKBl9lcnJvcg==');

@$core.Deprecated('Use conversationMessageDescriptor instead')
const ConversationMessage$json = {
  '1': 'ConversationMessage',
  '2': [
    {'1': 'role', '3': 1, '4': 1, '5': 9, '10': 'role'},
    {'1': 'content', '3': 2, '4': 1, '5': 9, '10': 'content'},
  ],
};

/// Descriptor for `ConversationMessage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List conversationMessageDescriptor = $convert.base64Decode(
    'ChNDb252ZXJzYXRpb25NZXNzYWdlEhIKBHJvbGUYASABKAlSBHJvbGUSGAoHY29udGVudBgCIA'
    'EoCVIHY29udGVudA==');

@$core.Deprecated('Use completionResultDescriptor instead')
const CompletionResult$json = {
  '1': 'CompletionResult',
  '2': [
    {'1': 'model', '3': 1, '4': 1, '5': 9, '10': 'model'},
    {
      '1': 'created_at',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'createdAt'
    },
    {
      '1': 'message',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.ConversationMessage',
      '10': 'message'
    },
    {'1': 'done', '3': 4, '4': 1, '5': 8, '10': 'done'},
    {
      '1': 'total_duration',
      '3': 5,
      '4': 1,
      '5': 3,
      '9': 0,
      '10': 'totalDuration',
      '17': true
    },
    {
      '1': 'load_duration',
      '3': 6,
      '4': 1,
      '5': 3,
      '9': 1,
      '10': 'loadDuration',
      '17': true
    },
    {
      '1': 'prompt_eval_count',
      '3': 7,
      '4': 1,
      '5': 3,
      '9': 2,
      '10': 'promptEvalCount',
      '17': true
    },
    {
      '1': 'prompt_eval_duration',
      '3': 8,
      '4': 1,
      '5': 3,
      '9': 3,
      '10': 'promptEvalDuration',
      '17': true
    },
    {
      '1': 'eval_count',
      '3': 9,
      '4': 1,
      '5': 3,
      '9': 4,
      '10': 'evalCount',
      '17': true
    },
    {
      '1': 'eval_duration',
      '3': 10,
      '4': 1,
      '5': 3,
      '9': 5,
      '10': 'evalDuration',
      '17': true
    },
    {
      '1': 'thinking',
      '3': 11,
      '4': 1,
      '5': 9,
      '9': 6,
      '10': 'thinking',
      '17': true
    },
  ],
  '8': [
    {'1': '_total_duration'},
    {'1': '_load_duration'},
    {'1': '_prompt_eval_count'},
    {'1': '_prompt_eval_duration'},
    {'1': '_eval_count'},
    {'1': '_eval_duration'},
    {'1': '_thinking'},
  ],
};

/// Descriptor for `CompletionResult`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List completionResultDescriptor = $convert.base64Decode(
    'ChBDb21wbGV0aW9uUmVzdWx0EhQKBW1vZGVsGAEgASgJUgVtb2RlbBI5CgpjcmVhdGVkX2F0GA'
    'IgASgLMhouZ29vZ2xlLnByb3RvYnVmLlRpbWVzdGFtcFIJY3JlYXRlZEF0EkAKB21lc3NhZ2UY'
    'AyABKAsyJi5haWNvLm1vZGVsc2VydmljZS5Db252ZXJzYXRpb25NZXNzYWdlUgdtZXNzYWdlEh'
    'IKBGRvbmUYBCABKAhSBGRvbmUSKgoOdG90YWxfZHVyYXRpb24YBSABKANIAFINdG90YWxEdXJh'
    'dGlvbogBARIoCg1sb2FkX2R1cmF0aW9uGAYgASgDSAFSDGxvYWREdXJhdGlvbogBARIvChFwcm'
    '9tcHRfZXZhbF9jb3VudBgHIAEoA0gCUg9wcm9tcHRFdmFsQ291bnSIAQESNQoUcHJvbXB0X2V2'
    'YWxfZHVyYXRpb24YCCABKANIA1IScHJvbXB0RXZhbER1cmF0aW9uiAEBEiIKCmV2YWxfY291bn'
    'QYCSABKANIBFIJZXZhbENvdW50iAEBEigKDWV2YWxfZHVyYXRpb24YCiABKANIBVIMZXZhbER1'
    'cmF0aW9uiAEBEh8KCHRoaW5raW5nGAsgASgJSAZSCHRoaW5raW5niAEBQhEKD190b3RhbF9kdX'
    'JhdGlvbkIQCg5fbG9hZF9kdXJhdGlvbkIUChJfcHJvbXB0X2V2YWxfY291bnRCFwoVX3Byb21w'
    'dF9ldmFsX2R1cmF0aW9uQg0KC19ldmFsX2NvdW50QhAKDl9ldmFsX2R1cmF0aW9uQgsKCV90aG'
    'lua2luZw==');

@$core.Deprecated('Use modelInfoDescriptor instead')
const ModelInfo$json = {
  '1': 'ModelInfo',
  '2': [
    {'1': 'name', '3': 1, '4': 1, '5': 9, '10': 'name'},
    {'1': 'model', '3': 2, '4': 1, '5': 9, '10': 'model'},
    {
      '1': 'modified_at',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'modifiedAt'
    },
    {'1': 'size', '3': 4, '4': 1, '5': 3, '10': 'size'},
    {'1': 'digest', '3': 5, '4': 1, '5': 9, '10': 'digest'},
    {
      '1': 'details',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.aico.modelservice.ModelDetails',
      '9': 0,
      '10': 'details',
      '17': true
    },
  ],
  '8': [
    {'1': '_details'},
  ],
};

/// Descriptor for `ModelInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List modelInfoDescriptor = $convert.base64Decode(
    'CglNb2RlbEluZm8SEgoEbmFtZRgBIAEoCVIEbmFtZRIUCgVtb2RlbBgCIAEoCVIFbW9kZWwSOw'
    'oLbW9kaWZpZWRfYXQYAyABKAsyGi5nb29nbGUucHJvdG9idWYuVGltZXN0YW1wUgptb2RpZmll'
    'ZEF0EhIKBHNpemUYBCABKANSBHNpemUSFgoGZGlnZXN0GAUgASgJUgZkaWdlc3QSPgoHZGV0YW'
    'lscxgGIAEoCzIfLmFpY28ubW9kZWxzZXJ2aWNlLk1vZGVsRGV0YWlsc0gAUgdkZXRhaWxziAEB'
    'QgoKCF9kZXRhaWxz');

@$core.Deprecated('Use modelDetailsDescriptor instead')
const ModelDetails$json = {
  '1': 'ModelDetails',
  '2': [
    {'1': 'parent_model', '3': 1, '4': 1, '5': 9, '10': 'parentModel'},
    {'1': 'format', '3': 2, '4': 1, '5': 9, '10': 'format'},
    {'1': 'family', '3': 3, '4': 1, '5': 9, '10': 'family'},
    {'1': 'families', '3': 4, '4': 3, '5': 9, '10': 'families'},
    {'1': 'parameter_size', '3': 5, '4': 1, '5': 3, '10': 'parameterSize'},
    {
      '1': 'quantization_level',
      '3': 6,
      '4': 1,
      '5': 3,
      '10': 'quantizationLevel'
    },
  ],
};

/// Descriptor for `ModelDetails`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List modelDetailsDescriptor = $convert.base64Decode(
    'CgxNb2RlbERldGFpbHMSIQoMcGFyZW50X21vZGVsGAEgASgJUgtwYXJlbnRNb2RlbBIWCgZmb3'
    'JtYXQYAiABKAlSBmZvcm1hdBIWCgZmYW1pbHkYAyABKAlSBmZhbWlseRIaCghmYW1pbGllcxgE'
    'IAMoCVIIZmFtaWxpZXMSJQoOcGFyYW1ldGVyX3NpemUYBSABKANSDXBhcmFtZXRlclNpemUSLQ'
    'oScXVhbnRpemF0aW9uX2xldmVsGAYgASgDUhFxdWFudGl6YXRpb25MZXZlbA==');

@$core.Deprecated('Use serviceStatusDescriptor instead')
const ServiceStatus$json = {
  '1': 'ServiceStatus',
  '2': [
    {'1': 'version', '3': 1, '4': 1, '5': 9, '10': 'version'},
    {'1': 'ollama_running', '3': 2, '4': 1, '5': 8, '10': 'ollamaRunning'},
    {'1': 'ollama_version', '3': 3, '4': 1, '5': 9, '10': 'ollamaVersion'},
    {
      '1': 'loaded_models_count',
      '3': 4,
      '4': 1,
      '5': 5,
      '10': 'loadedModelsCount'
    },
    {'1': 'loaded_models', '3': 5, '4': 3, '5': 9, '10': 'loadedModels'},
  ],
};

/// Descriptor for `ServiceStatus`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List serviceStatusDescriptor = $convert.base64Decode(
    'Cg1TZXJ2aWNlU3RhdHVzEhgKB3ZlcnNpb24YASABKAlSB3ZlcnNpb24SJQoOb2xsYW1hX3J1bm'
    '5pbmcYAiABKAhSDW9sbGFtYVJ1bm5pbmcSJQoOb2xsYW1hX3ZlcnNpb24YAyABKAlSDW9sbGFt'
    'YVZlcnNpb24SLgoTbG9hZGVkX21vZGVsc19jb3VudBgEIAEoBVIRbG9hZGVkTW9kZWxzQ291bn'
    'QSIwoNbG9hZGVkX21vZGVscxgFIAMoCVIMbG9hZGVkTW9kZWxz');

@$core.Deprecated('Use ollamaStatusDescriptor instead')
const OllamaStatus$json = {
  '1': 'OllamaStatus',
  '2': [
    {'1': 'running', '3': 1, '4': 1, '5': 8, '10': 'running'},
    {'1': 'version', '3': 2, '4': 1, '5': 9, '10': 'version'},
    {'1': 'host', '3': 3, '4': 1, '5': 9, '10': 'host'},
    {'1': 'port', '3': 4, '4': 1, '5': 5, '10': 'port'},
    {'1': 'loaded_models', '3': 5, '4': 3, '5': 9, '10': 'loadedModels'},
  ],
};

/// Descriptor for `OllamaStatus`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List ollamaStatusDescriptor = $convert.base64Decode(
    'CgxPbGxhbWFTdGF0dXMSGAoHcnVubmluZxgBIAEoCFIHcnVubmluZxIYCgd2ZXJzaW9uGAIgAS'
    'gJUgd2ZXJzaW9uEhIKBGhvc3QYAyABKAlSBGhvc3QSEgoEcG9ydBgEIAEoBVIEcG9ydBIjCg1s'
    'b2FkZWRfbW9kZWxzGAUgAygJUgxsb2FkZWRNb2RlbHM=');
