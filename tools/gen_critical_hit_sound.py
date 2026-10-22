#!/usr/bin/env python3
"""Synthesizes the short sound of a critical hit and writes it as an .ogg file.

    python tools/gen_critical_hit_sound.py

The sound is made from sine waves, noise and simple envelopes only (no recordings, no samples), with a
fixed random seed, so the same file comes out every time. It uses the envelope and decay helpers of
tools/gen_spell_sounds.py. The .wav file is made with the standard library and converted by ffmpeg
(libvorbis, mono, 44.1 kHz), which must be in the PATH. The file goes to
sounds/Spatial/Creatures/Default/Critical/FxCriticalHit01.ogg.
"""

import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

import numpy

import gen_spell_sounds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE = 44100
TAU = 2.0 * math.pi
SEED = 31
LENGTH = 0.45
ATTACK = 0.002
RELEASE = 0.08
PEAK = 0.85
TONE_FREQUENCIES = (820.0, 1230.0, 1745.0, 2470.0)
TONE_AMPLITUDES = (1.0, 0.6, 0.4, 0.25)
TONE_DECAY = 9.0
NOISE_AMPLITUDE = 0.5
NOISE_DECAY = 40.0
THUMP_FREQUENCY = 95.0
THUMP_AMPLITUDE = 0.7
THUMP_DECAY = 18.0
OGG_QUALITY = "3"
TARGET_PATH = ("sounds", "Spatial", "Creatures", "Default", "Critical", "FxCriticalHit01.ogg")


def make_critical_hit():
    """Returns the samples (-1..1, peak normalized to PEAK) of the critical hit sound.

    Layers: four decaying sines (bright ring), a short white noise crack and a low sine thump,
    shaped by one attack/release envelope.
    """
    rng = numpy.random.default_rng(SEED)
    count = int(LENGTH * RATE)
    noise = rng.uniform(-1.0, 1.0, count)
    samples = []
    for i in range(count):
        t = i / float(RATE)
        ring = 0.0
        for frequency, amplitude in zip(TONE_FREQUENCIES, TONE_AMPLITUDES):
            ring += amplitude * math.sin(TAU * frequency * t) * gen_spell_sounds.decay(t, TONE_DECAY)
        crack = NOISE_AMPLITUDE * float(noise[i]) * gen_spell_sounds.decay(t, NOISE_DECAY)
        thump = THUMP_AMPLITUDE * math.sin(TAU * THUMP_FREQUENCY * t) * gen_spell_sounds.decay(t, THUMP_DECAY)
        samples.append((ring + crack + thump) * gen_spell_sounds.envelope(t, LENGTH, ATTACK, RELEASE))
    peak = max(1e-6, max(abs(s) for s in samples))
    return [s / peak * PEAK for s in samples]


def write_wav(path, samples):
    """Writes the samples as a 16 bit mono wav file at RATE."""
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples))


def main():
    """Renders the sound and converts it to the target .ogg; returns the process exit code."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found in PATH")
        return 1
    folder = tempfile.mkdtemp()
    try:
        wav_path = os.path.join(folder, "CriticalHit.wav")
        write_wav(wav_path, make_critical_hit())
        target = os.path.join(ROOT, *TARGET_PATH)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
                               "-ac", "1", "-ar", str(RATE), "-c:a", "libvorbis", "-q:a", OGG_QUALITY, target])
        print("wrote", os.path.relpath(target, ROOT), os.path.getsize(target), "bytes")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
