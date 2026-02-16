import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/datasources/remote/proactive_remote_datasource.dart';
import 'package:aico_frontend/data/repositories/proactive_repository_impl.dart';
import 'package:aico_frontend/domain/repositories/proactive_repository.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'proactive_providers.g.dart';

/// Provider for ProactiveRemoteDataSource
@riverpod
ProactiveRemoteDataSource proactiveRemoteDataSource(Ref ref) {
  final apiClient = ref.watch(unifiedApiClientProvider);
  return ProactiveRemoteDataSource(apiClient);
}

/// Provider for ProactiveRepository
@riverpod
ProactiveRepository proactiveRepository(Ref ref) {
  final remoteDataSource = ref.watch(proactiveRemoteDataSourceProvider);
  return ProactiveRepositoryImpl(remoteDataSource);
}
