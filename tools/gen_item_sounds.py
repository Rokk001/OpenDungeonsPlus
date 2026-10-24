#!/usr/bin/env python3
"""Synthesize original item and room sounds as mono 44.1 kHz Ogg Vorbis.

Uses the project's spell-sound helpers; no recordings or external samples.
Set FFMPEG to an existing executable if ffmpeg is not on PATH.
The optional --output-root writes directly to a private art archive first.
"""

import argparse
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import gen_spell_sounds as sound

ROOT = Path(__file__).resolve().parent.parent
RATE = 44100
sound.RATE = RATE
TAU = sound.TAU


# Render short metallic coin impacts followed by the creaking balance beam.
def make_deal():
    # Mix the coin impacts and scale resonance at elapsed time t.
    def sample(t):
        value = 0.0
        for start, frequency in ((0.0, 2210.0), (0.09, 2790.0), (0.17, 3170.0)):
            local = t - start
            if local >= 0.0:
                value += (math.sin(TAU * frequency * local)
                          + 0.35 * math.sin(TAU * frequency * 2.73 * local)) * sound.decay(local, 18.0)
        if t >= 0.27:
            local = t - 0.27
            value += 0.22 * math.sin(TAU * (185.0 * local + 16.0 * math.sin(TAU * 2.0 * local))) * sound.envelope(local, 0.73, 0.06, 0.3)
        return value
    return sound.render(1.0, sample)


# Make a hooded merchant's short, breathy chuckle using voiced syllables.
def make_giggle():
    noise = sound.Noise(210)
    # Shape each voiced chuckle syllable at elapsed time t.
    def sample(t):
        local = t % 0.2
        voice = math.sin(TAU * 138.0 * t + 0.8 * math.sin(TAU * 6.0 * t))
        voice += 0.3 * math.sin(TAU * 414.0 * t)
        return (voice + 0.25 * noise.lowpass(0.5)) * sound.envelope(local, 0.2, 0.02, 0.11) * sound.envelope(t, 0.8, 0.02, 0.15)
    return sound.render(0.8, sample)


# Form a quiet, wordless haggle from dark resonances and breath noise.
def make_haggle():
    noise = sound.Noise(211)
    # Mix the wordless voice and breath at elapsed time t.
    def sample(t):
        syllable = 0.35 + 0.65 * math.sin(TAU * 2.5 * t) ** 2
        voice = math.sin(TAU * 112.0 * t + 0.9 * math.sin(TAU * 3.0 * t))
        voice += 0.25 * math.sin(TAU * 338.0 * t)
        return (voice * 0.55 + noise.lowpass(0.88) * 0.65) * syllable * sound.envelope(t, 1.4, 0.12, 0.3)
    return sound.render(1.4, sample)


# Render bubbling liquid with a quiet endpoint for seamless repetition.
def make_bubble():
    noise = sound.Noise(212)
    # Mix rising liquid bubbles at elapsed time t.
    def sample(t):
        local = t % 0.37
        bubble = math.sin(TAU * (105.0 * local + 180.0 * local * local)) * sound.decay(local, 17.0)
        bubble += 0.4 * math.sin(TAU * 65.0 * t) * math.sin(TAU * 3.5 * t)
        return (bubble + noise.lowpass(0.9) * 0.45) * sound.envelope(t, 4.0, 0.04, 0.04)
    return sound.render(4.0, sample)


# Synthesize escaping steam with a soft attack and a tapering tail.
def make_hiss():
    noise = sound.Noise(213)
    # Filter and envelope the steam at elapsed time t.
    def sample(t):
        return (noise.white() - noise.lowpass(0.9)) * sound.envelope(t, 1.2, 0.09, 0.8)
    return sound.render(1.2, sample)


# Create a cauldron pop followed by a resonant metal rattle.
def make_bang():
    noise = sound.Noise(214)
    # Mix the pressure pop and metallic tail at elapsed time t.
    def sample(t):
        pop = noise.white() * sound.decay(t, 32.0)
        metal = math.sin(TAU * 184.0 * t) + 0.45 * math.sin(TAU * 491.0 * t)
        return (pop + metal * 0.6 * sound.decay(t, 6.0)) * sound.envelope(t, 1.0, 0.001, 0.3)
    return sound.render(1.0, sample)


# Make a dry leaf rustle from modulated, filtered seeded noise.
def make_rustle():
    noise = sound.Noise(215)
    # Envelope the noisy leaf movements at elapsed time t.
    def sample(t):
        scratch = noise.white() - noise.lowpass(0.75)
        return scratch * (0.25 + 0.75 * math.sin(TAU * 8.0 * t) ** 2) * sound.envelope(t, 1.1, 0.12, 0.4)
    return sound.render(1.1, sample)


