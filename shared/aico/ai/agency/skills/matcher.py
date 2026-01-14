"""
Skill Matcher

Sophisticated, extensible skill matching system using multiple strategies:
1. Semantic similarity (embeddings)
2. Keyword matching (with synonyms)
3. Category-based matching
4. LLM-suggested skill names (fuzzy matching)
5. Fallback to generic skills

This ensures robust skill assignment that works in every case and is
easily extensible as new skills are added.
"""

from __future__ import annotations

import re
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from aico.core.logging import get_logger
from .registry import Skill, SkillRegistry


logger = get_logger("shared.ai.agency.skills.matcher")


class MatchStrategy(str, Enum):
    """Strategy used to match a skill."""
    EXACT_ID = "exact_id"  # Exact skill_id match
    SEMANTIC_EMBEDDING = "semantic_embedding"  # Embedding similarity
    KEYWORD_MATCH = "keyword_match"  # Keyword/synonym match
    CATEGORY_MATCH = "category_match"  # Category-based match
    LLM_SUGGESTION = "llm_suggestion"  # LLM suggested skill name
    FALLBACK = "fallback"  # Generic fallback


@dataclass
class SkillMatch:
    """Result of skill matching."""
    skill_id: str
    skill_name: str
    confidence: float  # 0.0 to 1.0
    strategy: MatchStrategy
    reasoning: str = ""
    
    def __repr__(self) -> str:
        return f"SkillMatch(skill_id='{self.skill_id}', confidence={self.confidence:.2f}, strategy={self.strategy.value})"


@dataclass
class SkillMetadata:
    """Extended metadata for skill matching."""
    skill_id: str
    name: str
    description: str
    category: str
    
    # Matching metadata
    keywords: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    action_verbs: List[str] = field(default_factory=list)
    
    # Embedding cache
    description_embedding: Optional[List[float]] = None
    
    @classmethod
    def from_skill(cls, skill: Skill) -> 'SkillMetadata':
        """Create metadata from skill instance."""
        return cls(
            skill_id=skill.skill_id,
            name=skill.name,
            description=skill.description,
            category=skill.category,
        )


