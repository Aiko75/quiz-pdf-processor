"""
Configuration manager for Quiz Processor app.
Stores and loads user settings persistently.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Manage application settings."""
    
    DEFAULT_SETTINGS = {
        "generate_answer_file": True,
    }
    
    def __init__(self, config_file: Optional[Path] = None):
        if config_file is None:
            config_file = Path(__file__).resolve().parent / "quiz_settings.json"
        
        self.config_file = config_file
        self.settings: Dict[str, Any] = self.DEFAULT_SETTINGS.copy()
        self.load()
    
    def load(self) -> None:
        """Load settings from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception:
                # If load fails, keep defaults
                pass
    
    def save(self) -> None:
        """Save current settings to config file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silently fail if save doesn't work
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value and save."""
        self.settings[key] = value
        self.save()


# Global config instance
config = Config()
