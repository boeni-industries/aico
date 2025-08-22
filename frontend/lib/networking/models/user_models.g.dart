// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

User _$UserFromJson(Map<String, dynamic> json) => User(
  uuid: json['uuid'] as String,
  fullName: json['fullName'] as String,
  nickname: json['nickname'] as String,
  userType: json['userType'] as String,
  pin: json['pin'] as String,
  createdAt: DateTime.parse(json['createdAt'] as String),
  updatedAt: DateTime.parse(json['updatedAt'] as String),
);

Map<String, dynamic> _$UserToJson(User instance) => <String, dynamic>{
  'uuid': instance.uuid,
  'fullName': instance.fullName,
  'nickname': instance.nickname,
  'userType': instance.userType,
  'pin': instance.pin,
  'createdAt': instance.createdAt.toIso8601String(),
  'updatedAt': instance.updatedAt.toIso8601String(),
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
      uuid: json['uuid'] as String,
      pin: json['pin'] as String,
    );

Map<String, dynamic> _$AuthenticateRequestToJson(
  AuthenticateRequest instance,
) => <String, dynamic>{'uuid': instance.uuid, 'pin': instance.pin};

AuthenticationResponse _$AuthenticationResponseFromJson(
  Map<String, dynamic> json,
) => AuthenticationResponse(
  success: json['success'] as bool,
  token: json['token'] as String?,
  user: json['user'] == null
      ? null
      : User.fromJson(json['user'] as Map<String, dynamic>),
  error: json['error'] as String?,
);

Map<String, dynamic> _$AuthenticationResponseToJson(
  AuthenticationResponse instance,
) => <String, dynamic>{
  'success': instance.success,
  'token': instance.token,
  'user': instance.user,
  'error': instance.error,
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
