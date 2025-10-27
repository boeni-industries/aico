import 'package:flutter/material.dart';

/// Represents a single entry in the timeline
class TimelineEntry {
  final DateTime timestamp;
  final Widget content;
  final Widget? label;
  final bool isHighlighted;
  final Color? nodeColor;
  final double? nodeSize;
  
  const TimelineEntry({
    required this.timestamp,
    required this.content,
    this.label,
    this.isHighlighted = false,
    this.nodeColor,
    this.nodeSize,
  });
}

/// Configuration for timeline appearance
class TimelineStyle {
  final Color threadColor;
  final double threadWidth;
  final Color nodeColor;
  final double nodeSize;
  final Color highlightedNodeColor;
  final double highlightedNodeSize;
  final double nodeLabelSpacing;
  final double contentSpacing;
  final double threadNodeSpacing;
  final TextStyle? labelTextStyle;
  final bool showDottedEnds;
  
  const TimelineStyle({
    this.threadColor = const Color(0xFF666666),
    this.threadWidth = 2.0,
    this.nodeColor = const Color(0xFF999999),
    this.nodeSize = 12.0,
    this.highlightedNodeColor = const Color(0xFFFFD700),
    this.highlightedNodeSize = 12.0,
    this.nodeLabelSpacing = 14.0,
    this.contentSpacing = 24.0,
    this.threadNodeSpacing = 80.0,
    this.labelTextStyle,
    this.showDottedEnds = true,
  });
}

/// A reusable timeline widget that supports both vertical and horizontal orientations
class TimelineWidget extends StatelessWidget {
  final List<TimelineEntry> entries;
  final Axis axis;
  final TimelineStyle style;
  final double threadPosition; // Position of thread line (0.0 = start, 1.0 = end)
  
  const TimelineWidget({
    super.key,
    required this.entries,
    this.axis = Axis.vertical,
    this.style = const TimelineStyle(),
    this.threadPosition = 0.15, // Default: 15% from start (100px column, thread at 50px = 0.5)
  });
  
  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }
    
    return axis == Axis.vertical
        ? _buildVerticalTimeline()
        : _buildHorizontalTimeline();
  }
  
  Widget _buildVerticalTimeline() {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: entries.length,
      itemBuilder: (context, index) {
        final entry = entries[index];
        final isFirst = index == 0;
        final isLast = index == entries.length - 1;
        
        return _TimelineItem(
          entry: entry,
          isFirst: isFirst,
          isLast: isLast,
          style: style,
          axis: axis,
          threadPosition: threadPosition,
        );
      },
    );
  }
  
  Widget _buildHorizontalTimeline() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: List.generate(entries.length, (index) {
          final entry = entries[index];
          final isFirst = index == 0;
          final isLast = index == entries.length - 1;
          
          return _TimelineItem(
            entry: entry,
            isFirst: isFirst,
            isLast: isLast,
            style: style,
            axis: axis,
            threadPosition: threadPosition,
          );
        }),
      ),
    );
  }
}

/// Individual timeline item with painted thread
class _TimelineItem extends StatelessWidget {
  final TimelineEntry entry;
  final bool isFirst;
  final bool isLast;
  final TimelineStyle style;
  final Axis axis;
  final double threadPosition;
  
  const _TimelineItem({
    required this.entry,
    required this.isFirst,
    required this.isLast,
    required this.style,
    required this.axis,
    required this.threadPosition,
  });
  
  @override
  Widget build(BuildContext context) {
    return axis == Axis.vertical
        ? _buildVerticalItem()
        : _buildHorizontalItem();
  }
  
