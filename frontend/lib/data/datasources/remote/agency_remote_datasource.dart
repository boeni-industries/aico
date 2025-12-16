import 'package:aico_frontend/data/models/agency_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Remote data source for agency system operations
/// 
/// Handles communication with the agency API endpoints for
/// retrieving agency state, intentions, goals, and curiosity status.
class AgencyRemoteDataSource {
  final UnifiedApiClient _apiClient;

  const AgencyRemoteDataSource(this._apiClient);

  /// Get complete agency state for the current user
  /// 
  /// Returns:
  ///   AgencyStateModel containing intentions, curiosity, profile, and consent actions
  Future<AgencyStateModel> getAgencyState() async {
    try {
      final response = await _apiClient.request<AgencyStateModel>(
        'GET',
        '/agency/state',
        fromJson: (json) => AgencyStateModel.fromJson(json),
      );
      
      if (response != null) {
        return response;
      }
      throw Exception('Invalid response from server');
    } catch (e) {
      throw Exception('Failed to get agency state: $e');
    }
  }

  /// Get intention set only
  /// 
  /// Args:
  ///   limit: Maximum number of active intentions to return
  /// 
  /// Returns:
  ///   IntentionSetModel containing current intentions and focus
  Future<IntentionSetModel> getIntentionSet({int limit = 10}) async {
    try {
      final response = await _apiClient.request<IntentionSetModel>(
        'GET',
        '/agency/intentions',
        queryParameters: {'limit': limit.toString()},
        fromJson: (json) => IntentionSetModel.fromJson(json),
      );
      
      if (response != null) {
        return response;
      }
      throw Exception('Invalid response from server');
    } catch (e) {
      throw Exception('Failed to get intention set: $e');
    }
  }

  /// Get curiosity status only
  /// 
  /// Returns:
  ///   CuriosityStatusModel containing curiosity level and opportunities
  Future<CuriosityStatusModel> getCuriosityStatus() async {
    try {
      final response = await _apiClient.request<CuriosityStatusModel>(
        'GET',
        '/agency/curiosity',
        fromJson: (json) => CuriosityStatusModel.fromJson(json),
      );
      
      if (response != null) {
        return response;
      }
      throw Exception('Invalid response from server');
    } catch (e) {
      throw Exception('Failed to get curiosity status: $e');
    }
  }
}
