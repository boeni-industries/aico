import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/presentation/providers/proactive_state_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/data/models/proactive_model.dart';

/// Notification bell icon that appears in the top-right toolbar area.
/// Opens a slide-out drawer with full notification history.
class ProactiveNotificationBell extends ConsumerWidget {
  final Color accentColor;

  const ProactiveNotificationBell({
    super.key,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final proactiveState = ref.watch(proactiveStateProvider);
    final pendingCount = proactiveState.pendingInitiations.length;
    
    return IconButton(
      icon: Stack(
        clipBehavior: Clip.none,
        children: [
          Icon(
            Icons.notifications_outlined,
            color: accentColor,
            size: 24,
          ),
          if (pendingCount > 0)
            Positioned(
              right: -2,
              top: -2,
              child: Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: accentColor,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: accentColor.withValues(alpha: 0.4),
                      blurRadius: 8,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                constraints: const BoxConstraints(
                  minWidth: 18,
                  minHeight: 18,
                ),
                child: Center(
                  child: Text(
                    pendingCount > 9 ? '9+' : '$pendingCount',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
      onPressed: () => _showNotificationDrawer(context),
      tooltip: pendingCount > 0 
          ? '$pendingCount pending notification${pendingCount > 1 ? 's' : ''}'
          : 'Notifications',
    );
  }

  void _showNotificationDrawer(BuildContext context) {
    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Notifications',
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (context, animation, secondaryAnimation) {
        return ProactiveNotificationDrawer(accentColor: accentColor);
      },
      transitionBuilder: (context, animation, secondaryAnimation, child) {
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(1.0, 0.0),
            end: Offset.zero,
          ).animate(CurvedAnimation(
            parent: animation,
            curve: Curves.easeOutCubic,
          )),
          child: child,
        );
      },
    );
  }
}

/// Slide-out drawer showing notification history with filters
class ProactiveNotificationDrawer extends ConsumerStatefulWidget {
  final Color accentColor;

  const ProactiveNotificationDrawer({
    super.key,
    required this.accentColor,
  });

  @override
  ConsumerState<ProactiveNotificationDrawer> createState() => _ProactiveNotificationDrawerState();
}

class _ProactiveNotificationDrawerState extends ConsumerState<ProactiveNotificationDrawer> {
  String _filter = 'all'; // all, pending, answered, dismissed

  @override
  void initState() {
    super.initState();
    // Fetch history when drawer opens
    Future.microtask(() => ref.read(proactiveStateProvider.notifier).fetchHistory());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final proactiveState = ref.watch(proactiveStateProvider);
    
    final allInitiations = [
      ...proactiveState.pendingInitiations,
      ...proactiveState.historyInitiations,
    ];
    
    final filteredInitiations = _filter == 'all'
        ? allInitiations
        : allInitiations.where((i) {
            if (_filter == 'pending') return i.resolutionStatus == 'pending';
            if (_filter == 'answered') return i.resolutionStatus == 'answered';
            if (_filter == 'dismissed') return i.resolutionStatus == 'dismissed' || i.resolutionStatus == 'later';
            return true;
          }).toList();

    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        width: 420,
        height: MediaQuery.of(context).size.height,
        child: ClipRRect(
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(GlassTheme.radiusXLarge),
            bottomLeft: Radius.circular(GlassTheme.radiusXLarge),
          ),
          child: BackdropFilter(
            filter: ImageFilter.blur(
              sigmaX: GlassTheme.blurHeavy,
              sigmaY: GlassTheme.blurHeavy,
            ),
            child: Container(
              decoration: BoxDecoration(
                color: isDark
                    ? Colors.black.withValues(alpha: 0.85)
                    : Colors.white.withValues(alpha: 0.95),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(GlassTheme.radiusXLarge),
                  bottomLeft: Radius.circular(GlassTheme.radiusXLarge),
                ),
                border: Border(
                  left: BorderSide(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.black.withValues(alpha: 0.1),
                    width: 1,
                  ),
                ),
              ),
              child: SafeArea(
                child: Column(
                  children: [
                    // Header
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Row(
                        children: [
                          Icon(
                            Icons.notifications,
                            color: widget.accentColor,
                            size: 28,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Notifications',
                              style: theme.textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () => Navigator.of(context).pop(),
                          ),
                        ],
                      ),
                    ),

                    // Filter tabs
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Row(
                        children: [
                          _buildFilterTab('all', 'All', allInitiations.length),
                          const SizedBox(width: 8),
                          _buildFilterTab('pending', 'Pending', proactiveState.pendingInitiations.length),
                          const SizedBox(width: 8),
                          _buildFilterTab('answered', 'Answered', 
                            allInitiations.where((i) => i.resolutionStatus == 'answered').length),
                          const SizedBox(width: 8),
                          _buildFilterTab('dismissed', 'Dismissed',
                            allInitiations.where((i) => i.resolutionStatus == 'dismissed' || i.resolutionStatus == 'later').length),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    // Notification list
                    Expanded(
                      child: filteredInitiations.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.notifications_none,
                                    size: 64,
                                    color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    'No notifications',
                                    style: theme.textTheme.bodyLarge?.copyWith(
                                      color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                              itemCount: filteredInitiations.length,
                              separatorBuilder: (context, index) => const SizedBox(height: 12),
                              itemBuilder: (context, index) {
                                final initiation = filteredInitiations[index];
                                return _buildNotificationCard(initiation);
                              },
                            ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFilterTab(String value, String label, int count) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final isSelected = _filter == value;

    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => setState(() => _filter = value),
          borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              color: isSelected
                  ? widget.accentColor.withValues(alpha: 0.15)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
              border: Border.all(
                color: isSelected
                    ? widget.accentColor.withValues(alpha: 0.3)
                    : (isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.black.withValues(alpha: 0.1)),
                width: 1,
              ),
            ),
            child: Column(
              children: [
                Text(
                  label,
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                    color: isSelected ? widget.accentColor : null,
                    fontSize: 11,
                  ),
                ),
                if (count > 0)
                  Text(
                    '$count',
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: isSelected ? widget.accentColor : theme.colorScheme.onSurface.withValues(alpha: 0.5),
                      fontSize: 10,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNotificationCard(InitiationModel initiation) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final isPending = initiation.resolutionStatus == 'pending';

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
      child: InkWell(
        onTap: isPending ? () => _showNotificationDetail(initiation) : null,
        borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isPending
                ? widget.accentColor.withValues(alpha: 0.08)
                : (isDark
                    ? Colors.white.withValues(alpha: 0.03)
                    : Colors.black.withValues(alpha: 0.02)),
            borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
            border: Border.all(
              color: isPending
                  ? widget.accentColor.withValues(alpha: 0.2)
                  : (isDark
                      ? Colors.white.withValues(alpha: 0.08)
                      : Colors.black.withValues(alpha: 0.08)),
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
                    size: 16,
                    color: widget.accentColor,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _getTimeAgo(initiation.initiatedAt),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                        fontSize: 12,
                      ),
                    ),
                  ),
                  _buildStatusBadge(initiation.resolutionStatus),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                initiation.question,
                style: theme.textTheme.bodyMedium?.copyWith(
                  height: 1.4,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
              if (isPending) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _buildQuickAction(
                        'Dismiss',
                        Icons.close,
                        () => _handleDismiss(initiation.initiationId),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _buildQuickAction(
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
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    final theme = Theme.of(context);
    Color color;
    String label;

    switch (status) {
      case 'pending':
        color = widget.accentColor;
        label = 'Pending';
        break;
      case 'answered':
        color = Colors.green;
        label = 'Answered';
        break;
      case 'dismissed':
        color = Colors.grey;
        label = 'Dismissed';
        break;
      case 'later':
        color = Colors.orange;
        label = 'Later';
        break;
      default:
        color = Colors.grey;
        label = status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: theme.textTheme.bodySmall?.copyWith(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildQuickAction(String label, IconData icon, VoidCallback onTap) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isDark
                ? Colors.white.withValues(alpha: 0.05)
                : Colors.black.withValues(alpha: 0.03),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.1)
                  : Colors.black.withValues(alpha: 0.1),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 14, color: theme.colorScheme.onSurface.withValues(alpha: 0.7)),
              const SizedBox(width: 4),
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
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

  void _showNotificationDetail(InitiationModel initiation) {
    Navigator.of(context).pop();
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      builder: (context) => ProactiveNotificationDetail(
        initiation: initiation,
        accentColor: widget.accentColor,
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
}

/// Detail dialog for a single notification
class ProactiveNotificationDetail extends ConsumerWidget {
  final InitiationModel initiation;
  final Color accentColor;

  const ProactiveNotificationDetail({
    super.key,
    required this.initiation,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 500),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
          child: BackdropFilter(
            filter: ImageFilter.blur(
              sigmaX: GlassTheme.blurHeavy,
              sigmaY: GlassTheme.blurHeavy,
            ),
            child: Container(
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.04)
                    : Colors.white.withValues(alpha: 0.95),
                borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                border: Border.all(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.1)
                      : Colors.white.withValues(alpha: 0.4),
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
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: accentColor.withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.chat_bubble,
                          color: accentColor,
                          size: 24,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Text(
                          'AICO wants to ask you',
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Text(
                    initiation.question,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      height: 1.6,
                    ),
                  ),
                  const SizedBox(height: 32),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () => _handleAnswer(context, ref),
                      icon: const Icon(Icons.chat),
                      label: const Text('Let\'s talk'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: accentColor,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _handleLater(context, ref),
                          icon: const Icon(Icons.schedule),
                          label: const Text('Later'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _handleDismiss(context, ref),
                          icon: const Icon(Icons.close),
                          label: const Text('Dismiss'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
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
          ),
        ),
      ),
    );
  }

  void _handleAnswer(BuildContext context, WidgetRef ref) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiation.initiationId,
      responseType: 'answered',
    );
    if (context.mounted) Navigator.of(context).pop();
  }

  void _handleLater(BuildContext context, WidgetRef ref) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiation.initiationId,
      responseType: 'later',
    );
    if (context.mounted) Navigator.of(context).pop();
  }

  void _handleDismiss(BuildContext context, WidgetRef ref) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiation.initiationId,
      responseType: 'dismissed',
    );
    if (context.mounted) Navigator.of(context).pop();
  }
}
