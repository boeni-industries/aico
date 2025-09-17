"""
AICO Central Topic Registry

Provides centralized topic definitions and builders for the AICO message bus system.
Uses hierarchical slash notation following industry best practices.

Topic Structure: <domain>/<object>/<action>/v<version>[/<properties>]
"""

from typing import Optional


class AICOTopics:
    """
    Central registry for all AICO message bus topics and prefixes.
    - Use ZMQ_*_PREFIX for ZMQ SUBSCRIBE (prefix matching)
    - Use ALL_* for DB/API queries and documentation (wildcard matching)
    """
    # ZMQ prefix constants for all major domains
    ZMQ_LOGS_PREFIX = "logs/"
    ZMQ_EMOTION_PREFIX = "emotion/"
    ZMQ_PERSONALITY_PREFIX = "personality/"
    ZMQ_AGENCY_PREFIX = "agency/"
    ZMQ_CONVERSATION_PREFIX = "conversation/"
    ZMQ_MEMORY_PREFIX = "memory/"
    ZMQ_USER_PREFIX = "user/"
    ZMQ_LLM_PREFIX = "llm/"
    ZMQ_UI_PREFIX = "ui/"
    ZMQ_SYSTEM_PREFIX = "system/"
    ZMQ_AUTH_PREFIX = "auth/"
    ZMQ_APP_PREFIX = "app/"
    ZMQ_CRISIS_PREFIX = "crisis/"
    ZMQ_EXPRESSION_PREFIX = "expression/"
    ZMQ_LEARNING_PREFIX = "learning/"
    ZMQ_OLLAMA_PREFIX = "ollama/"
    ZMQ_MODELSERVICE_PREFIX = "modelservice/"
    ZMQ_AI_PREFIX = "ai/"
    # Wildcard constants for queries/filters

    """Central registry for all AICO message bus topics"""
    
    # ===== DOMAIN CONSTANTS =====
    EMOTION = "emotion"
    PERSONALITY = "personality"
    AGENCY = "agency"
    CONVERSATION = "conversation"
    MEMORY = "memory"
    USER = "user"
    LLM = "llm"
    UI = "ui"
    SYSTEM = "system"
    LOGS = "logs"
    CRISIS = "crisis"
    EXPRESSION = "expression"
    LEARNING = "learning"
    OLLAMA = "ollama"
    MODELSERVICE = "modelservice"
    AI = "ai"
    
    # ===== COMMON TOPIC PATTERNS =====
    
    # Emotion Domain
    EMOTION_STATE_CURRENT = "emotion/state/current/v1"
    EMOTION_STATE_UPDATE = "emotion/state/update/v1"
    EMOTION_APPRAISAL_EVENT = "emotion/appraisal/event/v1"
    EMOTION_MOOD_UPDATE = "emotion/mood/update/v1"
    
    # Personality Domain
    PERSONALITY_STATE_CURRENT = "personality/state/current/v1"
    PERSONALITY_EXPRESSION_COMMUNICATION = "personality/expression/communication/v1"
    PERSONALITY_EXPRESSION_DECISION = "personality/expression/decision/v1"
    PERSONALITY_EXPRESSION_EMOTIONAL = "personality/expression/emotional/v1"
    PERSONALITY_TRAIT_UPDATE = "personality/trait/update/v1"
    
    # Agency Domain
    AGENCY_GOALS_CURRENT = "agency/goals/current/v1"
    AGENCY_GOALS_UPDATE = "agency/goals/update/v1"
    AGENCY_INITIATIVE_START = "agency/initiative/start/v1"
    AGENCY_DECISION_REQUEST = "agency/decision/request/v1"
    AGENCY_DECISION_RESPONSE = "agency/decision/response/v1"
    AGENCY_PLANNING_UPDATE = "agency/planning/update/v1"
    
    # Conversation Domain
    CONVERSATION_CONTEXT_CURRENT = "conversation/context/current/v1"
    CONVERSATION_CONTEXT_UPDATE = "conversation/context/update/v1"
    CONVERSATION_HISTORY_ADD = "conversation/history/add/v1"
    CONVERSATION_INTENT_DETECTED = "conversation/intent/detected/v1"
    CONVERSATION_USER_INPUT = "conversation/user/input/v1"
    CONVERSATION_AI_RESPONSE = "conversation/ai/response/v1"
    
    # Memory Domain
    MEMORY_STORE_REQUEST = "memory/store/request/v1"
    MEMORY_STORE_RESPONSE = "memory/store/response/v1"
    MEMORY_RETRIEVE_REQUEST = "memory/retrieve/request/v1"
    MEMORY_RETRIEVE_RESPONSE = "memory/retrieve/response/v1"
    MEMORY_CONSOLIDATION_START = "memory/consolidation/start/v1"
    MEMORY_CONSOLIDATION_COMPLETE = "memory/consolidation/complete/v1"
    
    # User Domain
    USER_INTERACTION_HISTORY = "user/interaction/history/v1"
    USER_FEEDBACK_EXPLICIT = "user/feedback/explicit/v1"
    USER_FEEDBACK_IMPLICIT = "user/feedback/implicit/v1"
    USER_STATE_UPDATE = "user/state/update/v1"
    USER_PRESENCE_UPDATE = "user/presence/update/v1"
    
    # LLM Domain
    LLM_CONVERSATION_EVENTS = "llm/conversation/events/v1"
    LLM_PROMPT_CONDITIONING_REQUEST = "llm/prompt/conditioning/request/v1"
    LLM_PROMPT_CONDITIONING_RESPONSE = "llm/prompt/conditioning/response/v1"
    LLM_MODEL_STATUS = "llm/model/status/v1"
    LLM_INFERENCE_REQUEST = "llm/inference/request/v1"
    LLM_INFERENCE_RESPONSE = "llm/inference/response/v1"
    
    # UI Domain
    UI_STATE_UPDATE = "ui/state/update/v1"
    UI_INTERACTION_EVENT = "ui/interaction/event/v1"
    UI_NOTIFICATION_SHOW = "ui/notification/show/v1"
    UI_COMMAND_EXECUTE = "ui/command/execute/v1"
    UI_PREFERENCES_UPDATE = "ui/preferences/update/v1"
    UI_CONNECTION_STATUS = "ui/connection/status/v1"
    
    # System Domain
    SYSTEM_BUS_STARTED = "system/bus/started/v1"
    SYSTEM_BUS_STOPPING = "system/bus/stopping/v1"
    SYSTEM_MODULE_REGISTERED = "system/module/registered/v1"
    SYSTEM_MODULE_UNREGISTERED = "system/module/unregistered/v1"
    SYSTEM_HEALTH_CHECK = "system/health/check/v1"
    SYSTEM_HEALTH_REQUEST = "system/health/request/v1"
    SYSTEM_HEALTH_RESPONSE = "system/health/response/v1"
    SYSTEM_STATUS_UPDATE = "system/status/update/v1"
    
    # Auth Domain
    AUTH_LOGIN_ATTEMPT = "auth/login/attempt/v1"
    AUTH_LOGIN_SUCCESS = "auth/login/success/v1"
    AUTH_LOGIN_FAILURE = "auth/login/failure/v1"
    AUTH_LOGIN_ERROR = "auth/login/error/v1"
    AUTH_LOGOUT_ATTEMPT = "auth/logout/attempt/v1"
    AUTH_LOGOUT_SUCCESS = "auth/logout/success/v1"
    AUTH_LOGOUT_ERROR = "auth/logout/error/v1"
    AUTH_AUTO_LOGIN_ATTEMPT = "auth/auto_login/attempt/v1"
    AUTH_AUTO_LOGIN_SUCCESS = "auth/auto_login/success/v1"
    AUTH_AUTO_LOGIN_FAILURE = "auth/auto_login/failure/v1"
    AUTH_AUTO_LOGIN_CONCURRENT = "auth/auto_login/concurrent/v1"
    AUTH_LOGIN_CONCURRENT = "auth/login/concurrent/v1"
    AUTH_AUTO_LOGIN_NO_CREDENTIALS = "auth/auto_login/no_credentials/v1"
    
    # App Domain
    APP_STARTUP = "app/startup/v1"
    APP_INITIALIZATION = "app/initialization/v1"
    APP_THEME_CHANGE = "app/theme/change/v1"
    
    # Logs Domain
    LOGS_ENTRY = "logs/entry/v1"
    LOGS_BATCH = "logs/batch/v1"
    LOGS_RETENTION_CLEANUP = "logs/retention/cleanup/v1"
    
    # Crisis Domain
    CRISIS_DETECTION_ALERT = "crisis/detection/alert/v1"
    CRISIS_RESPONSE_START = "crisis/response/start/v1"
    CRISIS_RESPONSE_COMPLETE = "crisis/response/complete/v1"
    
    # Expression Domain (cross-modal coordination)
    EXPRESSION_COORDINATION_REQUEST = "expression/coordination/request/v1"
    EXPRESSION_FEEDBACK_UPDATE = "expression/feedback/update/v1"
    
    # Learning Domain
    LEARNING_COORDINATION_START = "learning/coordination/start/v1"
    LEARNING_FEEDBACK_UPDATE = "learning/feedback/update/v1"
    
    # Ollama Domain (CLI management topics)
    OLLAMA_STATUS_REQUEST = "ollama/status/request/v1"
    OLLAMA_STATUS_RESPONSE = "ollama/status/response/v1"
    OLLAMA_INSTALL_REQUEST = "ollama/install/request/v1"
    OLLAMA_INSTALL_RESPONSE = "ollama/install/response/v1"
    OLLAMA_SERVE_REQUEST = "ollama/serve/request/v1"
    OLLAMA_SERVE_RESPONSE = "ollama/serve/response/v1"
    OLLAMA_LOGS_REQUEST = "ollama/logs/request/v1"
    OLLAMA_LOGS_RESPONSE = "ollama/logs/response/v1"
    OLLAMA_MODELS_REQUEST = "ollama/models/request/v1"
    OLLAMA_MODELS_RESPONSE = "ollama/models/response/v1"
    OLLAMA_MODELS_PULL_REQUEST = "ollama/models/pull/request/v1"
    OLLAMA_MODELS_PULL_RESPONSE = "ollama/models/pull/response/v1"
    OLLAMA_MODELS_REMOVE_REQUEST = "ollama/models/remove/request/v1"
    OLLAMA_MODELS_REMOVE_RESPONSE = "ollama/models/remove/response/v1"
    OLLAMA_SHUTDOWN_REQUEST = "ollama/shutdown/request/v1"
    OLLAMA_SHUTDOWN_RESPONSE = "ollama/shutdown/response/v1"
    OLLAMA_MODELS_START_REQUEST = "ollama/models/start/request/v1"
    OLLAMA_MODELS_START_RESPONSE = "ollama/models/start/response/v1"
    OLLAMA_MODELS_STOP_REQUEST = "ollama/models/stop/request/v1"
    OLLAMA_MODELS_STOP_RESPONSE = "ollama/models/stop/response/v1"
    OLLAMA_MODELS_RUNNING_REQUEST = "ollama/models/running/request/v1"
    OLLAMA_MODELS_RUNNING_RESPONSE = "ollama/models/running/response/v1"
    
    # Modelservice Domain (ZMQ topics for REST endpoint replacements)
    MODELSERVICE_HEALTH_REQUEST = "modelservice/health/request/v1"
    MODELSERVICE_HEALTH_RESPONSE = "modelservice/health/response/v1"
    
    # Chat endpoints (conversational with message arrays and roles)
    MODELSERVICE_CHAT_REQUEST = "modelservice/chat/request/v1"
    MODELSERVICE_CHAT_RESPONSE = "modelservice/chat/response/v1"
    MODELSERVICE_CHAT_STREAM = "modelservice/chat/stream/v1"
    
    # Completions endpoints (single prompt analysis tasks)
    MODELSERVICE_COMPLETIONS_REQUEST = "modelservice/completions/request/v1"
    MODELSERVICE_COMPLETIONS_RESPONSE = "modelservice/completions/response/v1"
    MODELSERVICE_COMPLETIONS_STREAM = "modelservice/completions/stream/v1"
    
    MODELSERVICE_MODELS_REQUEST = "modelservice/models/request/v1"
    MODELSERVICE_MODELS_RESPONSE = "modelservice/models/response/v1"
    MODELSERVICE_MODEL_INFO_REQUEST = "modelservice/model/info/request/v1"
    MODELSERVICE_MODEL_INFO_RESPONSE = "modelservice/model/info/response/v1"
    MODELSERVICE_EMBEDDINGS_REQUEST = "modelservice/embeddings/request/v1"
    MODELSERVICE_EMBEDDINGS_RESPONSE = "modelservice/embeddings/response/v1"
    MODELSERVICE_STATUS_REQUEST = "modelservice/status/request/v1"
    MODELSERVICE_STATUS_RESPONSE = "modelservice/status/response/v1"
    
    # AI Processing Domain (Message Bus Coordination)
    # Emotion Analysis
    AI_EMOTION_ANALYSIS_REQUEST = "ai/emotion/analysis/request/v1"
    AI_EMOTION_ANALYSIS_RESPONSE = "ai/emotion/analysis/response/v1"
    AI_EMOTION_FAST_ANALYSIS = "ai/emotion/fast/analyze/v1"
    AI_EMOTION_DEEP_ANALYSIS = "ai/emotion/deep/analyze/v1"
    
    # Personality Expression
    AI_PERSONALITY_EXPRESSION_REQUEST = "ai/personality/expression/request/v1"
    AI_PERSONALITY_EXPRESSION_RESPONSE = "ai/personality/expression/response/v1"
    AI_PERSONALITY_TRAIT_ANALYSIS = "ai/personality/trait/analyze/v1"
    AI_PERSONALITY_BEHAVIOR_ANALYSIS = "ai/personality/behavior/analyze/v1"
    
    # Memory Operations
    AI_MEMORY_RETRIEVAL_REQUEST = "ai/memory/retrieval/request/v1"
    AI_MEMORY_RETRIEVAL_RESPONSE = "ai/memory/retrieval/response/v1"
    AI_MEMORY_STORAGE_REQUEST = "ai/memory/storage/request/v1"
    AI_MEMORY_STORAGE_RESPONSE = "ai/memory/storage/response/v1"
    
    # Embodiment (Avatar & Voice)
    AI_EMBODIMENT_AVATAR_REQUEST = "ai/embodiment/avatar/request/v1"
    AI_EMBODIMENT_AVATAR_RESPONSE = "ai/embodiment/avatar/response/v1"
    AI_EMBODIMENT_VOICE_REQUEST = "ai/embodiment/voice/request/v1"
    AI_EMBODIMENT_VOICE_RESPONSE = "ai/embodiment/voice/response/v1"
    
    # Agency & Proactive Behavior
    AI_AGENCY_GOAL_GENERATION = "ai/agency/goal/generation/v1"
    AI_AGENCY_OPPORTUNITY_DETECTION = "ai/agency/opportunity/detection/v1"
    AI_AGENCY_PROACTIVE_TRIGGER = "ai/agency/proactive/trigger/v1"
    
    # Learning & Analytics (Non-blocking)
    AI_LEARNING_PERSONALITY_UPDATE = "ai/learning/personality/update/v1"
    AI_LEARNING_USER_PATTERN_UPDATE = "ai/learning/user_pattern/update/v1"
    AI_ANALYTICS_INTERACTION_DATA = "ai/analytics/interaction/data/v1"
    
    # Context Management
    AI_CONTEXT_THREAD_UPDATE = "ai/context/thread/update/v1"
    AI_CONTEXT_USER_UPDATE = "ai/context/user/update/v1"
    AI_CONTEXT_SHARED_STATE = "ai/context/shared/state/v1"
    
    # ===== TOPIC BUILDERS =====
    
    @staticmethod
    def emotion_state(action: str, version: str = "v1") -> str:
        """Build emotion state topic: emotion/state/<action>/<version>"""
        return f"emotion/state/{action}/{version}"
    
    @staticmethod
    def personality_expression(type: str, version: str = "v1") -> str:
        """Build personality expression topic: personality/expression/<type>/<version>"""
        return f"personality/expression/{type}/{version}"
    
    @staticmethod
    def agency_goals(action: str, version: str = "v1") -> str:
        """Build agency goals topic: agency/goals/<action>/<version>"""
        return f"agency/goals/{action}/{version}"
    
    @staticmethod
    def conversation_context(action: str, version: str = "v1") -> str:
        """Build conversation context topic: conversation/context/<action>/<version>"""
        return f"conversation/context/{action}/{version}"
    
    @staticmethod
    def memory_operation(operation: str, action: str, version: str = "v1") -> str:
        """Build memory operation topic: memory/<operation>/<action>/<version>"""
        return f"memory/{operation}/{action}/{version}"
    
    @staticmethod
    def user_interaction(type: str, version: str = "v1") -> str:
        """Build user interaction topic: user/interaction/<type>/<version>"""
        return f"user/interaction/{type}/{version}"
    
    @staticmethod
    def llm_operation(operation: str, action: str, version: str = "v1") -> str:
        """Build LLM operation topic: llm/<operation>/<action>/<version>"""
        return f"llm/{operation}/{action}/{version}"
    
    @staticmethod
    def ui_event(type: str, action: str, version: str = "v1") -> str:
        """Build UI event topic: ui/<type>/<action>/<version>"""
        return f"ui/{type}/{action}/{version}"
    
    @staticmethod
    def system_event(type: str, action: str, version: str = "v1") -> str:
        """Build system event topic: system/<type>/<action>/<version>"""
        return f"system/{type}/{action}/{version}"
    
    @staticmethod
    def logs_event(type: str, version: str = "v1") -> str:
        """Build logs event topic: logs/<type>/<version>"""
        return f"logs/{type}/{version}"
    
    @staticmethod
    def ai_processing(component: str, operation: str, action: str, version: str = "v1") -> str:
        """Build AI processing topic: ai/<component>/<operation>/<action>/<version>"""
        return f"ai/{component}/{operation}/{action}/{version}"
    
    @staticmethod
    def ai_coordination(correlation_id: str, component: str, operation: str, version: str = "v1") -> str:
        """Build AI coordination topic with correlation ID: ai/<component>/<operation>/<version>/<correlation_id>"""
        return f"ai/{component}/{operation}/{version}/{correlation_id}"
    
    @staticmethod
    def build_logs_topic(topic: str) -> str:
        """Build full logs topic by prefixing with logs domain"""
        if topic.startswith("logs/"):
            return topic
        return f"logs/{topic}"
    
    # ===== WILDCARD PATTERNS =====
    
    @staticmethod
    def domain_wildcard(domain: str) -> str:
        """Get wildcard pattern for entire domain: <domain>/*"""
        return f"{domain}/*"
    
    @staticmethod
    def object_wildcard(domain: str, object: str) -> str:
        """Get wildcard pattern for object: <domain>/<object>/*"""
        return f"{domain}/{object}/*"
    
    @staticmethod
    def action_wildcard(domain: str, object: str, action: str) -> str:
        """Get wildcard pattern for action: <domain>/<object>/<action>/*"""
        return f"{domain}/{object}/{action}/*"
    
    # Common wildcard patterns
    ALL_EMOTION = "emotion/*"
    ALL_PERSONALITY = "personality/*"
    ALL_AGENCY = "agency/*"
    ALL_CONVERSATION = "conversation/*"
    ALL_MEMORY = "memory/*"
    ALL_USER = "user/*"
    ALL_LLM = "llm/*"
    ALL_UI = "ui/*"
    ALL_SYSTEM = "system/*"
    ALL_LOGS = "logs/*"
    ALL_AUTH = "auth/*"
    ALL_APP = "app/*"
    ALL_AI = "ai/*"
    
    # State-specific wildcards
    ALL_CURRENT_STATE = "*/state/current/*"
    ALL_STATE_UPDATES = "*/state/update/*"
    ALL_EXPRESSIONS = "*/expression/*"
    
    # ===== TOPIC VALIDATION =====
    
    @staticmethod
    def validate_topic(topic: str) -> bool:
        """Validate topic follows AICO naming conventions"""
        if not topic:
            return False
        
        # Check for invalid characters
        if ' ' in topic or '\t' in topic or '\n' in topic:
            return False
        
        # Check length (max 250 chars per industry standards)
        if len(topic) > 250:
            return False
        
        # Check hierarchy depth (max 10 levels recommended)
        parts = topic.split('/')
        if len(parts) > 10:
            return False
        
        # Check for empty parts
        if any(not part for part in parts):
            return False
        
        return True
    
    @staticmethod
    def get_domain(topic: str) -> Optional[str]:
        """Extract domain from topic"""
        parts = topic.split('/')
        return parts[0] if parts else None
    
    @staticmethod
    def get_object(topic: str) -> Optional[str]:
        """Extract object from topic"""
        parts = topic.split('/')
        return parts[1] if len(parts) > 1 else None
    
    @staticmethod
    def get_action(topic: str) -> Optional[str]:
        """Extract action from topic"""
        parts = topic.split('/')
        return parts[2] if len(parts) > 2 else None
    
    @staticmethod
    def get_version(topic: str) -> Optional[str]:
        """Extract version from topic"""
        parts = topic.split('/')
        return parts[3] if len(parts) > 3 else None
    
    @staticmethod
    def get_log_topic(subsystem: str, module: str) -> str:
        """Generate log topic based on subsystem and module"""
        # Clean subsystem and module names
        clean_subsystem = subsystem.lower().replace(' ', '_') if subsystem else 'general'
        clean_module = module.lower().replace(' ', '_') if module else 'default'
        
        # Build hierarchical log topic
        return f"logs/{clean_subsystem}/{clean_module}/v1"


