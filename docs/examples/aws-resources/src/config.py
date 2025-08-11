"""Configuration management for AWS Resources Provider."""
import os
import boto3
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger('awsdemo-provider.config')

@dataclass
class ProviderConfig:
    """AWS Resources Provider configuration with validation and credential management."""
    
    # AWS Configuration
    region: str = "us-west-2"
    profile: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    session_token: Optional[str] = None
    
    # Provider Configuration
    assume_role_arn: Optional[str] = None
    assume_role_session_name: str = "pspf-aws-provider"
    assume_role_external_id: Optional[str] = None
    
    # Connection Configuration
    endpoint_url: Optional[str] = None  # For LocalStack/testing
    max_retries: int = 3
    retry_mode: str = "adaptive"
    
    # Behavioral Configuration
    skip_credentials_validation: bool = False
    skip_region_validation: bool = False
    
    # Internal fields
    _session: Optional[boto3.Session] = field(default=None, init=False, repr=False)
    _credentials_validated: bool = field(default=False, init=False, repr=False)
    
    def __post_init__(self):
        """Validate and initialize configuration after creation."""
        self._load_from_environment()
        self._validate_configuration()
        
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # AWS standard environment variables
        self.access_key = self.access_key or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = self.secret_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.session_token = self.session_token or os.getenv('AWS_SESSION_TOKEN')
        self.region = self.region or os.getenv('AWS_DEFAULT_REGION', self.region)
        self.profile = self.profile or os.getenv('AWS_PROFILE')
        
        # Provider-specific environment variables
        self.endpoint_url = self.endpoint_url or os.getenv('AWS_ENDPOINT_URL')
        
        if os.getenv('AWS_SKIP_CREDENTIALS_VALIDATION', '').lower() in ('true', '1'):
            self.skip_credentials_validation = True
            
        if os.getenv('AWS_SKIP_REGION_VALIDATION', '').lower() in ('true', '1'):
            self.skip_region_validation = True
            
        # Retry configuration
        max_retries_env = os.getenv('AWS_MAX_RETRIES')
        if max_retries_env and max_retries_env.isdigit():
            self.max_retries = int(max_retries_env)
            
        retry_mode_env = os.getenv('AWS_RETRY_MODE')
        if retry_mode_env in ('legacy', 'standard', 'adaptive'):
            self.retry_mode = retry_mode_env
            
        logger.debug(f"Loaded configuration from environment: region={self.region}, "
                    f"profile={self.profile}, endpoint_url={self.endpoint_url}")
    
    def _validate_configuration(self):
        """Validate configuration values."""
        if not self.region and not self.skip_region_validation:
            raise ValueError("AWS region is required. Set region parameter or AWS_DEFAULT_REGION environment variable.")
        
        if self.region and not self.skip_region_validation:
            # Validate region format
            valid_regions = self._get_valid_regions()
            if valid_regions and self.region not in valid_regions:
                logger.warning(f"Region '{self.region}' may not be valid. Valid regions: {valid_regions[:10]}...")
        
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        
        if self.retry_mode not in ('legacy', 'standard', 'adaptive'):
            raise ValueError("retry_mode must be 'legacy', 'standard', or 'adaptive'")
            
        logger.info(f"Configuration validation completed: region={self.region}")
    
    def _get_valid_regions(self) -> list:
        """Get list of valid AWS regions (cached)."""
        try:
            # This is expensive, so only do it if needed
            session = boto3.Session()
            ec2 = session.client('ec2', region_name='us-east-1')  # Global endpoint
            regions = ec2.describe_regions()
            return [r['RegionName'] for r in regions['Regions']]
        except Exception as e:
            logger.debug(f"Could not retrieve valid regions: {e}")
            return []
    
    async def get_session(self) -> boto3.Session:
        """Get or create AWS session with proper authentication."""
        if self._session is not None:
            return self._session
        
        try:
            # Create session based on available credentials
            session_kwargs = {}
            
            if self.profile:
                session_kwargs['profile_name'] = self.profile
                logger.debug(f"Using AWS profile: {self.profile}")
            else:
                # Use explicit credentials if provided
                if self.access_key and self.secret_key:
                    session_kwargs.update({
                        'aws_access_key_id': self.access_key,
                        'aws_secret_access_key': self.secret_key
                    })
                    if self.session_token:
                        session_kwargs['aws_session_token'] = self.session_token
                    logger.debug("Using explicit AWS credentials")
                else:
                    logger.debug("Using default AWS credentials (environment/instance profile)")
            
            # Create session
            self._session = boto3.Session(**session_kwargs)
            
            # Validate credentials if not skipped
            if not self.skip_credentials_validation:
                await self._validate_credentials()
            
            logger.info("AWS session created successfully")
            return self._session
            
        except Exception as e:
            logger.error(f"Failed to create AWS session: {e}")
            raise
    
    async def _validate_credentials(self):
        """Validate AWS credentials by making a test call."""
        if self._credentials_validated:
            return
            
        try:
            # Create STS client to validate credentials
            sts_client = await self.get_client('sts')
            
            # Make test call
            identity = sts_client.get_caller_identity()
            
            logger.info(f"AWS credentials validated. Account: {identity.get('Account')}, "
                       f"User: {identity.get('Arn')}")
            
            self._credentials_validated = True
            
        except Exception as e:
            logger.error(f"AWS credentials validation failed: {e}")
            if not self.skip_credentials_validation:
                raise
    
    async def get_client(self, service_name: str, **kwargs):
        """Get AWS service client with provider configuration."""
        session = await self.get_session()
        
        client_kwargs = {
            'region_name': self.region,
            'config': boto3.session.Config(
                retries={
                    'max_attempts': self.max_retries,
                    'mode': self.retry_mode
                }
            )
        }
        
        # Add endpoint URL for testing (LocalStack, etc.)
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url
            
        # Allow override of client parameters
        client_kwargs.update(kwargs)
        
        try:
            client = session.client(service_name, **client_kwargs)
            logger.debug(f"Created {service_name} client for region {self.region}")
            return client
        except Exception as e:
            logger.error(f"Failed to create {service_name} client: {e}")
            raise
    
    def get_resource_config(self) -> Dict[str, Any]:
        """Get configuration dictionary for resource implementations."""
        return {
            'region': self.region,
            'endpoint_url': self.endpoint_url,
            'max_retries': self.max_retries,
            'retry_mode': self.retry_mode,
            'skip_validation': self.skip_credentials_validation
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            'region': self.region,
            'profile': self.profile,
            'endpoint_url': self.endpoint_url,
            'max_retries': self.max_retries,
            'retry_mode': self.retry_mode,
            'skip_credentials_validation': self.skip_credentials_validation,
            'skip_region_validation': self.skip_region_validation,
            'assume_role_arn': self.assume_role_arn,
            'assume_role_session_name': self.assume_role_session_name
            # Note: Credentials are not included for security
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProviderConfig':
        """Create configuration from dictionary."""
        return cls(**data)
    
    def __repr__(self) -> str:
        """String representation without sensitive data."""
        return (f"ProviderConfig(region='{self.region}', profile='{self.profile}', "
                f"endpoint_url='{self.endpoint_url}', max_retries={self.max_retries})")

# 📦🍜📄🪄
