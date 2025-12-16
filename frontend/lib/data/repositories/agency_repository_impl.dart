import 'package:aico_frontend/data/datasources/remote/agency_remote_datasource.dart';
import 'package:aico_frontend/data/models/agency_model.dart';
import 'package:aico_frontend/domain/repositories/agency_repository.dart';

/// Implementation of AgencyRepository using remote data source
class AgencyRepositoryImpl implements AgencyRepository {
  final AgencyRemoteDataSource _remoteDataSource;

  const AgencyRepositoryImpl(this._remoteDataSource);

  @override
  Future<AgencyStateModel> getAgencyState() async {
    return await _remoteDataSource.getAgencyState();
  }

  @override
  Future<IntentionSetModel> getIntentionSet({int limit = 10}) async {
    return await _remoteDataSource.getIntentionSet(limit: limit);
  }

  @override
  Future<CuriosityStatusModel> getCuriosityStatus() async {
    return await _remoteDataSource.getCuriosityStatus();
  }
}
