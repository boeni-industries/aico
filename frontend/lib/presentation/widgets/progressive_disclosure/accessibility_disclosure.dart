import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

/// Accessibility-first progressive disclosure widget
/// Ensures proper screen reader support and keyboard navigation
class AccessibilityProgressiveDisclosure extends StatefulWidget {
  final String title;
  final Widget content;
  final Widget? expandedContent;
  final bool initiallyExpanded;
  final String? expandedSemanticLabel;
  final String? collapsedSemanticLabel;
  final VoidCallback? onExpansionChanged;

  const AccessibilityProgressiveDisclosure({
    super.key,
    required this.title,
    required this.content,
    this.expandedContent,
    this.initiallyExpanded = false,
    this.expandedSemanticLabel,
    this.collapsedSemanticLabel,
    this.onExpansionChanged,
  });

  @override
  State<AccessibilityProgressiveDisclosure> createState() => _AccessibilityProgressiveDisclosureState();
}

class _AccessibilityProgressiveDisclosureState extends State<AccessibilityProgressiveDisclosure>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _expandAnimation;
  late bool _isExpanded;

  @override
  void initState() {
    super.initState();
    _isExpanded = widget.initiallyExpanded;
    
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    _expandAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    );
    
    if (_isExpanded) {
      _controller.value = 1.0;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggleExpansion() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
    
    if (_isExpanded) {
      _controller.forward();
    } else {
      _controller.reverse();
    }
    
    widget.onExpansionChanged?.call();
    
    // Announce state change to screen readers
    SemanticsService.announce(
      _isExpanded 
          ? (widget.expandedSemanticLabel ?? '${widget.title} expanded')
          : (widget.collapsedSemanticLabel ?? '${widget.title} collapsed'),
      TextDirection.ltr,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          // Header with expansion button
          Semantics(
            button: true,
            expanded: _isExpanded,
            onTap: _toggleExpansion,
            child: InkWell(
              onTap: _toggleExpansion,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        widget.title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    AnimatedRotation(
                      turns: _isExpanded ? 0.5 : 0,
                      duration: const Duration(milliseconds: 300),
                      child: const Icon(Icons.expand_more),
                    ),
                  ],
                ),
              ),
            ),
          ),
          
          // Always visible content
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: widget.content,
          ),
          
          // Expandable content
          if (widget.expandedContent != null)
            SizeTransition(
              sizeFactor: _expandAnimation,
              child: FadeTransition(
                opacity: _expandAnimation,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: widget.expandedContent!,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// High contrast progressive disclosure for accessibility
class HighContrastDisclosure extends StatelessWidget {
  final String title;
  final Widget content;
  final bool isExpanded;
  final VoidCallback onToggle;

  const HighContrastDisclosure({
    super.key,
    required this.title,
    required this.content,
    required this.isExpanded,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isHighContrast = MediaQuery.of(context).highContrast;
    
    return Container(
      decoration: BoxDecoration(
        border: Border.all(
          color: isHighContrast 
              ? theme.colorScheme.onSurface
              : theme.dividerColor,
          width: isHighContrast ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Semantics(
            button: true,
            expanded: isExpanded,
            child: Material(
              color: isHighContrast 
                  ? (isExpanded ? theme.colorScheme.primary : Colors.transparent)
                  : theme.cardColor,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
              child: InkWell(
                onTap: onToggle,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: theme.textTheme.titleMedium?.copyWith(
                            color: isHighContrast && isExpanded 
                                ? theme.colorScheme.onPrimary
                                : null,
                            fontWeight: isHighContrast 
                                ? FontWeight.bold 
                                : FontWeight.normal,
                          ),
                        ),
                      ),
                      Icon(
                        isExpanded ? Icons.expand_less : Icons.expand_more,
                        color: isHighContrast && isExpanded 
                            ? theme.colorScheme.onPrimary
                            : null,
                        size: isHighContrast ? 28 : 24,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          
          if (isExpanded)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: isHighContrast 
                    ? theme.colorScheme.surface
                    : null,
                borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
              ),
              child: content,
            ),
        ],
      ),
    );
  }
}

/// Screen reader optimized disclosure with detailed announcements
class ScreenReaderOptimizedDisclosure extends StatefulWidget {
  final String title;
  final String? description;
  final Widget content;
  final List<String>? contentSummary;
  final bool announceContentChanges;

  const ScreenReaderOptimizedDisclosure({
    super.key,
    required this.title,
    this.description,
    required this.content,
    this.contentSummary,
    this.announceContentChanges = true,
  });

  @override
  State<ScreenReaderOptimizedDisclosure> createState() => _ScreenReaderOptimizedDisclosureState();
}

class _ScreenReaderOptimizedDisclosureState extends State<ScreenReaderOptimizedDisclosure> {
  bool _isExpanded = false;

  void _toggleExpansion() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
    
    if (widget.announceContentChanges) {
      final announcement = _isExpanded
          ? _buildExpandedAnnouncement()
          : '${widget.title} collapsed';
      
      SemanticsService.announce(announcement, TextDirection.ltr);
    }
  }

  String _buildExpandedAnnouncement() {
    final buffer = StringBuffer('${widget.title} expanded');
    
    if (widget.description != null) {
      buffer.write('. ${widget.description}');
    }
    
    if (widget.contentSummary != null && widget.contentSummary!.isNotEmpty) {
      buffer.write('. Contains: ${widget.contentSummary!.join(', ')}');
    }
    
    return buffer.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Expandable header
          Semantics(
            button: true,
            expanded: _isExpanded,
            hint: _isExpanded ? 'Double tap to collapse' : 'Double tap to expand',
            onTap: _toggleExpansion,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: _toggleExpansion,
                child: Container(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.title,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            if (widget.description != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                widget.description!,
                                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: Colors.grey[600],
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      Semantics(
                        excludeSemantics: true,
                        child: Icon(
                          _isExpanded ? Icons.expand_less : Icons.expand_more,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          
          // Expandable content with semantic boundaries
          if (_isExpanded)
            Semantics(
              container: true,
              label: '${widget.title} content',
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: widget.content,
              ),
            ),
        ],
      ),
    );
  }
}
