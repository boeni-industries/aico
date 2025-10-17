"""
Thinking Tag Parser for AICO

Parses <think> tags from LLM output to separate inner monologue from response.
Designed for streaming: processes chunks immediately without buffering.

Design Principles:
- Simple state machine (KISS)
- No buffering delays
- Handles split tags across chunks
- Fails loudly on malformed input
"""

import re
from typing import Tuple, Dict
from dataclasses import dataclass, field


@dataclass
class ParserState:
    """State for streaming parser - tracks position in tag structure"""
    in_thinking: bool = False
    tag_buffer: str = ""
    thinking_accumulated: str = ""
    response_accumulated: str = ""


class ThinkingParser:
    """
    Stateful parser for extracting <think> tags from streaming LLM output.
    
    Usage:
        parser = ThinkingParser()
        for chunk in stream:
            content, content_type = parser.parse_chunk(chunk)
            # Send content with content_type to frontend
    """
    
    THINK_OPEN = "<think>"
    THINK_CLOSE = "</think>"
    
    def __init__(self):
        self.state = ParserState()
    
    def parse_chunk(self, chunk: str) -> Tuple[str, str]:
        """
        Parse a streaming chunk and return (content, content_type).
        
        Args:
            chunk: Raw text chunk from LLM
            
        Returns:
            Tuple of (cleaned_content, content_type)
            content_type is either "thinking" or "response"
            
        Note:
            Handles tags split across chunks by maintaining state.
            Returns empty string if chunk is purely tag markup.
        """
        if not chunk:
            return "", "response"
        
        # Add chunk to buffer for tag detection
        buffer = self.state.tag_buffer + chunk
        self.state.tag_buffer = ""
        
        output_content = ""
        current_type = "thinking" if self.state.in_thinking else "response"
        
        i = 0
        while i < len(buffer):
            # Check for opening tag
            if not self.state.in_thinking and buffer[i:].startswith(self.THINK_OPEN):
                self.state.in_thinking = True
                i += len(self.THINK_OPEN)
                current_type = "thinking"
                continue
            
            # Check for closing tag
            if self.state.in_thinking and buffer[i:].startswith(self.THINK_CLOSE):
                self.state.in_thinking = False
                i += len(self.THINK_CLOSE)
                current_type = "response"
                continue
            
            # Check if we might be at the start of a tag (incomplete)
            remaining = buffer[i:]
            if self._might_be_tag_start(remaining):
                # Buffer it for next chunk
                self.state.tag_buffer = remaining
                break
            
            # Regular content
            output_content += buffer[i]
            i += 1
        
        # Accumulate for final extraction
        if current_type == "thinking":
            self.state.thinking_accumulated += output_content
        else:
            self.state.response_accumulated += output_content
        
        return output_content, current_type
    
    def _might_be_tag_start(self, text: str) -> bool:
        """Check if text might be the start of an incomplete tag"""
        if not text:
            return False
        
        # Check if it could be start of <think> or </think>
        for tag in [self.THINK_OPEN, self.THINK_CLOSE]:
            for length in range(1, len(tag)):
                if text == tag[:length]:
                    return True
        return False
    
    def get_final_content(self) -> Tuple[str, str]:
        """
        Get accumulated thinking and response content.
        Call this after all chunks are processed.
        
        Returns:
            Tuple of (thinking_content, response_content)
        """
        return (
            self.state.thinking_accumulated.strip(),
            self.state.response_accumulated.strip()
        )
    
    def reset(self):
        """Reset parser state for new conversation turn"""
        self.state = ParserState()


def extract_thinking_from_complete_text(text: str) -> Tuple[str, str]:
    """
    Extract thinking from complete text (non-streaming use case).
    
    Args:
        text: Complete LLM response with <think> tags
        
    Returns:
        Tuple of (thinking_content, response_content)
        
    Example:
        >>> text = "<think>User seems stressed</think>\\n\\nI hear you."
        >>> thinking, response = extract_thinking_from_complete_text(text)
        >>> print(thinking)
        "User seems stressed"
        >>> print(response)
        "I hear you."
    """
    # Simple regex extraction for complete text
    think_pattern = r'<think>(.*?)</think>'
    
    thinking_matches = re.findall(think_pattern, text, re.DOTALL)
    thinking_content = " ".join(thinking_matches).strip()
    
    # Remove all thinking tags and content
    response_content = re.sub(think_pattern, '', text, flags=re.DOTALL).strip()
    
    return thinking_content, response_content


def validate_thinking_tags(text: str) -> bool:
    """
    Validate that thinking tags are properly formed.
    
    Args:
        text: Text to validate
        
    Returns:
        True if tags are valid (balanced, properly nested)
        
    Raises:
        ValueError: If tags are malformed
    """
    open_count = text.count("<think>")
    close_count = text.count("</think>")
    
    if open_count != close_count:
        raise ValueError(
            f"Unbalanced thinking tags: {open_count} opening, {close_count} closing"
        )
    
    # Check for proper nesting (no nested <think> tags)
    depth = 0
    i = 0
    while i < len(text):
        if text[i:].startswith("<think>"):
            depth += 1
            if depth > 1:
                raise ValueError("Nested <think> tags are not allowed")
            i += len("<think>")
        elif text[i:].startswith("</think>"):
            depth -= 1
            if depth < 0:
                raise ValueError("Closing </think> without opening <think>")
            i += len("</think>")
        else:
            i += 1
    
    return True
