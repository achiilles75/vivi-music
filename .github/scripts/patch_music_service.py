import sys
import re

path = "app/src/main/kotlin/com/music/vivi/playback/MusicService.kt"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Clean duplicate imports if present
dup_imports = """import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import com.music.vivi.constants.SpatialAudioBluetoothOnlyKey
import com.music.vivi.constants.SpatialAudioEnabledKey
"""
clean_imports = """import com.music.vivi.constants.SpatialAudioBluetoothOnlyKey
import com.music.vivi.constants.SpatialAudioEnabledKey
"""
if dup_imports in code:
    code = code.replace(dup_imports, clean_imports)

while code.count("import android.media.AudioDeviceCallback") > 1:
    code = code.replace("import android.media.AudioDeviceCallback\n", "", 1)

while code.count("import android.media.AudioDeviceInfo") > 1:
    code = code.replace("import android.media.AudioDeviceInfo\n", "", 1)

# 2. Remove the old audioDeviceCallback (without updateSpatialAudioState) if both exist
old_callback_pattern = re.compile(
    r"    private val audioDeviceCallback = object : AudioDeviceCallback\(\) \{\s+"
    r"override fun onAudioDevicesAdded\(addedDevices: Array<out AudioDeviceInfo>\?\) \{\s+"
    r"super\.onAudioDevicesAdded\(addedDevices\)\s+"
    r"val hasBluetooth = addedDevices\?\.any \{\s+"
    r"it\.type == AudioDeviceInfo\.TYPE_BLUETOOTH_A2DP \|\|\s+"
    r"it\.type == AudioDeviceInfo\.TYPE_BLUETOOTH_SCO\s+"
    r"\} == true\s+"
    r"if \(hasBluetooth\) \{\s+"
    r"if \(dataStore\.get\(ResumeOnBluetoothConnectKey, false\)\) \{\s+"
    r"if \(player\.playbackState == Player\.STATE_READY && !player\.isPlaying\) \{\s+"
    r"player\.play\(\)\s+"
    r"\}\s+"
    r"\}\s+"
    r"\}\s+"
    r"\}\s+"
    r"\}\n",
    re.MULTILINE
)

if code.count("private val audioDeviceCallback") > 1:
    code = old_callback_pattern.sub("", code, count=1)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Cleaned up MusicService.kt duplicate definitions successfully")
