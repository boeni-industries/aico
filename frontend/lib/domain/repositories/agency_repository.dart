import 'package:aico_frontend/data/models/agency_model.dart';

/// Abstract repository interface for agency operations
abstract class AgencyRepository {
  /// Get complete agency state for the current user
  /// 
  /// Returns:
  ///   AgencyStateModel containing intentions, curiosity, profile, and consent actions
  Future<AgencyStateModel> getAgencyState();
  
  /// Get intention set only
  /// 
  /// Args:
  ///   limit: Maximum number of active intentions to return
  /// 
  /// Returns:
  ///   IntentionSetModel containing current intentions and focus
  Future<IntentionSetModel> getIntentionSet({int limit = 10});
  
  /// Get curiosity status only
  /// 
  /// Returns:
  ///   CuriosityStatusModel containing curiosity level and opportunities
  Future<CuriosityStatusModel> getCuriosityStatus();
}
