# Context Exporter V2 - Production-Ready

A production-ready version of the Context Exporter with enhanced reliability, performance optimization, and robust error handling.

## New Features in V2

### 1. **API Resilience**
- **Configurable Rate Limiting**: Prevents hitting API rate limits with token bucket algorithm
- **Exponential Backoff with Jitter**: Smart retry logic for transient failures
- **Circuit Breaker Pattern**: Prevents cascading failures when APIs are down
- **Request Timeout Configuration**: Customizable timeouts for different scenarios

### 2. **Performance Optimizations**
- **Request Caching**: Avoid duplicate API calls with TTL-based caching
- **Batch Size Optimization**: Configurable batch sizes for reliability
- **Progress Checkpointing**: Resume interrupted exports from where they left off
- **Performance Profiles**: Fast, Balanced, and Conservative modes

### 3. **Enhanced Error Handling**
- **Structured Logging**: JSON-formatted logs with detailed context
- **Comprehensive Error Reporting**: Track all API failures with context
- **Graceful Degradation**: Continue export even when some resources fail
- **API Response Validation**: Ensure data integrity

### 4. **Configuration Management**
- **JSON Configuration Files**: External configuration support
- **Environment Variable Overrides**: Easy deployment configuration
- **Multiple Profiles**: Pre-configured settings for different use cases

## Installation

```bash
# Install dependencies
pip3 install -r requirements.txt
```

## Configuration

### Environment Variables (.env file)
```bash
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
JIRA_URL=https://your-company.atlassian.net
ATLASSIAN_USERNAME=your-email@company.com
ATLASSIAN_API_TOKEN=your-api-token-here
```

### Performance Profiles

#### Fast Profile
- High request rate (20 req/s)
- Minimal retry delays
- Larger batch sizes
- Best for: Small exports, testing

#### Balanced Profile (Default)
- Moderate request rate (10 req/s)
- Standard retry delays
- Medium batch sizes
- Best for: Most use cases

#### Conservative Profile
- Low request rate (5 req/s)
- Extended retry delays
- Small batch sizes
- Best for: Large exports, unreliable networks

## Usage Examples

### Basic Export
```bash
# Export with default balanced profile
python3 context_exporter_v2.py --label "MyLabel"

# Export only Confluence content
python3 context_exporter_v2.py --label "MyLabel" --include-confluence

# Export only Jira content
python3 context_exporter_v2.py --label "MyLabel" --include-jira
```

### Performance Profiles
```bash
# Fast export (may hit rate limits)
python3 context_exporter_v2.py --label "MyLabel" --profile fast

# Conservative export for maximum reliability
python3 context_exporter_v2.py --label "MyLabel" --profile conservative
```

### Advanced Features
```bash
# Validate connectivity without exporting
python3 context_exporter_v2.py --label "MyLabel" --validate-only

# Dry run to see what would be exported
python3 context_exporter_v2.py --label "MyLabel" --dry-run

# List available checkpoints
python3 context_exporter_v2.py --list-checkpoints

# Resume from checkpoint
python3 context_exporter_v2.py --resume checkpoint_abc123.json

# Use custom configuration file
python3 context_exporter_v2.py --label "MyLabel" --config-file my_config.json

# Debug logging
python3 context_exporter_v2.py --label "MyLabel" --log-level DEBUG
```

## Configuration Options

### Custom Configuration File
Create a `exporter_config.json` file:

```json
{
  "profile": "balanced",
  "retry": {
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2.0,
    "jitter": true,
    "retry_on_status_codes": [429, 500, 502, 503, 504]
  },
  "rate_limit": {
    "requests_per_second": 10.0,
    "burst_size": 20,
    "min_request_interval": 0.1
  },
  "cache": {
    "enabled": true,
    "ttl": 300,
    "max_size": 1000
  }
}
```

### Environment Variable Overrides
```bash
# Override specific settings
export EXPORTER_MAX_RETRIES=5
export EXPORTER_REQUESTS_PER_SECOND=5.0
export EXPORTER_CACHE_ENABLED=false
export EXPORTER_LOG_LEVEL=DEBUG
```

## Monitoring and Troubleshooting

### Log Files
- **Location**: `context_exporter.log`
- **Format**: JSON-structured logs
- **Levels**: DEBUG, INFO, WARNING, ERROR

### Checkpoint Files
- **Location**: `.checkpoints/` directory
- **Format**: JSON with export state
- **Cleanup**: Old checkpoints auto-cleaned after 7 days

### Cache Directory
- **Location**: `.cache/context_exporter/`
- **Contents**: Cached API responses
- **TTL**: 5 minutes by default

### Performance Metrics
The exporter logs detailed performance metrics:
- API call counts and durations
- Export progress percentages
- Rate limiter statistics
- Circuit breaker states

## Troubleshooting

### Common Issues

#### Rate Limit Errors
```bash
# Use conservative profile
python3 context_exporter_v2.py --label "MyLabel" --profile conservative

# Or reduce request rate
export EXPORTER_REQUESTS_PER_SECOND=2.0
```

#### Connection Timeouts
```bash
# Increase timeouts
export EXPORTER_CONNECT_TIMEOUT=30
export EXPORTER_READ_TIMEOUT=60
```

#### Memory Issues with Large Exports
```bash
# Reduce batch sizes
export EXPORTER_CONFLUENCE_BATCH_SIZE=50
export EXPORTER_JIRA_BATCH_SIZE=25
```

### Debug Mode
```bash
# Enable debug logging
python3 context_exporter_v2.py --label "MyLabel" --log-level DEBUG

# Check API connectivity
python3 context_exporter_v2.py --label "MyLabel" --validate-only
```

## Testing

### Run Unit Tests
```bash
# Run all tests
python3 -m unittest test_api_client.py

# Run specific test class
python3 -m unittest test_api_client.TestResilientAPIClient

# Run with verbose output
python3 -m unittest -v test_api_client.py
```

### Integration Testing
```bash
# Test with small batch
python3 context_exporter_v2.py --label "TestLabel" --dry-run

# Validate connectivity
python3 context_exporter_v2.py --label "TestLabel" --validate-only
```

## Architecture

### Component Overview
1. **ExporterConfig**: Centralized configuration management
2. **ResilientAPIClient**: HTTP client with retry logic and rate limiting
3. **StructuredLogger**: JSON-formatted logging with context
4. **CheckpointManager**: Progress tracking and resume capability
5. **ContextExporterV2**: Main orchestrator

### Design Patterns
- **Circuit Breaker**: Prevents cascading failures
- **Token Bucket**: Rate limiting algorithm
- **Exponential Backoff**: Retry delay calculation
- **Factory Pattern**: Logger creation
- **Strategy Pattern**: Performance profiles

## Migration from V1

### Key Differences
1. **Command**: Use `context_exporter_v2.py` instead of `context_exporter.py`
2. **Profiles**: Add `--profile` flag for performance tuning
3. **Checkpoints**: Automatic progress saving
4. **Logging**: Structured JSON logs instead of plain text

### Backward Compatibility
- Same label-based export functionality
- Compatible `.env` file format
- Same PDF output format
- Same directory structure

## Contributing

### Adding New Features
1. Update configuration schema in `exporter_config.py`
2. Implement feature with proper error handling
3. Add structured logging
4. Write unit tests
5. Update documentation

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Handle exceptions gracefully

## License

Same as original Context Exporter