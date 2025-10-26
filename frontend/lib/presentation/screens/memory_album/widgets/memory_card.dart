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

class _MemoryCardState extends State<MemoryCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final emotionalColor = MemoryAlbumTheme.getEmotionalToneColor(
      widget.memory.emotionalTone,
    );

    // Debug: Print favorite status on rebuild
    print('🎨 MemoryCard building: ${widget.memory.memoryId.substring(0, 8)}... isFavorite=${widget.memory.isFavorite}');

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
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
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header: Type indicator + Actions
                    Row(
                      children: [
                        // Type indicator
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: widget.memory.isConversationMemory
                                ? const Color(0xFFB8A1EA).withOpacity(0.15)
                                : MemoryAlbumTheme.silver.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                widget.memory.isConversationMemory
                                    ? Icons.forum_rounded
                                    : Icons.chat_bubble_rounded,
                                size: 14,
                                color: widget.memory.isConversationMemory
                                    ? const Color(0xFFB8A1EA)
                                    : MemoryAlbumTheme.silver.withOpacity(0.7),
                              ),
                              const SizedBox(width: 4),
                              Text(
                                widget.memory.isConversationMemory ? 'Conversation' : 'Message',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: widget.memory.isConversationMemory
                                      ? const Color(0xFFB8A1EA)
                                      : MemoryAlbumTheme.silver.withOpacity(0.7),
                                ),
                              ),
                            ],
                          ),
                        ),
                        
                        const Spacer(),
                        
                        // Delete button
                        if (widget.onDelete != null)
                          Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () {
                                widget.onDelete?.call();
                              },
                              borderRadius: BorderRadius.circular(20),
                              hoverColor: Colors.red.withOpacity(0.2),
                              splashColor: Colors.red.withOpacity(0.3),
                              child: Padding(
                                padding: const EdgeInsets.all(6),
                                child: Icon(
                                  Icons.delete_outline_rounded,
                                  color: MemoryAlbumTheme.silver.withOpacity(0.7),
                                  size: 20,
                                ),
                              ),
                            ),
                          ),
                        
                        const SizedBox(width: 8),
                        
                        // Favorite star
                        Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () {
                              print('⭐ Star tapped! Current state: ${widget.memory.isFavorite}');
                              widget.onFavoriteToggle?.call();
                            },
                            borderRadius: BorderRadius.circular(20),
                            hoverColor: const Color(0xFFFFD700).withOpacity(0.2),
                            splashColor: const Color(0xFFFFD700).withOpacity(0.3),
                            child: Padding(
                              padding: const EdgeInsets.all(6),
                              child: Icon(
                                widget.memory.isFavorite
                                    ? Icons.star_rounded
                                    : Icons.star_outline_rounded,
                                color: widget.memory.isFavorite
                                    ? const Color(0xFFFFD700) // Bright yellow when starred
                                    : MemoryAlbumTheme.silver.withOpacity(0.7),
                                size: 24,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 12),
                    
                    // Content
                    Flexible(
                      child: Text(
                        (widget.memory.isConversationMemory 
                            ? (widget.memory.conversationSummary ?? widget.memory.content)
                            : widget.memory.content).trim(),
                        style: TextStyle(
                          fontSize: 15,
                          color: MemoryAlbumTheme.textPrimary,
                          height: 1.6,
                        ),
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    
                    const SizedBox(height: 12),
                    
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
          ),
    );
  }

  String _formatDate(DateTime date) {
    // Convert UTC to local time
    final localDate = date.toLocal();
    
    // Swiss format: DD.MM.YYYY HH:MM
    final day = localDate.day.toString().padLeft(2, '0');
    final month = localDate.month.toString().padLeft(2, '0');
    final year = localDate.year.toString();
    final hour = localDate.hour.toString().padLeft(2, '0');
    final minute = localDate.minute.toString().padLeft(2, '0');
    
    return '$day.$month.$year $hour:$minute';
  }
}
