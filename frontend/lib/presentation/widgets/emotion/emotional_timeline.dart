import 'dart:ui';

import 'package:aico_frontend/data/models/emotion_model.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotion_color_mapper.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotion_formatter.dart';
import 'package:flutter/material.dart';

/// Beautiful emotional timeline showing AI's emotional journey
class EmotionalTimeline extends StatelessWidget {
  final List<EmotionHistoryItem> emotionHistory;
  final bool isLoading;
  final VoidCallback? onCollapse;

  const EmotionalTimeline({
    super.key,
    required this.emotionHistory,
    this.isLoading = false,
    this.onCollapse,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // AICO soft purple accent (matches thinking display)
    final purpleAccent = isDark 
        ? const Color(0xFFB9A7E6)
        : const Color(0xFFB8A1EA);

    return Column(
      children: [
        // Header with collapse button (matches thinking display exactly)
        Padding(
          padding: const EdgeInsets.only(left: 12, right: 20, top: 16, bottom: 24),
          child: Row(
            children: [
              // Collapse button on left (matches thinking display)
              if (onCollapse != null)
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.06)
                        : Colors.white.withValues(alpha: 0.8),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.1)
                          : Colors.white.withValues(alpha: 0.3),
                      width: 1,
                    ),
                  ),
                  child: IconButton(
                    onPressed: onCollapse,
                    icon: Icon(
                      Icons.chevron_right,
                      color: purpleAccent.withValues(alpha: 0.6),
                      size: 16,
                    ),
                    tooltip: 'Collapse',
                    padding: EdgeInsets.zero,
                    iconSize: 16,
                  ),
                ),
              if (onCollapse != null) const SizedBox(width: 12),
              // Centered content (matches thinking display)
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Heart icon for emotions
                    Icon(
                      Icons.favorite,
                      size: 14,
                      color: purpleAccent.withValues(alpha: 0.7),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Emotional Journey',
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                        fontWeight: FontWeight.w500,
                        fontSize: 11,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        // Content
        Expanded(
          child: isLoading
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32.0),
                    child: CircularProgressIndicator(),
                  ),
                )
              : emotionHistory.isEmpty
                  ? _buildEmptyState(context)
                  : Stack(
                      children: [
                        // Continuous vertical line in background
                        if (emotionHistory.length > 1)
                          Positioned(
                            left: 32, // 16 padding + 16 (center of 32px timeline width)
                            top: 16, // Start below first dot
                            bottom: 0,
                            child: Container(
                              width: 2,
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.15),
                              ),
                            ),
                          ),
                        // Timeline items
                        ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          itemCount: emotionHistory.length,
                          itemBuilder: (context, index) {
                            final emotion = emotionHistory[index];
                            final isFirst = index == 0;
                            final isLast = index == emotionHistory.length - 1;

                            return _EmotionTimelineItem(
                              emotion: emotion,
                              isFirst: isFirst,
                              isLast: isLast,
                            );
                          },
                        ),
                      ],
                    ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.favorite_outline,
              size: 48,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
            ),
            const SizedBox(height: 16),
            Text(
              'No emotional history yet',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Start a conversation to see\nthe emotional journey',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmotionTimelineItem extends StatefulWidget {
  final EmotionHistoryItem emotion;
  final bool isFirst;
  final bool isLast;

  const _EmotionTimelineItem({
    required this.emotion,
    required this.isFirst,
    required this.isLast,
  });

  @override
  State<_EmotionTimelineItem> createState() => _EmotionTimelineItemState();
}

