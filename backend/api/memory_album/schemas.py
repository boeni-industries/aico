"""
Memory Album API Schemas

Pydantic models for memory album API requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RememberRequest(BaseModel):
    """Request schema for 'Remember This' action"""
    conversation_id: str = Field(..., description="Source conversation ID")
    message_id: Optional[str] = Field(None, description="Source message ID (None = whole conversation)")
    content: str = Field(..., description="The text to remember")
    content_type: str = Field(default="message", description="Type of content (message, conversation, excerpt)")
    fact_type: str = Field(default="preference", description="Type of fact (identity, preference, relationship, temporal)")
    category: str = Field(default="personal", description="Category (personal_info, preferences, relationships, etc.)")
    user_note: Optional[str] = Field(None, description="Optional user annotation")
    tags: Optional[List[str]] = Field(None, description="Optional user-defined tags")
    emotional_tone: Optional[str] = Field(None, description="Emotional tone (joyful, reflective, vulnerable, etc.)")
    memory_type: str = Field(default="fact", description="Type of memory (fact, insight, moment, milestone, wisdom)")
    
    # Conversation-level fields
    conversation_title: Optional[str] = Field(None, description="Title for conversation memory")
    conversation_summary: Optional[str] = Field(None, description="Summary of conversation")
    turn_range: Optional[str] = Field(None, description="Turn range (e.g., '1-5' or None = all)")
    key_moments: Optional[List[str]] = Field(None, description="Key moments from conversation")


class UpdateMemoryRequest(BaseModel):
    """Request schema for updating memory metadata"""
    user_note: Optional[str] = Field(None, description="User annotation")
    tags: Optional[List[str]] = Field(None, description="User-defined tags")
    is_favorite: Optional[bool] = Field(None, description="Favorite status")


class MemoryResponse(BaseModel):
    """Response schema for a single memory"""
    fact_id: str = Field(..., description="Memory identifier")
    content: str = Field(..., description="The remembered text")
    content_type: str = Field(..., description="Type of content (message, conversation, excerpt)")
    category: str = Field(..., description="Memory category")
    fact_type: str = Field(..., description="Fact type")
    user_note: Optional[str] = Field(None, description="User annotation")
    tags: Optional[List[str]] = Field(None, description="User-defined tags")
    is_favorite: bool = Field(..., description="Favorite status")
    emotional_tone: Optional[str] = Field(None, description="Emotional tone")
    memory_type: Optional[str] = Field(None, description="Memory type")
    source_conversation_id: str = Field(..., description="Source conversation")
    source_message_id: Optional[str] = Field(None, description="Source message")
    revisit_count: int = Field(..., description="Number of times viewed")
    last_revisited: Optional[str] = Field(None, description="Last revisit timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    # Conversation-level fields
    conversation_title: Optional[str] = Field(None, description="Title for conversation memory")
    conversation_summary: Optional[str] = Field(None, description="Summary of conversation")
    turn_range: Optional[str] = Field(None, description="Turn range")
    key_moments: Optional[List[str]] = Field(None, description="Key moments from conversation")


class MemoryListResponse(BaseModel):
    """Response schema for memory list"""
    memories: List[MemoryResponse] = Field(..., description="List of memories")
    total: int = Field(..., description="Total number of memories")
    limit: int = Field(..., description="Query limit used")
    offset: int = Field(..., description="Query offset used")


class RememberResponse(BaseModel):
    """Response schema for 'Remember This' action"""
    success: bool = Field(..., description="Whether operation succeeded")
    fact_id: str = Field(..., description="ID of the stored memory")
    message: str = Field(..., description="Success message")
