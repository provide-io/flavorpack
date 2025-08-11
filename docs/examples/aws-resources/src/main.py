#!/usr/bin/env python3
"""
AWS Resources Terraform Provider - PSPF Example
===============================================

Production-ready terraform provider demonstrating PSPF packaging
with AWS SDK integration and comprehensive resource management.
"""
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('awsdemo-provider')

# Import provider components
try:
    from provider import AWSResourcesProvider
    from config import ProviderConfig
except ImportError as e:
    logger.error(f"Failed to import provider modules: {e}")
    logger.error("Ensure all dependencies are installed and modules are available")
    sys.exit(1)

def parse_arguments() -> Dict[str, Any]:
    """Parse command line arguments."""
    args = {
        'command': 'serve',  # default command
        'verbose': False,
        'config_file': None,
        'aws_region': None,
        'aws_profile': None
    }
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i].lower()
        
        if arg in ['--help', '-h', 'help']:
            args['command'] = 'help'
        elif arg in ['--version', '-v', 'version']:
            args['command'] = 'version'
        elif arg == '--schema':
            args['command'] = 'schema'
        elif arg == '--test':
            args['command'] = 'test'
        elif arg == '--validate':
            args['command'] = 'validate'
        elif arg in ['--verbose', '-vv']:
            args['verbose'] = True
        elif arg == '--config' and i + 1 < len(sys.argv):
            args['config_file'] = sys.argv[i + 1]
            i += 1
        elif arg == '--region' and i + 1 < len(sys.argv):
            args['aws_region'] = sys.argv[i + 1]
            i += 1
        elif arg == '--profile' and i + 1 < len(sys.argv):
            args['aws_profile'] = sys.argv[i + 1]
            i += 1
        else:
            logger.warning(f"Unknown argument: {sys.argv[i]}")
        
        i += 1
    
    return args

def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Update root logger
    logging.getLogger().setLevel(level)
    
    # Configure specific loggers
    logging.getLogger('awsdemo-provider').setLevel(level)
    logging.getLogger('botocore').setLevel(logging.WARNING)  # Reduce AWS SDK noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)   # Reduce HTTP noise
    
    if verbose:
        logger.debug("Verbose logging enabled")

def load_config(args: Dict[str, Any]) -> ProviderConfig:
    """Load provider configuration from various sources."""
    try:
        # Start with default configuration
        config_kwargs = {}
        
        # Override with command line arguments
        if args.get('aws_region'):
            config_kwargs['region'] = args['aws_region']
        if args.get('aws_profile'):
            config_kwargs['profile'] = args['aws_profile']
        
        # Load from config file if specified
        if args.get('config_file'):
            config_file = Path(args['config_file'])
            if config_file.exists():
                import json
                with open(config_file) as f:
                    file_config = json.load(f)
                config_kwargs.update(file_config)
            else:
                logger.warning(f"Config file not found: {config_file}")
        
        # Create configuration
        config = ProviderConfig(**config_kwargs)
        logger.info(f"Loaded configuration: region={config.region}, profile={config.profile}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

async def run_provider_command(command: str, provider: AWSResourcesProvider) -> int:
    """Execute the specified provider command."""
    try:
        if command == 'help':
            provider.show_help()
            return 0
        elif command == 'version':
            provider.show_version()
            return 0
        elif command == 'schema':
            schema = await provider.get_schema()
            print(json.dumps(schema, indent=2))
            return 0
        elif command == 'test':
            return await provider.self_test()
        elif command == 'validate':
            return await provider.validate_config()
        elif command == 'serve':
            return await provider.serve()
        else:
            logger.error(f"Unknown command: {command}")
            provider.show_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("Provider interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Command '{command}' failed: {e}", exc_info=True)
        return 1

async def main() -> int:
    """Main entry point for the AWS resources provider."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging
        setup_logging(args['verbose'])
        
        logger.info("Starting AWS Resources Provider (PSPF)")
        logger.debug(f"Arguments: {args}")
        
        # Load configuration
        config = load_config(args)
        
        # Create provider instance
        provider = AWSResourcesProvider(config)
        
        # Initialize provider (validate AWS credentials, etc.)
        await provider.initialize()
        
        # Execute command
        return await run_provider_command(args['command'], provider)
        
    except Exception as e:
        logger.error(f"Provider startup failed: {e}", exc_info=True)
        return 1

def sync_main() -> int:
    """Synchronous wrapper for main function."""
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            logger.warning("Already in event loop, running synchronously")
            # If we're already in a loop, we need to handle this differently
            return asyncio.run_coroutine_threadsafe(main(), loop).result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(main())
            
    except KeyboardInterrupt:
        logger.info("Provider interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Provider failed: {e}")
        return 1

if __name__ == "__main__":
    # Entry point
    exit_code = sync_main()
    sys.exit(exit_code)

# 📦🍜📄🪄
