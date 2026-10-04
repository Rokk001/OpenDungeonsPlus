#!/usr/bin/env python3
"""Synthesizes the short sounds of the spell effects and writes them as .ogg files.

    python tools/gen_spell_sounds.py

The sounds are made from sine waves, noise and simple envelopes only (no recordings, no samples), with a
fixed random seed, so the same files come out every time. The .wav files are made with the standard
library and converted by ffmpeg (libvorbis), which must be in the PATH. Files go to
sounds/Spatial/Spells/<Family>/Fx<Family>01.ogg.
"""

import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE = 22050
TAU = 2.0 * math.pi


def n_samples(seconds):
    return int(seconds * RATE)


def envelope(t, length, attack, release):
    """Linear attack, exponential-looking release, 0..1."""
    if t < attack:
        return t / attack if attack > 0 else 1.0
    left = length - t
    if left < release:
        value = left / release
        return value * value
    return 1.0


def decay(t, rate):
    return math.exp(-rate * t)


class Noise(object):
    def __init__(self, seed):
        self.random = random.Random(seed)
        self.low = 0.0

    def white(self):
        return self.random.uniform(-1.0, 1.0)

    def lowpass(self, amount):
        """One-pole low pass noise, amount 0 (white) .. 0.99 (very dark)."""
        self.low = self.low * amount + self.white() * (1.0 - amount)
        return self.low


def render(length, func):
    samples = []
    for i in range(n_samples(length)):
        samples.append(func(i / float(RATE)))
    peak = max(1e-6, max(abs(s) for s in samples))
    return [s / peak * 0.8 for s in samples]


def sweep_phase(f0, f1, length, t):
    """Phase of a sine that moves from f0 to f1 over the length."""
    k = (f1 - f0) / length
    return TAU * (f0 * t + 0.5 * k * t * t)


def make_summon():
    length = 1.1
    noise = Noise(1)

    def f(t):
        e = envelope(t, length, 0.05, 0.5)
        tone = math.sin(sweep_phase(300.0, 900.0, length, t)) * 0.6
        tone += math.sin(sweep_phase(450.0, 1350.0, length, t)) * 0.25
        shimmer = math.sin(TAU * 2400.0 * t) * math.sin(TAU * 11.0 * t) * 0.15 * (t / length)
        return (tone + shimmer + noise.lowpass(0.6) * 0.05) * e
    return render(length, f)


def make_rally():
    length = 1.0
    noise = Noise(2)

    def f(t):
        base = 196.0 if t < 0.4 else 261.6
        e = envelope(t, length, 0.04, 0.3)
        value = 0.0
        for h in range(1, 7):
            value += math.sin(TAU * base * h * t) / h
        return (value * 0.5 + noise.lowpass(0.7) * 0.05) * e
    return render(length, f)


def make_explosion():
    length = 1.0
    noise = Noise(3)

    def f(t):
        crack = noise.white() * decay(t, 18.0)
        rumble = noise.lowpass(0.93) * 5.0 * decay(t, 3.5)
        thump = math.sin(TAU * (70.0 - 40.0 * t) * t) * decay(t, 6.0)
        return crack * 0.7 + rumble * 0.8 + thump
    return render(length, f)


def make_boost():
    length = 0.7
    notes = (392.0, 523.3, 659.3, 784.0)

    def f(t):
        index = min(len(notes) - 1, int(t / 0.12))
        local = t - index * 0.12
        e = decay(local, 5.0) * min(1.0, local / 0.01)
        tone = math.sin(TAU * notes[index] * t) + 0.3 * math.sin(TAU * notes[index] * 2.0 * t)
        return tone * e * envelope(t, length, 0.0, 0.2)
    return render(length, f)


def make_curse():
    length = 0.9
    noise = Noise(4)

    def f(t):
        e = envelope(t, length, 0.03, 0.4)
        vibrato = 1.0 + 0.03 * math.sin(TAU * 7.0 * t)
        tone = math.sin(sweep_phase(520.0, 140.0, length, t) * vibrato) * 0.7
        tone += math.sin(sweep_phase(525.0, 145.0, length, t) * 1.01) * 0.4
        return (tone + noise.lowpass(0.8) * 0.2) * e
    return render(length, f)


