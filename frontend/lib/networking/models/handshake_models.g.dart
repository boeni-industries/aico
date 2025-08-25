// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'handshake_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

HandshakeRequest _$HandshakeRequestFromJson(Map<String, dynamic> json) =>
    HandshakeRequest(
      handshakeRequest: json['handshake_request'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$HandshakeRequestToJson(HandshakeRequest instance) =>
    <String, dynamic>{'handshake_request': instance.handshakeRequest};

HandshakeResponse _$HandshakeResponseFromJson(Map<String, dynamic> json) =>
    HandshakeResponse(
      handshakeResponse: json['handshake_response'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$HandshakeResponseToJson(HandshakeResponse instance) =>
    <String, dynamic>{'handshake_response': instance.handshakeResponse};

EncryptedRequest _$EncryptedRequestFromJson(Map<String, dynamic> json) =>
    EncryptedRequest(
      encrypted: json['encrypted'] as bool,
      payload: json['payload'] as String,
      clientId: json['client_id'] as String,
    );

Map<String, dynamic> _$EncryptedRequestToJson(EncryptedRequest instance) =>
    <String, dynamic>{
      'encrypted': instance.encrypted,
      'payload': instance.payload,
      'client_id': instance.clientId,
    };

EncryptedResponse _$EncryptedResponseFromJson(Map<String, dynamic> json) =>
    EncryptedResponse(
      encrypted: json['encrypted'] as bool,
      payload: json['encrypted_payload'] as String,
    );

Map<String, dynamic> _$EncryptedResponseToJson(EncryptedResponse instance) =>
    <String, dynamic>{
      'encrypted': instance.encrypted,
      'encrypted_payload': instance.payload,
    };

EchoRequest _$EchoRequestFromJson(Map<String, dynamic> json) => EchoRequest(
  message: json['message'] as String,
  timestamp: (json['timestamp'] as num?)?.toInt(),
);

Map<String, dynamic> _$EchoRequestToJson(EchoRequest instance) =>
    <String, dynamic>{
      'message': instance.message,
      'timestamp': instance.timestamp,
    };

EchoResponse _$EchoResponseFromJson(Map<String, dynamic> json) => EchoResponse(
  echo: json['echo'] as String,
  status: json['status'] as String?,
  timestamp: (json['timestamp'] as num?)?.toInt(),
);

Map<String, dynamic> _$EchoResponseToJson(EchoResponse instance) =>
    <String, dynamic>{
      'echo': instance.echo,
      'status': instance.status,
      'timestamp': instance.timestamp,
    };
