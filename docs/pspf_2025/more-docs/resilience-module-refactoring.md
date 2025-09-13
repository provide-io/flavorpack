# Resilience Module Refactoring

## Overview
Refactor retry, circuit breaker, and fallback patterns from the `errors` module into a dedicated `resilience` module. This aligns with industry standards (Polly, Hystrix, resilience4j) where these patterns are treated as resilience strategies rather than error handling.

## Motivation
- **Semantic Correctness**: Retry, circuit breaker, and fallback are resilience patterns, not error types
- **Industry Alignment**: Matches patterns from Polly (.NET), Hystrix (Java), resilience4j
- **Clean Separation**: Errors define what went wrong; resilience defines how to recover
- **Code Reuse**: Eliminate duplication between `RetryPolicy` and `RetryMiddleware`

## Implementation Checklist

### Phase 1: Test Creation (TDD) ✅ **COMPLETED**
- [x] Create `tests/resilience/` directory
- [x] Create `tests/resilience/test_retry_executor.py`
  - [x] Test sync execution with various retry scenarios
  - [x] Test async execution with various retry scenarios
  - [x] Test integration with RetryPolicy
  - [x] Test all backoff strategies (fixed, linear, exponential, fibonacci)
  - [x] Test jitter application
  - [x] Test retry callbacks
  - [x] Test exception filtering
  - [x] Test logging behavior
- [x] Create `tests/resilience/test_retry_policy.py`
  - [x] Test policy configuration
  - [x] Test delay calculation for all strategies
  - [x] Test should_retry logic
  - [x] Test max_attempts enforcement
  - [x] Test retryable_errors filtering
- [x] Create `tests/resilience/test_retry_decorator.py`
  - [x] Test @retry decorator with sync functions
  - [x] Test @retry decorator with async functions
  - [x] Test decorator with RetryPolicy
  - [x] Test decorator with inline parameters
- [x] Create `tests/resilience/test_circuit_breaker.py`
  - [x] Test circuit breaker state transitions (closed -> open -> half-open)
  - [x] Test failure threshold triggering
  - [x] Test timeout behavior
  - [x] Test success reset
- [x] Create `tests/resilience/test_fallback.py`
  - [x] Test fallback chain execution
  - [x] Test fallback with retry
  - [x] Test fallback with circuit breaker
- [x] Create `tests/resilience/test_integration.py`
  - [x] Test retry + circuit breaker combination
  - [x] Test retry + fallback combination
  - [x] Test middleware integration

### Phase 2: Module Implementation ✅ **COMPLETED**
- [x] Create `src/provide/foundation/resilience/__init__.py`
- [x] Create `src/provide/foundation/resilience/retry.py`
  - [x] Implement `RetryPolicy` class (moved from errors/types.py)
  - [x] Implement `RetryExecutor` class
  - [x] Implement `BackoffStrategy` enum
- [x] Create `src/provide/foundation/resilience/decorators.py`
  - [x] Implement `@retry` decorator (replaces @retry_on_error)
  - [x] Implement `@circuit_breaker` decorator
  - [x] Implement `@fallback` decorator
- [x] Create `src/provide/foundation/resilience/circuit.py`
  - [x] Implement `CircuitBreaker` class
  - [x] Implement `CircuitState` enum
  - [x] Implement state transition logic
- [x] Create `src/provide/foundation/resilience/fallback.py`
  - [x] Implement `FallbackChain` class
  - [x] Implement fallback strategies

### Phase 3: Migration ✅ **COMPLETED**
- [x] Update `src/provide/foundation/transport/middleware.py`
  - [x] Import RetryPolicy from resilience module
  - [x] Update RetryMiddleware to use RetryExecutor
  - [x] Remove duplicate retry logic
- [x] Update `src/provide/foundation/errors/types.py`
  - [x] Remove RetryPolicy (moved to resilience)
  - [x] Add deprecation warning and re-export for compatibility
- [x] Update `src/provide/foundation/errors/decorators.py`
  - [x] Remove @retry_on_error implementation
  - [x] Add deprecation warning and re-export for compatibility
- [x] Move circuit breaker from errors to resilience
  - [x] Move @circuit_breaker decorator
  - [x] Update imports

### Phase 4: Update Dependencies ✅ **COMPLETED**
- [x] Find all imports of `RetryPolicy`
- [x] Find all imports of `@retry_on_error`
- [x] Find all imports of `@circuit_breaker`
- [x] Update imports to use resilience module
- [x] Maintain backward compatibility exports

### Phase 5: Testing & Validation ✅ **COMPLETED**
- [x] Run all existing tests to ensure compatibility
- [x] Run new resilience tests
- [x] Verify middleware behavior unchanged
- [x] Verify decorator behavior unchanged
- [x] Check test coverage (target: 100%)

## API Design

