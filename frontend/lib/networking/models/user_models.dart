import 'package:json_annotation/json_annotation.dart';

part 'user_models.g.dart';

@JsonSerializable()
class User {
  final String uuid;
  @JsonKey(name: 'full_name')
  final String fullName;
  final String nickname;
  @JsonKey(name: 'user_type')
  final String userType;
  final String? pin;
  @JsonKey(name: 'is_active')
  final bool? isActive;
  @JsonKey(name: 'primary_language')
  final String? primaryLanguage;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  const User({
    required this.uuid,
    required this.fullName,
    required this.nickname,
    required this.userType,
    this.pin,
    this.isActive,
    this.primaryLanguage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);
}

@JsonSerializable()
class CreateUserRequest {
  @JsonKey(name: 'full_name')
  final String fullName;
  final String nickname;
  @JsonKey(name: 'user_type')
  final String userType;
  final String pin;
  @JsonKey(name: 'primary_language')
  final String? primaryLanguage;

  const CreateUserRequest({
    required this.fullName,
    required this.nickname,
    required this.userType,
    required this.pin,
    this.primaryLanguage,
  });

  factory CreateUserRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateUserRequestFromJson(json);
  Map<String, dynamic> toJson() => _$CreateUserRequestToJson(this);
}

@JsonSerializable()
class UpdateUserRequest {
  @JsonKey(name: 'full_name')
  final String? fullName;
  final String? nickname;
  @JsonKey(name: 'user_type')
  final String? userType;
  final String? pin;
  @JsonKey(name: 'primary_language')
  final String? primaryLanguage;

  const UpdateUserRequest({
    this.fullName,
    this.nickname,
    this.userType,
    this.pin,
    this.primaryLanguage,
  });

  factory UpdateUserRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateUserRequestFromJson(json);
  Map<String, dynamic> toJson() => _$UpdateUserRequestToJson(this);
}

@JsonSerializable()
class AuthenticateRequest {
  @JsonKey(name: 'user_uuid')
  final String uuid;
  final String pin;

  const AuthenticateRequest({
    required this.uuid,
    required this.pin,
  });

  factory AuthenticateRequest.fromJson(Map<String, dynamic> json) =>
      _$AuthenticateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$AuthenticateRequestToJson(this);
}

@JsonSerializable()
class AuthenticationResponse {
  final bool success;
  @JsonKey(name: 'jwt_token')
  final String? token;
  final User? user;
  final String? error;
  @JsonKey(name: 'last_login')
  final DateTime? lastLogin;

  const AuthenticationResponse({
    required this.success,
    this.token,
    this.user,
    this.error,
    this.lastLogin,
  });

  factory AuthenticationResponse.fromJson(Map<String, dynamic> json) =>
      _$AuthenticationResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AuthenticationResponseToJson(this);
}

@JsonSerializable()
class UserListResponse {
  final List<User> users;
  final int total;

  const UserListResponse({
    required this.users,
    required this.total,
  });

  factory UserListResponse.fromJson(Map<String, dynamic> json) =>
      _$UserListResponseFromJson(json);
  Map<String, dynamic> toJson() => _$UserListResponseToJson(this);
}
