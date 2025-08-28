import 'package:json_annotation/json_annotation.dart';

part 'handshake_models.g.dart';

/// Request model for handshake endpoint
@JsonSerializable()
class HandshakeRequest {
  @JsonKey(name: 'handshake_request')
  final Map<String, dynamic> handshakeRequest;

  const HandshakeRequest({
    required this.handshakeRequest,
  });

  factory HandshakeRequest.fromJson(Map<String, dynamic> json) =>
      _$HandshakeRequestFromJson(json);

  Map<String, dynamic> toJson() => _$HandshakeRequestToJson(this);
}

/// Response model for handshake endpoint
@JsonSerializable()
class HandshakeResponse {
  @JsonKey(name: 'handshake_response')
  final Map<String, dynamic> handshakeResponse;

  const HandshakeResponse({
    required this.handshakeResponse,
  });

  factory HandshakeResponse.fromJson(Map<String, dynamic> json) =>
      _$HandshakeResponseFromJson(json);

  Map<String, dynamic> toJson() => _$HandshakeResponseToJson(this);
}

/// Request model for encrypted payloads
@JsonSerializable()
class EncryptedRequest {
  final bool encrypted;
  final String payload;
  @JsonKey(name: 'client_id')
  final String clientId;

  const EncryptedRequest({
    required this.encrypted,
    required this.payload,
    required this.clientId,
  });

  factory EncryptedRequest.fromJson(Map<String, dynamic> json) =>
      _$EncryptedRequestFromJson(json);

  Map<String, dynamic> toJson() => _$EncryptedRequestToJson(this);
}

/// Response model for encrypted payloads
@JsonSerializable()
class EncryptedResponse {
  final bool encrypted;
  @JsonKey(name: 'encrypted_payload')
  final String payload;

  const EncryptedResponse({
    required this.encrypted,
    required this.payload,
  });

  factory EncryptedResponse.fromJson(Map<String, dynamic> json) =>
      _$EncryptedResponseFromJson(json);

  Map<String, dynamic> toJson() => _$EncryptedResponseToJson(this);
}

/// Echo request model
@JsonSerializable()
class EchoRequest {
  final String message;
  final int? timestamp;

  const EchoRequest({
    required this.message,
    this.timestamp,
  });

  factory EchoRequest.fromJson(Map<String, dynamic> json) =>
      _$EchoRequestFromJson(json);

  Map<String, dynamic> toJson() => _$EchoRequestToJson(this);
}

/// Echo response model
@JsonSerializable()
class EchoResponse {
  final String echo;
  final String? status;
  final int? timestamp;

  const EchoResponse({
    required this.echo,
    this.status,
    this.timestamp,
  });

  factory EchoResponse.fromJson(Map<String, dynamic> json) =>
      _$EchoResponseFromJson(json);

  Map<String, dynamic> toJson() => _$EchoResponseToJson(this);
}