### RetryExecutor
```python
class RetryExecutor:
    def __init__(self, policy: RetryPolicy):
        self.policy = policy
    
    async def execute_async(self, func, *args, **kwargs):
        """Execute async function with retry logic."""
        
    def execute_sync(self, func, *args, **kwargs):
        """Execute sync function with retry logic."""
```

### Unified RetryPolicy
```python
@attrs.define
class RetryPolicy:
    max_attempts: int = 3
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    retryable_errors: tuple[type[Exception], ...] | None = None
    retryable_status_codes: set[int] | None = None  # For HTTP
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if should retry."""
    
    def should_retry_response(self, response: Any, attempt: int) -> bool:
        """Check if HTTP response should be retried."""
```

### Updated RetryMiddleware
```python
@attrs.define
class RetryMiddleware(Middleware):
    policy: RetryPolicy = attrs.field(
        factory=lambda: RetryPolicy(
            max_attempts=3,
            base_delay=0.5,
            retryable_status_codes={500, 502, 503, 504}
        )
    )
    
    async def execute_with_retry(self, execute_func, request):
        executor = RetryExecutor(self.policy)
        
        async def wrapped():
            response = await execute_func(request)
            if self.policy.should_retry_response(response, attempt=1):
                raise TransportError(f"Retryable status: {response.status}")
            return response
        
        return await executor.execute_async(wrapped)
```

## Migration Path

### Backward Compatibility
During migration, maintain backward compatibility by re-exporting from errors module:

```python
# src/provide/foundation/errors/types.py
from provide.foundation.resilience.retry import RetryPolicy
import warnings

def __getattr__(name):
    if name == "RetryPolicy":
        warnings.warn(
            "Importing RetryPolicy from errors.types is deprecated. "
            "Use provide.foundation.resilience.retry instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return RetryPolicy
    raise AttributeError(f"module {__name__} has no attribute {name}")
```

## Success Criteria
1. All existing tests pass without modification
2. New resilience tests achieve 100% coverage
3. No duplicate retry logic between decorator and middleware
4. Clean separation between error definition and resilience patterns
5. Performance unchanged or improved
6. Clear migration path with deprecation warnings

## Timeline
- Phase 1 (Tests): 2 hours
- Phase 2 (Implementation): 3 hours
- Phase 3 (Migration): 1 hour
- Phase 4 (Updates): 1 hour
- Phase 5 (Validation): 1 hour

Total: ~8 hours of focused work

## 🎉 **PROJECT COMPLETED**

**Completion Date**: 2025-09-09  
**Final Status**: ✅ **100% COMPLETE**

### Final Results
- **109 resilience tests passing** ✅
- **0 failing tests** ✅
- **All phases completed** ✅
- **Full backward compatibility maintained** ✅

### Key Accomplishments
1. ✅ **Complete module refactoring**: Moved all resilience patterns from `errors` to dedicated `resilience` module
2. ✅ **Unified retry logic**: Eliminated duplication between decorators and middleware using shared `RetryExecutor`
3. ✅ **Industry alignment**: Implemented patterns matching Polly, Hystrix, and resilience4j standards
4. ✅ **Comprehensive testing**: 109 tests covering all scenarios, edge cases, and integration patterns
5. ✅ **Clean separation**: Errors define what went wrong; resilience defines how to recover

### Technical Fixes Delivered
- **Fixed pytest freezing**: Resolved circular import in `utils/deps.py`
- **Enhanced fallback chains**: Proper exception tracking and metadata preservation
- **Corrected retry logging**: Fixed order of error logging vs retry checks
- **Improved circuit breaker**: Proper state transitions and recovery logic
- **Generator handling**: Correct support for generator functions in retry logic

### Module Structure Created
```
src/provide/foundation/resilience/
├── __init__.py              # Public API exports
├── retry.py                 # RetryPolicy, RetryExecutor, BackoffStrategy
├── decorators.py            # @retry, @circuit_breaker, @fallback decorators  
├── circuit.py               # CircuitBreaker, CircuitState
└── fallback.py              # FallbackChain, fallback strategies

tests/resilience/
├── test_retry_executor.py   # RetryExecutor comprehensive testing
├── test_retry_policy.py     # RetryPolicy configuration and behavior
├── test_retry_decorator.py  # @retry decorator testing  
├── test_circuit_breaker.py  # CircuitBreaker state machine testing
├── test_fallback.py         # FallbackChain execution testing
└── test_integration.py      # Cross-pattern integration testing
```

The resilience module now provides robust, industry-standard patterns for:
- **Retry**: Configurable backoff strategies with jitter and filtering
- **Circuit Breaker**: State-based failure detection and recovery
- **Fallback**: Graceful degradation through fallback chains

## References
- [Polly Resilience Framework](https://github.com/App-vNext/Polly)
- [Hystrix Circuit Breaker](https://github.com/Netflix/Hystrix)
- [resilience4j](https://resilience4j.readme.io/)
- [tenacity Python library](https://github.com/jd/tenacity)