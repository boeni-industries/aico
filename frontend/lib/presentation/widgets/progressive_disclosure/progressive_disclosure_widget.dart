import 'package:flutter/material.dart';

/// A widget that implements progressive disclosure UI pattern
/// Shows content in stages based on user interaction and context
class ProgressiveDisclosureWidget extends StatefulWidget {
  final Widget initialContent;
  final List<ProgressiveDisclosureLevel> levels;
  final bool autoExpand;
  final Duration animationDuration;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onExpansionChanged;

  const ProgressiveDisclosureWidget({
    super.key,
    required this.initialContent,
    required this.levels,
    this.autoExpand = false,
    this.animationDuration = const Duration(milliseconds: 300),
    this.padding,
    this.onExpansionChanged,
  });

  @override
  State<ProgressiveDisclosureWidget> createState() => _ProgressiveDisclosureWidgetState();
}

class _ProgressiveDisclosureWidgetState extends State<ProgressiveDisclosureWidget>
    with TickerProviderStateMixin {
  late List<AnimationController> _controllers;
  late List<Animation<double>> _animations;
  int _currentLevel = 0;

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
  }

  void _initializeAnimations() {
    _controllers = List.generate(
      widget.levels.length,
      (index) => AnimationController(
        duration: widget.animationDuration,
        vsync: this,
      ),
    );

    _animations = _controllers.map((controller) {
      return CurvedAnimation(
        parent: controller,
        curve: Curves.easeInOut,
      );
    }).toList();
  }

  @override
  void dispose() {
    for (final controller in _controllers) {
      controller.dispose();
    }
    super.dispose();
  }

  void _expandToLevel(int level) {
    if (level < 0 || level >= widget.levels.length) return;
    
    setState(() {
      _currentLevel = level;
    });

    // Animate controllers up to the target level
    for (int i = 0; i <= level; i++) {
      _controllers[i].forward();
    }

    // Reverse controllers beyond the target level
    for (int i = level + 1; i < _controllers.length; i++) {
      _controllers[i].reverse();
    }

    widget.onExpansionChanged?.call();
  }

  void _expandNext() {
    if (_currentLevel < widget.levels.length - 1) {
      _expandToLevel(_currentLevel + 1);
    }
  }


  @override
  Widget build(BuildContext context) {
    return Container(
      padding: widget.padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Initial content is always visible
          widget.initialContent,
          
          // Progressive disclosure levels
          ...widget.levels.asMap().entries.map((entry) {
            final index = entry.key;
            final level = entry.value;
            
            return AnimatedBuilder(
              animation: _animations[index],
              builder: (context, child) {
                return SizeTransition(
                  sizeFactor: _animations[index],
                  child: FadeTransition(
                    opacity: _animations[index],
                    child: Container(
                      width: double.infinity,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (level.showDivider && _animations[index].value > 0)
                            const Divider(),
                          
                          level.content,
                          
                          // Show expansion trigger if this is the current level
                          if (index == _currentLevel && level.expansionTrigger != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 8.0),
                              child: InkWell(
                                onTap: _expandNext,
                                child: level.expansionTrigger!,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            );
          }).toList(),
        ],
      ),
    );
  }
}

/// Represents a level in progressive disclosure
class ProgressiveDisclosureLevel {
  final Widget content;
  final Widget? expansionTrigger;
  final bool showDivider;
  final String? accessibilityLabel;

  const ProgressiveDisclosureLevel({
    required this.content,
    this.expansionTrigger,
    this.showDivider = false,
    this.accessibilityLabel,
  });
}

/// Adaptive progressive disclosure that responds to screen size
class AdaptiveProgressiveDisclosure extends StatelessWidget {
  final Widget compactContent;
  final Widget expandedContent;
  final double breakpoint;
  final Widget? trigger;

  const AdaptiveProgressiveDisclosure({
    super.key,
    required this.compactContent,
    required this.expandedContent,
    this.breakpoint = 600.0,
    this.trigger,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < breakpoint;
        
        if (isCompact && trigger != null) {
          return ProgressiveDisclosureWidget(
            initialContent: compactContent,
            levels: [
              ProgressiveDisclosureLevel(
                content: expandedContent,
                expansionTrigger: trigger,
              ),
            ],
          );
        }
        
        return isCompact ? compactContent : expandedContent;
      },
    );
  }
}

/// Context-aware progressive disclosure for complex forms
class ContextualDisclosure extends StatefulWidget {
  final Map<String, Widget> contexts;
  final String initialContext;
  final Widget Function(String context, void Function(String) switchContext)? contextSwitcher;

  const ContextualDisclosure({
    super.key,
    required this.contexts,
    required this.initialContext,
    this.contextSwitcher,
  });

  @override
  State<ContextualDisclosure> createState() => _ContextualDisclosureState();
}

class _ContextualDisclosureState extends State<ContextualDisclosure> {
  late String _currentContext;

  @override
  void initState() {
    super.initState();
    _currentContext = widget.initialContext;
  }

  void _switchContext(String newContext) {
    if (widget.contexts.containsKey(newContext)) {
      setState(() {
        _currentContext = newContext;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (widget.contextSwitcher != null)
          widget.contextSwitcher!(_currentContext, _switchContext),
        
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: Container(
            key: ValueKey(_currentContext),
            child: widget.contexts[_currentContext] ?? const SizedBox.shrink(),
          ),
        ),
      ],
    );
  }
}