# Produce two rounded water drops falling into the trough.
def make_drip():
    # Sum the two decaying drops at elapsed time t.
    def sample(t):
        value = 0.0
        for start in (0.0, 0.4):
            local = t - start
            if local >= 0.0:
                value += math.sin(TAU * (1250.0 * local - 850.0 * local * local)) * sound.decay(local, 24.0)
        return value * sound.envelope(t, 0.8, 0.002, 0.2)
    return sound.render(0.8, sample)


# Give the subterranean garden a subdued, repeating insect-like hum.
def make_hum():
    # Modulate the garden drone at elapsed time t.
    def sample(t):
        tone = math.sin(TAU * 220.0 * t) + 0.25 * math.sin(TAU * 443.0 * t)
        return tone * (0.6 + 0.2 * math.sin(TAU * 5.0 * t)) * sound.envelope(t, 4.0, 0.04, 0.04)
    return sound.render(4.0, sample)


# Split a wooden gift box with a short crack and falling fragments.
def make_crack():
    noise = sound.Noise(216)
    # Sum the wood impact and fragments at elapsed time t.
    def sample(t):
        value = noise.white() * sound.decay(t, 42.0)
        value += noise.lowpass(0.8) * 2.2 * sound.decay(t, 13.0)
        value += math.sin(TAU * 126.0 * t) * sound.decay(t, 18.0) * 0.5
        return value * sound.envelope(t, 0.7, 0.001, 0.2)
    return sound.render(0.7, sample)


# Combine a cork pop with two liquid gulps, without recorded voices.
def make_drink():
    noise = sound.Noise(217)
    # Sequence the cork and gulps at elapsed time t.
    def sample(t):
        value = math.sin(TAU * (760.0 * t - 450.0 * t * t)) * sound.decay(t, 45.0)
        for start in (0.23, 0.49):
            local = t - start
            if 0.0 <= local < 0.22:
                value += (math.sin(TAU * (130.0 * local + 240.0 * local * local))
                          + noise.lowpass(0.8)) * sound.envelope(local, 0.22, 0.025, 0.16)
        return value * sound.envelope(t, 0.9, 0.001, 0.15)
    return sound.render(0.9, sample)


# Lift a cloth bag with a soft impact and a brief fabric scuff.
def make_pickup():
    noise = sound.Noise(218)
    # Mix the bag impact and cloth friction at elapsed time t.
    def sample(t):
        bump = math.sin(TAU * 88.0 * t) * sound.decay(t, 22.0)
        return (bump * 0.6 + noise.lowpass(0.55) * 0.4) * sound.envelope(t, 0.45, 0.01, 0.28)
    return sound.render(0.45, sample)


SOUNDS = (
    ("Rooms/Merchant/Deal", make_deal),
    ("Rooms/Merchant/Giggle", make_giggle),
    ("Rooms/Merchant/Haggle", make_haggle),
    ("Rooms/AlchemyLab/Bubble", make_bubble),
    ("Rooms/AlchemyLab/Hiss", make_hiss),
    ("Rooms/AlchemyLab/Bang", make_bang),
    ("Rooms/HerbGarden/Rustle", make_rustle),
    ("Rooms/HerbGarden/Drip", make_drip),
    ("Rooms/HerbGarden/Hum", make_hum),
    ("Rooms/Workshop/Crack", make_crack),
    ("Creatures/Default/Drink", make_drink),
    ("Creatures/Default/Pickup", make_pickup),
)


# Write the twelve original sound families, retaining each synthesis WAV.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        print("Set FFMPEG or put ffmpeg on PATH", file=sys.stderr)
        return 1
    for family, make in SOUNDS:
        directory = args.output_root / "sounds" / "Spatial" / family
        directory.mkdir(parents=True, exist_ok=True)
        stem = "Fx" + family.rsplit("/", 1)[1] + "01"
        wav_path = directory / (stem + ".wav")
        target = directory / (stem + ".ogg")
        sound.write_wav(str(wav_path), make())
        subprocess.run([ffmpeg, "-n", "-loglevel", "error", "-nostdin", "-i", str(wav_path),
                        "-map_metadata", "-1", "-ac", "1", "-ar", str(RATE),
                        "-c:a", "libvorbis", "-q:a", "3", str(target)],
                       check=True, stdin=subprocess.DEVNULL, timeout=60)
        print("wrote", target.relative_to(args.output_root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
