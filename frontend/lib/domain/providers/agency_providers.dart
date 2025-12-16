import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/datasources/remote/agency_remote_datasource.dart';
import 'package:aico_frontend/data/repositories/agency_repository_impl.dart';
import 'package:aico_frontend/domain/repositories/agency_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provider for agency remote data source
final agencyRemoteDataSourceProvider = Provider<AgencyRemoteDataSource>((ref) {
  final apiClient = ref.watch(unifiedApiClientProvider);
  return AgencyRemoteDataSource(apiClient);
});

/// Provider for agency repository
final agencyRepositoryProvider = Provider<AgencyRepository>((ref) {
  final remoteDataSource = ref.watch(agencyRemoteDataSourceProvider);
  return AgencyRepositoryImpl(remoteDataSource);
});
