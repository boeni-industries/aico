import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/presentation/providers/proactive_state_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/data/models/proactive_model.dart';

/// Timeline view for proactive notifications
/// Matches the design pattern of ThinkingDisplay and EmotionalTimeline
class ProactiveTimeline extends ConsumerStatefulWidget {
  final VoidCallback onCollapse;

  const ProactiveTimeline({
    super.key,
    required this.onCollapse,
  });

  @override
  ConsumerState<ProactiveTimeline> createState() => _ProactiveTimelineState();
}

class _ProactiveTimelineState extends ConsumerState<ProactiveTimeline> {
  String _filter = 'pending'; // pending, all, answered, dismissed

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(proactiveStateProvider.notifier).fetchHistory());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final proactiveState = ref.watch(proactiveStateProvider);
    
    final allInitiations = [
      ...proactiveState.pendingInitiations,
      ...proactiveState.historyInitiations,
    ];
    
    final filteredInitiations = _getFilteredInitiations(allInitiations);

    final isDark = theme.brightness == Brightness.dark;
    final purpleAccent = isDark ? const Color(0xFFB9A7E6) : const Color(0xFFB8A1EA);

    return Column(
      children: [
        // Header with collapse button - matches ThinkingDisplay pattern
        Padding(
          padding: const EdgeInsets.only(left: 12, right: 20, top: 16, bottom: 24),
          child: Row(
            children: [
              // Collapse button
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
                  onPressed: widget.onCollapse,
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
              const SizedBox(width: 12),
              // Title
              Flexible(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.chat_bubble_outline,
                      color: purpleAccent.withValues(alpha: 0.6),
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        'Notifications',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          color: isDark ? Colors.white.withValues(alpha: 0.85) : Colors.black.withValues(alpha: 0.85),
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 40),
            ],
          ),
        ),

        // Filter tabs
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: _buildFilterTabs(theme, allInitiations, isDark),
        ),

        // Timeline list
        Expanded(
          child: filteredInitiations.isEmpty
              ? _buildEmptyState(theme)
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  itemCount: filteredInitiations.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    return _buildTimelineCard(
                      theme,
                      filteredInitiations[index],
                    );
                  },
                ),
        ),
      ],
    );
  }

  List<InitiationModel> _getFilteredInitiations(List<InitiationModel> all) {
    if (_filter == 'all') return all;
    if (_filter == 'pending') {
      return all.where((i) => i.resolutionStatus == 'pending').toList();
    }
    if (_filter == 'answered') {
      return all.where((i) => i.resolutionStatus == 'answered').toList();
    }
    if (_filter == 'dismissed') {
      return all.where((i) => 
        i.resolutionStatus == 'dismissed' || i.resolutionStatus == 'later'
      ).toList();
    }
    return all;
  }

  Widget _buildFilterTabs(ThemeData theme, List<InitiationModel> all, bool isDark) {
    final pendingCount = all.where((i) => i.resolutionStatus == 'pending').length;
    
    return Row(
      children: [
        _buildFilterTab('pending', 'Pending', pendingCount, isDark),
        const SizedBox(width: 8),
        _buildFilterTab('all', 'All', all.length, isDark),
        const SizedBox(width: 8),
        _buildFilterTab('answered', 'Answered', 
          all.where((i) => i.resolutionStatus == 'answered').length, isDark),
        const SizedBox(width: 8),
        _buildFilterTab('dismissed', 'Dismissed',
          all.where((i) => i.resolutionStatus == 'dismissed' || i.resolutionStatus == 'later').length, isDark),
      ],
    );
  }

  Widget _buildFilterTab(String value, String label, int count, bool isDark) {
    final theme = Theme.of(context);
    final isSelected = _filter == value;

    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _filter = value),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: isSelected
                ? Colors.white.withValues(alpha: 0.08)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Column(
            children: [
              Text(
                label,
                style: theme.textTheme.labelSmall?.copyWith(
                  fontSize: 10,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected
                      ? (isDark ? Colors.white.withValues(alpha: 0.9) : Colors.black.withValues(alpha: 0.85))
                      : theme.colorScheme.onSurface.withValues(alpha: 0.5),
                ),
                overflow: TextOverflow.ellipsis,
              ),
              if (count > 0)
                Text(
                  '$count',
                  style: theme.textTheme.labelSmall?.copyWith(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    color: isSelected
                        ? (isDark ? Colors.white.withValues(alpha: 0.7) : Colors.black.withValues(alpha: 0.7))
                        : theme.colorScheme.onSurface.withValues(alpha: 0.4),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 48,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.2),
          ),
          const SizedBox(height: 12),
          Text(
            _filter == 'pending' ? 'No pending questions' : 'No notifications',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineCard(ThemeData theme, InitiationModel initiation) {
    final isPending = initiation.resolutionStatus == 'pending';
    final accentColor = theme.colorScheme.primary;

    return GestureDetector(
      onTap: isPending ? () => _showDetailDialog(initiation) : null,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isPending
              ? Colors.white.withValues(alpha: 0.06)
              : Colors.white.withValues(alpha: 0.02),
          borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
          border: Border.all(
            color: isPending
                ? accentColor.withValues(alpha: 0.2)
                : Colors.white.withValues(alpha: 0.08),
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.chat_bubble_outline,
                  size: 12,
                  color: accentColor.withValues(alpha: 0.7),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    _getTimeAgo(initiation.initiatedAt),
                    style: theme.textTheme.labelSmall?.copyWith(
                      fontSize: 10,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ),
                _buildStatusBadge(theme, initiation.resolutionStatus),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              initiation.question,
              style: theme.textTheme.bodySmall?.copyWith(
                fontSize: 12,
                height: 1.4,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.85),
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            if (isPending) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _buildQuickAction(
                      theme,
                      'Dismiss',
                      Icons.close,
                      () => _handleDismiss(initiation.initiationId),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildQuickAction(
                      theme,
                      'Later',
                      Icons.schedule,
                      () => _handleLater(initiation.initiationId),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(ThemeData theme, String status) {
    Color color;
    String label;

    switch (status) {
      case 'pending':
        color = theme.colorScheme.primary;
        label = 'Pending';
        break;
      case 'answered':
        color = const Color(0xFF8DD686);
        label = 'Answered';
        break;
      case 'dismissed':
        color = Colors.grey;
        label = 'Dismissed';
        break;
      case 'later':
        color = const Color(0xFFED7867);
        label = 'Later';
        break;
      default:
        color = Colors.grey;
        label = status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          color: color,
          fontSize: 9,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildQuickAction(ThemeData theme, String label, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.1),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
            const SizedBox(width: 4),
            Text(
              label,
              style: theme.textTheme.labelSmall?.copyWith(
                fontSize: 10,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getTimeAgo(String timestamp) {
    final dateTime = DateTime.parse(timestamp);
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }

  void _showDetailDialog(InitiationModel initiation) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.6),
      builder: (context) => _ProactiveDetailDialog(
        initiation: initiation,
        onDismiss: () {
          Navigator.of(context).pop();
          _handleDismiss(initiation.initiationId);
        },
        onLater: () {
          Navigator.of(context).pop();
          _handleLater(initiation.initiationId);
        },
        onAnswer: () {
          Navigator.of(context).pop();
          _handleAnswer(initiation.initiationId);
        },
      ),
    );
  }

  void _handleDismiss(String initiationId) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiationId,
      responseType: 'dismissed',
    );
  }

  void _handleLater(String initiationId) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiationId,
      responseType: 'later',
    );
  }

  void _handleAnswer(String initiationId) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiationId,
      responseType: 'answered',
    );
  }
}

/// Detail dialog for a single notification
class _ProactiveDetailDialog extends StatelessWidget {
  final InitiationModel initiation;
  final VoidCallback onDismiss;
  final VoidCallback onLater;
  final VoidCallback onAnswer;

  const _ProactiveDetailDialog({
    required this.initiation,
    required this.onDismiss,
    required this.onLater,
    required this.onAnswer,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accentColor = theme.colorScheme.primary;

    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 440),
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.1),
            width: 1.5,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.chat_bubble,
                    color: accentColor,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'AICO wants to ask you',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(
              initiation.question,
              style: theme.textTheme.bodyMedium?.copyWith(
                height: 1.6,
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: onAnswer,
                icon: const Icon(Icons.chat, size: 16),
                label: const Text('Let\'s talk'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: accentColor,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onLater,
                    icon: const Icon(Icons.schedule, size: 14),
                    label: const Text('Later'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onDismiss,
                    icon: const Icon(Icons.close, size: 14),
                    label: const Text('Dismiss'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
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
