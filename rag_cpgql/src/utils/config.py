"""Configuration loader for RAG-CPGQL system."""
import yaml
import os
from pathlib import Path

class Config:
    """Configuration manager."""

    def __init__(self, config_path="config.yaml"):
        """Load configuration from YAML file."""
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        """Load YAML configuration."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, *keys, default=None):
        """Get nested configuration value."""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def qa_pairs_source(self):
        return self.get('data', 'qa_pairs_source')

    @property
    def cpgql_examples(self):
        return self.get('data', 'cpgql_examples')

    @property
    def train_split(self):
        return self.get('data', 'train_split')

    @property
    def test_split(self):
        return self.get('data', 'test_split')

    @property
    def joern_path(self):
        return self.get('joern', 'installation_path')

    @property
    def joern_cli_path(self):
        return self.get('joern', 'cli_path')

    @property
    def cpg_path(self):
        return self.get('joern', 'cpg_path')

    @property
    def joern_port(self):
        return self.get('joern', 'server_port', default=8080)

    @property
    def query_timeout(self):
        return self.get('joern', 'query_timeout', default=30)

    @property
    def finetuned_model_path(self):
        return self.get('models', 'finetuned', 'path')

    @property
    def base_model_path(self):
        return self.get('models', 'base', 'path')

    @property
    def embedding_model(self):
        return self.get('retrieval', 'embedding_model', default='all-MiniLM-L6-v2')

    @property
    def top_k_qa(self):
        return self.get('retrieval', 'top_k_qa', default=3)

    @property
    def top_k_cpgql(self):
        return self.get('retrieval', 'top_k_cpgql', default=5)

# Global config instance
config = None

def load_config(config_path="config.yaml"):
    """Load global configuration."""
    global config
    config = Config(config_path)
    return config

def get_config():
    """Get global configuration instance."""
    global config
    if config is None:
        config = load_config()
    return config