# ===== TOPIC PERMISSIONS =====

class TopicPermissions:
    """Defines topic access permissions for different client types"""
    
    # System components (full access)
    SYSTEM_PERMISSIONS = [
        "*"  # Full access to all topics
    ]
    
    # API Gateway permissions
    API_GATEWAY_PERMISSIONS = [
        "conversation/*",
        "emotion/*",
        "personality/*",
        "system/status/*",
        "admin/*",
        "ui/*"
    ]
    
    # Plugin permissions (restrictive by default)
    PLUGIN_BASE_PERMISSIONS = [
        "system/health/*",  # Can check system health
        "logs/entry/*"      # Can log messages
    ]
    
    # Frontend permissions
    FRONTEND_PERMISSIONS = [
        "ui/*",
        "conversation/*",
        "user/interaction/*",
        "system/status/*"
    ]
    
    # CLI permissions
    CLI_PERMISSIONS = [
        "system/*",
        "logs/*",
        "admin/*",
        "ai/*"
    ]


# ===== REMOVED MIGRATION HELPERS =====
# TopicMigration class removed - no backward compatibility needed.
# All code should use AICOTopics constants directly.


# ===== TOPIC METADATA =====

class TopicMetadata:
    """Metadata and configuration for topics"""
    
    # Topic retention policies (hours)
    RETENTION_POLICIES = {
        AICOTopics.EMOTION: 24,        # 1 day
        AICOTopics.PERSONALITY: 168,   # 1 week
        AICOTopics.AGENCY: 72,         # 3 days
        AICOTopics.CONVERSATION: 720,  # 30 days
        AICOTopics.MEMORY: 8760,       # 1 year
        AICOTopics.USER: 720,          # 30 days
        AICOTopics.LLM: 24,            # 1 day
        AICOTopics.UI: 1,              # 1 hour
        AICOTopics.SYSTEM: 8760,       # 1 year
        AICOTopics.LOGS: 720,          # 30 days
        AICOTopics.AI: 24,              # 1 day
    }
    
    # Topic frequency limits (messages per second)
    FREQUENCY_LIMITS = {
        AICOTopics.EMOTION: 10,        # High frequency for real-time emotion
        AICOTopics.PERSONALITY: 1,     # Low frequency for stable personality
        AICOTopics.AGENCY: 5,          # Medium frequency for goals/planning
        AICOTopics.CONVERSATION: 20,   # High frequency for real-time conversation
        AICOTopics.MEMORY: 2,          # Low frequency for memory operations
        AICOTopics.USER: 10,           # Medium frequency for interactions
        AICOTopics.LLM: 5,             # Medium frequency for inference
        AICOTopics.UI: 30,             # High frequency for UI updates
        AICOTopics.SYSTEM: 1,          # Low frequency for system events
        AICOTopics.LOGS: 100,          # Very high frequency for logging
        AICOTopics.AI: 50,              # High frequency for AI processing
    }
    
    # Critical topics that require persistence
    CRITICAL_TOPICS = {
        AICOTopics.SYSTEM_BUS_STARTED,
        AICOTopics.SYSTEM_BUS_STOPPING,
        AICOTopics.SYSTEM_MODULE_REGISTERED,
        AICOTopics.CRISIS_DETECTION_ALERT,
        AICOTopics.CRISIS_RESPONSE_START,
        AICOTopics.MEMORY_STORE_REQUEST,
        AICOTopics.USER_FEEDBACK_EXPLICIT,
    }
    
    @staticmethod
    def get_retention_hours(topic: str) -> int:
        """Get retention policy for topic (default: 24 hours)"""
        domain = AICOTopics.get_domain(topic)
        return TopicMetadata.RETENTION_POLICIES.get(domain, 24)
    
    @staticmethod
    def get_frequency_limit(topic: str) -> int:
        """Get frequency limit for topic (default: 10 msg/sec)"""
        domain = AICOTopics.get_domain(topic)
        return TopicMetadata.FREQUENCY_LIMITS.get(domain, 10)
    
    @staticmethod
    def is_critical(topic: str) -> bool:
        """Check if topic requires guaranteed persistence"""
        return topic in TopicMetadata.CRITICAL_TOPICS


# ===== CONVENIENCE FUNCTIONS =====

def build_topic(domain: str, object: str, action: str, version: str = "v1", 
                properties: Optional[str] = None) -> str:
    """Build a topic following AICO conventions"""
    topic = f"{domain}/{object}/{action}/{version}"
    if properties:
        topic += f"/{properties}"
    return topic


def parse_topic(topic: str) -> dict:
    """Parse topic into components"""
    parts = topic.split('/')
    result = {
        'domain': parts[0] if len(parts) > 0 else None,
        'object': parts[1] if len(parts) > 1 else None,
        'action': parts[2] if len(parts) > 2 else None,
        'version': parts[3] if len(parts) > 3 else None,
        'properties': '/'.join(parts[4:]) if len(parts) > 4 else None
    }
    return result


def is_wildcard_topic(topic: str) -> bool:
    """Check if topic contains wildcards"""
    return '*' in topic or '+' in topic


# ===== EXPORTS =====

__all__ = [
    'AICOTopics',
    'TopicPermissions', 
    'TopicMetadata',
    'build_topic',
    'parse_topic',
    'is_wildcard_topic'
]
