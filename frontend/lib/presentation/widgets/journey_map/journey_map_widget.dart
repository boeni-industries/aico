/// Journey Map Widget - Zoomable chronological timeline
/// 
/// Shows memories as an interactive, spatial timeline with:
/// - Multi-scale zoom (year → month → week)
/// - Smart node sizing based on importance
/// - Auto-detected relationship chapters
/// - Milestone markers
library;

import 'package:flutter/material.dart';
import 'dart:math' as math;

/// Data model for a memory node on the journey map
class JourneyNode {
  final String id;
  final DateTime timestamp;
  final String title;
  final String? preview;
  final bool isFavorite;
  final bool isMilestone;
  final String? milestoneReason;
  final int revisitCount;
  final bool hasNote;
  final Color color;
  final VoidCallback onTap;
  
  const JourneyNode({
    required this.id,
    required this.timestamp,
    required this.title,
    this.preview,
    this.isFavorite = false,
    this.isMilestone = false,
    this.milestoneReason,
    this.revisitCount = 0,
    this.hasNote = false,
    required this.color,
    required this.onTap,
  });
  
  /// Calculate node size based on importance
  double getSize(double baseSize) {
    double size = baseSize;
    
    if (isMilestone) return size * 3.0;
    if (isFavorite) size *= 2.0;
    if (revisitCount > 0) size *= (1 + revisitCount * 0.2);
    if (hasNote) size *= 1.3;
    
    return size.clamp(8.0, 40.0);
  }
}

/// Represents a chapter/phase in the relationship journey
class JourneyChapter {
  final String title;
  final String emoji;
  final DateTime startDate;
  final DateTime endDate;
  final Color color;
  final int memoryCount;
  
  const JourneyChapter({
    required this.title,
    required this.emoji,
    required this.startDate,
    required this.endDate,
    required this.color,
    required this.memoryCount,
  });
}

/// Main Journey Map widget
class JourneyMapWidget extends StatefulWidget {
  final List<JourneyNode> nodes;
  final List<JourneyChapter> chapters;
  final double initialZoom;
  
  const JourneyMapWidget({
    super.key,
    required this.nodes,
    required this.chapters,
    this.initialZoom = 1.0,
  });
  
  @override
  State<JourneyMapWidget> createState() => _JourneyMapWidgetState();
}

class _JourneyMapWidgetState extends State<JourneyMapWidget> {
  late TransformationController _transformController;
  JourneyNode? _hoveredNode;
  double _currentZoom = 1.0;
  final ScrollController _scrollController = ScrollController();
  
  @override
  void initState() {
    super.initState();
    _transformController = TransformationController();
    _currentZoom = widget.initialZoom;
  }
  
