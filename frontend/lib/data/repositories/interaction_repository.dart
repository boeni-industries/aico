import 'package:aico_frontend/networking/clients/unified_api_client.dart';

/// Repository for interaction API operations
/// 
/// Handles all HTTP communication with the backend interaction endpoints
/// following the API specification in docs/api/interactions-api.md
class InteractionRepository {
  final UnifiedApiClient _apiClient;

  InteractionRepository({
    required UnifiedApiClient apiClient,
  }) : _apiClient = apiClient;

  /// Get a specific interaction by ID with full event timeline
  Future<Map<String, dynamic>> getInteraction(String interactionId) async {
    try {
      final data = await _apiClient.get<Map<String, dynamic>>(
        '/interactions/$interactionId',
      );
      if (data == null) {
        throw InteractionNotFoundException('Interaction not found');
      }
      return data;
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// List interactions with optional filters
  Future<Map<String, dynamic>> listInteractions({
    String? status,
    String? type,
    String? requirement,
    String? severity,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
      };

      if (status != null) {
        queryParams['status'] = status;
      }
      if (type != null) {
        queryParams['type'] = type;
      }
      if (requirement != null) {
        queryParams['requirement'] = requirement;
      }
      if (severity != null) {
        queryParams['severity'] = severity;
      }

      final data = await _apiClient.get<Map<String, dynamic>>(
        '/interactions',
        queryParameters: queryParams,
      );
      if (data == null) {
        return {'items': [], 'total': 0};
      }
      return data;
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// Answer a question, choice, or dialogue interaction
  Future<Map<String, dynamic>> answerInteraction(
    String interactionId, {
    String? answerText,
    Map<String, dynamic>? answerJson,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (answerText != null) data['answer_text'] = answerText;
      if (answerJson != null) data['answer_json'] = answerJson;

      final response = await _apiClient.post<Map<String, dynamic>>(
        '/interactions/$interactionId/answer',
        data: data,
      );
      if (response == null) {
        throw InteractionApiException('Failed to answer interaction');
      }
      return response;
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// Approve an approval interaction
  Future<Map<String, dynamic>> approveInteraction(String interactionId) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/interactions/$interactionId/approve',
      );
      if (response == null) {
        throw InteractionApiException('Failed to approve interaction');
      }
      return response;
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// Reject an approval interaction
  Future<Map<String, dynamic>> rejectInteraction(String interactionId) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/interactions/$interactionId/reject',
      );
      if (response == null) {
        throw InteractionApiException('Failed to reject interaction');
      }
      return response;
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// Cancel any pending interaction
  Future<Map<String, dynamic>> cancelInteraction(String interactionId) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/interactions/$interactionId/cancel',
      );
      if (response == null) {
        throw InteractionApiException('Failed to cancel interaction');
      }
      return response;
    } catch (e) {
      throw _handleError(e);
    }
  }

  // Error handling

  Exception _handleError(dynamic e) {
    // UnifiedApiClient already handles encryption and throws appropriate exceptions
    return InteractionApiException(e.toString());
  }
}

// Custom exceptions

class InteractionException implements Exception {
  final String message;
  InteractionException(this.message);

  @override
  String toString() => message;
}

class InteractionValidationException extends InteractionException {
  InteractionValidationException(super.message);
}

class InteractionNotFoundException extends InteractionException {
  InteractionNotFoundException(super.message);
}

class InteractionConflictException extends InteractionException {
  InteractionConflictException(super.message);
}

class InteractionInvalidOperationException extends InteractionException {
  InteractionInvalidOperationException(super.message);
}

class InteractionApiException extends InteractionException {
  InteractionApiException(super.message);
}

class InteractionTimeoutException extends InteractionException {
  InteractionTimeoutException(super.message);
}

class InteractionNetworkException extends InteractionException {
  InteractionNetworkException(super.message);
}
