/// Memory Album Screen
/// 
/// Premium gold-on-blue aesthetic inspired by treasured family photo albums.
/// Deep navy background with silver/gold accents.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';
import 'package:aico_frontend/presentation/screens/memory_album/widgets/memory_card.dart';
import 'package:aico_frontend/presentation/screens/memory_album/memory_detail_screen.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:aico_frontend/data/models/memory_album_model.dart';

class MemoryAlbumScreen extends ConsumerStatefulWidget {
  const MemoryAlbumScreen({super.key});

  @override
  ConsumerState<MemoryAlbumScreen> createState() => _MemoryAlbumScreenState();
}

enum MemoryFilter { all, starred }

class _MemoryAlbumScreenState extends ConsumerState<MemoryAlbumScreen> {
  final ScrollController _scrollController = ScrollController();
  MemoryFilter _currentFilter = MemoryFilter.all;

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
                ? _buildEmptyState()
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

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.auto_awesome_outlined,
            size: 64,
            color: MemoryAlbumTheme.silver.withOpacity(0.3),
          ),
          const SizedBox(height: 24),
          Text(
            'No memories yet',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w600,
              color: MemoryAlbumTheme.silver.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Save your first memory from a conversation',
            style: TextStyle(
              fontSize: 16,
              color: MemoryAlbumTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMemoryGrid(List memories) {
    final memoryState = ref.watch(memoryAlbumProvider);
    
    // Filter memories based on current filter
    final filteredMemories = memories.where((memory) {
      switch (_currentFilter) {
        case MemoryFilter.starred:
          return memory.isFavorite;
        case MemoryFilter.all:
          return true;
      }
    }).toList();
    
    return CustomScrollView(
      controller: _scrollController,
      slivers: [
        // Header
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(40, 32, 40, 16),
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
                  '${filteredMemories.length} ${filteredMemories.length == 1 ? 'memory' : 'memories'}',
                  style: TextStyle(
                    fontSize: 14,
                    color: MemoryAlbumTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
        
        // Filter tabs
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(40, 0, 40, 24),
            child: _buildFilterTabs(),
          ),
        ),
        
        // Memory grid - single unified grid
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
                final memory = filteredMemories[index];
                return MemoryCard(
                  memory: memory,
                  onTap: () => _openMemoryDetail(memory),
                  onFavoriteToggle: () => _toggleFavorite(memory),
                  onDelete: () => _deleteMemory(memory),
                );
              },
              childCount: filteredMemories.length,
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

  Widget _buildFilterTabs() {
    return Row(
      children: [
        _buildFilterChip('All', MemoryFilter.all, Icons.grid_view_rounded),
        const SizedBox(width: 12),
        _buildFilterChip('Starred', MemoryFilter.starred, Icons.star_rounded),
      ],
    );
  }

  Widget _buildFilterChip(String label, MemoryFilter filter, IconData icon) {
    final isSelected = _currentFilter == filter;
    
    return GestureDetector(
      onTap: () {
        setState(() {
          _currentFilter = filter;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected
              ? MemoryAlbumTheme.gold.withOpacity(0.15)
              : Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected
                ? MemoryAlbumTheme.gold.withOpacity(0.5)
                : MemoryAlbumTheme.silver.withOpacity(0.2),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: isSelected
                  ? MemoryAlbumTheme.gold
                  : MemoryAlbumTheme.silver.withOpacity(0.7),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                color: isSelected
                    ? MemoryAlbumTheme.gold
                    : MemoryAlbumTheme.silver.withOpacity(0.7),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _openMemoryDetail(MemoryEntry memory) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => MemoryDetailScreen(memory: memory),
      ),
    );
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