  @override
  void dispose() {
    _transformController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    if (widget.nodes.isEmpty) {
      return Center(
        child: Text(
          'No memories yet.\nStart adding memories to see your journey!',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.5),
            fontSize: 16,
          ),
        ),
      );
    }
    
    return Column(
      children: [
        // Zoom controls and chapter legend
        _buildControls(),
        
        const SizedBox(height: 16),
        
        // Interactive journey map with overlay
        Expanded(
          child: Stack(
            clipBehavior: Clip.none, // Allow overflow
            children: [
              // Scrollable timeline
              SingleChildScrollView(
                controller: _scrollController,
                child: MouseRegion(
                  cursor: _hoveredNode != null 
                      ? SystemMouseCursors.click 
                      : SystemMouseCursors.basic,
                  onHover: (event) => _handleHover(event.localPosition),
                  onExit: (_) => setState(() => _hoveredNode = null),
                  child: SizedBox(
                    width: MediaQuery.of(context).size.width,
                    height: _calculateTimelineHeight(),
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTapUp: (details) => _handleTap(details.localPosition),
                      child: CustomPaint(
                        painter: JourneyMapPainter(
                          nodes: widget.nodes,
                          chapters: widget.chapters,
                          zoom: _currentZoom,
                          hoveredNode: _hoveredNode,
                        ),
                        size: Size(
                          MediaQuery.of(context).size.width,
                          _calculateTimelineHeight(),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              // Speech bubble overlay - outside scroll area
              if (_hoveredNode != null) _buildSpeechBubbleOverlay(),
            ],
          ),
        ),
      ],
    );
  }
  
  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.1),
        ),
      ),
      child: Row(
        children: [
          // Zoom level indicator
          Text(
            _getZoomLevelLabel(),
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          
          const SizedBox(width: 16),
          
          // Zoom controls
          IconButton(
            icon: const Icon(Icons.remove, color: Colors.white70, size: 20),
            onPressed: _zoomOut,
            tooltip: 'Zoom out',
          ),
          
          Slider(
            value: _currentZoom.clamp(0.5, 3.0),
            min: 0.5,
            max: 3.0,
            activeColor: Colors.white70,
            inactiveColor: Colors.white.withValues(alpha: 0.2),
            onChanged: (value) {
              setState(() {
                _currentZoom = value;
                _transformController.value = Matrix4.identity()..scale(value);
              });
            },
          ),
          
          IconButton(
            icon: const Icon(Icons.add, color: Colors.white70, size: 20),
            onPressed: _zoomIn,
            tooltip: 'Zoom in',
          ),
          
          const SizedBox(width: 24),
          
          // Visual legend
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildLegendItem(
                    Icons.circle,
                    'Memory',
                    Colors.white70,
                  ),
                  const SizedBox(width: 16),
                  _buildLegendItem(
                    Icons.star,
                    'Starred',
                    Colors.amber,
                  ),
                  const SizedBox(width: 16),
                  _buildLegendItem(
                    Icons.stars,
                    'Milestone',
                    Colors.amber,
                  ),
                ],
              ),
            ),
          ),
          
          const Spacer(),
          
          // Chapter legend
          if (widget.chapters.isNotEmpty)
            Wrap(
              spacing: 12,
              children: widget.chapters.map((chapter) {
                return Tooltip(
                  message: '${chapter.title} (${chapter.memoryCount} memories)',
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: chapter.color.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: chapter.color.withValues(alpha: 0.4),
                      ),
                    ),
                    child: Text(
                      '${chapter.emoji} ${chapter.title}',
                      style: TextStyle(
                        color: chapter.color,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }
  
  Widget _buildLegendItem(IconData icon, String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white60,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
  
  Widget _buildSpeechBubbleOverlay() {
    if (_hoveredNode == null) return const SizedBox.shrink();
    
    final node = _hoveredNode!;
    
    // Show milestone reason if it's a milestone, otherwise show preview
    String displayText;
    if (node.isMilestone && node.milestoneReason != null) {
      displayText = '⭐ ${node.milestoneReason}\n\n${node.preview ?? node.title}';
      if (displayText.length > 150) {
        displayText = '⭐ ${node.milestoneReason}\n\n${(node.preview ?? node.title).substring(0, 100)}...';
      }
    } else {
      final preview = node.preview ?? node.title;
      displayText = preview.length > 120 
          ? '${preview.substring(0, 120)}...' 
          : preview;
    }
    
    // Calculate position accounting for scroll
    final nodeY = _getNodeYPosition(node);
    final scrollOffset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final visibleY = nodeY - scrollOffset;
    
    return Positioned(
      left: MediaQuery.of(context).size.width / 2 + 24,
      top: math.max(10, visibleY - 30), // Adjust for scroll and prevent top cutoff
      child: IgnorePointer(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 280),
          child: CustomPaint(
            painter: GlassBubblePainter(
              accentColor: node.color,
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(22, 14, 16, 14),
              child: Text(
                displayText,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.95),
                  fontSize: 13,
                  height: 1.5,
                  fontWeight: FontWeight.w400,
                  letterSpacing: 0.3,
                  shadows: [
                    Shadow(
                      color: Colors.black.withValues(alpha: 0.3),
                      offset: const Offset(0, 1),
                      blurRadius: 2,
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
  
  double _getNodeYPosition(JourneyNode node) {
    const firstNodeY = 75.0; // Fixed position for first (latest) node
    
    final index = widget.nodes.indexOf(node);
    if (index == -1) return firstNodeY;
    
    // First node always at fixed position
    if (index == 0) return firstNodeY;
    
    final earliest = widget.nodes.first.timestamp;
    final latest = widget.nodes.last.timestamp;
    final totalDays = math.max(1, latest.difference(earliest).inDays);
    final allSameDay = totalDays < 2;
    
    if (allSameDay) {
      // Spacing scales with zoom
      final spacing = 100.0 * math.pow(_currentZoom, 2) * 3.0;
      return firstNodeY + (index * spacing);
    } else {
      // Position based on days from first node
      final daysSinceFirst = node.timestamp.difference(earliest).inDays;
      final pixelsPerDay = 100.0 * math.pow(_currentZoom, 2);
      return firstNodeY + (daysSinceFirst * pixelsPerDay);
    }
  }
  
  String _getZoomLevelLabel() {
    if (_currentZoom < 0.8) return 'Year View';
    if (_currentZoom < 1.5) return 'Month View';
    return 'Week View';
  }
  
  void _zoomIn() {
    _adjustZoom(_currentZoom + 0.5);
  }
  
  void _zoomOut() {
    _adjustZoom(_currentZoom - 0.5);
  }
  
  void _adjustZoom(double newZoom) {
    final clampedZoom = newZoom.clamp(0.5, 3.0);
    if (clampedZoom == _currentZoom) return;
    
    setState(() {
      _currentZoom = clampedZoom;
    });
    
    // No scroll adjustment needed - first node is always pinned at top
  }
  
  double _calculateTimelineHeight() {
    // Calculate height based on time span and zoom level
    if (widget.nodes.isEmpty) return 800;
    
    const firstNodeY = 75.0; // Fixed position for first (latest) node
    
    final earliest = widget.nodes.first.timestamp;
    final latest = widget.nodes.last.timestamp;
    final daySpan = math.max(1, latest.difference(earliest).inDays);
    
    // If all memories are on same day, use count-based height
    if (daySpan < 2) {
      // Spacing between nodes scales with zoom
      final spacing = 100.0 * math.pow(_currentZoom, 2) * 3.0;
      // First node at fixed Y, then spacing for remaining nodes
      return firstNodeY + ((widget.nodes.length - 1) * spacing) + 200; // +200 bottom padding
    }
    
    // Zoom affects pixels per day
    final pixelsPerDay = 100.0 * math.pow(_currentZoom, 2);
    // First node at fixed Y, then scale by days
    return firstNodeY + (daySpan * pixelsPerDay) + 200; // +200 bottom padding
  }
  
  void _handleHover(Offset position) {
    // Find node at hover position
    final centerX = MediaQuery.of(context).size.width / 2;
    final earliest = widget.nodes.first.timestamp;
    final latest = widget.nodes.last.timestamp;
    final totalDays = math.max(1, latest.difference(earliest).inDays);
    final allSameDay = totalDays < 2;
    final height = _calculateTimelineHeight();
    
    JourneyNode? newHoveredNode;
    
    for (int i = 0; i < widget.nodes.length; i++) {
      final node = widget.nodes[i];
      final double y;
      
      if (allSameDay) {
        final spacing = height / (widget.nodes.length + 1);
        y = spacing * (i + 1);
      } else {
        final daysSinceStart = node.timestamp.difference(earliest).inDays;
        y = (daysSinceStart / totalDays) * height;
      }
      
      final distance = math.sqrt(
        math.pow(position.dx - centerX, 2) + math.pow(position.dy - y, 2)
      );
      
      // Same radius as tap
      if (distance < 120) {
        newHoveredNode = node;
        break;
      }
    }
    
    // Only update if hover state changed
    if (newHoveredNode != _hoveredNode) {
      setState(() {
        _hoveredNode = newHoveredNode;
      });
    }
  }
  
  void _handleTap(Offset position) {
    print('Journey Map tapped at: $position');
    
    // Find node at tap position
    final centerX = MediaQuery.of(context).size.width / 2;
    final earliest = widget.nodes.first.timestamp;
    final latest = widget.nodes.last.timestamp;
    final totalDays = math.max(1, latest.difference(earliest).inDays);
    final allSameDay = totalDays < 2;
    final height = _calculateTimelineHeight();
    
    print('Center X: $centerX, Height: $height, Nodes: ${widget.nodes.length}');
    
    for (int i = 0; i < widget.nodes.length; i++) {
      final node = widget.nodes[i];
      final double y;
      
      if (allSameDay) {
        final spacing = height / (widget.nodes.length + 1);
        y = spacing * (i + 1);
      } else {
        final daysSinceStart = node.timestamp.difference(earliest).inDays;
        y = (daysSinceStart / totalDays) * height;
      }
      
      final distance = math.sqrt(
        math.pow(position.dx - centerX, 2) + math.pow(position.dy - y, 2)
      );
      
      print('Node $i at y=$y, distance=$distance');
      
      // Large tap target area - 120px radius to make tapping easier
      if (distance < 120) {
        print('Node $i tapped! Opening detail...');
        // Node tapped!
        node.onTap();
        return;
      }
    }
    
    print('No node tapped');
    // No node tapped, clear hover
    setState(() {
      _hoveredNode = null;
    });
  }
}

/// Custom painter for the journey map
class JourneyMapPainter extends CustomPainter {
  final List<JourneyNode> nodes;
  final List<JourneyChapter> chapters;
  final double zoom;
  final JourneyNode? hoveredNode;
  
  JourneyMapPainter({
    required this.nodes,
    required this.chapters,
    required this.zoom,
    this.hoveredNode,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    if (nodes.isEmpty) return;
    
    final centerX = size.width / 2;
    final earliest = nodes.first.timestamp;
    final latest = nodes.last.timestamp;
    final totalDays = math.max(1, latest.difference(earliest).inDays);
    
    // Draw chapter backgrounds
    _drawChapters(canvas, size, centerX, earliest, totalDays);
    
    // Draw main timeline thread
    _drawTimeline(canvas, size, centerX);
    
    // Draw nodes
    _drawNodes(canvas, size, centerX, earliest, totalDays);
  }
  
  void _drawChapters(Canvas canvas, Size size, double centerX, DateTime earliest, int totalDays) {
    for (final chapter in chapters) {
      final startY = _dateToY(chapter.startDate, earliest, totalDays, size.height);
      
      // Chapter label only - no background
      final textPainter = TextPainter(
        text: TextSpan(
          text: '${chapter.emoji} ${chapter.title}',
          style: TextStyle(
            color: chapter.color.withValues(alpha: 0.6),
            fontSize: 12,  // Fixed size, not scaled by zoom
            fontWeight: FontWeight.w600,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(20, startY + 10));
    }
  }
  
  void _drawTimeline(Canvas canvas, Size size, double centerX) {
    if (nodes.isEmpty) return;
    
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.2)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;
    
    const firstNodeY = 75.0; // Fixed position for first (latest) node
    final earliest = nodes.first.timestamp;
    final latest = nodes.last.timestamp;
    final totalDays = math.max(1, latest.difference(earliest).inDays);
    final allSameDay = totalDays < 2;
    
    // First node always at fixed Y
    final firstY = firstNodeY;
    double lastY;
    
    if (nodes.length == 1) {
      lastY = firstNodeY;
    } else if (allSameDay) {
      final spacing = 100.0 * math.pow(zoom, 2) * 3.0;
      lastY = firstNodeY + ((nodes.length - 1) * spacing);
    } else {
      final daySpan = latest.difference(earliest).inDays;
      final pixelsPerDay = 100.0 * math.pow(zoom, 2);
      lastY = firstNodeY + (daySpan * pixelsPerDay);
    }
    
    // Draw line only between first and last nodes
    canvas.drawLine(
      Offset(centerX, firstY),
      Offset(centerX, lastY),
      paint,
    );
  }
  
  void _drawNodes(Canvas canvas, Size size, double centerX, DateTime earliest, int totalDays) {
    const firstNodeY = 75.0; // Fixed position for first (latest) node
    final allSameDay = totalDays < 2;
    
    for (int i = 0; i < nodes.length; i++) {
      final node = nodes[i];
      final double y;
      
      // First node always at fixed position
      if (i == 0) {
        y = firstNodeY;
      } else if (allSameDay) {
        // Spacing scales with zoom
        final spacing = 100.0 * math.pow(zoom, 2) * 3.0;
        y = firstNodeY + (i * spacing);
      } else {
        // Position based on days from first node
        final daysSinceFirst = node.timestamp.difference(earliest).inDays;
        final pixelsPerDay = 100.0 * math.pow(zoom, 2);
        y = firstNodeY + (daysSinceFirst * pixelsPerDay);
      }
      
      // All nodes same size - simple and clear
      const nodeRadius = 10.0;
      final isHovered = hoveredNode?.id == node.id;
      
      // Enhanced glow when hovered
      if (isHovered) {
        final glowPaint = Paint()
          ..color = node.color.withValues(alpha: 0.6)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16);
        canvas.drawCircle(Offset(centerX, y), nodeRadius + 8, glowPaint);
      }
      
      // Soft ambient glow for all nodes
      final ambientGlow = Paint()
        ..color = node.color.withValues(alpha: 0.3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
      canvas.drawCircle(Offset(centerX, y), nodeRadius + 4, ambientGlow);
      
      // Node circle with gradient effect
      final nodePaint = Paint()
        ..shader = RadialGradient(
          colors: [
            node.color.withValues(alpha: 1.0),
            node.color.withValues(alpha: 0.85),
          ],
        ).createShader(Rect.fromCircle(center: Offset(centerX, y), radius: nodeRadius))
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(centerX, y), nodeRadius, nodePaint);
      
      // Luminous border
      final borderPaint = Paint()
        ..color = Colors.white.withValues(alpha: 0.4)
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;
      canvas.drawCircle(Offset(centerX, y), nodeRadius, borderPaint);
      
      // Star icon for milestones - high contrast
      if (node.isMilestone) {
        // Dark background for contrast
        final starBgPaint = Paint()
          ..color = Colors.black.withValues(alpha: 0.5)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(Offset(centerX, y), nodeRadius * 0.75, starBgPaint);
        
        // Bright star with glow
        _drawStar(canvas, Offset(centerX, y), nodeRadius * 0.6, Colors.white);
        
        // Add subtle glow to star
        final starGlowPaint = Paint()
          ..color = Colors.white.withValues(alpha: 0.6)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3)
          ..style = PaintingStyle.fill;
        _drawStarPath(canvas, Offset(centerX, y), nodeRadius * 0.6, starGlowPaint);
      }
    }
  }
  
  void _drawStar(Canvas canvas, Offset center, double radius, Color color) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;
    final path = _createStarPath(center, radius);
    canvas.drawPath(path, paint);
  }
  
  void _drawStarPath(Canvas canvas, Offset center, double radius, Paint paint) {
    final path = _createStarPath(center, radius);
    canvas.drawPath(path, paint);
  }
  
  Path _createStarPath(Offset center, double radius) {
    final path = Path();
    const points = 5;
    const innerRadius = 0.4;
    
    for (int i = 0; i < points * 2; i++) {
      final angle = (i * math.pi / points) - math.pi / 2;
      final r = (i.isEven ? radius : radius * innerRadius);
      final x = center.dx + r * math.cos(angle);
      final y = center.dy + r * math.sin(angle);
      
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    path.close();
    return path;
  }
  
  double _dateToY(DateTime date, DateTime earliest, int totalDays, double height) {
    final daysSinceStart = date.difference(earliest).inDays;
    return (daysSinceStart / totalDays) * height;
  }
  
  @override
  bool shouldRepaint(JourneyMapPainter oldDelegate) {
    return oldDelegate.zoom != zoom ||
        oldDelegate.hoveredNode != hoveredNode ||
        oldDelegate.nodes.length != nodes.length;
  }
}

/// Glass bubble painter with tail
class GlassBubblePainter extends CustomPainter {
  final Color accentColor;
  
  GlassBubblePainter({required this.accentColor});
  
  @override
  void paint(Canvas canvas, Size size) {
    final path = _createBubblePath(size);
    
    // Shadow layers
    canvas.drawShadow(
      path,
      Colors.black.withValues(alpha: 0.5),
      12,
      true,
    );
    
    // Glass fill with gradient
    final glassPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Colors.white.withValues(alpha: 0.15),
          Colors.white.withValues(alpha: 0.08),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;
    
    canvas.drawPath(path, glassPaint);
    
    // Accent glow
    final glowPaint = Paint()
      ..color = accentColor.withValues(alpha: 0.12)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20)
      ..style = PaintingStyle.fill;
    canvas.drawPath(path, glowPaint);
    
    // Border
    final borderPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawPath(path, borderPaint);
  }
  
  Path _createBubblePath(Size size) {
    final path = Path();
    const radius = 16.0;
    const tailWidth = 12.0;
    const tailHeight = 10.0;
    
    // Start from top-left
    path.moveTo(tailWidth + radius, 0);
    
    // Top-right corner
    path.lineTo(size.width - radius, 0);
    path.quadraticBezierTo(size.width, 0, size.width, radius);
    
    // Right side
    path.lineTo(size.width, size.height - radius);
    
    // Bottom-right corner
    path.quadraticBezierTo(size.width, size.height, size.width - radius, size.height);
    
    // Bottom side
    path.lineTo(tailWidth + radius, size.height);
    
    // Bottom-left corner
    path.quadraticBezierTo(tailWidth, size.height, tailWidth, size.height - radius);
    
    // Left side with tail
    final tailTop = size.height / 2 - tailHeight;
    final tailBottom = size.height / 2 + tailHeight;
    
    path.lineTo(tailWidth, tailBottom);
    path.quadraticBezierTo(tailWidth / 2, size.height / 2 + tailHeight / 2, 0, size.height / 2);
    path.quadraticBezierTo(tailWidth / 2, size.height / 2 - tailHeight / 2, tailWidth, tailTop);
    path.lineTo(tailWidth, radius);
    
    // Top-left corner
    path.quadraticBezierTo(tailWidth, 0, tailWidth + radius, 0);
    
    path.close();
    return path;
  }
  
  @override
  bool shouldRepaint(GlassBubblePainter oldDelegate) => oldDelegate.accentColor != accentColor;
}

/// Custom clipper for speech bubble with tail
class SpeechBubbleClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();
    const radius = 16.0;
    const tailWidth = 12.0;
    const tailHeight = 10.0;
    
    // Start from top-left, after the tail
    path.moveTo(tailWidth + radius, 0);
    
    // Top-right corner
    path.lineTo(size.width - radius, 0);
    path.quadraticBezierTo(
      size.width, 0,
      size.width, radius,
    );
    
    // Right side
    path.lineTo(size.width, size.height - radius);
    
    // Bottom-right corner
    path.quadraticBezierTo(
      size.width, size.height,
      size.width - radius, size.height,
    );
    
    // Bottom side
    path.lineTo(tailWidth + radius, size.height);
    
    // Bottom-left corner
    path.quadraticBezierTo(
      tailWidth, size.height,
      tailWidth, size.height - radius,
    );
    
    // Left side with smooth tail pointing left
    final tailTop = size.height / 2 - tailHeight;
    final tailBottom = size.height / 2 + tailHeight;
    
    path.lineTo(tailWidth, tailBottom);
    // Smooth curve to tail tip
    path.quadraticBezierTo(
      tailWidth / 2, size.height / 2 + tailHeight / 2,
      0, size.height / 2,
    );
    // Smooth curve back from tail tip
    path.quadraticBezierTo(
      tailWidth / 2, size.height / 2 - tailHeight / 2,
      tailWidth, tailTop,
    );
    path.lineTo(tailWidth, radius);
    
    // Top-left corner
    path.quadraticBezierTo(
      tailWidth, 0,
      tailWidth + radius, 0,
    );
    
    path.close();
    return path;
  }
  
  @override
  bool shouldReclip(CustomClipper<Path> oldClipper) => false;
}
