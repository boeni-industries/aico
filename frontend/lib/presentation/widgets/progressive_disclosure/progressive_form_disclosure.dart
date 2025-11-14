import 'package:flutter/material.dart';

/// Progressive disclosure specifically designed for forms
/// Reveals form sections based on user input and validation state
class ProgressiveFormDisclosure extends StatefulWidget {
  final List<FormDisclosureSection> sections;
  final GlobalKey<FormState>? formKey;
  final EdgeInsetsGeometry? padding;
  final bool validateBeforeExpansion;
  final VoidCallback? onSectionChanged;

  const ProgressiveFormDisclosure({
    super.key,
    required this.sections,
    this.formKey,
    this.padding,
    this.validateBeforeExpansion = true,
    this.onSectionChanged,
  });

  @override
  State<ProgressiveFormDisclosure> createState() => _ProgressiveFormDisclosureState();
}

class _ProgressiveFormDisclosureState extends State<ProgressiveFormDisclosure> {
  int _currentSection = 0;
  final Map<int, bool> _sectionValidation = {};

  @override
  void initState() {
    super.initState();
    _sectionValidation[0] = false; // First section starts as invalid
  }

  bool _canExpandToSection(int sectionIndex) {
    if (!widget.validateBeforeExpansion) return true;
    
    // Check if all previous sections are valid
    for (int i = 0; i < sectionIndex; i++) {
      if (_sectionValidation[i] != true) {
        return false;
      }
    }
    return true;
  }

  void _validateCurrentSection() {
    if (widget.formKey?.currentState?.validate() ?? false) {
      setState(() {
        _sectionValidation[_currentSection] = true;
      });
      
      // Auto-expand to next section if validation passes
      if (_currentSection < widget.sections.length - 1) {
        _expandToSection(_currentSection + 1);
      }
    } else {
      setState(() {
        _sectionValidation[_currentSection] = false;
      });
    }
  }

