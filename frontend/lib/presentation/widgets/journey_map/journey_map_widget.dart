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
        
        // Interactive journey map
        Expanded(
          child: SingleChildScrollView(
            controller: _scrollController,
            child: SizedBox(
              width: MediaQuery.of(context).size.width,
              height: _calculateTimelineHeight(),
              child: CustomPaint(
                painter: JourneyMapPainter(
                  nodes: widget.nodes,
                  chapters: widget.chapters,
                  zoom: _currentZoom,
                  hoveredNode: _hoveredNode,
                ),
                child: GestureDetector(
                  onTapUp: (details) => _handleTap(details.localPosition),
                  child: Container(color: Colors.transparent),
                ),
              ),
            ),
          ),
        ),
        
        // Hovered node preview
        if (_hoveredNode != null) _buildNodePreview(_hoveredNode!),
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
  
  Widget _buildNodePreview(JourneyNode node) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: node.color.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              if (node.isMilestone)
                const Icon(Icons.stars, color: Colors.amber, size: 16),
              if (node.isFavorite)
                const Icon(Icons.star, color: Colors.amber, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  node.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          if (node.preview != null) ...[
            const SizedBox(height: 8),
            Text(
              node.preview!,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.7),
                fontSize: 12,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
  
  String _getZoomLevelLabel() {
    if (_currentZoom < 0.8) return 'Year View';
    if (_currentZoom < 1.5) return 'Month View';
    return 'Week View';
  }
  
  void _zoomIn() {
    final newZoom = (_currentZoom + 0.5).clamp(0.5, 3.0);
    setState(() {
      _currentZoom = newZoom;
    });
  }
  
  void _zoomOut() {
    final newZoom = (_currentZoom - 0.5).clamp(0.5, 3.0);
    setState(() {
      _currentZoom = newZoom;
    });
  }
  
  double _calculateTimelineHeight() {
    // Calculate height based on time span and zoom level
    if (widget.nodes.isEmpty) return 800;
    
    final earliest = widget.nodes.first.timestamp;
    final latest = widget.nodes.last.timestamp;
    final daySpan = math.max(1, latest.difference(earliest).inDays);
    
    // If all memories are on same day, use count-based height
    if (daySpan < 2) {
      // Exponential zoom for dramatic effect
      // 0.5x = 100px spacing (very compressed - all visible in viewport)
      // 1.0x = 300px spacing (comfortable)
      // 3.0x = 1800px spacing (very expanded)
      final spacing = 100.0 * math.pow(_currentZoom, 2) * 3.0;
      // Add padding at top and bottom
      return (widget.nodes.length + 1) * spacing;
    }
    
    // Zoom affects pixels per day - exponential for dramatic effect
    // 0.5x = 25px/day (year view - very compressed)
    // 1.0x = 100px/day (month view)
    // 3.0x = 900px/day (week view - very expanded)
    final pixelsPerDay = 100.0 * math.pow(_currentZoom, 2);
    return math.max(800, daySpan * pixelsPerDay);
  }
  
  void _handleTap(Offset position) {
    // Find node at tap position
    final centerX = MediaQuery.of(context).size.width / 2;
    final earliest = widget.nodes.first.timestamp;
    final latest = widget.nodes.last.timestamp;
    final totalDays = math.max(1, latest.difference(earliest).inDays);
    final allSameDay = totalDays < 2;
    final height = _calculateTimelineHeight();
    
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
      
      final nodeSize = node.getSize(12.0);
      final distance = math.sqrt(
        math.pow(position.dx - centerX, 2) + math.pow(position.dy - y, 2)
      );
      
      if (distance < nodeSize) {
        // Node tapped!
        node.onTap();
        return;
      }
    }
    
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
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.2)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;
    
    canvas.drawLine(
      Offset(centerX, 0),
      Offset(centerX, size.height),
      paint,
    );
  }
  
  void _drawNodes(Canvas canvas, Size size, double centerX, DateTime earliest, int totalDays) {
    // Node size is CONSTANT regardless of zoom
    final baseNodeSize = 12.0;
    
    // If all nodes are on same day, space them evenly
    final allSameDay = totalDays < 2;
    
    for (int i = 0; i < nodes.length; i++) {
      final node = nodes[i];
      final double y;
      
      if (allSameDay) {
        // Space nodes evenly across the height
        final spacing = size.height / (nodes.length + 1);
        y = spacing * (i + 1);
      } else {
        y = _dateToY(node.timestamp, earliest, totalDays, size.height);
      }
      
      final nodeSize = node.getSize(baseNodeSize);
      
      // Node shadow/glow
      if (node.isFavorite || node.isMilestone) {
        final glowPaint = Paint()
          ..color = node.color.withValues(alpha: 0.4)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
        canvas.drawCircle(Offset(centerX, y), nodeSize + 4, glowPaint);
      }
      
      // Node circle
      final nodePaint = Paint()
        ..color = node.color
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(centerX, y), nodeSize / 2, nodePaint);
      
      // Node border
      final borderPaint = Paint()
        ..color = Colors.white.withValues(alpha: 0.3)
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;
      canvas.drawCircle(Offset(centerX, y), nodeSize / 2, borderPaint);
      
      // Milestone icon
      if (node.isMilestone) {
        _drawStar(canvas, Offset(centerX, y), nodeSize / 2, Colors.white);
      }
    }
  }
  
  void _drawStar(Canvas canvas, Offset center, double radius, Color color) {
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
    
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;
    canvas.drawPath(path, paint);
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
