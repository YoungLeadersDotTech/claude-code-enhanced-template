#!/usr/bin/env python3
"""
Configuration management for Context Exporter
Handles rate limiting, retry settings, and performance profiles
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path

@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status_codes: list = field(default_factory=lambda: [429, 500, 502, 503, 504])
    
@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    min_request_interval: float = 0.1  # minimum seconds between requests
    
@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception_types: list = field(default_factory=lambda: ['RequestException', 'Timeout'])
    
@dataclass
class CacheConfig:
    """Configuration for request caching"""
    enabled: bool = True
    ttl: int = 300  # seconds
    max_size: int = 1000  # maximum number of cached items
    cache_dir: str = ".cache/context_exporter"
    
@dataclass
class TimeoutConfig:
    """Configuration for request timeouts"""
    connect_timeout: float = 10.0  # seconds
    read_timeout: float = 30.0  # seconds
    
@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    confluence_batch_size: int = 100  # reduced from 1000 for reliability
    jira_batch_size: int = 50  # reduced from 100 for reliability
    max_concurrent_requests: int = 5
    
@dataclass
class CheckpointConfig:
    """Configuration for progress checkpointing"""
    enabled: bool = True
    checkpoint_dir: str = ".checkpoints"
    checkpoint_interval: int = 10  # save progress every N items
    
@dataclass
class LoggingConfig:
    """Configuration for structured logging"""
    level: str = "INFO"
    format: str = "json"  # json or text
    log_file: Optional[str] = "context_exporter.log"
    console_output: bool = True
    
class ExporterProfile:
    """Predefined configuration profiles"""
    
    FAST = {
        "name": "fast",
        "description": "Fast export with minimal delays (may hit rate limits)",
        "retry": RetryConfig(max_retries=2, initial_delay=0.5),
        "rate_limit": RateLimitConfig(requests_per_second=20.0, min_request_interval=0.05),
        "timeout": TimeoutConfig(connect_timeout=5.0, read_timeout=20.0),
        "batch": BatchConfig(confluence_batch_size=200, jira_batch_size=100),
    }
    
    BALANCED = {
        "name": "balanced",
        "description": "Balanced profile for most use cases",
        "retry": RetryConfig(),  # default values
        "rate_limit": RateLimitConfig(),  # default values
        "timeout": TimeoutConfig(),  # default values
        "batch": BatchConfig(),  # default values
    }
    
    CONSERVATIVE = {
        "name": "conservative",
        "description": "Conservative profile for maximum reliability",
        "retry": RetryConfig(max_retries=5, initial_delay=2.0, max_delay=120.0),
        "rate_limit": RateLimitConfig(requests_per_second=5.0, min_request_interval=0.2),
        "timeout": TimeoutConfig(connect_timeout=15.0, read_timeout=60.0),
        "batch": BatchConfig(confluence_batch_size=50, jira_batch_size=25, max_concurrent_requests=2),
    }

class ExporterConfig:
    """Main configuration class for Context Exporter"""
    
    def __init__(self, profile: str = "balanced", config_file: Optional[str] = None):
        self.profile_name = profile
        self.config_file = config_file or os.getenv("EXPORTER_CONFIG_FILE", "exporter_config.json")
        
        # Initialize with profile defaults
        self._load_profile(profile)
        
        # Load custom config from file if exists
        if Path(self.config_file).exists():
            self._load_config_file()
            
        # Override with environment variables
        self._load_env_overrides()
        
    def _load_profile(self, profile: str):
        """Load a predefined profile"""
        profiles = {
            "fast": ExporterProfile.FAST,
            "balanced": ExporterProfile.BALANCED,
            "conservative": ExporterProfile.CONSERVATIVE,
        }
        
        if profile not in profiles:
            raise ValueError(f"Unknown profile: {profile}. Available: {list(profiles.keys())}")
            
        profile_config = profiles[profile]
        
        # Set configuration from profile
        self.retry = profile_config.get("retry", RetryConfig())
        self.rate_limit = profile_config.get("rate_limit", RateLimitConfig())
        self.circuit_breaker = CircuitBreakerConfig()
        self.cache = CacheConfig()
        self.timeout = profile_config.get("timeout", TimeoutConfig())
        self.batch = profile_config.get("batch", BatchConfig())
        self.checkpoint = CheckpointConfig()
        self.logging = LoggingConfig()
        
    def _load_config_file(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                
            # Update configurations from file
            if "retry" in config_data:
                self.retry = RetryConfig(**config_data["retry"])
            if "rate_limit" in config_data:
                self.rate_limit = RateLimitConfig(**config_data["rate_limit"])
            if "circuit_breaker" in config_data:
                self.circuit_breaker = CircuitBreakerConfig(**config_data["circuit_breaker"])
            if "cache" in config_data:
                self.cache = CacheConfig(**config_data["cache"])
            if "timeout" in config_data:
                self.timeout = TimeoutConfig(**config_data["timeout"])
            if "batch" in config_data:
                self.batch = BatchConfig(**config_data["batch"])
            if "checkpoint" in config_data:
                self.checkpoint = CheckpointConfig(**config_data["checkpoint"])
            if "logging" in config_data:
                self.logging = LoggingConfig(**config_data["logging"])
                
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
            
    def _load_env_overrides(self):
        """Override configuration with environment variables"""
        # Retry settings
        if env_val := os.getenv("EXPORTER_MAX_RETRIES"):
            self.retry.max_retries = int(env_val)
        if env_val := os.getenv("EXPORTER_RETRY_DELAY"):
            self.retry.initial_delay = float(env_val)
            
        # Rate limit settings
        if env_val := os.getenv("EXPORTER_REQUESTS_PER_SECOND"):
            self.rate_limit.requests_per_second = float(env_val)
        if env_val := os.getenv("EXPORTER_MIN_REQUEST_INTERVAL"):
            self.rate_limit.min_request_interval = float(env_val)
            
        # Timeout settings
        if env_val := os.getenv("EXPORTER_CONNECT_TIMEOUT"):
            self.timeout.connect_timeout = float(env_val)
        if env_val := os.getenv("EXPORTER_READ_TIMEOUT"):
            self.timeout.read_timeout = float(env_val)
            
        # Batch settings
        if env_val := os.getenv("EXPORTER_CONFLUENCE_BATCH_SIZE"):
            self.batch.confluence_batch_size = int(env_val)
        if env_val := os.getenv("EXPORTER_JIRA_BATCH_SIZE"):
            self.batch.jira_batch_size = int(env_val)
            
        # Cache settings
        if env_val := os.getenv("EXPORTER_CACHE_ENABLED"):
            self.cache.enabled = env_val.lower() in ["true", "1", "yes"]
        if env_val := os.getenv("EXPORTER_CACHE_TTL"):
            self.cache.ttl = int(env_val)
            
        # Checkpoint settings
        if env_val := os.getenv("EXPORTER_CHECKPOINT_ENABLED"):
            self.checkpoint.enabled = env_val.lower() in ["true", "1", "yes"]
            
        # Logging settings
        if env_val := os.getenv("EXPORTER_LOG_LEVEL"):
            self.logging.level = env_val.upper()
        if env_val := os.getenv("EXPORTER_LOG_FORMAT"):
            self.logging.format = env_val.lower()
            
    def save_to_file(self, filepath: Optional[str] = None):
        """Save current configuration to a JSON file"""
        filepath = filepath or self.config_file
        
        config_dict = {
            "profile": self.profile_name,
            "retry": {
                "max_retries": self.retry.max_retries,
                "initial_delay": self.retry.initial_delay,
                "max_delay": self.retry.max_delay,
                "exponential_base": self.retry.exponential_base,
                "jitter": self.retry.jitter,
                "retry_on_status_codes": self.retry.retry_on_status_codes,
            },
            "rate_limit": {
                "requests_per_second": self.rate_limit.requests_per_second,
                "burst_size": self.rate_limit.burst_size,
                "min_request_interval": self.rate_limit.min_request_interval,
            },
            "circuit_breaker": {
                "failure_threshold": self.circuit_breaker.failure_threshold,
                "recovery_timeout": self.circuit_breaker.recovery_timeout,
                "expected_exception_types": self.circuit_breaker.expected_exception_types,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "ttl": self.cache.ttl,
                "max_size": self.cache.max_size,
                "cache_dir": self.cache.cache_dir,
            },
            "timeout": {
                "connect_timeout": self.timeout.connect_timeout,
                "read_timeout": self.timeout.read_timeout,
            },
            "batch": {
                "confluence_batch_size": self.batch.confluence_batch_size,
                "jira_batch_size": self.batch.jira_batch_size,
                "max_concurrent_requests": self.batch.max_concurrent_requests,
            },
            "checkpoint": {
                "enabled": self.checkpoint.enabled,
                "checkpoint_dir": self.checkpoint.checkpoint_dir,
                "checkpoint_interval": self.checkpoint.checkpoint_interval,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "log_file": self.logging.log_file,
                "console_output": self.logging.console_output,
            },
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
            
    def get_profile_info(self) -> Dict[str, Any]:
        """Get information about the current profile and settings"""
        return {
            "profile": self.profile_name,
            "requests_per_second": self.rate_limit.requests_per_second,
            "max_retries": self.retry.max_retries,
            "batch_sizes": {
                "confluence": self.batch.confluence_batch_size,
                "jira": self.batch.jira_batch_size,
            },
            "timeouts": {
                "connect": self.timeout.connect_timeout,
                "read": self.timeout.read_timeout,
            },
            "cache_enabled": self.cache.enabled,
            "checkpoint_enabled": self.checkpoint.enabled,
        }