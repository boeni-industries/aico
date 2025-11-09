import 'package:aico_frontend/data/models/user_model.dart';
import 'package:aico_frontend/domain/repositories/auth_repository.dart';

class AuthModel {
  final UserModel user;
  final String token;
  final String? refreshToken;
  final DateTime? lastLogin;

  const AuthModel({
    required this.user,
    required this.token,
    this.refreshToken,
    this.lastLogin,
  });

  factory AuthModel.fromJson(Map<String, dynamic> json) {
    return AuthModel(
      user: UserModel.fromJson(json['user'] ?? {}),
      token: json['jwt_token']?.toString() ?? json['token']?.toString() ?? '',
      refreshToken: json['refresh_token']?.toString(),
      lastLogin: json['last_login'] != null 
          ? DateTime.parse(json['last_login'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user': user.toJson(),
      'token': token,
      'refresh_token': refreshToken,
      'last_login': lastLogin?.toIso8601String(),
    };
  }

  // Convert to domain entity
  AuthResult toDomain() {
    return AuthResult(
      user: user.toDomain(),
      token: token,
      refreshToken: refreshToken,
      lastLogin: lastLogin,
    );
  }

  // Create from domain entity
  factory AuthModel.fromDomain(AuthResult authResult) {
    return AuthModel(
      user: UserModel.fromDomain(authResult.user),
      token: authResult.token,
      refreshToken: authResult.refreshToken,
      lastLogin: authResult.lastLogin,
    );
  }
}
