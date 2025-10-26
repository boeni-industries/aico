/// Memory Album Screen
/// 
/// Premium gold-on-blue aesthetic inspired by treasured family photo albums.
/// Deep navy background with silver/gold accents.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';
import 'package:aico_frontend/presentation/screens/memory_album/widgets/memory_empty_state.dart';
import 'package:aico_frontend/presentation/screens/memory_album/widgets/memory_card.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:aico_frontend/data/models/memory_album_model.dart';

class MemoryAlbumScreen extends ConsumerStatefulWidget {
  const MemoryAlbumScreen({super.key});

  @override
  ConsumerState<MemoryAlbumScreen> createState() => _MemoryAlbumScreenState();
}

class _MemoryAlbumScreenState extends ConsumerState<MemoryAlbumScreen> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Load initial page of memories
    Future.microtask(() => ref.read(memoryAlbumProvider.notifier).loadMemories());
    
    // Setup infinite scroll listener
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent * 0.8) {
      // Load more when user scrolls to 80% of the list
      ref.read(memoryAlbumProvider.notifier).loadMoreMemories();
    }
  }

  @override
  Widget build(BuildContext context) {
    final memoryState = ref.watch(memoryAlbumProvider);
    
    // Transparent scaffold to let app's background gradient show through
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: memoryState.isLoading
            ? _buildLoadingState()
            : memoryState.memories.isEmpty
                ? const MemoryEmptyState()
                : _buildMemoryGrid(memoryState.memories),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: CircularProgressIndicator(
        valueColor: AlwaysStoppedAnimation<Color>(
          MemoryAlbumTheme.silver,
        ),
      ),
    );
  }

  Widget _buildMemoryGrid(List memories) {
    final memoryState = ref.watch(memoryAlbumProvider);
    
    return CustomScrollView(
      controller: _scrollController,
      slivers: [
        // Header
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(40, 32, 40, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Title with silver color
                Text(
                  'Memory Timeline',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w600,
                    color: MemoryAlbumTheme.silver,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 8),
                
                // Subtitle
                Text(
                  '${memories.length} ${memories.length == 1 ? 'memory' : 'memories'} saved',
                  style: TextStyle(
                    fontSize: 14,
                    color: MemoryAlbumTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
        
        // Memory grid
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(40, 0, 40, 40),
          sliver: SliverGrid(
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 400,
              mainAxisSpacing: 24,
              crossAxisSpacing: 24,
              childAspectRatio: 1.2,
            ),
            delegate: SliverChildBuilderDelegate(
              (context, index) {
                final memory = memories[index];
                return MemoryCard(
                  memory: memory,
                  onTap: () => _openMemoryDetail(memory),
                  onFavoriteToggle: () => _toggleFavorite(memory),
                  onDelete: () => _deleteMemory(memory),
                );
              },
              childCount: memories.length,
            ),
          ),
        ),
        
        // Loading more indicator
        if (memoryState.isLoadingMore)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Center(
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(
                    MemoryAlbumTheme.silver,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  void _openMemoryDetail(MemoryEntry memory) {
    // TODO: Navigate to memory detail screen
    debugPrint('Open memory: ${memory.memoryId}');
  }

  void _toggleFavorite(MemoryEntry memory) {
    ref.read(memoryAlbumProvider.notifier).toggleFavorite(memory);
  }

  Future<void> _deleteMemory(MemoryEntry memory) async {
    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Memory'),
        content: const Text('Are you sure you want to delete this memory? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(memoryAlbumProvider.notifier).deleteMemory(memory.memoryId);
    }
  }
}
