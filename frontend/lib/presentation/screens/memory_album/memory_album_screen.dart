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
import 'package:aico_frontend/presentation/widgets/timeline/timeline_widget.dart';
import 'package:aico_frontend/presentation/widgets/journey_map/journey_map_widget.dart';
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

  void _deleteMemory(MemoryEntry memory) {
    // TODO: Implement delete functionality
    ref.read(memoryAlbumProvider.notifier).deleteMemory(memory.memoryId);
  }

  List<Widget> _buildStoryView(List memories) {
    // Convert memories to journey nodes
    final nodes = memories.map<JourneyNode>((memory) {
      return JourneyNode(
        id: memory.memoryId,
        timestamp: memory.createdAt,
        title: _extractTitle(memory),
        preview: _extractPreview(memory),
        isFavorite: memory.isFavorite,
        isMilestone: _isMilestone(memory, memories),
        revisitCount: 0, // TODO: Track revisit count
        hasNote: memory.userNote != null && memory.userNote!.isNotEmpty,
        color: memory.isConversationMemory 
            ? MemoryAlbumTheme.gold 
            : MemoryAlbumTheme.silver,
        onTap: () => _openMemoryDetail(memory),
      );
    }).toList();
    
    // Auto-detect chapters
    final chapters = _detectChapters(memories);
    
    return [
      SliverToBoxAdapter(
        child: SizedBox(
          height: MediaQuery.of(context).size.height - 200,
          child: JourneyMapWidget(
            nodes: nodes,
            chapters: chapters,
            initialZoom: 1.0,
          ),
        ),
      ),
    ];
  }
  
  String _extractTitle(MemoryEntry memory) {
    final content = memory.conversationSummary ?? memory.content;
    
    // Remove leading/trailing whitespace and newlines
    final cleaned = content.trim();
    if (cleaned.isEmpty) return 'Untitled Memory';
    
    // Extract first non-empty line
    final lines = cleaned.split('\n');
    String firstLine = '';
    for (final line in lines) {
      final trimmed = line.trim();
      if (trimmed.isNotEmpty) {
        firstLine = trimmed;
        break;
      }
    }
    
    if (firstLine.isEmpty) return 'Untitled Memory';
    
    // If it starts with "You:" or "AICO:", extract the actual content
    if (firstLine.startsWith('You:')) {
      firstLine = firstLine.substring(4).trim();
    } else if (firstLine.startsWith('AICO:')) {
      firstLine = firstLine.substring(5).trim();
    }
    
    return firstLine.length > 50 
        ? '${firstLine.substring(0, 50)}...' 
        : firstLine;
  }
  
  String _extractPreview(MemoryEntry memory) {
    final content = memory.conversationSummary ?? memory.content;
    
    // Remove leading/trailing whitespace
    final cleaned = content.trim();
    if (cleaned.isEmpty) return '';
    
    return cleaned.length > 100 
        ? '${cleaned.substring(0, 100)}...' 
        : cleaned;
  }
  
  bool _isMilestone(MemoryEntry memory, List memories) {
    final index = memories.indexOf(memory);
    // Mark every 10th, 50th, 100th memory as milestone
    final count = memories.length - index;
    return count == 1 || count == 10 || count == 50 || count == 100 || count == 250;
  }
  
  List<JourneyChapter> _detectChapters(List memories) {
    if (memories.isEmpty) return [];
    
    // Simple chapter detection: group by month
    final chapters = <JourneyChapter>[];
    DateTime? currentStart;
    int currentCount = 0;
    
    for (int i = 0; i < memories.length; i++) {
      final memory = memories[i];
      final date = memory.createdAt;
      
      if (currentStart == null) {
        currentStart = date;
        currentCount = 1;
      } else if (date.month != currentStart.month || date.year != currentStart.year) {
        // New chapter
        chapters.add(JourneyChapter(
          title: _getMonthName(currentStart.month),
          emoji: _getChapterEmoji(chapters.length),
          startDate: currentStart,
          endDate: memories[i - 1].createdAt,
          color: _getChapterColor(chapters.length),
          memoryCount: currentCount,
        ));
        currentStart = date;
        currentCount = 1;
      } else {
        currentCount++;
      }
    }
    
    // Add last chapter
    if (currentStart != null) {
      chapters.add(JourneyChapter(
        title: _getMonthName(currentStart.month),
        emoji: _getChapterEmoji(chapters.length),
        startDate: currentStart,
        endDate: memories.last.createdAt,
        color: _getChapterColor(chapters.length),
        memoryCount: currentCount,
      ));
    }
    
    return chapters;
  }
  
  String _getMonthName(int month) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[month - 1];
  }
  
  String _getChapterEmoji(int index) {
    const emojis = ['🌱', '💡', '🌟', '🎯', '🚀', '💫', '🌈', '✨'];
    return emojis[index % emojis.length];
  }
  
  Color _getChapterColor(int index) {
    const colors = [
      Color(0xFFB8A1EA), // Purple
      Color(0xFF8DD686), // Green
      Color(0xFF8DD6B8), // Mint
      Color(0xFFE8A87C), // Orange
      Color(0xFF85C1E2), // Blue
    ];
    return colors[index % colors.length];
  }

  List<Widget> _buildTimelineView(List memories) {
    // Convert memories to timeline entries
    final timelineEntries = memories.map<TimelineEntry>((memory) {
      final isFirst = memories.indexOf(memory) == 0;
      
      return TimelineEntry(
        timestamp: memory.createdAt,
        label: Text(_formatShortDate(memory.createdAt)),
        isHighlighted: isFirst, // First (newest) is highlighted
        content: _buildMemoryCard(memory),
      );
    }).toList();
    
    return [
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(40, 0, 40, 0),
        sliver: SliverToBoxAdapter(
          child: TimelineWidget(
            entries: timelineEntries,
            axis: Axis.vertical,
            style: TimelineStyle(
              threadColor: MemoryAlbumTheme.silver,
              threadWidth: 2.0,
              nodeColor: MemoryAlbumTheme.silver,
              nodeSize: 12.0,
              highlightedNodeColor: MemoryAlbumTheme.gold,
              highlightedNodeSize: 12.0,
              nodeLabelSpacing: 14.0,
              contentSpacing: 16.0,
              threadNodeSpacing: 0.0, // Not used - dots will be centered on content
              labelTextStyle: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: MemoryAlbumTheme.silver.withValues(alpha: 0.6),
              ),
              showDottedEnds: true,
            ),
            threadPosition: 0.5, // Thread at 50px in 100px column
          ),
        ),
      ),
    ];
  }
  
  Widget _buildMemoryCard(MemoryEntry memory) {
    // Extract user query for conversation memories
    String contentPreview;
    if (memory.isConversationMemory) {
      // Parse conversation to extract just the user's query
      final lines = memory.content.split('\n');
      final userLines = <String>[];
      bool isUserMessage = false;
      
      for (final line in lines) {
        if (line.startsWith('You:')) {
          isUserMessage = true;
          userLines.add(line.substring(4).trim());
        } else if (line.startsWith('AICO:')) {
          break; // Stop at first AICO response
        } else if (isUserMessage && line.trim().isNotEmpty) {
          userLines.add(line.trim());
        }
      }
      
      final userQuery = userLines.join(' ').trim();
      contentPreview = userQuery.length > 500 
          ? '${userQuery.substring(0, 500)}...' 
          : userQuery;
    } else {
      // For non-conversation memories, use summary or content
      final rawContent = memory.conversationSummary ?? memory.content;
      final trimmedContent = rawContent.replaceAll(RegExp(r'^\n+'), '');
      contentPreview = trimmedContent.length > 500 
          ? '${trimmedContent.substring(0, 500)}...' 
          : trimmedContent;
    }
    
    return GestureDetector(
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
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.4),
              blurRadius: 20,
              offset: const Offset(0, 8),
              spreadRadius: -4,
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Content preview
            Text(
              contentPreview,
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 14,
                height: 1.5,
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Tags and favorite
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Type badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: memory.isConversationMemory 
                        ? MemoryAlbumTheme.gold.withValues(alpha: 0.15)
                        : MemoryAlbumTheme.silver.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: memory.isConversationMemory 
                          ? MemoryAlbumTheme.gold.withValues(alpha: 0.3)
                          : MemoryAlbumTheme.silver.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Text(
                    memory.isConversationMemory ? 'Conversation' : 'Message',
                    style: TextStyle(
                      color: memory.isConversationMemory 
                          ? MemoryAlbumTheme.gold
                          : MemoryAlbumTheme.silver,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                
                const SizedBox(width: 8),
                
                // Tags
                if (memory.tags.isNotEmpty)
                  Expanded(
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: memory.tags.take(2).map((tag) {
                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: MemoryAlbumTheme.silver.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: MemoryAlbumTheme.silver.withValues(alpha: 0.2),
                            ),
                          ),
                          child: Text(
                            tag,
                            style: TextStyle(
                              color: MemoryAlbumTheme.silver.withValues(alpha: 0.8),
                              fontSize: 11,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  )
                else
                  const Spacer(),
                
                // Favorite star - right aligned
                IconButton(
                  icon: Icon(
                    memory.isFavorite ? Icons.star : Icons.star_border,
                    color: memory.isFavorite ? MemoryAlbumTheme.gold : MemoryAlbumTheme.silver.withValues(alpha: 0.5),
                    size: 20,
                  ),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  onPressed: () => _toggleFavorite(memory),
                ),
              ],
            ),
          ],
        ),
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
  
}
