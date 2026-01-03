import 'package:aico_frontend/data/models/proactive_model.dart';

/// Abstract repository interface for proactive conversation operations
abstract class ProactiveRepository {
  /// Get all pending proactive initiations for current user
  Future<List<InitiationModel>> getPendingInitiations();
  
  /// Get initiation history
  Future<List<InitiationModel>> getInitiationHistory({int limit = 20});
  
  /// Respond to a proactive initiation
  Future<void> respondToInitiation(InitiationResponseRequest request);
}
