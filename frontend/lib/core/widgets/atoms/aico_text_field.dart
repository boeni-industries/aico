import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AicoTextField extends StatefulWidget {
  final TextEditingController? controller;
  final String? label;
  final String? hint;
  final IconData? prefixIcon;
  final Widget? suffixIcon;
  final bool obscureText;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final String? Function(String?)? validator;
  final void Function(String)? onChanged;
  final void Function(String)? onSubmitted;
  final void Function()? onTap;
  final bool readOnly;
  final bool enabled;
  final int? maxLines;
  final int? minLines;
  final int? maxLength;
  final List<TextInputFormatter>? inputFormatters;
  final FocusNode? focusNode;
  final bool autofocus;

  const AicoTextField({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText = false,
    this.keyboardType,
    this.textInputAction,
    this.validator,
    this.onChanged,
    this.onSubmitted,
    this.onTap,
    this.readOnly = false,
    this.enabled = true,
    this.maxLines = 1,
    this.minLines,
    this.maxLength,
    this.inputFormatters,
    this.focusNode,
    this.autofocus = false,
  });

  @override
  State<AicoTextField> createState() => _AicoTextFieldState();
}

class _AicoTextFieldState extends State<AicoTextField>
    with SingleTickerProviderStateMixin {
  late FocusNode _focusNode;
  late final AnimationController _animationController;
  // Animation for future focus effects - currently unused
  // late Animation<double> _focusAnimation;

  bool _isFocused = false;
  String? _errorText;

  @override
  void initState() {
    super.initState();
    _focusNode = widget.focusNode ?? FocusNode();
    
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );

    // Focus animation setup removed - not currently used in UI

    _focusNode.addListener(_onFocusChange);
    
    if (widget.autofocus) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _focusNode.requestFocus();
      });
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Animation setup removed - using standard Material 3 borders now
  }

  @override
  void dispose() {
    if (widget.focusNode == null) {
      _focusNode.dispose();
    }
    _animationController.dispose();
    super.dispose();
  }

  void _onFocusChange() {
    setState(() {
      _isFocused = _focusNode.hasFocus;
    });

    if (_isFocused) {
      _animationController.forward();
    } else {
      _animationController.reverse();
      _validateField();
    }
  }

  void _validateField() {
    if (widget.validator != null) {
      final error = widget.validator!(widget.controller?.text);
      setState(() {
        _errorText = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.label != null) ...[
          GestureDetector(
            onTap: () => _focusNode.requestFocus(),
            child: Text(
              widget.label!,
              style: theme.textTheme.labelMedium?.copyWith(
                color: _isFocused 
                  ? colorScheme.primary 
                  : colorScheme.onSurface.withValues(alpha: 0.7),
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(height: 8),
        ],
        
        AnimatedBuilder(
          animation: _animationController,
          builder: (context, child) {
            return TextFormField(
              controller: widget.controller,
              focusNode: _focusNode,
              obscureText: widget.obscureText,
              keyboardType: widget.keyboardType,
              textInputAction: widget.textInputAction,
              onChanged: widget.onChanged,
              onFieldSubmitted: widget.onSubmitted,
              onTap: widget.onTap,
              readOnly: widget.readOnly,
              enabled: widget.enabled,
              maxLines: widget.maxLines,
              minLines: widget.minLines,
              maxLength: widget.maxLength,
              inputFormatters: widget.inputFormatters,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: widget.enabled 
                  ? colorScheme.onSurface 
                  : colorScheme.onSurface.withValues(alpha: 0.5),
              ),
              decoration: InputDecoration(
                hintText: widget.hint,
                hintStyle: theme.textTheme.bodyLarge?.copyWith(
                  color: colorScheme.onSurface.withValues(alpha: 0.5),
                ),
                prefixIcon: widget.prefixIcon != null
                  ? Icon(
                      widget.prefixIcon,
                      color: _isFocused 
                        ? colorScheme.primary 
                        : colorScheme.onSurface.withValues(alpha: 0.6),
                      size: 20,
                    )
                  : null,
                suffixIcon: widget.suffixIcon,
                filled: true,
                fillColor: widget.enabled 
                  ? colorScheme.surface 
                  : colorScheme.surface.withValues(alpha: 0.5),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16), // Following design principles - rounded
                  borderSide: BorderSide(
                    color: colorScheme.outline,
                    width: 1,
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(
                    color: colorScheme.outline,
                    width: 1,
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(
                    color: colorScheme.primary, // Soft purple focus from design principles
                    width: 2,
                  ),
                ),
                errorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(
                    color: colorScheme.error, // Coral for errors
                    width: 1,
                  ),
                ),
                focusedErrorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(
                    color: colorScheme.error,
                    width: 2,
                  ),
                ),
                disabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(
                    color: colorScheme.outline.withValues(alpha: 0.5),
                    width: 1,
                  ),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 16,
                ),
                counterText: '', // Hide character counter
              ),
            );
          },
        ),
        
        if (_errorText != null) ...[
          const SizedBox(height: 6),
          Row(
            children: [
              Icon(
                Icons.error_outline,
                size: 16,
                color: colorScheme.error,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _errorText!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.error,
                  ),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
