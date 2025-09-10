import 'package:aico_frontend/core/providers.dart';
import 'package:aico_frontend/data/datasources/local/auth_local_datasource.dart';
import 'package:aico_frontend/data/datasources/remote/auth_remote_datasource.dart';
import 'package:aico_frontend/data/repositories/auth_repository_impl.dart';
import 'package:aico_frontend/domain/repositories/auth_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Data source providers
final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  final dio = ref.read(dioProvider);
  return AuthRemoteDataSourceImpl(dio);
});

final authLocalDataSourceProvider = Provider<AuthLocalDataSource>((ref) {
  final secureStorage = ref.read(secureStorageProvider);
  final sharedPreferences = ref.read(sharedPreferencesProvider);
  return AuthLocalDataSourceImpl(secureStorage, sharedPreferences);
});

// Repository providers
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final remoteDataSource = ref.read(authRemoteDataSourceProvider);
  final localDataSource = ref.read(authLocalDataSourceProvider);
  return AuthRepositoryImpl(remoteDataSource, localDataSource);
});
