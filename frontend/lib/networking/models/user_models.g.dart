// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

User _$UserFromJson(Map<String, dynamic> json) => User(
  uuid: json['uuid'] as String,
  fullName: json['full_name'] as String,
  nickname: json['nickname'] as String,
  userType: json['user_type'] as String,
  pin: json['pin'] as String?,
  isActive: json['is_active'] as bool?,
  createdAt: DateTime.parse(json['created_at'] as String),
  updatedAt: DateTime.parse(json['updated_at'] as String),
);

Map<String, dynamic> _$UserToJson(User instance) => <String, dynamic>{
  'uuid': instance.uuid,
  'full_name': instance.fullName,
  'nickname': instance.nickname,
  'user_type': instance.userType,
  'pin': instance.pin,
  'is_active': instance.isActive,
  'created_at': instance.createdAt.toIso8601String(),
  'updated_at': instance.updatedAt.toIso8601String(),
};

CreateUserRequest _$CreateUserRequestFromJson(Map<String, dynamic> json) =>
    CreateUserRequest(
      fullName: json['fullName'] as String,
      nickname: json['nickname'] as String,
      userType: json['userType'] as String,
      pin: json['pin'] as String,
    );

Map<String, dynamic> _$CreateUserRequestToJson(CreateUserRequest instance) =>
    <String, dynamic>{
      'fullName': instance.fullName,
      'nickname': instance.nickname,
      'userType': instance.userType,
      'pin': instance.pin,
    };

UpdateUserRequest _$UpdateUserRequestFromJson(Map<String, dynamic> json) =>
    UpdateUserRequest(
      fullName: json['fullName'] as String?,
      nickname: json['nickname'] as String?,
      userType: json['userType'] as String?,
      pin: json['pin'] as String?,
    );

Map<String, dynamic> _$UpdateUserRequestToJson(UpdateUserRequest instance) =>
    <String, dynamic>{
      'fullName': instance.fullName,
      'nickname': instance.nickname,
      'userType': instance.userType,
      'pin': instance.pin,
    };

AuthenticateRequest _$AuthenticateRequestFromJson(Map<String, dynamic> json) =>
    AuthenticateRequest(
      uuid: json['user_uuid'] as String,
      pin: json['pin'] as String,
    );

Map<String, dynamic> _$AuthenticateRequestToJson(
  AuthenticateRequest instance,
) => <String, dynamic>{'user_uuid': instance.uuid, 'pin': instance.pin};

AuthenticationResponse _$AuthenticationResponseFromJson(
  Map<String, dynamic> json,
) => AuthenticationResponse(
  success: json['success'] as bool,
  token: json['jwt_token'] as String?,
  user: json['user'] == null
      ? null
      : User.fromJson(json['user'] as Map<String, dynamic>),
  error: json['error'] as String?,
  lastLogin: json['last_login'] == null
      ? null
      : DateTime.parse(json['last_login'] as String),
);

Map<String, dynamic> _$AuthenticationResponseToJson(
  AuthenticationResponse instance,
) => <String, dynamic>{
  'success': instance.success,
  'jwt_token': instance.token,
  'user': instance.user,
  'error': instance.error,
  'last_login': instance.lastLogin?.toIso8601String(),
};

UserListResponse _$UserListResponseFromJson(Map<String, dynamic> json) =>
    UserListResponse(
      users: (json['users'] as List<dynamic>)
          .map((e) => User.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
    );

Map<String, dynamic> _$UserListResponseToJson(UserListResponse instance) =>
    <String, dynamic>{'users': instance.users, 'total': instance.total};
