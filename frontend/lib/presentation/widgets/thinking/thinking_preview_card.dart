import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:aico_frontend/presentation/providers/conversation_provider.dart';

/// Preview card showing last 2-3 thoughts when hovering over ambient indicator
/// Slides in from right with glassmorphic design
class ThinkingPreviewCard extends StatelessWidget {
  final List<ThinkingTurn> recentThoughts;
  final String? streamingThought;
  final bool isStreaming;
  final VoidCallback onExpand;

  const ThinkingPreviewCard({
    super.key,
    required this.recentThoughts,
    this.streamingThought,
    this.isStreaming = false,
    required this.onExpand,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final purpleAccent = isDark ? const Color(0xFFB9A7E6) : const Color(0xFFB8A1EA);

    // Prepare display items (last 2-3 thoughts)
    final displayItems = <_PreviewItem>[];
    
    // Add streaming thought if present
    if (streamingThought != null && streamingThought!.trim().isNotEmpty) {
      displayItems.add(_PreviewItem(
        content: streamingThought!,
        timestamp: DateTime.now(),
        isStreaming: true,
      ));
    }

    // Add recent completed thoughts (up to 2 more)
    final remainingSlots = 3 - displayItems.length;
    final completedThoughts = recentThoughts.take(remainingSlots).map((turn) {
      return _PreviewItem(
        content: turn.content,
        timestamp: turn.timestamp,
        isStreaming: false,
      );
    }).toList();
    displayItems.addAll(completedThoughts);

    // Calculate how many more thoughts exist
    final moreCount = recentThoughts.length - completedThoughts.length;

    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
        child: Container(
          width: 280,
          constraints: const BoxConstraints(maxHeight: 400),
          decoration: BoxDecoration(
            color: isDark
                ? Colors.white.withValues(alpha: 0.04)
                : Colors.white.withValues(alpha: 0.60),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.20),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.3),
                blurRadius: 40,
                offset: const Offset(8, 0),
                spreadRadius: -10,
              ),
              BoxShadow(
                color: purpleAccent.withValues(alpha: 0.1),
                blurRadius: 60,
                offset: Offset.zero,
                spreadRadius: -5,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              _buildHeader(theme, purpleAccent, isDark),

              // Divider
              Container(
                height: 1,
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.white.withValues(alpha: 0.0),
                      Colors.white.withValues(alpha: 0.1),
                      Colors.white.withValues(alpha: 0.0),
                    ],
                  ),
                ),
              ),

              // Content
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Display thoughts
                      for (int i = 0; i < displayItems.length; i++) ...[
                        if (i > 0) const SizedBox(height: 12),
                        _buildThoughtItem(
                          theme,
                          purpleAccent,
                          displayItems[i],
                        ),
                      ],

                      // More thoughts indicator
                      if (moreCount > 0) ...[
                        const SizedBox(height: 12),
                        Text(
                          '⋮ $moreCount more thought${moreCount == 1 ? '' : 's'}',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.35),
                            fontSize: 11,
                          ),
                        ),
                      ],

                      // Expand action
                      const SizedBox(height: 16),
                      _buildExpandAction(theme, purpleAccent),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(ThemeData theme, Color purpleAccent, bool isDark) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        children: [
          Text(
            'Inner Monologue',
            style: theme.textTheme.titleSmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
              fontWeight: FontWeight.w500,
              fontSize: 11,
              letterSpacing: 0.8,
            ),
          ),
          if (isStreaming) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: purpleAccent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.auto_awesome_rounded,
                    size: 10,
                    color: purpleAccent,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Live',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: purpleAccent.withValues(alpha: 0.8),
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildThoughtItem(ThemeData theme, Color purpleAccent, _PreviewItem item) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Timestamp
        Text(
          _formatTimestamp(item.timestamp),
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.35),
            fontSize: 10,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        // Content (truncated)
        Text(
          _truncateContent(item.content),
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            fontSize: 12,
            height: 1.5,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }

  Widget _buildExpandAction(ThemeData theme, Color purpleAccent) {
    return InkWell(
      onTap: onExpand,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: purpleAccent.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: purpleAccent.withValues(alpha: 0.2),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Expand for full history',
              style: theme.textTheme.labelMedium?.copyWith(
                color: purpleAccent,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: 4),
            Icon(
              Icons.arrow_forward_rounded,
              size: 14,
              color: purpleAccent,
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);

    if (diff.inSeconds < 5) return 'Just now';
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
  }

  String _truncateContent(String content) {
    const maxLength = 60;
    if (content.length <= maxLength) return content;
    return '${content.substring(0, maxLength)}...';
  }
}

class _PreviewItem {
  final String content;
  final DateTime timestamp;
  final bool isStreaming;

  _PreviewItem({
    required this.content,
    required this.timestamp,
    required this.isStreaming,
  });
}
