/// Memory Detail Screen
/// 
/// Emotional scroll story design - award-winning visual fidelity
/// Conversation flows like poetry with page-turning momentum
library;

import 'dart:ui';

import 'package:aico_frontend/data/models/memory_album_model.dart';
import 'package:aico_frontend/presentation/providers/memory_album_provider.dart';
import 'package:aico_frontend/presentation/theme/memory_album_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class MemoryDetailScreen extends ConsumerStatefulWidget {
  final MemoryEntry memory;

  const MemoryDetailScreen({
    super.key,
    required this.memory,
  });

  @override
  ConsumerState<MemoryDetailScreen> createState() => _MemoryDetailScreenState();
}

class _MemoryDetailScreenState extends ConsumerState<MemoryDetailScreen> {
  final ScrollController _scrollController = ScrollController();
  double _scrollProgress = 0.0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.hasClients) {
      final maxScroll = _scrollController.position.maxScrollExtent;
      final currentScroll = _scrollController.offset;
      setState(() {
        _scrollProgress = maxScroll > 0 ? (currentScroll / maxScroll).clamp(0.0, 1.0) : 0.0;
      });
    }
  }

  Color _getMoodColor() {
    final tone = widget.memory.emotionalTone?.toLowerCase();
    switch (tone) {
      case 'reflective':
      case 'thoughtful':
        return const Color(0xFFB8A1EA); // Purple
      case 'joyful':
      case 'happy':
        return const Color(0xFF8DD686); // Green
      case 'vulnerable':
      case 'sad':
        return const Color(0xFF8DD6B8); // Mint
      default:
        return const Color(0xFFB8A1EA);
    }
  }

  List<Map<String, String>> _parseConversation() {
    final content = widget.memory.conversationSummary ?? widget.memory.content;
    
    // For non-conversation memories (Messages), format as single AICO message
    if (!widget.memory.isConversationMemory) {
      return [{
        'speaker': 'AICO',
        'content': content.trim(),
      }];
    }
    
    // For conversations, parse the dialogue
    final lines = content.split('\n\n');
    final exchanges = <Map<String, String>>[];
    
    for (final line in lines) {
      final trimmed = line.trim();
      if (trimmed.isEmpty) continue;
      
      if (trimmed.startsWith('You:')) {
        exchanges.add({
          'speaker': 'YOU',
          'content': trimmed.substring(4).trim(),
        });
      } else if (trimmed.startsWith('AICO:')) {
        exchanges.add({
          'speaker': 'AICO',
          'content': trimmed.substring(5).trim(),
        });
      } else {
        // If no prefix, treat as continuation of previous or standalone
        if (exchanges.isEmpty) {
          exchanges.add({
            'speaker': 'CONTENT',
            'content': trimmed,
          });
        } else {
          // Append to previous exchange
          final last = exchanges.last;
          last['content'] = '${last['content']}\n\n$trimmed';
        }
      }
    }
    
    return exchanges;
  }

  @override
  Widget build(BuildContext context) {
    final moodColor = _getMoodColor();
    final exchanges = _parseConversation();
    
    return Scaffold(
      backgroundColor: MemoryAlbumTheme.background,
      body: Stack(
        children: [
          // Ambient mood glow (parallax effect)
          Positioned.fill(
            child: Transform.translate(
              offset: Offset(0, -_scrollProgress * 50),
              child: Container(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment.topCenter,
                    radius: 1.5,
                    colors: [
                      moodColor.withValues(alpha: 0.08),
                      moodColor.withValues(alpha: 0.04),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
          ),
          
          // Main content
          CustomScrollView(
            controller: _scrollController,
            physics: const BouncingScrollPhysics(),
            slivers: [
              // Floating header (pinned to stay visible)
              SliverAppBar(
                backgroundColor: MemoryAlbumTheme.background.withValues(alpha: 0.95),
                elevation: 0,
                floating: true,
                pinned: true,
                leading: IconButton(
                  icon: Icon(
                    Icons.arrow_back_rounded,
                    color: MemoryAlbumTheme.silver,
                    size: 28,
                  ),
                  onPressed: () => Navigator.pop(context),
                ),
                actions: [
                  IconButton(
                    icon: Icon(
                      widget.memory.isFavorite
                          ? Icons.star_rounded
                          : Icons.star_outline_rounded,
                      color: widget.memory.isFavorite
                          ? MemoryAlbumTheme.gold
                          : MemoryAlbumTheme.silver.withValues(alpha: 0.7),
                      size: 28,
                    ),
                    onPressed: () {
                      ref.read(memoryAlbumProvider.notifier).toggleFavorite(widget.memory);
                    },
                  ),
                  const SizedBox(width: 16),
                ],
              ),

              // Content without background container
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(40, 20, 40, 40),
                sliver: SliverToBoxAdapter(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [

                            // Header section
                            Container(
                              padding: const EdgeInsets.all(20),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.02),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.05),
                                  width: 1,
                                ),
                              ),
                              child: Row(
                                children: [
                                  // Type badge
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: widget.memory.isConversationMemory
                                          ? const Color(0xFFB8A1EA).withValues(alpha: 0.15)
                                          : MemoryAlbumTheme.silver.withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(
                                          widget.memory.isConversationMemory
                                              ? Icons.forum_rounded
                                              : Icons.chat_bubble_rounded,
                                          size: 14,
                                          color: widget.memory.isConversationMemory
                                              ? const Color(0xFFB8A1EA)
                                              : MemoryAlbumTheme.silver.withValues(alpha: 0.7),
                                        ),
                                        const SizedBox(width: 6),
                                        Text(
                                          widget.memory.isConversationMemory ? 'Conversation' : 'Message',
                                          style: TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w600,
                                            color: widget.memory.isConversationMemory
                                                ? const Color(0xFFB8A1EA)
                                                : MemoryAlbumTheme.silver.withValues(alpha: 0.7),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  
                                  const SizedBox(width: 16),
                                  
                                  // Date and emotional tone
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          _formatSwissDate(widget.memory.createdAt),
                                          style: const TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w500,
                                            color: MemoryAlbumTheme.textPrimary,
                                          ),
                                        ),
                                        if (widget.memory.emotionalTone != null) ...[
                                          const SizedBox(height: 2),
                                          Text(
                                            widget.memory.emotionalTone!,
                                            style: TextStyle(
                                              fontSize: 12,
                                              color: MemoryAlbumTheme.textSecondary,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            
                            const SizedBox(height: 40),
                            
                            // Conversation exchanges (bubbles)
                            ...exchanges.asMap().entries.map((entry) {
                              final index = entry.key;
                              final exchange = entry.value;
                              final speaker = exchange['speaker']!;
                              final isYou = speaker == 'YOU';
                              final isContent = speaker == 'CONTENT';
                              final content = exchange['content']!;
                              
                              // Check if previous message was from same speaker
                              final prevSpeaker = index > 0 ? exchanges[index - 1]['speaker'] : null;
                              final sameSpeaker = prevSpeaker == speaker;
                              
                              // Dynamic spacing
                              final spacingBefore = index == 0 ? 0.0 : (sameSpeaker ? 12.0 : 32.0);
                              
                              // For generic content, center it
                              if (isContent) {
                                return Column(
                                  children: [
                                    SizedBox(height: spacingBefore),
                                    Text(
                                      content,
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        fontSize: 16,
                                        color: MemoryAlbumTheme.textSecondary,
                                        height: 1.6,
                                      ),
                                    ),
                                  ],
                                );
                              }
                              
                              return IntrinsicHeight(
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.stretch,
                                  children: [
                                    // Timeline visualization
                                    SizedBox(
                                      width: 32,
                                      child: Column(
                                        children: [
                                          // Connecting line from previous (if not first)
                                          if (index > 0)
                                            Container(
                                              width: 2,
                                              height: spacingBefore,
                                              color: Colors.white.withValues(alpha: 0.12),
                                            )
                                          else
                                            SizedBox(height: spacingBefore),
                                          
                                          // Timeline circle
                                          Container(
                                            width: 32,
                                            height: 32,
                                            decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              color: isYou
                                                  ? Colors.white.withValues(alpha: 0.08)
                                                  : moodColor.withValues(alpha: 0.2),
                                              border: Border.all(
                                                color: isYou
                                                    ? Colors.white.withValues(alpha: 0.2)
                                                    : moodColor.withValues(alpha: 0.5),
                                                width: 2,
                                              ),
                                            ),
                                            child: ClipOval(
                                              child: isYou
                                                  ? Icon(
                                                      Icons.person,
                                                      size: 18,
                                                      color: Colors.white.withValues(alpha: 0.6),
                                                    )
                                                  : Image.asset(
                                                      'assets/images/aico.png',
                                                      width: 20,
                                                      height: 20,
                                                      fit: BoxFit.cover,
                                                    ),
                                            ),
                                          ),
                                          
                                          // Connecting line to next (if not last)
                                          // Expands to fill remaining height
                                          if (index < exchanges.length - 1)
                                            Expanded(
                                              child: Container(
                                                width: 2,
                                                color: Colors.white.withValues(alpha: 0.12),
                                              ),
                                            ),
                                        ],
                                      ),
                                    ),
                                  
                                  const SizedBox(width: 16),
                                  
                                  // Message content
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        SizedBox(height: spacingBefore),
                                        
                                        // Speaker label (more prominent)
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: isYou
                                                ? Colors.white.withValues(alpha: 0.05)
                                                : moodColor.withValues(alpha: 0.1),
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            isYou ? 'YOU' : 'AICO',
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.w700,
                                              color: isYou
                                                  ? MemoryAlbumTheme.textSecondary
                                                  : moodColor,
                                              letterSpacing: 1.5,
                                            ),
                                          ),
                                        ),
                                        
                                        const SizedBox(height: 10),
                                        
                                        // Message bubble
                                        ClipRRect(
                                          borderRadius: BorderRadius.circular(20),
                                          child: BackdropFilter(
                                            filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                                            child: Container(
                                              padding: const EdgeInsets.all(20),
                                              decoration: BoxDecoration(
                                                color: isYou
                                                    ? Colors.white.withValues(alpha: 0.04)
                                                    : moodColor.withValues(alpha: 0.08),
                                                borderRadius: BorderRadius.circular(20),
                                                border: Border.all(
                                                  color: isYou
                                                      ? Colors.white.withValues(alpha: 0.08)
                                                      : moodColor.withValues(alpha: 0.2),
                                                  width: 1,
                                                ),
                                                boxShadow: [
                                                  BoxShadow(
                                                    color: Colors.black.withValues(alpha: 0.2),
                                                    blurRadius: 20,
                                                    offset: const Offset(0, 6),
                                                    spreadRadius: -4,
                                                  ),
                                                ],
                                              ),
                                              child: Text(
                                                content.trim(),
                                                style: TextStyle(
                                                  fontSize: 16.0,
                                                  fontWeight: isYou ? FontWeight.w400 : FontWeight.w500,
                                                  color: isYou
                                                      ? const Color(0xFFB8BCC8)
                                                      : MemoryAlbumTheme.textPrimary,
                                                  height: 1.6,
                                                  letterSpacing: 0.01,
                                                ),
                                              ),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              );
                            }),
                            
                            const SizedBox(height: 32),

                            // User note (centered, glowing)
                            if (widget.memory.userNote != null && widget.memory.userNote!.isNotEmpty) ...[
                              Center(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
                                  decoration: BoxDecoration(
                                    boxShadow: [
                                      BoxShadow(
                                        color: const Color(0xFFB8A1EA).withValues(alpha: 0.15),
                                        blurRadius: 30,
                                        spreadRadius: 5,
                                      ),
                                    ],
                                  ),
                                  child: Text(
                                    '"${widget.memory.userNote}"',
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontStyle: FontStyle.italic,
                                      color: Color(0xFFB8A1EA),
                                      height: 1.6,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 40),
                            ],

                            // Tags (if any)
                            if (widget.memory.tags.isNotEmpty) ...[
                              Center(
                                child: Wrap(
                                  spacing: 12,
                                  runSpacing: 12,
                                  alignment: WrapAlignment.center,
                                  children: widget.memory.tags.map((tag) {
                                    return Text(
                                      '#$tag',
                                      style: TextStyle(
                                        fontSize: 13,
                                        color: MemoryAlbumTheme.silver.withValues(alpha: 0.6),
                                        letterSpacing: 0.5,
                                      ),
                                    );
                                  }).toList(),
                                ),
                              ),
                            ],
                          ],
                  ),
                ),
              ),
            ],
          ),
          
          // Bottom fade gradient (creates scroll momentum)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            height: 120,
            child: IgnorePointer(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      MemoryAlbumTheme.background,
                      MemoryAlbumTheme.background.withValues(alpha: 0.0),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  String _formatSwissDate(DateTime date) {
    final localDate = date.toLocal();
    final day = localDate.day.toString().padLeft(2, '0');
    final month = localDate.month.toString().padLeft(2, '0');
    final year = localDate.year.toString();
    final hour = localDate.hour.toString().padLeft(2, '0');
    final minute = localDate.minute.toString().padLeft(2, '0');
    return '$day.$month.$year $hour:$minute';
  }

}
