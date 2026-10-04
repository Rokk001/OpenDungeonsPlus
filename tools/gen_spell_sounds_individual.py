#!/usr/bin/env python3
"""Synthesizes an own sound for every spell (cast, and where it makes sense impact or end) as .ogg files.

    python tools/gen_spell_sounds_individual.py

Same method as tools/gen_spell_sounds.py: sine waves, saw waves, noise and simple envelopes only (no
recordings, no samples), fixed random seeds, so the same files come out every time. ffmpeg (libvorbis) must
be in the PATH. Files go to sounds/Spatial/Spells/<Family>/Fx<Family>01.ogg. The families are named after the
spell and the moment: <Spell>Cast (played with the cast message of the server), <Spell>Impact and <Spell>End
(started by config/roomAmbienceSpellsFx.cfg). The shared families of gen_spell_sounds.py stay as fallback.
"""

import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

from gen_spell_sounds import (RATE, TAU, Noise, decay, envelope, render, sweep_phase, write_wav)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def saw(phase, harmonics=8):
    """Band limited saw wave of a phase in radians."""
    return sum(math.sin(phase * h) / h for h in range(1, harmonics + 1)) * 0.6


def echo(samples, delay, gain, repeats):
    """Adds decaying copies of the sound, which makes a hall."""
    step = int(delay * RATE)
    out = list(samples) + [0.0] * (step * repeats)
    for r in range(1, repeats + 1):
        for i, s in enumerate(samples):
            out[i + step * r] += s * (gain ** r)
    return out