def make_dark():
    length = 1.3
    noise = Noise(5)

    def f(t):
        swell = math.sin(math.pi * min(1.0, t / length))
        tremolo = 0.75 + 0.25 * math.sin(TAU * 5.0 * t)
        tone = math.sin(TAU * 110.0 * t) + math.sin(TAU * 110.7 * t) + 0.4 * math.sin(TAU * 164.0 * t)
        return (tone * 0.4 + noise.lowpass(0.9) * 1.5) * swell * tremolo
    return render(length, f)


def make_gold():
    length = 0.9
    rng = random.Random(6)
    times = [0.0] + sorted(rng.uniform(0.04, 0.45) for _ in range(5))
    freqs = [1760.0, 2093.0, 2637.0, 2349.0, 3136.0, 2794.0]

    def f(t):
        value = 0.0
        for start, freq in zip(times, freqs):
            if t >= start:
                local = t - start
                value += (math.sin(TAU * freq * local) + 0.4 * math.sin(TAU * freq * 2.76 * local)) * decay(local, 9.0)
        return value
    return render(length, f)


def make_lightning():
    length = 1.3
    noise = Noise(7)

    def f(t):
        crack = noise.white() * decay(t, 40.0) * 1.0
        hiss = noise.white() * decay(t, 7.0) * 0.25
        rumble = noise.lowpass(0.95) * 6.0 * decay(t, 2.2) * min(1.0, t / 0.05)
        return crack + hiss + rumble
    return render(length, f)


def make_tremor():
    length = 1.6
    noise = Noise(8)

    def f(t):
        swell = math.sin(math.pi * min(1.0, t / length)) ** 0.6
        shake = 0.7 + 0.3 * math.sin(TAU * 13.0 * t)
        low = math.sin(TAU * 42.0 * t) * 0.8 + math.sin(TAU * 57.0 * t) * 0.4
        return (noise.lowpass(0.96) * 6.0 + low) * swell * shake
    return render(length, f)


def make_hen():
    length = 0.55

    def f(t):
        pop = math.sin(TAU * (900.0 - 1500.0 * t) * t) * decay(t, 25.0)
        e = envelope(t, length, 0.0, 0.2)
        chirp = math.sin(sweep_phase(700.0, 350.0, length, t) + 3.0 * math.sin(TAU * 18.0 * t)) * (0.5 + 0.5 * math.sin(TAU * 9.0 * t))
        return (pop * 0.8 + chirp * 0.5 * (1.0 if t > 0.05 else 0.0)) * e
    return render(length, f)


def make_fire():
    length = 1.1
    noise = Noise(9)

    def f(t):
        e = math.sin(math.pi * min(1.0, t / length)) ** 0.8
        sweep = 0.4 + 0.5 * min(1.0, t / 0.5)
        crackle = noise.white() * (1.0 if noise.random.random() < 0.02 else 0.0) * 1.5
        return (noise.lowpass(sweep * 0.9) * 4.0 + crackle) * e
    return render(length, f)


SOUNDS = (
    ("Summon", make_summon),
    ("Rally", make_rally),
    ("Explosion", make_explosion),
    ("Boost", make_boost),
    ("Curse", make_curse),
    ("Dark", make_dark),
    ("Gold", make_gold),
    ("Lightning", make_lightning),
    ("Tremor", make_tremor),
    ("Hen", make_hen),
    ("Fire", make_fire),
)


def write_wav(path, samples):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples))


def main():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found in PATH")
        return 1
    folder = tempfile.mkdtemp()
    try:
        for family, make in SOUNDS:
            wav_path = os.path.join(folder, family + ".wav")
            write_wav(wav_path, make())
            target_dir = os.path.join(ROOT, "sounds", "Spatial", "Spells", family)
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, "Fx%s01.ogg" % family)
            subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
                                   "-c:a", "libvorbis", "-q:a", "3", target])
            print("wrote", os.path.relpath(target, ROOT), os.path.getsize(target), "bytes")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
