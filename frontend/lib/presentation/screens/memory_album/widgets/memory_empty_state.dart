/// Memory Album Empty State
/// 
/// Beautiful empty state with silver book icon and gold shimmer.
/// Inviting, warm, and premium aesthetic.

import 'package:flutter/material.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';

class MemoryEmptyState extends StatefulWidget {
  const MemoryEmptyState({super.key});

  @override
  State<MemoryEmptyState> createState() => _MemoryEmptyStateState();
}

class _MemoryEmptyStateState extends State<MemoryEmptyState> {

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Book icon - same as original
          const Icon(
            Icons.auto_stories,
            size: 64,
            color: Colors.grey,
          ),
          
          const SizedBox(height: 32),
          
          // Title - Silver
          Text(
            'Memory Timeline',
            style: TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.w600,
              color: MemoryAlbumTheme.silver,
              letterSpacing: 0.5,
            ),
          ),
          
          const SizedBox(height: 12),
          
          // Subtitle - Soft gray, italic for warmth
          Text(
            'Our story begins here...',
            style: TextStyle(
              fontSize: 16,
              fontStyle: FontStyle.italic,
              color: MemoryAlbumTheme.textSecondary,
              letterSpacing: 0.3,
            ),
          ),
          
          const SizedBox(height: 40),
          
          // Invitation text
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 20),
            decoration: BoxDecoration(
              color: MemoryAlbumTheme.glassLight,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: MemoryAlbumTheme.glassBorder,
                width: 1.0,
              ),
            ),
            child: Column(
              children: [
                Text(
                  'Save special moments from our conversations',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    color: MemoryAlbumTheme.textSecondary,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.auto_awesome,
                      size: 16,
                      color: MemoryAlbumTheme.gold,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Tap "Remember This" on any message',
                      style: TextStyle(
                        fontSize: 13,
                        color: MemoryAlbumTheme.gold,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