  Widget _buildVerticalItem() {
    final nodeSize = entry.nodeSize ?? 
        (entry.isHighlighted ? style.highlightedNodeSize : style.nodeSize);
    final nodeColor = entry.nodeColor ?? 
        (entry.isHighlighted ? style.highlightedNodeColor : style.nodeColor);
    
    // Calculate thread position in pixels (e.g., 100px * 0.5 = 50px)
    final threadLinePosition = 100 * threadPosition;
    
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Timeline thread column - will match content height
          SizedBox(
            width: 100,
            child: Stack(
              children: [
                // Thread line - continuous from top to bottom (or center for last)
                if (!isLast)
                  Positioned(
                    left: threadLinePosition - style.threadWidth / 2,
                    top: isFirst ? 40 : 0,
                    bottom: 0,
                    child: Container(
                      width: style.threadWidth,
                      color: style.threadColor.withValues(alpha: 0.2),
                    ),
                  )
                else
                  // For last entry, use Center to stop at middle
                  Positioned.fill(
                    left: threadLinePosition - style.threadWidth / 2,
                    right: null,
                    child: Align(
                      alignment: Alignment.topCenter,
                      child: FractionallySizedBox(
                        heightFactor: 0.5,
                        child: Container(
                          width: style.threadWidth,
                          color: style.threadColor.withValues(alpha: 0.2),
                        ),
                      ),
                    ),
                  ),
                
                // Dotted line at top for first entry
                if (isFirst)
                  Positioned(
                    left: 0,
                    right: 0,
                    top: 0,
                    height: 40,
                    child: CustomPaint(
                      painter: _DottedLinePainter(
                        color: style.threadColor.withValues(alpha: 0.3),
                        strokeWidth: style.threadWidth,
                        position: threadLinePosition,
                      ),
                    ),
                  ),
                
                // Node and label - centered vertically
                Center(
                  child: Row(
                    children: [
                      // Date label - takes space up to the spacing before dot
                      if (entry.label != null)
                        Expanded(
                          child: Padding(
                            padding: EdgeInsets.only(right: style.nodeLabelSpacing),
                            child: DefaultTextStyle(
                              style: style.labelTextStyle ?? 
                                  const TextStyle(fontSize: 10, color: Color(0xFF999999)),
                              textAlign: TextAlign.right,
                              overflow: TextOverflow.visible,
                              softWrap: false,
                              maxLines: 1,
                              child: entry.label!,
                            ),
                          ),
                        ),
                      
                      // Node - positioned at exact center
                      Container(
                        width: nodeSize,
                        height: nodeSize,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: nodeColor,
                          boxShadow: entry.isHighlighted ? [
                            BoxShadow(
                              color: nodeColor.withValues(alpha: 0.4),
                              blurRadius: 12,
                              spreadRadius: 2,
                            ),
                          ] : [
                            BoxShadow(
                              color: nodeColor.withValues(alpha: 0.2),
                              blurRadius: 4,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                      ),
                      
                      // Right spacer to keep dot centered at threadPosition
                      SizedBox(width: 100 - threadLinePosition - nodeSize / 2),
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          // Content
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                top: isFirst ? 40 : 0,
                bottom: isLast ? 0 : style.contentSpacing,
              ),
              child: entry.content,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildHorizontalItem() {
    // Similar structure but rotated 90 degrees
    // Implementation would swap Row/Column and adjust positioning
    return const SizedBox(); // Placeholder for horizontal implementation
  }
}

/// Custom painter for vertical timeline
class _VerticalTimelinePainter extends CustomPainter {
  final bool isFirst;
  final bool isLast;
  final Color threadColor;
  final double threadWidth;
  final Color nodeColor;
  final double nodeSize;
  final double threadPosition;
  final double nodeLabelSpacing;
  final double threadNodeSpacing;
  final bool showDottedEnds;
  final bool hasGlow;
  
  _VerticalTimelinePainter({
    required this.isFirst,
    required this.isLast,
    required this.threadColor,
    required this.threadWidth,
    required this.nodeColor,
    required this.nodeSize,
    required this.threadPosition,
    required this.nodeLabelSpacing,
    required this.threadNodeSpacing,
    required this.showDottedEnds,
    required this.hasGlow,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    final threadPaint = Paint()
      ..color = threadColor.withValues(alpha: 0.2)
      ..strokeWidth = threadWidth
      ..strokeCap = StrokeCap.round;
    
    // Draw top thread segment
    if (!isFirst) {
      canvas.drawLine(
        Offset(threadPosition, 0),
        Offset(threadPosition, threadNodeSpacing + nodeSize / 2),
        threadPaint,
      );
    } else if (showDottedEnds) {
      // Dotted line for first entry
      _drawDottedLine(
        canvas,
        Offset(threadPosition, 0),
        Offset(threadPosition, threadNodeSpacing + nodeSize / 2),
        threadPaint,
      );
    }
    
    // Draw bottom thread segment (stop at node for last entry)
    if (!isLast) {
      canvas.drawLine(
        Offset(threadPosition, threadNodeSpacing + nodeSize / 2),
        Offset(threadPosition, size.height),
        threadPaint,
      );
    }
    
    // Draw node
    final nodePaint = Paint()
      ..color = nodeColor
      ..style = PaintingStyle.fill;
    
    final nodeCenter = Offset(threadPosition, threadNodeSpacing + nodeSize / 2);
    
    // Draw glow if highlighted
    if (hasGlow) {
      final glowPaint = Paint()
        ..color = nodeColor.withValues(alpha: 0.4)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
      canvas.drawCircle(nodeCenter, nodeSize / 2 + 2, glowPaint);
    }
    
    canvas.drawCircle(nodeCenter, nodeSize / 2, nodePaint);
  }
  
  void _drawDottedLine(Canvas canvas, Offset start, Offset end, Paint paint) {
    const dashLength = 4.0;
    const dashSpace = 4.0;
    
    final distance = (end - start).distance;
    final direction = (end - start) / distance;
    
    double currentDistance = 0;
    while (currentDistance < distance) {
      final dashStart = start + direction * currentDistance;
      final dashEnd = start + direction * (currentDistance + dashLength).clamp(0, distance);
      canvas.drawLine(dashStart, dashEnd, paint);
      currentDistance += dashLength + dashSpace;
    }
  }
  
  @override
  bool shouldRepaint(_VerticalTimelinePainter oldDelegate) {
    return oldDelegate.isFirst != isFirst ||
        oldDelegate.isLast != isLast ||
        oldDelegate.nodeColor != nodeColor ||
        oldDelegate.hasGlow != hasGlow;
  }
}

/// Custom painter for dotted lines
class _DottedLinePainter extends CustomPainter {
  final Color color;
  final double strokeWidth;
  final double position;
  
  _DottedLinePainter({
    required this.color,
    required this.strokeWidth,
    required this.position,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    
    const dashHeight = 4.0;
    const dashSpace = 4.0;
    double startY = 0;
    
    while (startY < size.height) {
      canvas.drawLine(
        Offset(position, startY),
        Offset(position, startY + dashHeight),
        paint,
      );
      startY += dashHeight + dashSpace;
    }
  }
  
  @override
  bool shouldRepaint(_DottedLinePainter oldDelegate) {
    return oldDelegate.color != color || 
        oldDelegate.strokeWidth != strokeWidth ||
        oldDelegate.position != position;
  }
}

