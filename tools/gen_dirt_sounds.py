#!/usr/bin/env python3
"""Synthesizes the sounds of relieving oneself, cleaning and the toilet room and writes them as .ogg files.

    python tools/gen_dirt_sounds.py

Same method as tools/gen_spell_sounds.py: sine waves, noise and simple envelopes only (no recordings, no
samples), fixed random seeds, so the same files come out every time. ffmpeg (libvorbis) must be in the PATH.
Files go to
    sounds/Spatial/Creatures/Default/Relieve/FxRelieve01.ogg   a short comic plop
    sounds/Spatial/Creatures/Default/Clean/FxClean01.ogg       scrubbing strokes
    sounds/Spatial/Rooms/Toilet/Flush/FxToiletFlush01.ogg      rushing water and a gurgle
    sounds/Spatial/Rooms/Toilet/Drip/FxToiletDrip01.ogg        a single water drop (played now and then as ambience)
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile

from gen_spell_sounds import TAU, Noise, decay, envelope, render, sweep_phase, write_wav

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scaled(samples, gain):
    """Returns the samples multiplied by a gain (render() normalises every sound, this keeps quiet ones quiet)."""
    return [s * gain for s in samples]


def bubble(t, start, f0, f1, rate):
    """A rising bubble tone that starts at the time `start` and dies away."""
    if t < start:
        return 0.0
    local = t - start
    return math.sin(sweep_phase(f0, f1, 0.12, min(local, 0.12)) + (local - min(local, 0.12)) * TAU * f1) \
        * decay(local, rate) * min(1.0, local / 0.003)


def make_relieve():
    """A short comic plop: two bubbles, the second smaller and higher, with a little wet noise."""
    length = 0.55
    noise = Noise(701)

    def f(t):
        value = bubble(t, 0.0, 240.0, 620.0, 9.0) + 0.55 * bubble(t, 0.17, 380.0, 900.0, 14.0)
        value += noise.lowpass(0.8) * 0.18 * decay(t, 18.0)
        return value * envelope(t, length, 0.002, 0.08)
    return render(length, f)


def make_clean():
    """Scrubbing: dull noise swelling and fading at about seven strokes a second, a rough bristle layer on top."""
    length = 1.3
    noise = Noise(711)
    grit = Noise(712)

    def f(t):
        stroke = 0.5 + 0.5 * math.sin(TAU * 6.5 * t - 1.2)
        stroke = stroke ** 1.5
        body = noise.lowpass(0.55) * 1.4
        bristles = grit.white() * 0.35
        return (body + bristles) * stroke * envelope(t, length, 0.05, 0.25)
    return scaled(render(length, f), 0.7)


def make_flush():
    """Water rushing down: rising and falling noise, a gurgling tone that wobbles and a last glug."""
    length = 2.6
    noise = Noise(721)
    low = Noise(722)

    def f(t):
        swell = math.sin(math.pi * min(1.0, t / 2.0)) ** 0.8 if t < 2.0 else 0.0
        rush = noise.lowpass(0.35 + 0.4 * swell) * 2.0 * swell
        gurgle_hz = 150.0 + 40.0 * math.sin(TAU * 5.0 * t) + 25.0 * low.lowpass(0.9)
        gurgle = math.sin(TAU * gurgle_hz * t) * 0.35 * swell * (0.5 + 0.5 * math.sin(TAU * 9.0 * t))
        glug = bubble(t, 2.05, 160.0, 90.0, 7.0) * 0.8
        return (rush + gurgle + glug) * envelope(t, length, 0.04, 0.4)
    return render(length, f)


def make_drip():
    """One water drop: a quick rising ping with a faint echo."""
    length = 0.8

    def f(t):
        ping = bubble(t, 0.0, 900.0, 2100.0, 24.0) + 0.3 * bubble(t, 0.26, 800.0, 1800.0, 30.0)
        return ping * envelope(t, length, 0.001, 0.1)
    return scaled(render(length, f), 0.55)


SOUNDS = (
    (("Creatures", "Default"), "Relieve", "FxRelieve01.ogg", make_relieve),
    (("Creatures", "Default"), "Clean", "FxClean01.ogg", make_clean),
    (("Rooms", "Toilet"), "Flush", "FxToiletFlush01.ogg", make_flush),
    (("Rooms", "Toilet"), "Drip", "FxToiletDrip01.ogg", make_drip),
)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found in PATH")
        return 1
    folder = tempfile.mkdtemp()
    try:
        for parents, family, filename, make in SOUNDS:
            wav_path = os.path.join(folder, family + ".wav")
            write_wav(wav_path, make())
            target_dir = os.path.join(ROOT, "sounds", "Spatial", *(parents + (family,)))
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, filename)
            subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
                                   "-c:a", "libvorbis", "-q:a", "3", target])
            print("wrote", os.path.relpath(target, ROOT), os.path.getsize(target), "bytes")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