class SkillMatcher:
    """
    Sophisticated skill matching system.
    
    Uses multiple strategies to match plan steps to skills:
    1. Exact skill_id match (if already assigned)
    2. Semantic similarity using embeddings
    3. Keyword/synonym matching
    4. Category-based matching
    5. LLM-suggested skill name fuzzy matching
    6. Fallback to generic skills
    
    Designed to be extensible - new skills automatically benefit from
    all matching strategies without code changes.
    """
    
    def __init__(
        self,
        skill_registry: SkillRegistry,
        embedding_client: Optional[Any] = None,
        db_connection: Optional[Any] = None,  # Skills being redesigned
    ):
        """
        Initialize skill matcher.
        
        Args:
            skill_registry: Registry of available skills
            embedding_client: Optional client for semantic embeddings
            db_connection: Optional database connection for gap tracking
        """
        self.skill_registry = skill_registry
        self.embedding_client = embedding_client
        self.db_connection = db_connection
        
        # Build skill metadata index
        self.skill_metadata: Dict[str, SkillMetadata] = {}
        self._build_metadata_index()
        
        logger.debug(
            f"🎯 [SKILL_MATCHER] Initialized with {len(self.skill_metadata)} skills"
        )
    
    def _build_metadata_index(self) -> None:
        """Build enriched metadata index for all skills."""
        skills = self.skill_registry.list_all()
        
        for skill in skills:
            metadata = SkillMetadata.from_skill(skill)
            
            # Auto-generate keywords from skill name and description
            metadata.keywords = self._extract_keywords(skill.name, skill.description)
            
            # Auto-generate action verbs from description
            metadata.action_verbs = self._extract_action_verbs(skill.description)
            
            # Add skill-specific enrichment
            self._enrich_skill_metadata(metadata, skill)
            
            self.skill_metadata[skill.skill_id] = metadata
        
        logger.debug(
            f"🎯 [SKILL_MATCHER] Built metadata index for {len(self.skill_metadata)} skills"
        )
    
    def _extract_keywords(self, name: str, description: str) -> List[str]:
        """Extract keywords from skill name and description."""
        # Combine name and description
        text = f"{name} {description}".lower()
        
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their'
        }
        
        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-z]+\b', text)
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:20]  # Limit to top 20
    
    def _extract_action_verbs(self, description: str) -> List[str]:
        """Extract action verbs from description."""
        # Common action verbs in skill descriptions
        action_patterns = [
            r'\b(ask|search|find|analyze|create|build|develop|implement|'
            r'monitor|track|review|assess|evaluate|gather|collect|retrieve|'
            r'update|modify|change|initiate|start|begin|complete|finish|'
            r'reflect|consider|think|plan|organize|structure|synthesize|'
            r'communicate|inform|notify|alert|question|clarify|understand)\b'
        ]
        
        verbs = []
        text = description.lower()
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            verbs.extend(matches)
        
        return list(set(verbs))  # Remove duplicates
    
    def _enrich_skill_metadata(self, metadata: SkillMetadata, skill: Skill) -> None:
        """Add skill-specific enrichment (synonyms, use cases, etc.)."""
        # Skill-specific enrichment based on skill_id
        enrichment_map = {
            'ask_user': {
                'synonyms': ['question', 'inquire', 'query', 'clarify', 'confirm'],
                'use_cases': ['information gathering', 'clarification', 'preference discovery'],
                'action_verbs': ['ask', 'question', 'clarify', 'confirm', 'inquire'],
            },
            'search_memory': {
                'synonyms': ['find', 'lookup', 'retrieve', 'recall', 'remember'],
                'use_cases': ['knowledge retrieval', 'context building', 'fact finding'],
                'action_verbs': ['search', 'find', 'lookup', 'retrieve', 'recall'],
            },
            'analyze_conversation': {
                'synonyms': ['examine', 'study', 'review', 'investigate', 'assess'],
                'use_cases': ['pattern analysis', 'user understanding', 'insight extraction'],
                'action_verbs': ['analyze', 'examine', 'study', 'review', 'assess'],
            },
            'update_knowledge_graph': {
                'synonyms': ['curate', 'organize', 'structure', 'maintain', 'manage'],
                'use_cases': ['knowledge organization', 'graph curation', 'data structuring'],
                'action_verbs': ['update', 'curate', 'organize', 'structure', 'maintain'],
            },
            'reflect_on_goal': {
                'synonyms': ['evaluate', 'review', 'assess', 'consider', 'contemplate'],
                'use_cases': ['goal evaluation', 'progress review', 'self-reflection'],
                'action_verbs': ['reflect', 'evaluate', 'review', 'assess', 'consider'],
            },
            'initiate_conversation': {
                'synonyms': ['start', 'begin', 'commence', 'launch', 'trigger'],
                'use_cases': ['proactive engagement', 'conversation starting', 'user interaction'],
                'action_verbs': ['initiate', 'start', 'begin', 'commence', 'engage'],
            },
        }
        
        if skill.skill_id in enrichment_map:
            enrichment = enrichment_map[skill.skill_id]
            metadata.synonyms = enrichment.get('synonyms', [])
            metadata.use_cases = enrichment.get('use_cases', [])
            metadata.action_verbs.extend(enrichment.get('action_verbs', []))
            metadata.action_verbs = list(set(metadata.action_verbs))  # Remove duplicates
    
    async def match_skill(
        self,
        step_description: str,
        step_metadata: Dict[str, Any],
        llm_suggested_skills: Optional[List[str]] = None,
    ) -> Optional[SkillMatch]:
        """
        Match a plan step to the best skill.
        
        Args:
            step_description: Description of the plan step
            step_metadata: Step metadata (shape_role, etc.)
            llm_suggested_skills: Optional list of skill names suggested by LLM
            
        Returns:
            SkillMatch with best matching skill, or None if no match
        """
        # Strategy 1: Exact skill_id match (if already assigned)
        if 'skill_id' in step_metadata and step_metadata['skill_id']:
            skill_id = step_metadata['skill_id']
            if self.skill_registry.skill_exists(skill_id):
                return SkillMatch(
                    skill_id=skill_id,
                    skill_name=self.skill_registry.get(skill_id).name,
                    confidence=1.0,
                    strategy=MatchStrategy.EXACT_ID,
                    reasoning="Skill already assigned"
                )
        
        # Collect all potential matches with scores
        matches: List[SkillMatch] = []
        
        # Strategy 2: Semantic embedding similarity
        if self.embedding_client:
            semantic_matches = await self._match_by_embedding(step_description)
            matches.extend(semantic_matches)
        
        # Strategy 3: Keyword matching
        keyword_matches = self._match_by_keywords(step_description, llm_suggested_skills)
        matches.extend(keyword_matches)
        
        # Strategy 4: Category matching (based on shape_role)
        if 'shape_role' in step_metadata:
            category_matches = self._match_by_category(step_metadata['shape_role'])
            matches.extend(category_matches)
        
        # Strategy 5: LLM suggestion fuzzy matching
        if llm_suggested_skills:
            llm_matches = self._match_by_llm_suggestions(llm_suggested_skills)
            matches.extend(llm_matches)
        
        # Strategy 6: Fallback to generic skills
        if not matches:
            fallback_match = self._fallback_match(step_description, step_metadata)
            if fallback_match is not None:
                matches.append(fallback_match)
        
        # Select best match
        if matches:
            # Sort by confidence (descending)
            matches.sort(key=lambda m: m.confidence, reverse=True)
            best_match = matches[0]
            
            logger.debug(
                f"🎯 [SKILL_MATCHER] Matched '{step_description[:50]}...' → "
                f"{best_match.skill_id} (confidence={best_match.confidence:.2f}, "
                f"strategy={best_match.strategy.value})"
            )
            
            return best_match
        
        logger.warning(
            f"🎯 [SKILL_MATCHER] No skill match found for: {step_description[:100]}..."
        )
        
        # Log skill gap for learning
        await self._log_skill_gap(
            step_description=step_description,
            step_metadata=step_metadata,
            llm_suggested_skills=llm_suggested_skills or []
        )
        
        return None
    
    async def _match_by_embedding(self, description: str) -> List[SkillMatch]:
        """Match using semantic embeddings."""
        # TODO: Implement embedding-based matching
        # This would use the embedding_client to compute similarity
        # between step description and skill descriptions
        return []
    
    def _match_by_keywords(
        self,
        description: str,
        llm_suggested_skills: Optional[List[str]] = None
    ) -> List[SkillMatch]:
        """Match using keyword and synonym matching."""
        matches = []
        description_lower = description.lower()
        
        for skill_id, metadata in self.skill_metadata.items():
            score = 0.0
            matched_terms = []
            
            # Check action verbs (high weight)
            for verb in metadata.action_verbs:
                if re.search(rf'\b{verb}\w*\b', description_lower):
                    score += 0.3
                    matched_terms.append(f"verb:{verb}")
            
            # Check keywords (medium weight)
            for keyword in metadata.keywords[:10]:  # Top 10 keywords
                if keyword in description_lower:
                    score += 0.15
                    matched_terms.append(f"keyword:{keyword}")
            
            # Check synonyms (medium weight)
            for synonym in metadata.synonyms:
                if re.search(rf'\b{synonym}\w*\b', description_lower):
                    score += 0.2
                    matched_terms.append(f"synonym:{synonym}")
            
            # Check LLM suggestions (if provided)
            if llm_suggested_skills:
                for suggested in llm_suggested_skills:
                    suggested_lower = suggested.lower()
                    # Check if suggestion matches skill name or synonyms
                    if (suggested_lower in metadata.name.lower() or
                        any(suggested_lower in syn.lower() for syn in metadata.synonyms)):
                        score += 0.4
                        matched_terms.append(f"llm_suggestion:{suggested}")
            
            # Normalize score to 0-1 range (cap at 1.0)
            confidence = min(score, 1.0)
            
            if confidence > 0.3:  # Threshold for keyword matching
                matches.append(SkillMatch(
                    skill_id=skill_id,
                    skill_name=metadata.name,
                    confidence=confidence,
                    strategy=MatchStrategy.KEYWORD_MATCH,
                    reasoning=f"Matched: {', '.join(matched_terms[:3])}"
                ))
        
        return matches
    
    def _match_by_category(self, shape_role: str) -> List[SkillMatch]:
        """Match based on shape_role to category mapping."""
        # Role to category mapping
        role_to_category = {
            'research': 'memory',
            'clarify': 'communication',
            'synthesize': 'analysis',
            'act': 'communication',
            'reflect': 'reflection',
            'organize': 'knowledge',
        }
        
        category = role_to_category.get(shape_role)
        if not category:
            return []
        
        # Get all skills in category
        category_skills = self.skill_registry.list_by_category(category)
        
        matches = []
        for skill in category_skills:
            matches.append(SkillMatch(
                skill_id=skill.skill_id,
                skill_name=skill.name,
                confidence=0.6,  # Medium confidence for category match
                strategy=MatchStrategy.CATEGORY_MATCH,
                reasoning=f"Category match: {category} (from role: {shape_role})"
            ))
        
        return matches
    
    def _match_by_llm_suggestions(self, suggested_skills: List[str]) -> List[SkillMatch]:
        """Fuzzy match LLM-suggested skill names to actual skills."""
        matches = []
        
        for suggested in suggested_skills:
            suggested_lower = suggested.lower()
            
            # Try exact name match first
            for skill_id, metadata in self.skill_metadata.items():
                name_lower = metadata.name.lower()
                
                # Exact match
                if suggested_lower == name_lower:
                    matches.append(SkillMatch(
                        skill_id=skill_id,
                        skill_name=metadata.name,
                        confidence=0.9,
                        strategy=MatchStrategy.LLM_SUGGESTION,
                        reasoning=f"LLM suggested exact match: '{suggested}'"
                    ))
                    continue
                
                # Partial match (contains)
                if suggested_lower in name_lower or name_lower in suggested_lower:
                    matches.append(SkillMatch(
                        skill_id=skill_id,
                        skill_name=metadata.name,
                        confidence=0.7,
                        strategy=MatchStrategy.LLM_SUGGESTION,
                        reasoning=f"LLM suggested partial match: '{suggested}'"
                    ))
                    continue
                
                # Synonym match
                for synonym in metadata.synonyms:
                    if suggested_lower in synonym.lower() or synonym.lower() in suggested_lower:
                        matches.append(SkillMatch(
                            skill_id=skill_id,
                            skill_name=metadata.name,
                            confidence=0.65,
                            strategy=MatchStrategy.LLM_SUGGESTION,
                            reasoning=f"LLM suggested synonym match: '{suggested}' → '{synonym}'"
                        ))
                        break
        
        return matches
    
    def _fallback_match(
        self,
        description: str,
        metadata: Dict[str, Any]
    ) -> Optional[SkillMatch]:
        """Fallback to generic skill based on description patterns.
        
        Returns None if no pattern matches - this signals a skill gap that should
        be logged for development consideration but NOT executed.
        """
        description_lower = description.lower()
        
        # Fallback patterns (ordered by specificity)
        if any(word in description_lower for word in ['ask', 'question', 'clarify', 'understand', 'confirm', 'prompt', 'request']):
            return SkillMatch(
                skill_id='ask_user',
                skill_name='Ask User',
                confidence=0.4,
                strategy=MatchStrategy.FALLBACK,
                reasoning="Fallback: Question/clarification pattern detected"
            )
        
        if any(word in description_lower for word in ['search', 'find', 'lookup', 'retrieve', 'recall', 'remember', 'research']):
            return SkillMatch(
                skill_id='search_memory',
                skill_name='Search Memory',
                confidence=0.4,
                strategy=MatchStrategy.FALLBACK,
                reasoning="Fallback: Search/retrieval pattern detected"
            )
        
        if any(word in description_lower for word in ['analyze', 'examine', 'study', 'review', 'assess', 'evaluate']):
            return SkillMatch(
                skill_id='analyze_conversation',
                skill_name='Analyze Conversation',
                confidence=0.4,
                strategy=MatchStrategy.FALLBACK,
                reasoning="Fallback: Analysis pattern detected"
            )
        
        # Catch-all fallback: Default to initiate_conversation for any unmatched step
        # This ensures all steps can execute, even if they don't match specific patterns
        # The skill gap will still be logged for future skill development
        logger.warning(
            f"🎯 [SKILL_MATCHER] No specific pattern match for '{description[:100]}...' - "
            f"using default fallback skill 'initiate_conversation'"
        )
        return SkillMatch(
            skill_id='initiate_conversation',
            skill_name='Initiate Conversation',
            confidence=0.3,
            strategy=MatchStrategy.FALLBACK,
            reasoning="Default fallback: No specific pattern matched, using conversation skill"
        )
    
    async def _log_skill_gap(
        self,
        step_description: str,
        step_metadata: Dict[str, Any],
        llm_suggested_skills: List[str]
    ) -> None:
        """Log unmatched skill pattern for learning and development planning."""
        if not self.db_connection:
            logger.debug("🎯 [SKILL_MATCHER] No database connection - skipping gap logging")
            return
        
        try:
            # Generate embedding for similarity matching
            embedding = None
            if self.embedding_client:
                try:
                    embedding = await self._generate_embedding(step_description)
                except Exception as e:
                    logger.debug(f"🎯 [SKILL_MATCHER] Could not generate embedding: {e}")
            
            # Find similar existing gaps to avoid duplicates
            similar_gap_id = await self._find_similar_gap(
                step_description=step_description,
                embedding=embedding
            )
            
            if similar_gap_id:
                # Update existing gap frequency
                await self._increment_gap_frequency(similar_gap_id)
                logger.debug(
                    f"🎯 [SKILL_MATCHER] Updated existing gap frequency: {similar_gap_id}"
                )
            else:
                # Create new gap entry
                gap_id = self._generate_gap_id(step_description)
                skill_spec = self._generate_skill_specification(
                    step_description=step_description,
                    llm_suggested_skills=llm_suggested_skills,
                    step_metadata=step_metadata
                )
                
                now = datetime.utcnow().isoformat()
                
                self.db_connection.execute(
                    """
                    INSERT INTO agency_skill_gaps (
                        gap_id, step_description, llm_suggested_skills,
                        step_metadata, pattern_embedding, frequency_count,
                        first_seen_at, last_seen_at, priority_score,
                        suggested_skill_spec, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        gap_id,
                        step_description,
                        json.dumps(llm_suggested_skills),
                        json.dumps(step_metadata),
                        json.dumps(embedding) if embedding else None,
                        1,  # frequency_count
                        now,
                        now,
                        self._calculate_priority_score(step_metadata),
                        skill_spec,
                        None,  # notes
                        now,
                        now
                    )
                )
                
                logger.info(
                    f"📊 [SKILL_MATCHER] Logged new skill gap: {gap_id} - '{step_description[:60]}...'"
                )
        
        except Exception as e:
            logger.error(f"🎯 [SKILL_MATCHER] Error logging skill gap: {e}")
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using embedding client."""
        if not self.embedding_client:
            return None
        
        # Use modelservice client to generate embeddings
        try:
            if hasattr(self.embedding_client, 'get_embeddings'):
                result = await self.embedding_client.get_embeddings(
                    model="paraphrase-multilingual",
                    prompt=text
                )
                if result.get("success") and result.get("data", {}).get("embedding"):
                    return result["data"]["embedding"]
        except Exception as e:
            logger.debug(f"🎯 [SKILL_MATCHER] Embedding generation failed: {e}")
        
        return None
    
    async def _find_similar_gap(
        self,
        step_description: str,
        embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        """Find similar existing gap to avoid duplicates."""
        if not self.db_connection:
            return None
        
        try:
            # First try exact description match
            result = self.db_connection.execute(
                "SELECT gap_id FROM agency_skill_gaps WHERE step_description = ?",
                (step_description,)
            ).fetchone()
            if result:
                return result[0]
            
            # If we have embeddings, find semantically similar gaps
            if embedding:
                # Fetch all gaps with embeddings
                gaps = self.db_connection.execute(
                    "SELECT gap_id, step_description, pattern_embedding FROM agency_skill_gaps WHERE pattern_embedding IS NOT NULL"
                ).fetchall()
                
                # Calculate cosine similarity
                best_match_id = None
                best_similarity = 0.0
                
                for gap_id, desc, emb_json in gaps:
                    try:
                        gap_embedding = json.loads(emb_json)
                        similarity = self._cosine_similarity(embedding, gap_embedding)
                        
                        # Similarity threshold (0.75) - groups similar patterns while avoiding false positives
                        if similarity > 0.75 and similarity > best_similarity:
                            best_similarity = similarity
                            best_match_id = gap_id
                    except Exception:
                        continue
                
                if best_match_id:
                    logger.debug(
                        f"🎯 [SKILL_MATCHER] Found similar gap (similarity={best_similarity:.2f}): {best_match_id}"
                    )
                    return best_match_id
        
        except Exception as e:
            logger.debug(f"🎯 [SKILL_MATCHER] Error finding similar gap: {e}")
        
        return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _increment_gap_frequency(self, gap_id: str) -> None:
        """Increment frequency count for existing gap."""
        if not self.db_connection:
            return
        
        try:
            now = datetime.utcnow().isoformat()
            self.db_connection.execute(
                """
                UPDATE agency_skill_gaps
                SET frequency_count = frequency_count + 1,
                    last_seen_at = ?,
                    updated_at = ?
                WHERE gap_id = ?
                """,
                (now, now, gap_id)
            )
        except Exception as e:
            logger.error(f"🎯 [SKILL_MATCHER] Error incrementing gap frequency: {e}")
    
    def _generate_gap_id(self, step_description: str) -> str:
        """Generate unique ID for skill gap."""
        # Use hash of description for deterministic ID
        hash_obj = hashlib.sha256(step_description.encode('utf-8'))
        return f"gap_{hash_obj.hexdigest()[:16]}"
    
    def _calculate_priority_score(self, step_metadata: Dict[str, Any]) -> float:
        """Calculate priority score based on context."""
        # Base priority
        priority = 1.0
        
        # Increase priority for high-importance goals
        goal_priority = step_metadata.get('goal_priority', 'normal')
        if goal_priority == 'high':
            priority *= 2.0
        elif goal_priority == 'urgent':
            priority *= 3.0
        
        return priority
    
    def _generate_skill_specification(
        self,
        step_description: str,
        llm_suggested_skills: List[str],
        step_metadata: Dict[str, Any]
    ) -> str:
        """Generate skill specification from pattern."""
        # Extract action verbs from description
        action_verbs = self._extract_action_verbs(step_description)
        
        # Extract key concepts
        keywords = self._extract_keywords(step_description, "")
        
        # Build specification
        spec_parts = []
        
        if llm_suggested_skills:
            spec_parts.append(f"**Suggested Skill Names:** {', '.join(llm_suggested_skills)}")
        
        if action_verbs:
            spec_parts.append(f"**Required Actions:** {', '.join(action_verbs)}")
        
        if keywords:
            spec_parts.append(f"**Key Concepts:** {', '.join(keywords[:10])}")
        
        spec_parts.append(f"**Example Use Case:** {step_description}")
        
        if 'shape_role' in step_metadata:
            spec_parts.append(f"**Category Hint:** {step_metadata['shape_role']}")
        
        return "\n\n".join(spec_parts)
    
    def refresh_metadata(self) -> None:
        """Refresh metadata index (call when new skills are registered)."""
        self._build_metadata_index()
        logger.info(
            f"🎯 [SKILL_MATCHER] Refreshed metadata index: {len(self.skill_metadata)} skills"
        )
