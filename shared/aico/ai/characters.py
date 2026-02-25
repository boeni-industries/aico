"""Character management for AICO.

Loads character definitions from configuration and builds system messages.
"""

from typing import Dict, Any, Optional


class CharacterManager:
    """Manages character definitions and system message construction."""
    
    def __init__(self, config_manager):
        """Initialize character manager.
        
        Args:
            config_manager: ConfigurationManager instance
        """
        self.config_manager = config_manager
    
    def get_character(self, name: str) -> Dict[str, Any]:
        """Load character configuration.
        
        Args:
            name: Character name (e.g., 'eve')
            
        Returns:
            Character configuration dict
            
        Raises:
            ValueError: If character not found
        """
        character = self.config_manager.get(f"characters.{name}", None)
        if not character:
            raise ValueError(f"Character '{name}' not found in configuration")
        return character
    
    def list_characters(self) -> list[str]:
        """List available character names.
        
        Returns:
            List of character names
        """
        characters = self.config_manager.get("characters", {})
        return list(characters.keys())
    
    def build_system_message(
        self,
        character_name: str,
        memory_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Build system message with character personality and optional memory context.
        
        Args:
            character_name: Name of character to use
            memory_context: Optional dict with 'facts' or other context
            
        Returns:
            System message dict with 'role' and 'content'
        """
        character = self.get_character(character_name)
        
        # Start with character's system prompt
        system_content = character["system_prompt"]

        system_content += "\n\nWhen you reason internally, wrap that private reasoning in <think> and </think> tags. Provide the user-facing answer outside of these tags."

        system_content += "\n\nAlways respond in the same language as the user's most recent message."
        
        # Add memory context if provided
        if memory_context and memory_context.get("facts"):
            system_content += "\n\nContext from previous conversations:\n"
            for fact in memory_context["facts"]:
                system_content += f"- {fact}\n"
        
        return {
            "role": "system",
            "content": system_content
        }
    
    def get_parameters(self, character_name: str) -> Dict[str, Any]:
        """Get model parameters for character.
        
        Args:
            character_name: Name of character
            
        Returns:
            Parameters dict
        """
        character = self.get_character(character_name)
        return character.get("parameters", {})
    
    def get_base_model(self, character_name: str) -> str:
        """Get base model identifier for character.
        
        Args:
            character_name: Name of character
            
        Returns:
            Base model identifier
        """
        character = self.get_character(character_name)
        return character.get("base_model", "")
