/// Memory Detail Screen
/// 
/// Full-screen view of a single memory with all details.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';

class MemoryDetailScreen extends ConsumerWidget {
  final MemoryEntry memory;

  const MemoryDetailScreen({
    super.key,
    required this.memory,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: MemoryAlbumTheme.background,
      body: CustomScrollView(
        slivers: [
          // App bar with back button
          SliverAppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            leading: IconButton(
              icon: Icon(
                Icons.arrow_back_rounded,
                color: MemoryAlbumTheme.silver,
              ),
              onPressed: () => Navigator.pop(context),
            ),
            actions: [
              // Favorite toggle
              IconButton(
                icon: Icon(
                  memory.isFavorite
                      ? Icons.star_rounded
                      : Icons.star_outline_rounded,
                  color: memory.isFavorite
                      ? MemoryAlbumTheme.gold
                      : MemoryAlbumTheme.silver.withOpacity(0.7),
                ),
                onPressed: () {
                  ref.read(memoryAlbumProvider.notifier).toggleFavorite(memory);
                },
              ),
              const SizedBox(width: 16),
            ],
          ),

          // Content
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(40, 0, 40, 40),
            sliver: SliverList(
              delegate: SliverChildListDelegate([

                // Title (for conversation memories)
                if (memory.isConversationMemory &&
                    memory.conversationTitle != null) ...[
                  Text(
                    memory.conversationTitle!,
                    style: const TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w600,
                      color: MemoryAlbumTheme.textPrimary,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // Main content
                Text(
                  memory.content,
                  style: const TextStyle(
                    fontSize: 18,
                    color: MemoryAlbumTheme.textPrimary,
                    height: 1.6,
                  ),
                ),

                const SizedBox(height: 32),

                // User note (if any)
                if (memory.userNote != null && memory.userNote!.isNotEmpty) ...[
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: MemoryAlbumTheme.gold.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: MemoryAlbumTheme.gold.withOpacity(0.3),
                        width: 1,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.note_outlined,
                              size: 16,
                              color: MemoryAlbumTheme.gold,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Your Note',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: MemoryAlbumTheme.gold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          memory.userNote!,
                          style: TextStyle(
                            fontSize: 16,
                            color: MemoryAlbumTheme.textPrimary,
                            height: 1.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // Tags (if any)
                if (memory.tags.isNotEmpty) ...[
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: memory.tags.map((tag) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: MemoryAlbumTheme.silver.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: MemoryAlbumTheme.silver.withOpacity(0.3),
                            width: 1,
                          ),
                        ),
                        child: Text(
                          '#$tag',
                          style: TextStyle(
                            fontSize: 13,
                            color: MemoryAlbumTheme.silver,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 24),
                ],

                // Metadata
                const Divider(
                  color: Color(0xFF2A3441),
                  height: 48,
                ),

                _buildMetadataRow(
                  'Created',
                  _formatDate(memory.createdAt),
                  Icons.calendar_today_outlined,
                ),

                if (memory.emotionalTone != null) ...[
                  const SizedBox(height: 16),
                  _buildMetadataRow(
                    'Emotional Tone',
                    memory.emotionalTone!,
                    Icons.mood_outlined,
                  ),
                ],

                const SizedBox(height: 16),
                _buildMetadataRow(
                  'Category',
                  memory.category,
                  Icons.folder_outlined,
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetadataRow(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(
          icon,
          size: 16,
          color: MemoryAlbumTheme.silver.withOpacity(0.5),
        ),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: TextStyle(
            fontSize: 14,
            color: MemoryAlbumTheme.textSecondary,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            color: MemoryAlbumTheme.textPrimary,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
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