class _EmotionTimelineItemState extends State<_EmotionTimelineItem> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final emotionColor = EmotionColorMapper.getColor(widget.emotion.feeling);
    final emotionLabel = EmotionFormatter.formatLabel(widget.emotion.feeling);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline dot (line is in Stack background)
          SizedBox(
            width: 32,
            child: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: emotionColor,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isDark
                        ? Colors.black.withValues(alpha: 0.3)
                        : Colors.white.withValues(alpha: 0.5),
                    width: 2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: emotionColor.withValues(alpha: 0.5),
                      blurRadius: 8,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ),
            ),
          ),
            const SizedBox(width: 12),
            // Emotion card
            Expanded(
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _isExpanded = !_isExpanded;
                });
              },
              child: ClipRRect(
                borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          emotionColor.withValues(alpha: 0.12),
                          emotionColor.withValues(alpha: 0.06),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                      border: Border.all(
                        color: emotionColor.withValues(alpha: 0.2),
                        width: 1,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Header: emotion label + timestamp
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                emotionLabel,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: emotionColor,
                                  letterSpacing: 0.02,
                                ),
                              ),
                            ),
                            Text(
                              _formatTimestamp(widget.emotion.timestamp),
                              style: theme.textTheme.labelSmall?.copyWith(
                                fontSize: 10,
                                fontWeight: FontWeight.w500,
                                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        // Emotion metrics mini-visualization
                        _buildMetricsBar(emotionColor),
                        // Expanded details
                        if (_isExpanded) ...[
                          const SizedBox(height: 12),
                          _buildExpandedDetails(theme, emotionColor),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsBar(Color emotionColor) {
    return Row(
      children: [
        _MetricIndicator(
          label: 'V',
          value: widget.emotion.valence,
          color: emotionColor,
          tooltip: 'Valence (positive/negative)',
        ),
        const SizedBox(width: 8),
        _MetricIndicator(
          label: 'A',
          value: widget.emotion.arousal,
          color: emotionColor,
          tooltip: 'Arousal (energy level)',
        ),
        const SizedBox(width: 8),
        _MetricIndicator(
          label: 'I',
          value: widget.emotion.intensity,
          color: emotionColor,
          tooltip: 'Intensity',
        ),
      ],
    );
  }

  Widget _buildExpandedDetails(ThemeData theme, Color emotionColor) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _DetailRow(
            label: 'Valence',
            value: widget.emotion.valence,
            description: widget.emotion.valence > 0 ? 'Positive' : 'Negative',
            color: emotionColor,
          ),
          const SizedBox(height: 6),
          _DetailRow(
            label: 'Arousal',
            value: widget.emotion.arousal,
            description: EmotionFormatter.getArousalLabel(widget.emotion.arousal),
            color: emotionColor,
          ),
          const SizedBox(height: 6),
          _DetailRow(
            label: 'Intensity',
            value: widget.emotion.intensity,
            description: '${(widget.emotion.intensity * 100).round()}%',
            color: emotionColor,
          ),
        ],
      ),
    );
  }

  String _formatTimestamp(String timestamp) {
    try {
      final dateTime = DateTime.parse(timestamp);
      final now = DateTime.now();
      final difference = now.difference(dateTime);

      if (difference.inSeconds < 60) {
        return '${difference.inSeconds}s ago';
      } else if (difference.inMinutes < 60) {
        return '${difference.inMinutes}m ago';
      } else if (difference.inHours < 24) {
        return '${difference.inHours}h ago';
      } else {
        return '${difference.inDays}d ago';
      }
    } catch (e) {
      return 'recently';
    }
  }
}

class _MetricIndicator extends StatelessWidget {
  final String label;
  final double value;
  final Color color;
  final String tooltip;

  const _MetricIndicator({
    required this.label,
    required this.value,
    required this.color,
    required this.tooltip,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final normalizedValue = (value + 1) / 2; // Convert -1..1 to 0..1

    return Expanded(
      child: Tooltip(
        message: '$tooltip: ${(normalizedValue * 100).round()}%',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: theme.textTheme.labelSmall?.copyWith(
                fontSize: 9,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                letterSpacing: 0.05,
              ),
            ),
            const SizedBox(height: 4),
            Stack(
              children: [
                // Background bar with border (shows 100%)
                Container(
                  height: 8,
                  decoration: BoxDecoration(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.5),
                      width: 1,
                    ),
                  ),
                ),
                // Filled portion (shows actual value)
                Padding(
                  padding: const EdgeInsets.all(1),
                  child: FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: normalizedValue.clamp(0.0, 1.0),
                    child: Container(
                      height: 6,
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final double value;
  final String description;
  final Color color;

  const _DetailRow({
    required this.label,
    required this.value,
    required this.description,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      children: [
        SizedBox(
          width: 60,
          child: Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ),
        Expanded(
          child: Container(
            height: 6,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(3),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: ((value + 1) / 2).clamp(0.0, 1.0),
              child: Container(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 60,
          child: Text(
            description,
            textAlign: TextAlign.end,
            style: theme.textTheme.labelSmall?.copyWith(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ),
      ],
    );
  }
}