  void _expandToSection(int sectionIndex) {
    if (!_canExpandToSection(sectionIndex)) return;
    
    setState(() {
      _currentSection = sectionIndex;
    });
    
    widget.onSectionChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: widget.padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Section indicators
          _buildSectionIndicators(),
          
          const SizedBox(height: 16),
          
          // Form sections with progressive disclosure
          ...widget.sections.asMap().entries.map((entry) {
            final index = entry.key;
            final section = entry.value;
            final isVisible = index <= _currentSection;
            final isValid = _sectionValidation[index] == true;
            
            return AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: isVisible ? null : 0,
              child: AnimatedOpacity(
                duration: const Duration(milliseconds: 300),
                opacity: isVisible ? 1.0 : 0.0,
                child: Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Section header
                        Row(
                          children: [
                            Icon(
                              isValid ? Icons.check_circle : Icons.radio_button_unchecked,
                              color: isValid ? Colors.green : Colors.grey,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              section.title,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ],
                        ),
                        
                        if (section.description != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            section.description!,
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                        
                        const SizedBox(height: 16),
                        
                        // Section content
                        section.content,
                        
                        // Navigation buttons for current section
                        if (index == _currentSection) ...[
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              // Previous button
                              if (index > 0)
                                TextButton(
                                  onPressed: () => _expandToSection(index - 1),
                                  child: const Text('Previous'),
                                ),
                              
                              const Spacer(),
                              
                              // Next/Validate button
                              ElevatedButton(
                                onPressed: _validateCurrentSection,
                                child: Text(
                                  index == widget.sections.length - 1 
                                      ? 'Complete' 
                                      : 'Next',
                                ),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildSectionIndicators() {
    return Row(
      children: widget.sections.asMap().entries.map((entry) {
        final index = entry.key;
        final section = entry.value;
        final isCompleted = _sectionValidation[index] == true;
        final isCurrent = index == _currentSection;
        final isAccessible = _canExpandToSection(index);
        
        return Expanded(
          child: GestureDetector(
            onTap: isAccessible ? () => _expandToSection(index) : null,
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
              decoration: BoxDecoration(
                color: isCurrent 
                    ? Theme.of(context).primaryColor.withValues(alpha: 0.1)
                    : isCompleted 
                        ? Colors.green.withValues(alpha: 0.1)
                        : Colors.grey.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isCurrent 
                      ? Theme.of(context).primaryColor
                      : isCompleted 
                          ? Colors.green
                          : Colors.grey,
                  width: isCurrent ? 2 : 1,
                ),
              ),
              child: Column(
                children: [
                  Icon(
                    isCompleted 
                        ? Icons.check_circle
                        : isCurrent 
                            ? Icons.radio_button_checked
                            : Icons.radio_button_unchecked,
                    color: isCurrent 
                        ? Theme.of(context).primaryColor
                        : isCompleted 
                            ? Colors.green
                            : Colors.grey,
                    size: 20,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    section.title,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: isCurrent 
                          ? Theme.of(context).primaryColor
                          : isCompleted 
                              ? Colors.green
                              : Colors.grey,
                      fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

/// Represents a section in progressive form disclosure
class FormDisclosureSection {
  final String title;
  final String? description;
  final Widget content;
  final bool Function()? validator;

  const FormDisclosureSection({
    required this.title,
    this.description,
    required this.content,
    this.validator,
  });
}

/// Smart disclosure that adapts based on user expertise level
class ExpertiseAwareDisclosure extends StatefulWidget {
  final Widget beginnerContent;
  final Widget intermediateContent;
  final Widget expertContent;
  final UserExpertiseLevel initialLevel;
  final VoidCallback? onLevelChanged;

  const ExpertiseAwareDisclosure({
    super.key,
    required this.beginnerContent,
    required this.intermediateContent,
    required this.expertContent,
    this.initialLevel = UserExpertiseLevel.beginner,
    this.onLevelChanged,
  });

  @override
  State<ExpertiseAwareDisclosure> createState() => _ExpertiseAwareDisclosureState();
}

class _ExpertiseAwareDisclosureState extends State<ExpertiseAwareDisclosure> {
  late UserExpertiseLevel _currentLevel;

  @override
  void initState() {
    super.initState();
    _currentLevel = widget.initialLevel;
  }

  void _setExpertiseLevel(UserExpertiseLevel level) {
    setState(() {
      _currentLevel = level;
    });
    widget.onLevelChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Expertise level selector
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Interface Complexity',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                SegmentedButton<UserExpertiseLevel>(
                  segments: const [
                    ButtonSegment(
                      value: UserExpertiseLevel.beginner,
                      label: Text('Simple'),
                      icon: Icon(Icons.sentiment_satisfied),
                    ),
                    ButtonSegment(
                      value: UserExpertiseLevel.intermediate,
                      label: Text('Standard'),
                      icon: Icon(Icons.sentiment_neutral),
                    ),
                    ButtonSegment(
                      value: UserExpertiseLevel.expert,
                      label: Text('Advanced'),
                      icon: Icon(Icons.sentiment_very_satisfied),
                    ),
                  ],
                  selected: {_currentLevel},
                  onSelectionChanged: (Set<UserExpertiseLevel> selection) {
                    _setExpertiseLevel(selection.first);
                  },
                ),
              ],
            ),
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Content based on expertise level
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: Container(
            key: ValueKey(_currentLevel),
            child: _getContentForLevel(),
          ),
        ),
      ],
    );
  }

  Widget _getContentForLevel() {
    switch (_currentLevel) {
      case UserExpertiseLevel.beginner:
        return widget.beginnerContent;
      case UserExpertiseLevel.intermediate:
        return widget.intermediateContent;
      case UserExpertiseLevel.expert:
        return widget.expertContent;
    }
  }
}

enum UserExpertiseLevel {
  beginner,
  intermediate,
  expert,
}
