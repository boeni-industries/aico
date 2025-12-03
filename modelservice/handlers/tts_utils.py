"""
Shared utilities for TTS handlers.

This module provides common functionality used across all TTS engines
to avoid code duplication (DRY principle).
"""

import re


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing markdown, emojis, and special formatting.
    
    This function is shared across all TTS handlers (XTTS, Piper, Kokoro) to ensure
    consistent text preprocessing and avoid code duplication.
    
    Args:
        text: Raw text with markdown, emojis, and formatting
        
    Returns:
        Cleaned text suitable for TTS synthesis
    """
    # Convert em-dashes and double hyphens to period for pauses
    text = re.sub(r'\s*—\s*', '. ', text)  # Em-dash → period with space
    text = re.sub(r'\s*–\s*', '. ', text)  # En-dash → period with space
    text = re.sub(r'\s+--\s+', '. ', text)  # Double hyphen → period with space
    
    # Expand common abbreviations for better pronunciation
    text = re.sub(r'\bP\.S\.', 'Postscript', text, flags=re.IGNORECASE)
    text = re.sub(r'\be\.g\.', 'for example', text, flags=re.IGNORECASE)
    text = re.sub(r'\bi\.e\.', 'that is', text, flags=re.IGNORECASE)
    text = re.sub(r'\betc\.', 'etcetera', text, flags=re.IGNORECASE)
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove ALL emojis - comprehensive Unicode ranges
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons (😀😁😂)
    text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Symbols & pictographs (🌍🎉🎨)
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport & map (🚀🚗🏠)
    text = re.sub(r'[\U0001F900-\U0001F9FF]', '', text)  # Supplemental Symbols (🥰🤩🥳)
    text = re.sub(r'[\U0001FA00-\U0001FA6F]', '', text)  # Extended pictographs (🫠🫡)
    text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)  # Symbols and Pictographs Extended-A (🫶🫰)
    text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags (🇺🇸🇬🇧)
    text = re.sub(r'[\U00002702-\U000027B0]', '', text)  # Dingbats (✂✉)
    text = re.sub(r'[\U000024C2-\U0001F251]', '', text)  # Enclosed characters (🄐🄑)
    text = re.sub(r'[\U0001F780-\U0001F7FF]', '', text)  # Geometric Shapes Extended
    text = re.sub(r'[\U0001F800-\U0001F8FF]', '', text)  # Supplemental Arrows-C
    text = re.sub(r'[\U00002600-\U000026FF]', '', text)  # Miscellaneous Symbols (☀☁)
    text = re.sub(r'[\U00002700-\U000027BF]', '', text)  # Dingbats (✓✗)
    text = re.sub(r'[\U0001F0A0-\U0001F0FF]', '', text)  # Playing cards (🂡🂢)
    text = re.sub(r'[\U0001F100-\U0001F1FF]', '', text)  # Enclosed Alphanumeric Supplement (🄀🄁)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove trailing punctuation artifacts (space before closing paren/bracket)
    text = re.sub(r'\s+([)\]}])', r'\1', text)
    
    # Remove any remaining non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    # CRITICAL: Ensure all periods and commas have EXACTLY ONE space after them
    # This MUST be last for proper pronunciation
    text = re.sub(r'\.\s*', '. ', text)  # Period followed by any whitespace → period + single space
    text = re.sub(r',\s*', ', ', text)  # Comma followed by any whitespace → comma + single space
    
    return text
