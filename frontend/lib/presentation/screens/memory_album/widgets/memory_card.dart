/// Memory Card Widget
/// 
/// Glassmorphic card with premium gold-on-blue aesthetic.
/// Silver borders, gold accents for favorites, emotional tone glows.

import 'package:flutter/material.dart';
import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';

class MemoryCard extends StatefulWidget {
  final MemoryEntry memory;
  final VoidCallback? onTap;
  final VoidCallback? onFavoriteToggle;
  final VoidCallback? onDelete;

  const MemoryCard({
    super.key,
    required this.memory,
    this.onTap,
    this.onFavoriteToggle,
    this.onDelete,
  });

  @override
  State<MemoryCard> createState() => _MemoryCardState();
}

class _MemoryCardState extends State<MemoryCard>
    with SingleTickerProviderStateMixin {
  bool _isHovered = false;
  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    
    // Subtle pulsing glow for favorites
    if (widget.memory.isFavorite) {
      _glowController = AnimationController(
        vsync: this,
        duration: const Duration(seconds: 2),
      )..repeat(reverse: true);
      
      _glowAnimation = Tween<double>(
        begin: 0.15,
        end: 0.25,
      ).animate(CurvedAnimation(
        parent: _glowController,
        curve: Curves.easeInOut,
      ));
    } else {
      _glowController = AnimationController(vsync: this);
      _glowAnimation = AlwaysStoppedAnimation(0.0);
    }
  }

  @override
  void dispose() {
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final emotionalColor = MemoryAlbumTheme.getEmotionalToneColor(
      widget.memory.emotionalTone,
    );

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedBuilder(
        animation: _glowAnimation,
        builder: (context, child) {
          return GestureDetector(
            onTap: widget.onTap,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              transform: Matrix4.identity()
                ..scale(_isHovered ? 1.02 : 1.0),
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: MemoryAlbumTheme.glassCard(
                  isFavorite: widget.memory.isFavorite,
                  emotionalTone: emotionalColor,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header: Icon, Type, Favorite
                    Row(
                      children: [
                        // Memory type icon with color
                        Text(
                          widget.memory.iconEmoji,
                          style: const TextStyle(fontSize: 24),
                        ),
                        const SizedBox(width: 12),
                        
                        // Memory type label
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: MemoryAlbumTheme.getMemoryTypeColor(
                              widget.memory.type.value,
                            ).withOpacity(0.15),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: MemoryAlbumTheme.getMemoryTypeColor(
                                widget.memory.type.value,
                              ).withOpacity(0.3),
                              width: 1.0,
                            ),
                          ),
                          child: Text(
                            widget.memory.type.value.toUpperCase(),
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: MemoryAlbumTheme.getMemoryTypeColor(
                                widget.memory.type.value,
                              ),
                              letterSpacing: 0.8,
                            ),
                          ),
                        ),
                        
                        const Spacer(),
                        
                        // Delete button
                        if (widget.onDelete != null)
                          GestureDetector(
                            onTap: widget.onDelete,
                            child: Icon(
                              Icons.delete_outline_rounded,
                              color: MemoryAlbumTheme.silver.withOpacity(0.5),
                              size: 20,
                            ),
                          ),
                        
                        const SizedBox(width: 12),
                        
                        // Favorite star
                        GestureDetector(
                          onTap: widget.onFavoriteToggle,
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            child: Icon(
                              widget.memory.isFavorite
                                  ? Icons.star_rounded
                                  : Icons.star_outline_rounded,
                              color: widget.memory.isFavorite
                                  ? MemoryAlbumTheme.gold
                                  : MemoryAlbumTheme.silver.withOpacity(0.5),
                              size: 24,
                            ),
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 16),
                    
                    // Content
                    if (widget.memory.isConversationMemory) ...[
                      // Conversation title
                      if (widget.memory.conversationTitle != null)
                        Text(
                          widget.memory.conversationTitle!,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: MemoryAlbumTheme.textPrimary,
                            height: 1.4,
                          ),
                        ),
                      const SizedBox(height: 8),
                      
                      // Conversation summary
                      if (widget.memory.conversationSummary != null)
                        Text(
                          widget.memory.conversationSummary!,
                          style: TextStyle(
                            fontSize: 14,
                            color: MemoryAlbumTheme.textSecondary,
                            height: 1.6,
                          ),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ] else ...[
                      // Message content
                      Text(
                        widget.memory.content,
                        style: const TextStyle(
                          fontSize: 15,
                          color: MemoryAlbumTheme.textPrimary,
                          height: 1.6,
                        ),
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    
                    const SizedBox(height: 16),
                    
                    // Footer: Date, Tags
                    Row(
                      children: [
                        // Date with silver icon
                        Icon(
                          Icons.calendar_today_rounded,
                          size: 14,
                          color: MemoryAlbumTheme.silver.withOpacity(0.6),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _formatDate(widget.memory.createdAt),
                          style: TextStyle(
                            fontSize: 12,
                            color: MemoryAlbumTheme.textTertiary,
                          ),
                        ),
                        
                        const SizedBox(width: 16),
                        
                        // Tags
                        if (widget.memory.tags.isNotEmpty) ...[
                          Icon(
                            Icons.label_rounded,
                            size: 14,
                            color: MemoryAlbumTheme.silver.withOpacity(0.6),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              widget.memory.tags.take(2).join(', '),
                              style: TextStyle(
                                fontSize: 12,
                                color: MemoryAlbumTheme.textTertiary,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);
    
    if (difference.inDays == 0) {
      return 'Today';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else {
      // Simple date format: "Jan 15, 2025"
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return '${months[date.month - 1]} ${date.day}, ${date.year}';
    }
  }
}
