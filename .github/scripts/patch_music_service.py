import sys
import re

path = "app/src/main/kotlin/com/music/vivi/playback/MusicService.kt"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Imports
if "SpatialAudioEnabledKey" not in code:
    imports_to_add = """import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import com.music.vivi.constants.SpatialAudioBluetoothOnlyKey
import com.music.vivi.constants.SpatialAudioEnabledKey
"""
    code = code.replace("package com.music.vivi.playback\n", "package com.music.vivi.playback\n\n" + imports_to_add)

# 2. Helpers and device callback
if "spatialProcessors" not in code:
    helpers = """    private val spatialProcessors = java.util.concurrent.CopyOnWriteArrayList<SpatialAudioProcessor>()

    private fun isBluetoothAudioConnected(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val devices = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            devices.any {
                it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
                it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO
            }
        } else {
            @Suppress("DEPRECATION")
            audioManager.isBluetoothA2dpOn || audioManager.isBluetoothScoOn
        }
    }

    private fun updateSpatialAudioState() {
        scope.launch {
            val enabled = dataStore.get(SpatialAudioEnabledKey, false)
            val bluetoothOnly = dataStore.get(SpatialAudioBluetoothOnlyKey, false)
            val isBt = isBluetoothAudioConnected()
            val shouldEnable = enabled && (!bluetoothOnly || isBt)
            spatialProcessors.forEach { it.enabled = shouldEnable }
        }
    }

    private val audioDeviceCallback = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>?) {
            super.onAudioDevicesAdded(addedDevices)
            val hasBluetooth = addedDevices?.any {
                it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
                it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO
            } == true

            if (hasBluetooth) {
                if (dataStore.get(ResumeOnBluetoothConnectKey, false)) {
                    if (player.playbackState == Player.STATE_READY && !player.isPlaying) {
                        player.play()
                    }
                }
            }
            updateSpatialAudioState()
        }

        override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>?) {
            super.onAudioDevicesRemoved(removedDevices)
            updateSpatialAudioState()
        }
    }

    override fun onCreate() {
"""
    code = code.replace("    override fun onCreate() {\n", helpers, 1)

# 3. Register device callback in onCreate
if "audioManager.registerAudioDeviceCallback(audioDeviceCallback" not in code:
    code = code.replace(
        "registerReceiver(screenStateReceiver, screenStateFilter)",
        "registerReceiver(screenStateReceiver, screenStateFilter)\n        audioManager.registerAudioDeviceCallback(audioDeviceCallback, null)"
    )

# 4. Observe spatial audio settings in onCreate
if "SpatialAudioBluetoothOnlyKey" not in code or "collectLatest(scope) { (enabled, bluetoothOnly) ->" not in code:
    flow_code = """        combine(
            dataStore.data.map { it[SpatialAudioEnabledKey] ?: false },
            dataStore.data.map { it[SpatialAudioBluetoothOnlyKey] ?: false }
        ) { enabled, bluetoothOnly ->
            enabled to bluetoothOnly
        }.distinctUntilChanged()
        .collectLatest(scope) { (enabled, bluetoothOnly) ->
            val isBt = isBluetoothAudioConnected()
            val shouldEnable = enabled && (!bluetoothOnly || isBt)
            spatialProcessors.forEach { it.enabled = shouldEnable }
        }

"""
    target = "setupLoudnessEnhancer()}"
    if target in code:
        code = code.replace(target, target + "\n\n" + flow_code, 1)

# 5. createExoPlayer wiring
if "spatialProcessors.add(spatialProcessor)" not in code:
    if "val spatialProcessor = SpatialAudioProcessor().apply { enabled = true }" in code:
        code = code.replace(
            "val spatialProcessor = SpatialAudioProcessor().apply { enabled = true }",
            "val spatialProcessor = SpatialAudioProcessor()\n        spatialProcessors.add(spatialProcessor)\n        updateSpatialAudioState()"
        )
    elif "val spatialProcessor = SpatialAudioProcessor()" in code and "spatialProcessors.add(spatialProcessor)" not in code:
        code = code.replace(
            "val spatialProcessor = SpatialAudioProcessor()",
            "val spatialProcessor = SpatialAudioProcessor()\n        spatialProcessors.add(spatialProcessor)\n        updateSpatialAudioState()"
        )

# 6. Unregister callback in onDestroy
if "unregisterAudioDeviceCallback(audioDeviceCallback)" not in code:
    code = code.replace(
        "super.onDestroy()",
        "try {\n            audioManager.unregisterAudioDeviceCallback(audioDeviceCallback)\n        } catch (e: Exception) {\n            Timber.tag(TAG).e(e, \"Failed to unregister audio device callback\")\n        }\n        super.onDestroy()"
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Patch applied successfully to MusicService.kt")
