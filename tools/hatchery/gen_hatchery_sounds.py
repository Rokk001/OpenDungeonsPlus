#!/usr/bin/env python3
"""Synthesizes the sounds of the hatchery animals and writes them as .ogg files.

    python tools/hatchery/gen_hatchery_sounds.py

Rooster crow, hen cluck, food call, chick peep and egg crack are made from harmonic tones with a simple
vowel-like spectrum, noise bursts and envelopes only (no recordings, no samples). A fixed random seed
makes the same files come out every time. The .wav files are written with the standard library and
converted by ffmpeg (libvorbis), which must be in the PATH. Files go to
sounds/Spatial/Rooms/Hatchery/<Family>/<Family><NN>.ogg, two variants per family.
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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 22050
TAU = 2.0 * math.pi


def n_samples(seconds):
    return int(seconds * RATE)


def decay(t, rate):
    return math.exp(-rate * t)


def smooth(t, start, end):
    """0 before start, 1 after end, smooth in between."""
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    x = (t - start) / (end - start)
    return x * x * (3.0 - 2.0 * x)


def lerp(a, b, x):
    return a + (b - a) * x


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


class Voice(object):
    """Harmonic tone with a vowel-like spectrum: harmonics near the formants are loud."""

    def __init__(self, formants, count=24):
        self.phase = 0.0
        self.formants = formants
        self.count = count

    def sample(self, f0, formants=None):
        self.phase += TAU * f0 / RATE
        if self.phase > TAU * 1000.0:
            self.phase -= TAU * 1000.0
        use = formants if formants is not None else self.formants
        value = 0.0
        for h in range(1, self.count + 1):
            freq = f0 * h
            if freq > RATE * 0.45:
                break
            gain = 0.0
            for centre, width, level in use:
                gain += level * math.exp(-((freq - centre) / width) ** 2)
            value += gain * math.sin(self.phase * h) / math.sqrt(h)
        return value


def render(length, func, level=0.8):
    samples = []
    for i in range(n_samples(length)):
        samples.append(func(i / float(RATE)))
    peak = max(1e-6, max(abs(s) for s in samples))
    return [s / peak * level for s in samples]


def fade(t, length, attack, release):
    if t < attack:
        return t / attack
    left = length - t
    if left < release:
        return max(0.0, left / release)
    return 1.0


def make_crow(variant):
    # Four parts like a crow: a short rising start, a short middle, a high held part, a long falling end.
    length = 1.7 + 0.1 * variant
    noise = Noise(10 + variant)
    voice = Voice(((900.0, 500.0, 1.0), (2100.0, 800.0, 0.55), (3400.0, 900.0, 0.2)))
    base = 520.0 * (1.0 + 0.07 * variant)
    parts = ((0.00, 0.22, 0.85, 1.05), (0.26, 0.42, 1.05, 1.0), (0.46, 0.92, 1.45, 1.2), (0.96, length - 0.05, 1.2, 0.62))

    def f(t):
        pitch = 0.0
        amp = 0.0
        for start, end, p0, p1 in parts:
            if start <= t < end:
                x = (t - start) / (end - start)
                pitch = base * lerp(p0, p1, x)
                amp = min(1.0, (t - start) / 0.02) * min(1.0, (end - t) / 0.04)
        if amp <= 0.0:
            voice.sample(base * 0.5)
            return 0.0
        vib = 1.0 + 0.025 * math.sin(TAU * 8.0 * t) * smooth(t, 0.9, 1.1)
        crack = 1.0 + 0.3 * math.sin(TAU * 60.0 * t)
        tone = voice.sample(pitch * vib) * crack
        return (tone + noise.lowpass(0.5) * 0.08) * amp * fade(t, length, 0.0, 0.1)
    return render(length, f)


def cluck_sample(voice, noise, local, f0, length):
    """One short cluck: a dull pop with a quickly falling pitch."""
    pitch = f0 * (1.0 - 0.35 * (local / length))
    env = smooth(local, 0.0, 0.006) * decay(local, 28.0)
    return (voice.sample(pitch) + noise.lowpass(0.6) * 0.15) * env


def make_cluck(variant):
    length = 0.85
    noise = Noise(20 + variant)
    voice = Voice(((650.0, 300.0, 1.0), (1500.0, 500.0, 0.6)))
    starts = (0.00, 0.17, 0.34, 0.52) if variant == 0 else (0.00, 0.14, 0.30, 0.43, 0.60)
    f0 = 330.0 + 40.0 * variant

    def f(t):
        value = 0.0
        for index, start in enumerate(starts):
            if start <= t < start + 0.11:
                value = cluck_sample(voice, noise, t - start, f0 * (1.0 + 0.1 * (index % 2)), 0.11)
        # a longer, rising "baaack" at the end
        if t >= starts[-1] + 0.12:
            local = t - starts[-1] - 0.12
            if local < 0.2:
                pitch = lerp(f0 * 0.95, f0 * 1.5, local / 0.2)
                value = voice.sample(pitch) * smooth(local, 0.0, 0.01) * decay(local, 8.0) * 0.9
        return value
    return render(length, f)


def make_food_call(variant):
    # Quick soft clucks in a row, getting a little higher, as the rooster calls the hens to a find.
    length = 1.2
    noise = Noise(30 + variant)
    voice = Voice(((800.0, 350.0, 1.0), (1800.0, 600.0, 0.5)))
    count = 7 + variant
    gap = 0.14

    def f(t):
        index = int(t / gap)
        if index >= count:
            return 0.0
        local = t - index * gap
        if local > 0.09:
            return 0.0
        f0 = 380.0 * (1.0 + 0.045 * index) * (1.0 + 0.06 * variant)
        return cluck_sample(voice, noise, local, f0, 0.09) * (0.7 + 0.3 * (index == count - 1))
    return render(length, f)


def make_peep(variant):
    length = 0.7
    voice = Voice(((3000.0, 900.0, 1.0), (4500.0, 700.0, 0.3)), count=6)
    starts = (0.0, 0.2, 0.38) if variant == 0 else (0.0, 0.16, 0.30, 0.46)

    def f(t):
        value = 0.0
        for index, start in enumerate(starts):
            local = t - start
            if 0.0 <= local < 0.1:
                x = local / 0.1
                pitch = 2600.0 * (1.0 + 0.08 * variant) * (1.0 + 0.35 * math.sin(math.pi * x)) - 400.0 * x
                value = voice.sample(pitch) * math.sin(math.pi * x) ** 0.7 * (1.0 - 0.1 * index)
        return value
    return render(length, f, 0.7)


def make_egg_crack(variant):
    length = 0.6
    noise = Noise(50 + variant)
    ticks = [0.0, 0.08, 0.15, 0.25, 0.31] if variant == 0 else [0.0, 0.1, 0.18, 0.22, 0.34]
    jitter = random.Random(60 + variant)
    shapes = [(jitter.uniform(2400.0, 5200.0), jitter.uniform(160.0, 320.0)) for _ in ticks]
    state = {"phase": [0.0 for _ in ticks]}

    def f(t):
        value = 0.0
        for index, start in enumerate(ticks):
            local = t - start
            if 0.0 <= local < 0.04:
                freq, rate = shapes[index]
                state["phase"][index] += TAU * freq / RATE
                value += math.sin(state["phase"][index]) * decay(local, rate) * (0.9 - 0.1 * index)
        # the shell crumbling at the end
        if t > 0.33:
            local = t - 0.33
            value += noise.white() * decay(local, 14.0) * 0.35 * (1.0 if noise.random.random() < 0.15 else 0.0)
        return value
    return render(length, f, 0.7)


FAMILIES = (
    ("Crow", make_crow),
    ("Cluck", make_cluck),
    ("FoodCall", make_food_call),
    ("Peep", make_peep),
    ("EggCrack", make_egg_crack),
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
        for family, make in FAMILIES:
            target_dir = os.path.join(ROOT, "sounds", "Spatial", "Rooms", "Hatchery", family)
            os.makedirs(target_dir, exist_ok=True)
            for variant in range(2):
                wav_path = os.path.join(folder, "%s%d.wav" % (family, variant))
                write_wav(wav_path, make(variant))
                target = os.path.join(target_dir, "%s%02d.ogg" % (family, variant + 1))
                subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
                                       "-c:a", "libvorbis", "-q:a", "3", target])
                print("wrote", os.path.relpath(target, ROOT), os.path.getsize(target), "bytes")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
