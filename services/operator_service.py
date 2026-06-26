from fastapi import HTTPException, status


LIGHT_MODE_MAP = {
    "infrared": "InfraRed",
    "ir": "InfraRed",
    "variablewhitelight": "WhiteLight",
    "whitelight": "WhiteLight",
    "white": "WhiteLight",
    "color": "WhiteLight",
    "auto": "Auto",
}


class OperatorService:
    def __init__(self, runtime, ptz, lights, logger):
        self.runtime = runtime
        self.ptz = ptz
        self.lights = lights
        self.logger = logger

    def move(self, direction):
        commands = {
            "up": lambda: self.ptz.move(0, 0.5),
            "down": lambda: self.ptz.move(0, -0.5),
            "left": lambda: self.ptz.move(-0.5, 0),
            "right": lambda: self.ptz.move(0.5, 0),
            "stop": self.ptz.stop_pantilt,
        }
        return self._run_manual_command("move", direction, commands)

    def zoom(self, direction):
        commands = {
            "in": lambda: self.ptz.zoom(0.3),
            "out": lambda: self.ptz.zoom(-0.3),
            "stop": self.ptz.stop_zoom,
        }
        return self._run_manual_command("zoom", direction, commands)

    def focus(self, direction):
        commands = {
            "near": lambda: self.ptz.focus(0.3),
            "far": lambda: self.ptz.focus(-0.3),
            "stop": self.ptz.stop_focus,
        }
        return self._run_manual_command("focus", direction, commands)

    def set_lights(self, mode, brightness=100):
        target_mode = LIGHT_MODE_MAP.get(mode.lower())
        if target_mode is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown light mode '{mode}'. Valid modes: {sorted(LIGHT_MODE_MAP)}",
            )

        if not 0 <= brightness <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="brightness must be between 0 and 100",
            )

        self.logger.info("Lighting map: from '%s' to camera mode '%s' (brightness: %s)", mode, target_mode, brightness)

        ok = self.lights.set_lighting(target_mode, str(brightness))
        return {
            "status": "success" if ok else "error",
            "requested_mode": mode,
            "sent_to_camera": target_mode,
            "brightness": brightness,
        }

    def toggle_guard(self):
        return {"status": self.runtime.toggle_guard()}

    def _run_manual_command(self, command_type, direction, commands):
        command = commands.get(direction)
        if command is None:
            return {"status": "error", "message": f"Unknown direction: {direction}"}

        self.runtime.manual_override()
        command()
        return {"status": "success", "direction": direction}
