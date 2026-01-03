import 'package:aico_frontend/data/datasources/remote/proactive_remote_datasource.dart';
import 'package:aico_frontend/data/models/proactive_model.dart';
import 'package:aico_frontend/domain/repositories/proactive_repository.dart';

/// Implementation of ProactiveRepository
class ProactiveRepositoryImpl implements ProactiveRepository {
  final ProactiveRemoteDataSource _remoteDataSource;

  const ProactiveRepositoryImpl(this._remoteDataSource);

  @override
  Future<List<InitiationModel>> getPendingInitiations() async {
    return await _remoteDataSource.getPendingInitiations();
  }

  @override
  Future<List<InitiationModel>> getInitiationHistory({int limit = 20}) async {
    return await _remoteDataSource.getInitiationHistory(limit: limit);
  }

  @override
  Future<void> respondToInitiation(InitiationResponseRequest request) async {
    await _remoteDataSource.respondToInitiation(request);
  }
}
