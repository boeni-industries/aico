/// Memory Album Repository
///
/// Handles API communication for the Memory Album feature.
/// Manages user-curated memories (facts) via the backend API.
library;

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:flutter/foundation.dart';

class MemoryAlbumRepository {
  final UnifiedApiClient _apiClient;

  MemoryAlbumRepository(this._apiClient);

  /// Remember a message or conversation
  Future<String> rememberContent(RememberRequest request) async {
    AICOLog.info('Saving memory', topic: 'memory_album_repository', extra: {
      'content_type': request.contentType.value,
      'conversation_id': request.conversationId,
      'has_message_id': request.messageId != null,
    });
    
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/memory-album/remember',
      data: request.toJson(),
    );

    AICOLog.debug('Response received', topic: 'memory_album_repository', extra: {
      'response_is_null': response == null,
      'response_type': response.runtimeType.toString(),
      'response_keys': response?.keys.toList(),
    });
    
    if (response == null) {
      AICOLog.error('Response is null despite 201 status', topic: 'memory_album_repository');
      throw Exception('Failed to save memory: Response is null');
    }
    
    // Backend returns: { "success": true, "fact_id": "...", "message": "..." }
    final factId = response['fact_id'] as String?;
    
    if (factId == null) {
      AICOLog.error('fact_id missing from response', topic: 'memory_album_repository', extra: {
        'response_keys': response.keys.toList(),
        'response': response.toString(),
      });
      throw Exception('Failed to save memory: fact_id missing from response');
    }
    
    AICOLog.info('Memory saved successfully', topic: 'memory_album_repository', extra: {
      'fact_id': factId,
    });
    return factId;
  }

  /// Get memories with optional filters
  Future<List<MemoryEntry>> getMemories({
    String? category,
    bool favoritesOnly = false,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
      };

      if (category != null) queryParams['category'] = category;
      if (favoritesOnly) queryParams['favorites_only'] = true;

      final response = await _apiClient.get<Map<String, dynamic>>(
        '/memory-album',
        queryParameters: queryParams,
      );

      if (response != null && response['memories'] != null) {
        final memories = (response['memories'] as List)
            .map((json) => MemoryEntry.fromJson(json as Map<String, dynamic>))
            .toList();
        return memories;
      } else {
        return [];
      }
    } catch (e) {
      debugPrint('Error loading memories: $e');
      AICOLog.error('Failed to load memories', 
        topic: 'memory_album_repository',
        error: e,
        extra: {
          'category': category,
          'favorites_only': favoritesOnly,
          'limit': limit,
          'offset': offset,
        },
      );
      rethrow;
    }
  }

  /// Update memory metadata (notes, tags, favorites)
  Future<MemoryEntry> updateMemory(
    String memoryId,
    UpdateMemoryRequest request,
  ) async {
    final response = await _apiClient.patch<Map<String, dynamic>>(
      '/memory-album/$memoryId',
      data: request.toJson(),
    );

    if (response != null) {
      return MemoryEntry.fromJson(response);
    } else {
      throw Exception('Failed to update memory');
    }
  }

  /// Delete a memory
  Future<bool> deleteMemory(String memoryId) async {
    try {
      await _apiClient.delete('/memory-album/$memoryId');
      return true;
    } catch (e) {
      return false;
    }
  }
}