def normalise(samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    return [s / peak * 0.8 for s in samples]


def bell(t, freq, rate, partials=(1.0, 2.4, 3.9)):
    return sum(math.sin(TAU * freq * p * t) / (i + 1) for i, p in enumerate(partials)) * decay(t, rate)


# ---------------------------------------------------------------- Casts
def summon_worker_cast():
    length = 0.9
    noise = Noise(101)

    def f(t):
        rise = math.sin(sweep_phase(160.0, 520.0, length, t)) * min(1.0, t / 0.4) * 0.6
        hollow = noise.lowpass(0.85) * 1.2 * math.sin(math.pi * min(1.0, t / 0.7))
        pop = 0.0
        if t > 0.62:
            pop = math.sin(TAU * (700.0 - 800.0 * (t - 0.62)) * t) * decay(t - 0.62, 20.0) * 0.9
        return (rise + hollow * 0.4 + pop) * envelope(t, length, 0.03, 0.2)
    return render(length, f)


def call_to_war_cast():
    length = 1.1

    def f(t):
        base = 196.0 if t < 0.4 else 293.7
        vib = 1.0 + 0.006 * math.sin(TAU * 6.0 * t)
        local = t if t < 0.4 else t - 0.4
        swell = min(1.0, local / 0.06)
        return saw(TAU * base * vib * t, 10) * swell * envelope(t, length, 0.0, 0.35)
    return render(length, f)


def heal_cast():
    length = 1.2
    notes = (523.3, 659.3, 784.0, 1046.5)

    def f(t):
        value = 0.0
        for i, n in enumerate(notes):
            start = i * 0.14
            if t >= start:
                local = t - start
                vib = 1.0 + 0.004 * math.sin(TAU * 5.0 * local)
                value += ((math.sin(TAU * n * vib * local) + 0.25 * math.sin(TAU * n * 3.0 * local))
                          * decay(local, 2.6) * min(1.0, local / 0.02))
        return value
    return render(length, f)


def explosion_cast():
    length = 0.6
    noise = Noise(103)

    def f(t):
        whine = math.sin(sweep_phase(260.0, 1500.0, length, t)) * (t / length) ** 1.5
        air = noise.lowpass(0.5) * (t / length) * 0.6
        return (whine * 0.7 + air) * envelope(t, length, 0.02, 0.05)
    return render(length, f)


def haste_cast():
    length = 0.5
    noise = Noise(104)

    def f(t):
        centre = 0.35 + 0.6 * (t / length)
        air = (noise.lowpass(1.0 - centre) - noise.lowpass(0.5)) * 2.0
        tone = math.sin(sweep_phase(420.0, 1800.0, length, t)) * 0.35
        return (air + tone) * envelope(t, length, 0.02, 0.25)
    return render(length, f)


def defense_cast():
    length = 0.8
    noise = Noise(105)

    def f(t):
        clank = bell(t, 330.0, 5.0, (1.0, 2.76, 5.4, 8.9))
        tick = noise.white() * decay(t, 90.0)
        hum = math.sin(TAU * 165.0 * t) * decay(t, 3.0) * 0.4
        return clank * 0.8 + tick * 0.6 + hum
    return render(length, f)


def slow_cast():
    length = 1.1
    noise = Noise(106)

    def f(t):
        drop = math.sin(sweep_phase(300.0, 85.0, length, t) + 2.5 * math.sin(TAU * 3.0 * t))
        wob = 0.65 + 0.35 * math.sin(TAU * 4.0 * t)
        return (drop * 0.8 + noise.lowpass(0.97) * 2.0) * wob * envelope(t, length, 0.05, 0.5)
    return render(length, f)


def strength_cast():
    length = 0.8

    def f(t):
        bend = 1.0 + 0.12 * min(1.0, t / 0.2)
        chord = (saw(TAU * 110.0 * bend * t) + saw(TAU * 165.0 * bend * t) + saw(TAU * 220.0 * bend * t)) / 3.0
        punch = math.sin(TAU * (90.0 - 60.0 * t) * t) * decay(t, 12.0)
        return (chord * 0.7 + punch) * envelope(t, length, 0.01, 0.4)
    return render(length, f)


def weak_cast():
    length = 1.0
    noise = Noise(108)

    def f(t):
        slide = sweep_phase(330.0, 247.0, length, t)
        sag = 1.0 + 0.02 * math.sin(TAU * 5.5 * t)
        tone = math.sin(slide * sag) * 0.6 + math.sin(slide * 1.19 * sag) * 0.35
        crackle = noise.white() * (1.0 if noise.random.random() < 0.015 else 0.0)
        return (tone + crackle * 0.6) * envelope(t, length, 0.03, 0.6)
    return render(length, f)


def eye_evil_cast():
    length = 1.2
    noise = Noise(109)

    def f(t):
        whisper = (noise.lowpass(0.2) - noise.lowpass(0.7)) * 3.0 * math.sin(math.pi * min(1.0, t / length))
        open_tone = 0.0
        if t > 0.5:
            open_tone = math.sin(sweep_phase(600.0, 2400.0, length, t)) * min(1.0, (t - 0.5) / 0.4) * decay(max(0.0, t - 0.9), 8.0)
        return (whisper * 0.7 + open_tone * 0.35) * (0.7 + 0.3 * math.sin(TAU * 9.0 * t))
    return render(length, f)


def gold_cast():
    length = 0.8
    noise = Noise(110)

    def f(t):
        value = bell(t, 1318.5, 7.0, (1.0, 2.0, 3.0))
        if t > 0.12:
            value += bell(t - 0.12, 1760.0, 6.0, (1.0, 2.0, 3.0)) * 0.8
        clink = noise.white() * decay(t, 120.0) * 0.5
        return value + clink
    return render(length, f)


def lightning_cast():
    length = 0.55
    noise = Noise(111)

    def f(t):
        gate = 1.0 if noise.random.random() < 0.55 else 0.25
        zap = math.sin(sweep_phase(3200.0, 220.0, length, t)) * decay(t, 4.0)
        return (zap * 0.6 + noise.white() * gate * decay(t, 6.0) * 0.8) * min(1.0, t / 0.004)
    return render(length, f)


def tremor_cast():
    length = 1.3
    noise = Noise(112)

    def f(t):
        swell = (t / length) ** 0.8
        grind = noise.lowpass(0.97) * 6.0
        low = math.sin(TAU * (36.0 + 10.0 * t) * t) * 0.9
        scrape = noise.white() * (1.0 if noise.random.random() < 0.01 else 0.0) * 0.8
        return (grind + low + scrape) * swell * envelope(t, length, 0.0, 0.25)
    return render(length, f)


def defector_cast():
    length = 1.0

    def f(t):
        carrier = sweep_phase(340.0, 190.0, length, t)
        ring = math.sin(carrier) * math.sin(TAU * (47.0 + 20.0 * t) * t)
        sour = math.sin(carrier * 1.414) * 0.4
        return (ring * 0.9 + sour) * envelope(t, length, 0.04, 0.4)
    return render(length, f)


def hexen_hen_cast():
    length = 0.7

    def f(t):
        value = 0.0
        for start in (0.0, 0.2, 0.4):
            if t >= start:
                local = t - start
                if local < 0.15:
                    freq = 520.0 + 380.0 * math.sin(math.pi * local / 0.15) - 200.0 * local
                    value += (math.sin(TAU * freq * local + 6.0 * math.sin(TAU * 30.0 * local))
                              * math.sin(math.pi * local / 0.15))
        return value * 0.8 + math.sin(TAU * (1400.0 - 2400.0 * t) * t) * decay(t, 18.0) * 0.4
    return render(length, f)


def inferno_cast():
    length = 1.5
    noise = Noise(114)

    def f(t):
        swell = math.sin(math.pi * min(1.0, t / length)) ** 0.7
        roar = noise.lowpass(0.88) * 4.5
        growl = math.sin(TAU * 62.0 * t + 4.0 * math.sin(TAU * 7.0 * t)) * 0.8
        crackle = noise.white() * (1.0 if noise.random.random() < 0.03 else 0.0)
        return (roar + growl + crackle * 1.5) * swell
    return render(length, f)


def possess_cast():
    length = 1.2

    def f(t):
        slide = sweep_phase(220.0, 440.0, length, t)
        tone = math.sin(slide) + math.sin(slide * 1.0068) + 0.3 * math.sin(slide * 2.0)
        return tone * envelope(t, length, 0.1, 0.2) * (0.8 + 0.2 * math.sin(TAU * 6.0 * t))
    return normalise(echo(render(length, f), 0.17, 0.5, 4))


def champion_cast():
    length = 1.3
    noise = Noise(116)

    def f(t):
        value = 0.0
        for i, n in enumerate((261.6, 329.6, 392.0)):
            start = i * 0.18
            if t >= start:
                value += saw(TAU * n * t, 9) * min(1.0, (t - start) / 0.04) * 0.5
        value *= envelope(t, length, 0.0, 0.5)
        if t > 0.45:
            value += noise.white() * decay(t - 0.45, 6.0) * 0.12
        return value
    return render(length, f)


# ---------------------------------------------------------------- Impacts
def explosion_impact():
    length = 1.6
    noise = Noise(121)

    def f(t):
        crack = noise.white() * decay(t, 25.0)
        boom = math.sin(TAU * (55.0 - 25.0 * min(t, 0.8)) * t) * decay(t, 3.0) * 1.2
        rumble = noise.lowpass(0.96) * 6.0 * decay(t, 2.0)
        debris = noise.white() * (1.0 if noise.random.random() < 0.004 else 0.0) * decay(t, 2.5)
        return crack * 0.8 + boom + rumble * 0.7 + debris
    return render(length, f)


def lightning_impact():
    length = 1.6
    noise = Noise(122)

    def f(t):
        crack = noise.white() * decay(t, 60.0)
        sizzle = noise.white() * decay(t, 10.0) * 0.2 * (1.0 if noise.random.random() < 0.5 else 0.1)
        thunder = noise.lowpass(0.97) * 7.0 * decay(max(0.0, t - 0.05), 1.8) * min(1.0, t / 0.08)
        return crack * 1.2 + sizzle + thunder
    return render(length, f)


def tremor_impact():
    length = 1.1
    noise = Noise(123)
    rng = random.Random(1230)
    hits = sorted(rng.uniform(0.0, 0.8) for _ in range(9))

    def f(t):
        value = 0.0
        for h in hits:
            if t >= h:
                value += noise.lowpass(0.8) * decay(t - h, 30.0) * 3.0
        return value + math.sin(TAU * 44.0 * t) * decay(t, 3.5)
    return render(length, f)


def inferno_impact():
    length = 1.0
    noise = Noise(124)

    def f(t):
        thump = math.sin(TAU * (90.0 - 50.0 * t) * t) * decay(t, 7.0)
        whoosh = noise.lowpass(0.8) * 3.0 * decay(t, 4.0)
        sizzle = noise.white() * (1.0 if noise.random.random() < 0.06 else 0.0) * decay(t, 2.0)
        return thump + whoosh + sizzle * 0.8
    return render(length, f)


def gold_impact():
    length = 1.0
    rng = random.Random(1250)
    times = sorted(rng.uniform(0.0, 0.6) for _ in range(7))
    freqs = [rng.choice((1976.0, 2349.0, 2637.0, 3136.0, 2093.0)) for _ in times]

    def f(t):
        value = 0.0
        for start, freq in zip(times, freqs):
            if t >= start:
                value += bell(t - start, freq, 14.0, (1.0, 2.7)) * 0.7
        return value
    return render(length, f)


def heal_impact():
    length = 0.7

    def f(t):
        freq = 880.0 * (2.0 ** (2.0 * min(1.0, t / 0.5)))
        tone = math.sin(TAU * freq * t) * 0.5 + math.sin(TAU * freq * 1.5 * t) * 0.25
        return tone * decay(t, 4.0) * envelope(t, length, 0.01, 0.3)
    return render(length, f)


def haste_impact():
    length = 0.3
    noise = Noise(127)

    def f(t):
        tick = noise.white() * decay(t, 70.0)
        zip_tone = math.sin(sweep_phase(900.0, 3000.0, length, t)) * decay(t, 12.0)
        return tick * 0.5 + zip_tone
    return render(length, f)


# ---------------------------------------------------------------- Ends
def possess_end():
    length = 1.2

    def f(t):
        slide = sweep_phase(440.0, 110.0, length, t)
        return (math.sin(slide) + math.sin(slide * 1.0068)) * envelope(t, length, 0.02, 0.5)
    return normalise(echo(render(length, f), 0.15, 0.45, 4))


def defector_end():
    length = 0.9

    def f(t):
        slide = sweep_phase(190.0, 380.0, length, t)
        resolve = math.sin(slide) * (1.0 - t / length) * math.sin(TAU * (47.0 - 40.0 * t / length) * t)
        chime = bell(t - 0.5, 880.0, 6.0, (1.0, 2.0)) * 0.8 if t > 0.5 else 0.0
        return (resolve * 0.8 + chime) * envelope(t, length, 0.03, 0.3)
    return render(length, f)


def hexen_hen_end():
    length = 0.8
    noise = Noise(130)

    def f(t):
        pop = math.sin(TAU * (800.0 - 1400.0 * t) * t) * decay(t, 25.0)
        poof = noise.lowpass(0.9) * 3.0 * decay(max(0.0, t - 0.03), 6.0)
        cluck = 0.0
        if t > 0.45:
            local = t - 0.45
            cluck = (math.sin(TAU * (260.0 + 160.0 * math.sin(math.pi * local / 0.2)) * local)
                     * math.sin(math.pi * min(1.0, local / 0.2)))
        return pop * 0.8 + poof * 0.6 + cluck * 0.5
    return render(length, f)


SOUNDS = (
    ("SummonWorkerCast", summon_worker_cast),
    ("CallToWarCast", call_to_war_cast),
    ("HealCast", heal_cast),
    ("ExplosionCast", explosion_cast),
    ("HasteCast", haste_cast),
    ("DefenseCast", defense_cast),
    ("SlowCast", slow_cast),
    ("StrengthCast", strength_cast),
    ("WeakCast", weak_cast),
    ("EyeEvilCast", eye_evil_cast),
    ("GoldCast", gold_cast),
    ("LightningCast", lightning_cast),
    ("TremorCast", tremor_cast),
    ("DefectorCast", defector_cast),
    ("HexenHenCast", hexen_hen_cast),
    ("InfernoCast", inferno_cast),
    ("PossessCast", possess_cast),
    ("ChampionCast", champion_cast),
    ("ExplosionImpact", explosion_impact),
    ("LightningImpact", lightning_impact),
    ("TremorImpact", tremor_impact),
    ("InfernoImpact", inferno_impact),
    ("GoldImpact", gold_impact),
    ("HealImpact", heal_impact),
    ("HasteImpact", haste_impact),
    ("PossessEnd", possess_end),
    ("DefectorEnd", defector_end),
    ("HexenHenEnd", hexen_hen_end),
)


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
