import 'package:flutter/material.dart';

/// Floating voice input button that overlays the center of bottom navigation.
/// Provides immediate access to voice interaction with AICO's avatar system.
class FloatingVoiceButton extends StatefulWidget {
  const FloatingVoiceButton({super.key});

  @override
  State<FloatingVoiceButton> createState() => _FloatingVoiceButtonState();
}

class _FloatingVoiceButtonState extends State<FloatingVoiceButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _pulseAnimation;
  
  bool _isListening = false;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 1.1,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));

    _pulseAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _toggleListening() {
    setState(() {
      _isListening = !_isListening;
    });

    if (_isListening) {
      _animationController.repeat(reverse: true);
      // TODO: Start voice recording
    } else {
      _animationController.stop();
      _animationController.reset();
      // TODO: Stop voice recording and process
    }
  }

  @override
  Widget build(BuildContext context) {
    // final theme = Theme.of(context);
    final accentColor = const Color(0xFFB8A1EA); // Soft purple accent

    return AnimatedBuilder(
      animation: _animationController,
      builder: (context, child) {
        return Stack(
          alignment: Alignment.center,
          children: [
            // Pulse effect when listening
            if (_isListening)
              Container(
                width: 80 * (1 + _pulseAnimation.value * 0.3),
                height: 80 * (1 + _pulseAnimation.value * 0.3),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accentColor.withValues(alpha: 0.2 * (1 - _pulseAnimation.value)),
                ),
              ),
            
            // Main button
            Transform.scale(
              scale: _isListening ? _scaleAnimation.value : 1.0,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: _isListening
                        ? [
                            accentColor,
                            accentColor.withValues(alpha: 0.8),
                          ]
                        : [
                            accentColor.withValues(alpha: 0.9),
                            accentColor,
                          ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: accentColor.withValues(alpha: 0.3),
                      blurRadius: _isListening ? 12 : 8,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _toggleListening,
                    borderRadius: BorderRadius.circular(28),
                    child: Icon(
                      _isListening ? Icons.mic : Icons.mic_none,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
