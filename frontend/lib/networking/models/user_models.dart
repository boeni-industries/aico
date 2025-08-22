import 'package:json_annotation/json_annotation.dart';

part 'user_models.g.dart';

@JsonSerializable()
class User {
  final String uuid;
  final String fullName;
  final String nickname;
  final String userType;
  final String pin;
  final DateTime createdAt;
  final DateTime updatedAt;

  const User({
    required this.uuid,
    required this.fullName,
    required this.nickname,
    required this.userType,
    required this.pin,
    required this.createdAt,
    required this.updatedAt,
  });

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);
}

@JsonSerializable()
class CreateUserRequest {
  final String fullName;
  final String nickname;
  final String userType;
  final String pin;

  const CreateUserRequest({
    required this.fullName,
    required this.nickname,
    required this.userType,
    required this.pin,
  });

  factory CreateUserRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateUserRequestFromJson(json);
  Map<String, dynamic> toJson() => _$CreateUserRequestToJson(this);
}

@JsonSerializable()
class UpdateUserRequest {
  final String? fullName;
  final String? nickname;
  final String? userType;
  final String? pin;

  const UpdateUserRequest({
    this.fullName,
    this.nickname,
    this.userType,
    this.pin,
  });

  factory UpdateUserRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateUserRequestFromJson(json);
  Map<String, dynamic> toJson() => _$UpdateUserRequestToJson(this);
}

@JsonSerializable()
class AuthenticateRequest {
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
  final String? token;
  final User? user;
  final String? error;

  const AuthenticationResponse({
    required this.success,
    this.token,
    this.user,
    this.error,
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
