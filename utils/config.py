import os
import tomli
from pathlib import Path
from typing import Any, Dict, Optional

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from TOML file and environment variables."""
        config_path = Path(__file__).parent.parent / "config.toml"
        
        try:
            with open(config_path, "rb") as f:
                self._config = tomli.load(f)
            
            # Load sensitive data from environment variables
            # Database configuration
            self._config["database"]["supabase"]["url"] = os.getenv("SUPABASE_URL", "")
            self._config["database"]["supabase"]["key"] = os.getenv("SUPABASE_KEY", "")
            self._config["database"]["supabase"]["anon_key"] = os.getenv("SUPABASE_ANON_KEY", "")
            
            self._config["database"]["postgres"]["user"] = os.getenv("DB_USER", "")
            self._config["database"]["postgres"]["password"] = os.getenv("DB_PASSWORD", "")
            self._config["database"]["postgres"]["host"] = os.getenv("DB_HOST", "")
            self._config["database"]["postgres"]["port"] = int(os.getenv("DB_PORT", "6543"))
            self._config["database"]["postgres"]["name"] = os.getenv("DB_NAME", "postgres")
            
            # OpenAI configuration
            self._config["openai"]["api_key"] = os.getenv("OPENAI_API_KEY", "")
            self._config["openai"]["assistant_id"] = os.getenv("ASSISTANT_ID", "")
            self._config["openai"]["vector_store"] = os.getenv("VECTOR_STORE", "")
            
            # Authentication configuration
            self._config["auth"]["username"] = os.getenv("APP_USERNAME", "demo")
            self._config["auth"]["password_hash"] = os.getenv("APP_PASSWORD_HASH", "")
            
            # Set environment-specific configurations
            env = os.getenv("APP_ENV", "production")
            self._config["application"]["environment"] = env
            
            if env == "development":
                self._config["application"]["debug"] = True
                self._config["logging"]["level"] = "DEBUG"
                
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {str(e)}")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        try:
            return self._config[section][key]
        except KeyError:
            return default

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Get a nested configuration value."""
        current = self._config
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current

    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Get an entire configuration section."""
        return self._config.get(section)

    @property
    def database_path(self) -> str:
        """Get the SQLite database path."""
        return self.get("database", "sqlite_path")

    @property
    def supabase_url(self) -> str:
        """Get the Supabase URL."""
        return self.get_nested("database", "supabase", "url")

    @property
    def supabase_key(self) -> str:
        """Get the Supabase key."""
        return self.get_nested("database", "supabase", "key")

    @property
    def openai_api_key(self) -> str:
        """Get the OpenAI API key."""
        return self.get("openai", "api_key")

    @property
    def openai_model(self) -> str:
        """Get the OpenAI model name."""
        return self.get("openai", "model")

    @property
    def assistant_id(self) -> str:
        """Get the OpenAI Assistant ID."""
        return self.get("openai", "assistant_id")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.get("application", "environment") == "production"

    @property
    def debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get("application", "debug", False)

    @property
    def postgres_dsn(self) -> str:
        """Get the PostgreSQL connection string."""
        pg = self.get_section("database")["postgres"]
        return f"postgresql://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['name']}"

# Create a singleton instance
config = Config()
