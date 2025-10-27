/// Memory Album Screen
/// 
/// Premium gold-on-blue aesthetic inspired by treasured family photo albums.
/// Deep navy background with silver/gold accents.
library;

import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:aico_frontend/presentation/screens/memory_album/memory_detail_screen.dart';
import 'package:aico_frontend/presentation/screens/memory_album/widgets/memory_card.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class MemoryAlbumScreen extends ConsumerStatefulWidget {
  const MemoryAlbumScreen({super.key});

  @override
  ConsumerState<MemoryAlbumScreen> createState() => _MemoryAlbumScreenState();
}

enum MemoryFilter { all, starred }
enum MemoryViewMode { grid, timeline, story }

class _MemoryAlbumScreenState extends ConsumerState<MemoryAlbumScreen> {
  final ScrollController _scrollController = ScrollController();
  MemoryFilter _currentFilter = MemoryFilter.all;
  MemoryViewMode _viewMode = MemoryViewMode.grid;

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
            color: MemoryAlbumTheme.silver.withValues(alpha: 0.3),
          ),
          const SizedBox(height: 24),
          Text(
            'No memories yet',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w600,
              color: MemoryAlbumTheme.silver.withValues(alpha: 0.7),
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
        
        // Filter tabs and view mode switcher
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(40, 0, 40, 24),
            child: Row(
              children: [
                Expanded(child: _buildFilterTabs()),
                const SizedBox(width: 16),
                _buildViewModeSwitcher(),
              ],
            ),
          ),
        ),
        
        // Memory content based on view mode
        if (_viewMode == MemoryViewMode.grid)
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
          )
        else if (_viewMode == MemoryViewMode.timeline)
          ..._buildTimelineView(filteredMemories)
        else if (_viewMode == MemoryViewMode.story)
          ..._buildStoryView(filteredMemories),
        
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

  Widget _buildViewModeSwitcher() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: MemoryAlbumTheme.silver.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildViewModeIcon(MemoryViewMode.grid, Icons.grid_view_rounded),
          const SizedBox(width: 4),
          _buildViewModeIcon(MemoryViewMode.timeline, Icons.view_timeline_rounded),
          const SizedBox(width: 4),
          _buildViewModeIcon(MemoryViewMode.story, Icons.auto_stories_rounded),
        ],
      ),
    );
  }

  Widget _buildViewModeIcon(MemoryViewMode mode, IconData icon) {
    final isSelected = _viewMode == mode;
    
    return GestureDetector(
      onTap: () {
        setState(() {
          _viewMode = mode;
        });
      },
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: isSelected
              ? MemoryAlbumTheme.gold.withValues(alpha: 0.2)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(
          icon,
          size: 20,
          color: isSelected
              ? MemoryAlbumTheme.gold
              : MemoryAlbumTheme.silver.withValues(alpha: 0.5),
        ),
      ),
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
              ? MemoryAlbumTheme.gold.withValues(alpha: 0.15)
              : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected
                ? MemoryAlbumTheme.gold.withValues(alpha: 0.5)
                : MemoryAlbumTheme.silver.withValues(alpha: 0.2),
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
                  : MemoryAlbumTheme.silver.withValues(alpha: 0.7),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                color: isSelected
                    ? MemoryAlbumTheme.gold
                    : MemoryAlbumTheme.silver.withValues(alpha: 0.7),
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

  List<Widget> _buildTimelineView(List memories) {
    // Single continuous timeline - no grouping, time flows continuously
    return [
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(40, 0, 40, 0),
        sliver: SliverList(
          delegate: SliverChildBuilderDelegate(
            (context, index) {
              final memory = memories[index];
              final isFirst = index == 0;
              final isLast = index == memories.length - 1;
              
              // No padding wrapper - spacing handled inside card with timeline extension
              return _buildTimelineCard(memory, isFirst: isFirst, isLast: isLast);
            },
            childCount: memories.length,
          ),
        ),
      ),
    ];
  }
  
  Widget _buildTimelineCard(MemoryEntry memory, {bool isFirst = false, bool isLast = false}) {
    // Get first 200 characters of content for preview, trim leading newlines
    final rawContent = memory.isConversationMemory 
        ? memory.content
        : memory.conversationSummary ?? memory.content;
    
    // Remove leading newlines
    final trimmedContent = rawContent.replaceAll(RegExp(r'^\n+'), '');
    
    final contentPreview = trimmedContent.length > 200 
        ? '${trimmedContent.substring(0, 200)}...' 
        : trimmedContent;
    
    // First (newest) memory is gold, all others silver
    final isGold = isFirst;
    
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Timeline column with date label and thread (100px to accommodate date)
          SizedBox(
            width: 100,
            child: Stack(
              children: [
                // Continuous thread line - full height
                Column(
                  children: [
                    // Top segment
                    if (isFirst)
                      Align(
                        alignment: Alignment.center,
                        child: SizedBox(
                          height: 40,
                          width: 2,
                          child: CustomPaint(
                            painter: _DottedLinePainter(
                              color: MemoryAlbumTheme.silver.withValues(alpha: 0.3),
                              strokeWidth: 2,
                            ),
                          ),
                        ),
                      )
                    else
                      Align(
                        alignment: Alignment.center,
                        child: Container(
                          width: 2,
                          height: 40,
                          color: MemoryAlbumTheme.silver.withValues(alpha: 0.2),
                        ),
                      ),
                    
                    // Middle segment - continuous through dot area
                    Expanded(
                      child: Align(
                        alignment: Alignment.center,
                        child: Container(
                          width: 2,
                          color: MemoryAlbumTheme.silver.withValues(alpha: 0.2),
                        ),
                      ),
                    ),
                    
                    // Bottom extension
                    if (isLast)
                      Align(
                        alignment: Alignment.center,
                        child: SizedBox(
                          height: 40,
                          width: 2,
                          child: CustomPaint(
                            painter: _DottedLinePainter(
                              color: MemoryAlbumTheme.silver.withValues(alpha: 0.3),
                              strokeWidth: 2,
                            ),
                          ),
                        ),
                      )
                    else
                      Align(
                        alignment: Alignment.center,
                        child: Container(
                          width: 2,
                          height: 16,
                          color: MemoryAlbumTheme.silver.withValues(alpha: 0.2),
                        ),
                      ),
                  ],
                ),
                
                // Date and dot overlaid on top of thread
                Positioned(
                  top: 80, // 40px top segment + 40px spacer
                  left: 0,
                  right: 0,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Date label - fixed width to position dot at 50px
                      SizedBox(
                        width: 34, // 50px (center) - 6px (radius) - 10px (spacing) = 34px
                        child: MouseRegion(
                          cursor: SystemMouseCursors.help,
                          child: Tooltip(
                            message: _formatSwissDate(memory.createdAt),
                            textStyle: const TextStyle(
                              fontSize: 12,
                              color: Colors.white,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.black.withValues(alpha: 0.9),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              _formatShortDate(memory.createdAt),
                              textAlign: TextAlign.right,
                              softWrap: false,
                              maxLines: 1,
                              overflow: TextOverflow.visible,
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w500,
                                color: MemoryAlbumTheme.silver.withValues(alpha: 0.6),
                              ),
                            ),
                          ),
                        ),
                      ),
                      
                      const SizedBox(width: 10), // 10px spacing
                      
                      // Memory node - at 50px (34 + 10 + 6 = 50)
                      MouseRegion(
                        cursor: SystemMouseCursors.help,
                        child: Tooltip(
                          message: _formatSwissDate(memory.createdAt),
                          textStyle: const TextStyle(
                            fontSize: 12,
                            color: Colors.white,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.9),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: isGold
                                  ? MemoryAlbumTheme.gold 
                                  : MemoryAlbumTheme.silver.withValues(alpha: 0.5),
                              boxShadow: isGold ? [
                                BoxShadow(
                                  color: MemoryAlbumTheme.gold.withValues(alpha: 0.4),
                                  blurRadius: 12,
                                  spreadRadius: 2,
                                ),
                              ] : [
                                BoxShadow(
                                  color: MemoryAlbumTheme.silver.withValues(alpha: 0.2),
                                  blurRadius: 4,
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          
          // Memory card content
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(top: 40, bottom: isLast ? 0 : 16),
              child: GestureDetector(
                    onTap: () => _openMemoryDetail(memory),
                    child: Container(
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.04),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.1),
                          width: 1.5,
                        ),
                        boxShadow: [
                          // Floating depth (design principles: multi-layer shadows)
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.4),
                            blurRadius: 20,
                            offset: const Offset(0, 8),
                            spreadRadius: -4,
                          ),
                        ],
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              contentPreview,
                              style: TextStyle(
                                fontSize: 15,
                                color: MemoryAlbumTheme.textPrimary,
                                height: 1.6,
                                letterSpacing: 0.2,
                              ),
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (memory.isFavorite) ...[
                            const SizedBox(width: 12),
                            Icon(
                              Icons.star_rounded,
                              size: 18,
                              color: MemoryAlbumTheme.gold,
                            ),
                          ],
                        ],
                      ),
                    ),
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  String _formatShortDate(DateTime date) {
    final localDate = date.toLocal();
    final day = localDate.day.toString().padLeft(2, '0');
    final month = localDate.month.toString().padLeft(2, '0');
    final year = localDate.year.toString().substring(2); // Get last 2 digits (e.g., "2025" -> "25")
    return '$day.$month.$year';
  }
  
  String _formatSwissDate(DateTime date) {
    final localDate = date.toLocal();
    final day = localDate.day.toString().padLeft(2, '0');
    final month = localDate.month.toString().padLeft(2, '0');
    final year = localDate.year;
    final hour = localDate.hour.toString().padLeft(2, '0');
    final minute = localDate.minute.toString().padLeft(2, '0');
    
    return '$day.$month.$year $hour:$minute';
  }
  
  List<Widget> _buildStoryView(List memories) {
    // TODO: Implement story view
    return [
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.all(40),
          child: Center(
            child: Text(
              'Story view coming soon',
              style: TextStyle(
                fontSize: 16,
                color: MemoryAlbumTheme.textSecondary,
              ),
            ),
          ),
        ),
      ),
    ];
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

// Custom painter for dotted timeline lines
class _DottedLinePainter extends CustomPainter {
  final Color color;
  final double strokeWidth;
  
  _DottedLinePainter({
    required this.color,
    required this.strokeWidth,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    
    const dashHeight = 4.0;
    const dashSpace = 4.0;
    double startY = 0;
    
    while (startY < size.height) {
      canvas.drawLine(
        Offset(size.width / 2, startY),
        Offset(size.width / 2, startY + dashHeight),
        paint,
      );
      startY += dashHeight + dashSpace;
    }
  }
  
  @override
  bool shouldRepaint(_DottedLinePainter oldDelegate) {
    return oldDelegate.color != color || oldDelegate.strokeWidth != strokeWidth;
  }
}
