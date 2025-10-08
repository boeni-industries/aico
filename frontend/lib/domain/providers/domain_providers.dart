import 'package:aico_frontend/data/providers/data_providers.dart';
import 'package:aico_frontend/domain/usecases/auth_usecases.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Use case providers
final loginUseCaseProvider = Provider<LoginUseCase>((ref) {
  final authRepository = ref.read(authRepositoryProvider);
  return LoginUseCase(authRepository);
});

final autoLoginUseCaseProvider = Provider<AutoLoginUseCase>((ref) {
  final authRepository = ref.read(authRepositoryProvider);
  return AutoLoginUseCase(authRepository);
});

final logoutUseCaseProvider = Provider<LogoutUseCase>((ref) {
  final authRepository = ref.read(authRepositoryProvider);
  return LogoutUseCase(authRepository);
});

final refreshTokenUseCaseProvider = Provider<RefreshTokenUseCase>((ref) {
  final authRepository = ref.read(authRepositoryProvider);
  return RefreshTokenUseCase(authRepository);
});

final checkAuthStatusUseCaseProvider = Provider<CheckAuthStatusUseCase>((ref) {
  final authRepository = ref.read(authRepositoryProvider);
  return CheckAuthStatusUseCase(authRepository);
});
