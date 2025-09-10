import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/core/providers.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/datasources/local/auth_local_datasource.dart';
import 'package:aico_frontend/data/datasources/remote/auth_remote_datasource.dart';
import 'package:aico_frontend/data/repositories/auth_repository_impl.dart';
import 'package:aico_frontend/data/repositories/user_repository_impl.dart';
import 'package:aico_frontend/domain/repositories/auth_repository.dart';
import 'package:aico_frontend/domain/repositories/user_repository.dart';

/// Auth local datasource provider
final authLocalDataSourceProvider = Provider<AuthLocalDataSource>((ref) {
  final secureStorage = ref.watch(flutterSecureStorageProvider);
  final sharedPreferences = ref.watch(sharedPreferencesProvider);
  return AuthLocalDataSourceImpl(secureStorage, sharedPreferences);
});

/// Auth remote datasource provider
final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  final apiClient = ref.watch(unifiedApiClientProvider);
  return AuthRemoteDataSourceImpl(apiClient);
});

/// Auth repository provider
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final remoteDataSource = ref.watch(authRemoteDataSourceProvider);
  final localDataSource = ref.watch(authLocalDataSourceProvider);
  return AuthRepositoryImpl(remoteDataSource, localDataSource);
});

/// User repository provider
final userRepositoryProvider = Provider<UserRepository>((ref) {
  final userService = ref.watch(userServiceProvider);
  return UserDataRepository(userService);
});
