/// Memory Album Repository
///
/// Handles API communication for the Memory Album feature.
/// Manages user-curated memories (facts) via the backend API.
library;

import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';

class MemoryAlbumRepository {
  final UnifiedApiClient _apiClient;

  MemoryAlbumRepository(this._apiClient);

  /// Remember a message or conversation
  Future<String> rememberContent(RememberRequest request) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/api/v1/memory-album/remember',
      data: request.toJson(),
    );

    if (response != null && response['fact_id'] != null) {
      return response['fact_id'] as String;
    } else {
      throw Exception('Failed to save memory');
    }
  }

  /// Get memories with optional filters
  Future<List<MemoryEntry>> getMemories({
    String? category,
    bool favoritesOnly = false,
    int limit = 50,
    int offset = 0,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': limit,
      'offset': offset,
    };

    if (category != null) queryParams['category'] = category;
    if (favoritesOnly) queryParams['favorites_only'] = true;

    final response = await _apiClient.get<Map<String, dynamic>>(
      '/api/v1/memory-album',
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
  }

  /// Update memory metadata (notes, tags, favorites)
  Future<MemoryEntry> updateMemory(
    String memoryId,
    UpdateMemoryRequest request,
  ) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      '/api/v1/memory-album/$memoryId',
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
      await _apiClient.delete('/api/v1/memory-album/$memoryId');
      return true;
    } catch (e) {
      return false;
    }
  }
}
