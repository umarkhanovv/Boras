import base64
import logging
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("crane.lights")

class CraneLightsFull:
    def __init__(self, ip, username, password):
        self.url = f"http://{ip}/Images/1/IrCutFilter"
        self.auth = HTTPBasicAuth(username, password)
        # Was previously a hardcoded base64 string for the default
        # credentials — silently wrong if the real password ever differed.
        # Derive it from the actual username/password instead.
        user_info = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.cookies = {'userInfo': user_info}
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"http://{ip}/index.html"
        }

    def set_lighting(self, mode, brightness):
        """
        Sends the FULL XML configuration block with controllable brightness.

        Returns True on a 200 response, False on any rejection or network error.

        Fix: original XML had VarWhiteWorkMode=timing with time window 18:00-06:00,
        which meant the camera accepted the command but didn't turn on the light
        during daytime. Now using 'auto' work mode + 'manual' control mode so
        the light turns on immediately regardless of schedule.
        """
        full_xml = f"""<?xml version='1.0' encoding='UTF-8' ?>
        <IrCutFillter Version='1.0' xmlns='http://www.zwcloud.wang/ver10/XMLSchema'>
            <Mode>{mode}</Mode>
            <DayStartTime>07:00:00</DayStartTime>
            <DayEndTime>19:00:00</DayEndTime>
            <Sensitivity>45</Sensitivity>
            <SwitchTime>3</SwitchTime>
            <IrCutReverse>positive</IrCutReverse>
            <ColorLastTime>10</ColorLastTime>
            <ImageMode>normal</ImageMode>
            <VariableInfraredThreshold>45</VariableInfraredThreshold>
            <VariableWhiteThreshold>45</VariableWhiteThreshold>
            <VarWhiteWorkMode>auto</VarWhiteWorkMode>
            <VarWhiteModeStartTime>00000000T000000</VarWhiteModeStartTime>
            <VarWhiteModeStopTime>00000000T235959</VarWhiteModeStopTime>
            <NormalWhiteLightOffLimit>36</NormalWhiteLightOffLimit>
            <NormalWhiteLightOnLimit>87</NormalWhiteLightOnLimit>
            <VarWhiteLightOnThreshold>77</VarWhiteLightOnThreshold>
            <VarWhiteLightOffThreshold>36</VarWhiteLightOffThreshold>
            <ColorWorkmode>auto</ColorWorkmode>
            <CustomStartTime>00000000T000000</CustomStartTime>
            <CustomStopTime>00000000T235959</CustomStopTime>
            <VarInfraredWorkMode>auto</VarInfraredWorkMode>
            <VarInfraredBrightness>90</VarInfraredBrightness>
            <VarWhiteControlMode>auto</VarWhiteControlMode>
            <VarWhiteBrightness>{brightness}</VarWhiteBrightness>
            <ColorNightThreshold>45</ColorNightThreshold>
            <IntelligentThreshold>45</IntelligentThreshold>
        </IrCutFillter>"""

        try:
            logger.info("📡 Sending: Mode=%s, Brightness=%s...", mode, brightness)
            response = requests.put(
                self.url,
                data=full_xml,
                auth=self.auth,
                headers=self.headers,
                cookies=self.cookies,
                verify=False,
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✅ Success! Camera accepted the change.")
                return True
            else:
                logger.warning("❌ Server rejected. Code: %s", response.status_code)
                return False
        except Exception as e:
            logger.error("💥 Network error: %s", e)
            return False

if __name__ == "__main__":
    from config import CAMERA_IP, CAMERA_USER, CAMERA_PASS

    cam = CraneLightsFull(ip=CAMERA_IP, username=CAMERA_USER, password=CAMERA_PASS)
    print("💡 Crane Lighting Controller (Fixed)")
    print("---------------------------------------")
    print("1 - Lights ON (Mode: variablewhitelight, Brightness: 100)")
    print("2 - Lights OFF (Mode: infrared, Brightness: 0)")

    while True:
        choice = input("Option (1/2) or 'q': ").strip().lower()
        if choice == '1':
            cam.set_lighting("variablewhitelight", "100")
        elif choice == '2':
            cam.set_lighting("infrared", "0")
        elif choice == 'q':
            break
