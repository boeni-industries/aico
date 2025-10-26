/// Memory Album Provider
/// 
/// State management for Memory Album feature using Riverpod 3.x.
/// Handles loading, creating, and updating memories.
library;

import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/data/repositories/memory_album_repository.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'memory_album_provider.g.dart';

/// State for memories list
class MemoriesState {
  final List<MemoryEntry> memories;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final String? error;
  final int currentPage;

  const MemoriesState({
    this.memories = const [],
    this.isLoading = false,
    this.isLoadingMore = false,
    this.hasMore = true,
    this.error,
    this.currentPage = 0,
  });

  MemoriesState copyWith({
    List<MemoryEntry>? memories,
    bool? isLoading,
    bool? isLoadingMore,
    bool? hasMore,
    String? error,
    int? currentPage,
  }) {
    return MemoriesState(
      memories: memories ?? this.memories,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMore: hasMore ?? this.hasMore,
      error: error,
      currentPage: currentPage ?? this.currentPage,
    );
  }
}

/// Provider for Memory Album repository
@riverpod
MemoryAlbumRepository memoryAlbumRepository(Ref ref) {

  final apiClient = ref.watch(unifiedApiClientProvider);
  return MemoryAlbumRepository(apiClient);
}

/// Notifier for managing memories
@riverpod
class MemoryAlbumNotifier extends _$MemoryAlbumNotifier {
  late final MemoryAlbumRepository _repository;
  static const int _pageSize = 20;

  @override
  MemoriesState build() {
    _repository = ref.read(memoryAlbumRepositoryProvider);
    return const MemoriesState();
  }

  /// Load initial page of memories
  Future<void> loadMemories({
    String? category,
    bool favoritesOnly = false,
  }) async {
    state = state.copyWith(
      isLoading: true, 
      error: null,
      currentPage: 0,
      memories: [], // Clear existing
    );
    
    try {
      final memories = await _repository.getMemories(
        category: category,
        favoritesOnly: favoritesOnly,
        limit: _pageSize,
        offset: 0,
      );
      
      state = state.copyWith(
        memories: memories,
        isLoading: false,
        hasMore: memories.length >= _pageSize,
        currentPage: 1,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Load next page of memories (for infinite scroll)
  Future<void> loadMoreMemories({
    String? category,
    bool favoritesOnly = false,
  }) async {
    if (state.isLoadingMore || !state.hasMore) return;
    
    state = state.copyWith(isLoadingMore: true);
    
    try {
      final newMemories = await _repository.getMemories(
        category: category,
        favoritesOnly: favoritesOnly,
        limit: _pageSize,
        offset: state.currentPage * _pageSize,
      );
      
      state = state.copyWith(
        memories: [...state.memories, ...newMemories],
        isLoadingMore: false,
        hasMore: newMemories.length >= _pageSize,
        currentPage: state.currentPage + 1,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingMore: false,
        error: e.toString(),
      );
    }
  }

  /// Remember a message
  Future<String?> rememberMessage({
    required String conversationId,
    required String messageId,
    required String content,
    String? userNote,
    List<String>? tags,
    String? emotionalTone,
  }) async {
    try {
      final request = RememberRequest(
        conversationId: conversationId,
        messageId: messageId,
        content: content,
        contentType: MemoryContentType.message,
        userNote: userNote,
        tags: tags,
        emotionalTone: emotionalTone,
      );
      
      final memoryId = await _repository.rememberContent(request);
      
      // Reload from beginning to show the new one (it will be first)
      state = state.copyWith(currentPage: 0, memories: []);
      await loadMemories();
      
      return memoryId;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Remember a full conversation
  Future<String?> rememberConversation({
    required String conversationId,
    required String title,
    required String summary,
    List<String>? keyMoments,
    String? userNote,
    List<String>? tags,
  }) async {
    try {
      final request = RememberRequest(
        conversationId: conversationId,
        messageId: null, // No specific message - whole conversation
        content: summary,
        contentType: MemoryContentType.conversation,
        conversationTitle: title,
        conversationSummary: summary,
        keyMoments: keyMoments,
        userNote: userNote,
        tags: tags,
        memoryType: 'moment',
      );
      
      final memoryId = await _repository.rememberContent(request);
      
      // Reload from beginning
      state = state.copyWith(currentPage: 0, memories: []);
      await loadMemories();
      
      return memoryId;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Toggle favorite status
  Future<void> toggleFavorite(MemoryEntry memory) async {
    try {
      final request = UpdateMemoryRequest(
        isFavorite: !memory.isFavorite,
      );
      
      await _repository.updateMemory(memory.memoryId, request);
      
      // Update local state
      final updatedMemories = state.memories.map((m) {
        if (m.memoryId == memory.memoryId) {
          return m.copyWith(isFavorite: !m.isFavorite);
        }
        return m;
      }).toList();
      
      state = state.copyWith(memories: updatedMemories);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Update memory notes/tags
  Future<void> updateMemory({
    required String memoryId,
    String? userNote,
    List<String>? tags,
  }) async {
    try {
      final request = UpdateMemoryRequest(
        userNote: userNote,
        tags: tags,
      );
      
      final updatedMemory = await _repository.updateMemory(memoryId, request);
      
      // Update local state
      final updatedMemories = state.memories.map((m) {
        if (m.memoryId == memoryId) {
          return updatedMemory;
        }
        return m;
      }).toList();
      
      state = state.copyWith(memories: updatedMemories);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Delete a memory
  Future<bool> deleteMemory(String memoryId) async {
    try {
      final success = await _repository.deleteMemory(memoryId);
      
      if (success) {
        // Remove from local state
        final updatedMemories = state.memories.where((m) => m.memoryId != memoryId).toList();
        state = state.copyWith(memories: updatedMemories);
      }
      
      return success;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }
}

