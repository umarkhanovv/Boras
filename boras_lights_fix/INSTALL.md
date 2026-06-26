# Boras — Lights Fix

## Bug: lights commands accepted but light doesn't turn on

Symptom: `/api/lights` returns 200, log shows "✅ Success! Camera accepted the
change." but the physical light doesn't turn on.

## Root cause

The XML sent to the camera had `VarWhiteWorkMode=timing` with time window
18:00-06:00. This means the camera accepts the command but only actually
turns on the light during that time window. During daytime (06:00-18:00),
the camera silently ignores the "on" command.

Same issue with `ColorWorkmode=custom` and `VarWhiteControlMode=custom` —
all tied to the same 18:00-06:00 schedule.

## Fix

Changed in `lights.py`:
- `VarWhiteWorkMode`: `timing` → `auto`
- `VarWhiteControlMode`: `custom` → `auto`
- `ColorWorkmode`: `custom` → `auto`
- Time windows: `18:00-06:00` → `00:00-23:59` (full day)

Now the camera should turn on the light immediately regardless of time.

## How to install

```bash
cd ~/Desktop/Boras
unzip ~/Downloads/boras_lights_fix.zip
cp boras_lights_fix/lights.py ./lights.py
```

## After install — restart server

```bash
cd ~/Desktop/Boras
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then click "White Light" button in the web panel. The light should turn on
immediately.

## If still doesn't work

If the light still doesn't turn on after this fix, the camera might have
additional scheduling or threshold logic. Try:

1. Open camera's web UI directly: http://10.60.98.215/
2. Find the lighting/IR-cut settings page
3. Check if there's a separate "manual override" or "always on" option
4. Try setting brightness to 100 manually in the camera UI to confirm
   the hardware works

Some cameras require the light to be physically enabled in a separate
setting before API commands take effect.
