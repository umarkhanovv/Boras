# Boras — Runtime Bug Fixes v2

## Bugs fixed

### Bug 1: `invalid_tilt_speed` (120 errors in metrics)
YOLO returns numpy.float32 values for cx/cy/group_height. These propagated
through auto_aim into ptz.move(), where CranePTZ._safe_speed() rejected
them because `isinstance(numpy.float32, (int, float))` is False.

**Fix:** `auto_aim()` now converts ALL inputs to Python float at the entry
point. All ptz.move/zoom/focus calls also wrap values in float() as defense
in depth.

### Bug 2: `Imaging focus -> HTTP 400` (focus not supported)
Camera doesn't support ONVIF Imaging service for focus control. Every
focus() and stop_focus() call returned HTTP 400, bumping error counter.

**Fix:** New config setting `ptz.enable_focus_control` (default True).
When set to False, focus() and stop_focus() become silent no-ops.
Also: focus() now uses suppress_error=True so even if camera rejects,
error counter doesn't grow.

## How to install

```bash
cd ~/Desktop/Boras
unzip ~/Downloads/boras_runtime_fix2.zip
cp -r boras_runtime_fix2/* .
rm -rf boras_runtime_fix2
```

## After install — disable focus control (recommended for your camera)

Since your camera returns HTTP 400 for all focus commands, disable focus:

**Option A — environment variable:**
```bash
export CRANE_DISABLE_FOCUS=1
cd ~/Desktop/Boras
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Option B — edit config_local.py:**
Add this line to your `config_local.py`:
```python
# Disable focus control — camera doesn't support ONVIF Imaging focus
import os
os.environ["CRANE_DISABLE_FOCUS"] = "1"
```

**Option C — edit config.py default:**
Change `enable_focus_control: bool = True` to `False` in config.py PTZConfig.

## What changed

### behavior/tracking.py
- `auto_aim()`: explicit `float()` conversion for cx/cy/group_height/frame_width/frame_height at entry
- `ptz.move(float(speed_x), 0.0)` and `ptz.move(0.0, float(-speed_y))` — defense in depth
- `ptz.zoom(float(...))` and `ptz.focus(float(...))` — same

### services/ptz_service.py
- New `self._enable_focus` flag from `cfg.enable_focus_control`
- `focus()`: returns early if `_enable_focus=False`, otherwise uses `suppress_error=True`
- `stop_focus()`: returns early if `_enable_focus=False`

### config.py
- New PTZConfig field: `enable_focus_control: bool = True`
- New env override: `CRANE_DISABLE_FOCUS` (set to "1" or "true" to disable)

## After fix — expected behavior

- `metrics.errors` should stop growing (was 120, should stay at 0 or near 0)
- No more `invalid_tilt_speed` errors in event log
- No more `Imaging focus -> HTTP 400` warnings
- `tracking_trace.auto_aim.decision: "tilt"` will now actually move the camera
  (previously tilt was rejected by _safe_speed)
- `ptz_commands` counter will grow as tilt/zoom commands succeed

## Total tests: 209 passed
