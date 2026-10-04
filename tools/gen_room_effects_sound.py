#!/usr/bin/env python3
"""Synthesises the two sounds of the extra room effects (config/roomAmbienceDeferred.cfg).

    python tools/gen_room_effects_sound.py

Writes sounds/Spatial/Rooms/Temple/Gong/Gong01.ogg (a bell-like gong, sum of decaying partials) and
sounds/Spatial/Rooms/Hatchery/RoosterCrow/RoosterCrow01.ogg (a crow made of gliding, formant-shaped
harmonic tones). Everything is computed from sine waves and noise by this script, nothing is taken
from a recording or another work.

Needs numpy and ffmpeg (with the Vorbis encoder) on the path.
"""

import math
import os
import subprocess
import tempfile
import wave

import numpy as np

RATE = 44100


def write_ogg(samples, path):
    peak = float(np.max(np.abs(samples)))
    if peak > 0.0:
        samples = samples * (0.7 / peak)
    data = (samples * 32767.0).astype("<i2").tobytes()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        wav_path = os.path.join(folder, "sound.wav")
        with wave.open(wav_path, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(RATE)
            handle.writeframes(data)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, "-c:a", "libvorbis", "-q:a", "4", path],
                       check=True)


def gong():
    length = 4.2
    t = np.arange(int(RATE * length)) / RATE
    base = 172.0
    # frequency ratio, level, decay time in seconds
    partials = ((1.0, 1.0, 3.2), (1.47, 0.7, 2.6), (1.98, 0.55, 2.2), (2.52, 0.45, 1.7), (3.11, 0.3, 1.3),
                (4.07, 0.22, 1.0), (5.2, 0.12, 0.7))
    out = np.zeros_like(t)
    rng = np.random.RandomState(5)
    for index, (ratio, level, decay) in enumerate(partials):
        phase = rng.uniform(0, 2 * math.pi)
        # a slow beating from a second, slightly detuned partial makes the shimmer of a gong
        beat = 1.0 + 0.0035 * (index + 1)
        wave_a = np.sin(2 * math.pi * base * ratio * t + phase)
        wave_b = np.sin(2 * math.pi * base * ratio * beat * t + phase * 0.5)
        out += level * np.exp(-t / decay) * (0.6 * wave_a + 0.4 * wave_b)
    # the strike: a short burst of filtered noise
    noise = rng.uniform(-1, 1, len(t))
    kernel = np.ones(24) / 24.0
    noise = np.convolve(noise, kernel, mode="same")
    out += 0.5 * noise * np.exp(-t / 0.05)
    attack = np.minimum(1.0, t / 0.004)
    return out * attack


def crow():
    # syllables: start, length, pitch at start, pitch at end, vibrato depth
    syllables = ((0.00, 0.17, 520.0, 640.0, 0.0), (0.21, 0.12, 600.0, 640.0, 0.0), (0.38, 0.30, 620.0, 880.0, 0.01),
                 (0.74, 1.05, 900.0, 520.0, 0.03))
    length = 2.0
    t = np.arange(int(RATE * length)) / RATE
    out = np.zeros_like(t)
    rng = np.random.RandomState(9)
    for start, duration, f_start, f_end, vibrato in syllables:
        count = int(duration * RATE)
        offset = int(start * RATE)
        local = np.arange(count) / RATE
        progress = local / duration
        # the pitch glides with a curve, the long tail sags at the end
        pitch = f_start + (f_end - f_start) * (progress ** 1.4)
        pitch = pitch * (1.0 + vibrato * np.sin(2 * math.pi * 13.0 * local))
        pitch = pitch * (1.0 + 0.004 * rng.uniform(-1, 1, count))
        phase = 2 * math.pi * np.cumsum(pitch) / RATE
        tone = np.zeros(count)
        for harmonic in range(1, 22):
            frequency = pitch * harmonic
            # two formants make the harsh, nasal colour of the call
            shape = (math.exp(-((harmonic * f_start - 1300.0) / 900.0) ** 2) + 0.7 * math.exp(-((harmonic * f_start - 2700.0) / 1000.0) ** 2))
            shape = np.where(frequency < 6000.0, shape, 0.0)
            tone += shape * np.sin(harmonic * phase) / math.sqrt(harmonic)
        fade_in = np.minimum(1.0, local / 0.015)
        fade_out = np.minimum(1.0, (duration - local) / (0.06 if duration < 0.5 else 0.25))
        envelope = fade_in * np.clip(fade_out, 0.0, 1.0)
        # a rough, strained voice: fast amplitude flutter
        flutter = 1.0 + 0.25 * np.sin(2 * math.pi * 55.0 * local + rng.uniform(0, 6))
        out[offset:offset + count] += tone * envelope * flutter
    return out


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    write_ogg(gong(), os.path.join(root, "sounds", "Spatial", "Rooms", "Temple", "Gong", "Gong01.ogg"))
    print("wrote Gong01.ogg")
    write_ogg(crow(), os.path.join(root, "sounds", "Spatial", "Rooms", "Hatchery", "RoosterCrow", "RoosterCrow01.ogg"))
    print("wrote RoosterCrow01.ogg")


if __name__ == "__main__":
    main()
