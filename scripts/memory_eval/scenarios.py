"""
Conversation Scenarios for Memory Evaluation

Defines realistic conversation scenarios that test different aspects of AICO's
memory system including entity extraction, context retention, thread management,
and semantic understanding.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation scenario"""
    user_message: str
    expected_entities: Dict[str, List[str]] = field(default_factory=dict)
    expected_context_elements: List[str] = field(default_factory=list)
    context_hints: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    
    # Memory-specific expectations
    should_remember_from_turns: List[int] = field(default_factory=list)
    should_reference_entities: List[str] = field(default_factory=list)
    thread_expectation: str = "continue"  # continue, new, reactivate


@dataclass 
class ConversationScenario:
    """Complete conversation scenario for memory testing"""
    name: str
    description: str
    conversation_turns: List[ConversationTurn]
    success_criteria: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Memory testing focus areas
    tests_working_memory: bool = True
    tests_episodic_memory: bool = True
    tests_semantic_memory: bool = True
    tests_procedural_memory: bool = False
    tests_thread_management: bool = True
    tests_entity_extraction: bool = True
    
    # Scenario metadata
    estimated_duration_minutes: int = 5
    difficulty_level: str = "medium"  # easy, medium, hard, expert


class ScenarioLibrary:
    """Library of predefined conversation scenarios for memory evaluation"""
    
    def __init__(self):
        self.scenarios: Dict[str, ConversationScenario] = {}
        self._initialize_scenarios()
        
    def _initialize_scenarios(self):
        """Initialize all predefined scenarios"""
        
        # Comprehensive Memory Test - Primary 6-turn scenario
        self.scenarios["comprehensive_memory_test"] = ConversationScenario(
            name="comprehensive_memory_test",
            description="6-turn conversation testing all memory components with entity extraction, context retention, and thread management",
            conversation_turns=[
                ConversationTurn(
                    user_message="Hi AICO! I'm Michael, and I just moved to San Francisco last week. I'm really excited about starting my new job at TechCorp on Monday!",
                    expected_entities={
                        "PERSON": ["Michael"],
                        "GPE": ["San Francisco"], 
                        "ORG": ["TechCorp"],
                        "DATE": ["last week", "Monday"]
                    },
                    expected_context_elements=[
                        "user_name_michael",
                        "location_san_francisco", 
                        "new_job_techcorp",
                        "recent_move",
                        "excitement_emotion"
                    ],
                    validation_rules=[
                        "should_acknowledge_name",
                        "should_show_enthusiasm",
                        "should_ask_follow_up_about_job_or_move"
                    ],
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="Thanks! I'm a bit nervous though. It's a software engineering role, and I'll be working on their AI platform. Do you have any advice for starting a new tech job?",
                    expected_entities={
                        "WORK_OF_ART": ["AI platform"],
                        "PERSON": ["software engineer"]
                    },
                    expected_context_elements=[
                        "job_role_software_engineer",
                        "nervous_emotion",
                        "ai_platform_work",
                        "seeking_advice"
                    ],
                    should_remember_from_turns=[1],
                    should_reference_entities=["Michael", "TechCorp"],
                    validation_rules=[
                        "should_remember_user_name",
                        "should_reference_techcorp_context",
                        "should_provide_relevant_advice",
                        "should_acknowledge_nervousness"
                    ],
                    thread_expectation="continue"
                ),
                ConversationTurn(
                    user_message="That's great advice! By the way, I have a cat named Whiskers who's been stressed about the move. Any tips for helping pets adjust to new places?",
                    expected_entities={
                        "PERSON": ["Whiskers"],
                        "ANIMAL": ["cat"]
                    },
                    expected_context_elements=[
                        "pet_cat_whiskers",
                        "pet_stress",
                        "move_adjustment",
                        "topic_shift_to_pets"
                    ],
                    should_remember_from_turns=[1],
                    should_reference_entities=["Michael", "San Francisco"],
                    validation_rules=[
                        "should_remember_recent_move_context",
                        "should_provide_pet_advice",
                        "should_handle_topic_shift_gracefully"
                    ],
                    thread_expectation="continue"
                ),
                ConversationTurn(
                    user_message="Perfect! Oh, I almost forgot - my birthday is next Friday, October 13th. I'm turning 28. I was thinking of exploring some restaurants in the city to celebrate.",
                    expected_entities={
                        "DATE": ["next Friday", "October 13th"],
                        "CARDINAL": ["28"],
                        "EVENT": ["birthday"]
                    },
                    expected_context_elements=[
                        "birthday_october_13",
                        "age_28",
                        "restaurant_celebration",
                        "city_exploration"
                    ],
                    should_remember_from_turns=[1],
                    should_reference_entities=["Michael", "San Francisco"],
                    validation_rules=[
                        "should_acknowledge_birthday",
                        "should_suggest_sf_restaurants",
                        "should_remember_sf_location",
                        "should_show_enthusiasm_for_celebration"
                    ],
                    thread_expectation="continue"
                ),
                ConversationTurn(
                    user_message="Those sound amazing! I love Italian food. Actually, can you remind me what my job title is again? I want to make sure I introduce myself correctly on Monday.",
                    expected_entities={
                        "CUISINE": ["Italian"],
                        "DATE": ["Monday"]
                    },
                    expected_context_elements=[
                        "italian_food_preference",
                        "job_title_verification",
                        "monday_start_reminder"
                    ],
                    should_remember_from_turns=[2],
                    should_reference_entities=["software engineering", "TechCorp"],
                    validation_rules=[
                        "should_recall_job_title_software_engineer",
                        "should_reference_techcorp",
                        "should_remember_monday_start_date",
                        "should_acknowledge_italian_preference"
                    ],
                    thread_expectation="continue"
                ),
                ConversationTurn(
                    user_message="Exactly! And what was my cat's name again? I want to tell my new coworkers about him.",
                    expected_entities={
                        "ANIMAL": ["cat"],
                        "PERSON": ["coworkers"]
                    },
                    expected_context_elements=[
                        "cat_name_recall",
                        "coworker_sharing",
                        "pet_introduction"
                    ],
                    should_remember_from_turns=[3],
                    should_reference_entities=["Whiskers", "cat"],
                    validation_rules=[
                        "should_recall_cat_name_whiskers",
                        "should_remember_cat_context",
                        "should_show_continuity_with_pet_discussion"
                    ],
                    thread_expectation="continue"
                )
            ],
            success_criteria={
                "context_adherence": 0.85,
                "knowledge_retention": 0.90,
                "entity_extraction": 0.80,
                "conversation_relevancy": 0.85,
                "thread_management": 0.95,
                "overall_score": 0.85
            },
            tags=["comprehensive", "memory", "entities", "context", "6-turn"],
            tests_working_memory=True,
            tests_episodic_memory=True,
            tests_semantic_memory=True,
            tests_thread_management=True,
            tests_entity_extraction=True,
            estimated_duration_minutes=8,
            difficulty_level="medium"
        )
        
        # Entity Extraction Focus Test
        self.scenarios["entity_extraction_intensive"] = ConversationScenario(
            name="entity_extraction_intensive",
            description="Intensive entity extraction testing with complex named entities and relationships",
            conversation_turns=[
                ConversationTurn(
                    user_message="I'm planning a trip to Tokyo, Japan from December 15th to December 22nd, 2024. I'll be staying at the Grand Hyatt Tokyo in Roppongi district.",
                    expected_entities={
                        "GPE": ["Tokyo", "Japan", "Roppongi"],
                        "DATE": ["December 15th", "December 22nd", "2024"],
                        "ORG": ["Grand Hyatt Tokyo"],
                        "FAC": ["Grand Hyatt Tokyo"]
                    },
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="I want to visit the Tokyo National Museum, Senso-ji Temple, and maybe catch a baseball game at Tokyo Dome. My budget is around $3000 USD.",
                    expected_entities={
                        "FAC": ["Tokyo National Museum", "Senso-ji Temple", "Tokyo Dome"],
                        "MONEY": ["$3000", "USD"],
                        "EVENT": ["baseball game"]
                    },
                    should_remember_from_turns=[1],
                    thread_expectation="continue"
                ),
                ConversationTurn(
                    user_message="I'm also meeting my colleague Sarah Chen from Microsoft's Tokyo office on December 18th for dinner at Sukiyabashi Jiro.",
                    expected_entities={
                        "PERSON": ["Sarah Chen"],
                        "ORG": ["Microsoft"],
                        "GPE": ["Tokyo"],
                        "DATE": ["December 18th"],
                        "ORG": ["Sukiyabashi Jiro"]
                    },
                    should_remember_from_turns=[1],
                    thread_expectation="continue"
                )
            ],
            success_criteria={
                "entity_extraction": 0.95,
                "knowledge_retention": 0.85,
                "context_adherence": 0.80
            },
            tags=["entities", "extraction", "complex", "travel"],
            tests_entity_extraction=True,
            difficulty_level="hard"
        )
        
        # Thread Management Test
        self.scenarios["thread_management_test"] = ConversationScenario(
            name="thread_management_test", 
            description="Tests thread creation, continuation, and reactivation logic",
            conversation_turns=[
                ConversationTurn(
                    user_message="Hi! I need help with my Python project.",
                    expected_context_elements=["programming_help", "python_project"],
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="Actually, let's talk about something completely different. What's the weather like?",
                    expected_context_elements=["topic_change", "weather_inquiry"],
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="Going back to my Python project - I'm having trouble with async functions.",
                    expected_context_elements=["python_project", "async_functions", "programming_help"],
                    should_remember_from_turns=[1],
                    thread_expectation="reactivate"
                )
            ],
            success_criteria={
                "thread_management": 0.90,
                "context_adherence": 0.85
            },
            tags=["threads", "management", "context-switching"],
            tests_thread_management=True,
            difficulty_level="medium"
        )
        
        # Long-term Memory Test
        self.scenarios["long_term_memory_test"] = ConversationScenario(
            name="long_term_memory_test",
            description="Tests long-term retention and recall across extended conversations",
            conversation_turns=[
                ConversationTurn(
                    user_message="I'm Sarah, a marine biologist studying coral reefs in the Great Barrier Reef. I've been working on this research for 3 years.",
                    expected_entities={
                        "PERSON": ["Sarah"],
                        "WORK_OF_ART": ["marine biologist"],
                        "LOC": ["Great Barrier Reef"],
                        "DATE": ["3 years"]
                    },
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="Let's talk about cooking instead. I love making Italian pasta dishes.",
                    expected_context_elements=["cooking", "italian_cuisine", "pasta"],
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="Back to my research - can you help me understand coral bleaching patterns?",
                    should_remember_from_turns=[1],
                    should_reference_entities=["Sarah", "marine biologist", "Great Barrier Reef"],
                    validation_rules=[
                        "should_remember_sarah_name",
                        "should_recall_marine_biology_context",
                        "should_reference_coral_reef_research"
                    ],
                    thread_expectation="reactivate"
                )
            ],
            success_criteria={
                "knowledge_retention": 0.95,
                "thread_management": 0.85,
                "context_adherence": 0.90
            },
            tags=["long-term", "retention", "recall"],
            tests_episodic_memory=True,
            tests_semantic_memory=True,
            difficulty_level="hard"
        )
        
        # Performance Stress Test
        self.scenarios["performance_stress_test"] = ConversationScenario(
            name="performance_stress_test",
            description="High-volume conversation with many entities and context switches for performance testing",
            conversation_turns=[
                ConversationTurn(
                    user_message="I'm organizing a conference in New York City from March 15-17, 2024. We have speakers from Google, Microsoft, Apple, Amazon, and Meta coming. The venue is the Javits Center.",
                    expected_entities={
                        "GPE": ["New York City"],
                        "DATE": ["March 15-17, 2024"],
                        "ORG": ["Google", "Microsoft", "Apple", "Amazon", "Meta", "Javits Center"]
                    },
                    thread_expectation="new"
                ),
                ConversationTurn(
                    user_message="We need catering for 500 people, including vegetarian, vegan, and gluten-free options. Budget is $50,000. Can you suggest some NYC caterers?",
                    expected_entities={
                        "CARDINAL": ["500"],
                        "MONEY": ["$50,000"],
                        "GPE": ["NYC"]
                    },
                    should_remember_from_turns=[1],
                    thread_expectation="continue"
                )
            ],
            success_criteria={
                "entity_extraction": 0.90,
                "performance_metrics": {"response_time_ms": 2000}
            },
            tags=["performance", "stress", "high-volume"],
            difficulty_level="expert"
        )
        
    def get_scenario(self, name: str) -> Optional[ConversationScenario]:
        """Get a scenario by name"""
        return self.scenarios.get(name)
        
    def list_scenarios(self) -> List[str]:
        """List all available scenario names"""
        return list(self.scenarios.keys())
        
    def get_scenarios_by_tag(self, tag: str) -> List[ConversationScenario]:
        """Get all scenarios with a specific tag"""
        return [scenario for scenario in self.scenarios.values() if tag in scenario.tags]
        
    def get_scenarios_by_difficulty(self, difficulty: str) -> List[ConversationScenario]:
        """Get scenarios by difficulty level"""
        return [scenario for scenario in self.scenarios.values() if scenario.difficulty_level == difficulty]
        
    def add_custom_scenario(self, scenario: ConversationScenario):
        """Add a custom scenario to the library"""
        self.scenarios[scenario.name] = scenario
