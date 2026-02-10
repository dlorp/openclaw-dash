# Connection Failure Warnings Implementation

**Branch:** `feature/show-connection-warnings`  
**Status:** ✅ Complete and tested

## Problem

Dashboard was silently using fallback/cached data when gateway was unreachable. Users thought it was working but were seeing zeros or stale data with no indication that anything was wrong.

## Solution

Added visible warnings at multiple levels when collectors are in degraded state:

### 1. TUI Warning Banner

**New widget:** `ConnectionWarningBanner`
- Monitors all collector states in real-time
- Shows prominent yellow banner across top of dashboard when any collector is degraded
- Auto-hides when all collectors healthy
- Messages adapt based on issue severity:
  - `⚠️ Gateway unreachable - using fallback data` (most critical)
  - `⚠️ Circuit breaker open: sessions, agents`
  - `⚠️ Using cached data (3 sources)`

**Integration:**
- Added to `app.py` compose() after Header
- Refreshes during both auto-refresh and manual refresh cycles
- Uses existing `CollectorState` infrastructure from `base.py`

### 2. CLI Status Indicators

**Enhanced `--status` output:**
- Gateway panel now shows state flags:
  - `⚠ STALE` (yellow) - data is old
  - `⚠ CIRCUIT OPEN` (red) - collector circuit breaker tripped
  - `📦 cached` (dim) - using cached data
- Warning message at top if any collectors degraded:
  ```
  ⚠️  Warning: Using fallback/cached data for: gateway, sessions
  ```

### 3. Existing Infrastructure Leveraged

No changes needed to collectors themselves - they already track state properly:

- **`CollectorState` enum** in `base.py`: OK, ERROR, TIMEOUT, UNAVAILABLE, STALE
- **`CollectorResult`** dataclass: tracks error, state, duration, retry count
- **Cache layer flags**: `_stale`, `_circuit_open`, `_from_cache`, `_error`
- **Global state tracking**: `get_collector_state()`, `update_collector_state()`
- **Gateway collector**: already tracks consecutive failures and last healthy time

## Files Changed

```
src/openclaw_dash/widgets/connection_warning.py  (new, 114 lines)
src/openclaw_dash/app.py                         (+22 lines)
src/openclaw_dash/cli.py                         (+24 lines)
```

## Testing

✅ Import successful  
✅ TUI starts without errors  
✅ `--status` output shows correctly  
✅ No warnings shown when gateway healthy  

## Example Scenarios

### Scenario 1: Gateway Offline
**Before:** Dashboard shows zeros everywhere, user confused  
**After:** Yellow banner: `⚠️ Gateway unreachable - using fallback data`

### Scenario 2: Transient Network Issue
**Before:** Stale data silently used, no indication  
**After:** Banner: `⚠️ Using cached data: sessions, agents` + `📦 cached` flag on status

### Scenario 3: Circuit Breaker Tripped
**Before:** Collector stops working silently  
**After:** Banner: `⚠️ Circuit breaker open: billing` + `⚠ CIRCUIT OPEN` flag on status

## Design Notes

- **Non-intrusive:** Banner only appears when needed, doesn't clutter UI
- **Actionable:** Messages give context about what's wrong
- **Consistent:** Same state detection logic used in TUI and CLI
- **Performant:** Leverages existing state tracking, no extra API calls
- **Robust:** Wrapped in try/except to never crash the dashboard

## Future Enhancements (optional)

- Add "retry now" button to banner that invalidates caches
- Show time since last successful refresh for each collector
- Add banner to `--watch` mode as well
- Color-code collectors by health in metrics panel
