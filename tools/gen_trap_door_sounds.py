#!/usr/bin/env python3
"""Synthesizes the short sounds of the traps and doors and writes them as .ogg files.

    python tools/gen_trap_door_sounds.py

Same method as tools/gen_spell_sounds.py: sine waves, noise and simple envelopes only (no recordings, no
samples), fixed random seeds, so the same files come out every time. ffmpeg (libvorbis) must be in the PATH.
Files go to
    sounds/Spatial/Traps/<Type>/<Role>/Fx<Type><Role>01.ogg   (Fire, Idle, Reload, Sold)
    sounds/Spatial/Doors/<Type>/<Role>/Fx<Type><Role>01.ogg   (Open, Close, Hit, Break, Sold)
The cannon already has a firing sound, so it only gets Idle and Reload.
"""

import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

from gen_spell_sounds import TAU, Noise, decay, envelope, render, sweep_phase, write_wav

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def swell(t, length):
    return math.sin(math.pi * min(1.0, max(0.0, t / length)))


def ring(t, start, freq, rate, partials=(1.0, 2.76, 5.4)):
    """A struck metal or glass body: a few inharmonic partials that die away."""
    if t < start:
        return 0.0
    local = t - start
    value = 0.0
    for index, part in enumerate(partials):
        value += math.sin(TAU * freq * part * local) / (1.0 + index)
    return value * decay(local, rate)


def thump(t, start, f0, f1, rate):
    """A short low knock whose pitch falls from f0 to f1."""
    if t < start:
        return 0.0
    local = t - start
    return math.sin(TAU * (f1 + (f0 - f1) * math.exp(-30.0 * local)) * local) * decay(local, rate)


def times(seed, count, low, high):
    rng = random.Random(seed)
    return sorted(rng.uniform(low, high) for _ in range(count))


def clicks(t, starts, freq, rate):
    value = 0.0
    for start in starts:
        if t >= start:
            local = t - start
            value += math.sin(TAU * freq * local) * decay(local, rate)
    return value


# ------------------------------------------------------------------ traps

def spike_fire():
    length = 0.45
    noise = Noise(101)

    def f(t):
        shing = noise.white() * decay(t, 14.0) * min(1.0, t / 0.004) * 0.5
        metal = ring(t, 0.0, 2300.0, 9.0) * 0.5 + ring(t, 0.03, 3100.0, 12.0) * 0.3
        return shing + metal + thump(t, 0.0, 180.0, 70.0, 14.0) * 0.6
    return render(length, f)


def spike_idle():
    length = 0.3
    noise = Noise(102)

    def f(t):
        return (noise.white() * decay(t, 30.0) * 0.4 + ring(t, 0.0, 3400.0, 30.0, (1.0,))) * 0.5
    return render(length, f)


def spike_reload():
    length = 0.7
    noise = Noise(103)

    def f(t):
        e = swell(t, length)
        return noise.lowpass(0.55 + 0.3 * (t / length)) * 3.0 * e + thump(t, length - 0.12, 140.0, 70.0, 20.0) * 0.8
    return render(length, f)


def cannon_idle():
    length = 0.9
    noise = Noise(104)

    def f(t):
        e = swell(t, length)
        grind = math.sin(sweep_phase(80.0, 55.0, length, t)) * 0.5 * (0.7 + 0.3 * math.sin(TAU * 17.0 * t))
        return (noise.lowpass(0.93) * 3.0 + grind) * e
    return render(length, f)


def cannon_reload():
    length = 0.8
    noise = Noise(105)

    def f(t):
        clack = ring(t, 0.0, 900.0, 18.0, (1.0, 2.4)) + ring(t, 0.28, 700.0, 18.0, (1.0, 2.4)) * 0.8
        hiss = noise.white() * decay(max(0.0, t - 0.4), 5.0) * (1.0 if t > 0.4 else 0.0) * 0.25
        return clack * 0.7 + hiss
    return render(length, f)


def boulder_fire():
    length = 1.6
    noise = Noise(106)
    knocks = times(107, 9, 0.1, 1.4)

    def f(t):
        e = swell(t, length) ** 0.6
        rumble = noise.lowpass(0.95) * 6.0 * e
        roll = math.sin(TAU * 38.0 * t) * 0.5 * e * (0.6 + 0.4 * math.sin(TAU * 4.0 * t))
        stones = sum(thump(t, k, 200.0, 60.0, 16.0) for k in knocks) * 0.4
        return rumble + roll + stones
    return render(length, f)


def boulder_idle():
    length = 0.5
    noise = Noise(108)

    def f(t):
        return (noise.lowpass(0.9) * 4.0 * swell(t, length) + thump(t, 0.2, 150.0, 70.0, 22.0) * 0.5)
    return render(length, f)


def boulder_reload():
    length = 0.9
    noise = Noise(109)
    drops = times(110, 6, 0.05, 0.7)

    def f(t):
        return thump(t, 0.0, 120.0, 45.0, 9.0) + sum(clicks(t, [d], 500.0 + 700.0 * (i % 3), 40.0) for i, d in enumerate(drops)) * 0.3 \
            + noise.lowpass(0.9) * 2.0 * decay(t, 4.0)
    return render(length, f)


def alarm_fire():
    length = 1.4

    def f(t):
        slot = int(t / 0.28)
        freq = 880.0 if slot % 2 == 0 else 660.0
        local = t - slot * 0.28
        gate = min(1.0, local / 0.01) * min(1.0, (0.28 - local) / 0.03)
        tone = math.sin(TAU * freq * t) + 0.5 * math.sin(TAU * freq * 2.0 * t) + 0.3 * math.sin(TAU * freq * 3.0 * t)
        return tone * gate * envelope(t, length, 0.0, 0.2)
    return render(length, f)


def alarm_idle():
    length = 0.25

    def f(t):
        return math.sin(TAU * 1250.0 * t) * min(1.0, t / 0.01) * decay(t, 14.0)
    return render(length, f)


def alarm_reload():
    length = 0.5

    def f(t):
        return math.sin(sweep_phase(900.0, 350.0, length, t)) * envelope(t, length, 0.01, 0.25)
    return render(length, f)


def fear_fire():
    length = 1.5
    noise = Noise(111)

    def f(t):
        vib = 1.0 + 0.04 * math.sin(TAU * 6.0 * t)
        wail = math.sin(sweep_phase(520.0, 190.0, length, t) * vib) + 0.5 * math.sin(sweep_phase(780.0, 285.0, length, t) * vib)
        return (wail * 0.6 + noise.lowpass(0.7) * 0.8) * swell(t, length) ** 0.7
    return render(length, f)


def fear_idle():
    length = 1.1
    noise = Noise(112)

    def f(t):
        murmur = noise.lowpass(0.6) * (0.5 + 0.5 * math.sin(TAU * 4.5 * t)) * (0.5 + 0.5 * math.sin(TAU * 1.7 * t))
        return murmur * swell(t, length) * 2.0
    return render(length, f)


def fear_reload():
    length = 1.0
    noise = Noise(113)

    def f(t):
        return (math.sin(sweep_phase(260.0, 120.0, length, t)) * 0.5 + noise.lowpass(0.9) * 1.5) * swell(t, length)
    return render(length, f)


def gas_fire():
    length = 1.3
    noise = Noise(114)

    def f(t):
        hiss = noise.white() - noise.lowpass(0.5)
        return hiss * swell(t, length) ** 0.5 * min(1.0, t / 0.03) * 1.5
    return render(length, f)


def gas_idle():
    length = 0.9
    pops = times(115, 7, 0.05, 0.8)

    def f(t):
        value = 0.0
        for index, start in enumerate(pops):
            if t >= start:
                local = t - start
                freq = 300.0 + 90.0 * (index % 4) + 500.0 * local
                value += math.sin(TAU * freq * local) * decay(local, 30.0)
        return value
    return render(length, f)


def gas_reload():
    length = 0.8
    noise = Noise(116)

    def f(t):
        hiss = (noise.white() - noise.lowpass(0.5)) * decay(t, 6.0) * 0.8
        return hiss + thump(t, 0.5, 130.0, 70.0, 20.0) * 0.9
    return render(length, f)


def lightning_fire():
    length = 1.0
    noise = Noise(117)

    def f(t):
        zap = noise.white() * decay(t, 35.0)
        buzz = math.sin(TAU * 120.0 * t) * math.sin(TAU * 2900.0 * t) * decay(t, 9.0) * 0.6
        boom = noise.lowpass(0.95) * 5.0 * decay(t, 3.0) * min(1.0, t / 0.04)
        return zap + buzz + boom
    return render(length, f)


def lightning_idle():
    length = 0.7
    rng = random.Random(118)
    sparks = sorted(rng.uniform(0.02, 0.6) for _ in range(10))

    def f(t):
        return clicks(t, sparks, 3800.0, 220.0) * 0.6 + math.sin(TAU * 100.0 * t) * 0.1 * swell(t, length)
    return render(length, f)


def lightning_reload():
    length = 0.9

    def f(t):
        whine = math.sin(sweep_phase(2400.0, 500.0, length, t)) * decay(t, 3.0)
        return whine * 0.5 * math.sin(TAU * 55.0 * t) + whine * 0.3
    return render(length, f)


def fireburst_fire():
    length = 1.3
    noise = Noise(119)

    def f(t):
        sweep = 0.97 - 0.4 * min(1.0, t / 0.4)
        whoosh = noise.lowpass(sweep) * 5.0 * min(1.0, t / 0.05) * decay(t, 1.8)
        crackle = noise.white() * (1.0 if noise.random.random() < 0.015 else 0.0) * 1.2 * decay(t, 2.0)
        return whoosh + crackle + thump(t, 0.0, 110.0, 50.0, 8.0) * 0.8
    return render(length, f)


def fireburst_idle():
    length = 0.8
    rng = random.Random(120)
    pops = sorted(rng.uniform(0.02, 0.7) for _ in range(8))
    noise = Noise(121)

    def f(t):
        return clicks(t, pops, 1500.0, 140.0) * 0.5 + noise.lowpass(0.97) * 2.0 * swell(t, length)
    return render(length, f)


def fireburst_reload():
    length = 0.9
    noise = Noise(122)

    def f(t):
        tick = clicks(t, [0.3, 0.55, 0.78], 2500.0, 80.0) * 0.4
        return (noise.white() - noise.lowpass(0.6)) * decay(t, 5.0) * 0.6 + tick
    return render(length, f)


def freeze_fire():
    length = 1.2
    noise = Noise(123)
    chips = times(124, 6, 0.0, 0.25)

    def f(t):
        crack = noise.white() * decay(t, 45.0)
        shards = sum(ring(t, c, 2600.0 + 450.0 * i, 14.0, (1.0, 1.7, 2.9)) for i, c in enumerate(chips)) * 0.25
        mist = (noise.white() - noise.lowpass(0.5)) * swell(t, length) * 0.25
        return crack + shards + mist
    return render(length, f)


def freeze_idle():
    length = 1.0

    def f(t):
        return ring(t, 0.0, 3300.0, 6.0, (1.0, 1.5)) * 0.5 + ring(t, 0.35, 4200.0, 7.0, (1.0, 1.5)) * 0.35
    return render(length, f)


def freeze_reload():
    length = 1.2

    def f(t):
        value = 0.0
        for index, freq in enumerate((1568.0, 1976.0, 2349.0)):
            value += ring(t, 0.25 * index, freq, 5.0, (1.0, 2.0))
        return value * 0.5 * envelope(t, length, 0.0, 0.3)
    return render(length, f)


def banner_fire():
    length = 1.0
    noise = Noise(125)

    def f(t):
        flap = noise.white() * (abs(math.sin(TAU * 7.0 * t)) ** 3) * decay(t, 2.5)
        horn = (math.sin(TAU * 196.0 * t) + 0.5 * math.sin(TAU * 392.0 * t)) * envelope(t, length, 0.05, 0.5) * 0.4
        return flap * 0.8 + horn
    return render(length, f)


def banner_idle():
    length = 1.0
    noise = Noise(126)

    def f(t):
        gust = (0.5 + 0.5 * math.sin(TAU * 3.0 * t)) * (0.5 + 0.5 * math.sin(TAU * 0.9 * t + 1.0))
        return noise.lowpass(0.8) * 3.0 * gust * swell(t, length)
    return render(length, f)


def trigger_fire():
    length = 1.0

    def f(t):
        value = ring(t, 0.0, 660.0, 4.0, (1.0, 2.0, 3.0)) + ring(t, 0.12, 990.0, 4.0, (1.0, 2.0, 3.0))
        shimmer = math.sin(TAU * 2640.0 * t) * math.sin(TAU * 9.0 * t) * decay(t, 3.0) * 0.2
        return value * 0.6 + shimmer
    return render(length, f)


def trigger_idle():
    length = 1.0

    def f(t):
        return math.sin(TAU * 220.0 * t) * (0.7 + 0.3 * math.sin(TAU * 5.0 * t)) * swell(t, length) \
            + 0.3 * math.sin(TAU * 330.0 * t) * swell(t, length)
    return render(length, f)


def trigger_reload():
    length = 0.5

    def f(t):
        return ring(t, 0.0, 440.0, 14.0, (1.0, 2.0)) * 0.6 + ring(t, 0.15, 330.0, 14.0, (1.0, 2.0)) * 0.4
    return render(length, f)


# ------------------------------------------------------------------ doors

def creak(t, length, f0, f1, seed_phase=0.0):
    """Wood or hinge creak: a sliding tone with an uneven, stuttering amplitude."""
    stutter = 0.6 + 0.4 * math.sin(TAU * 23.0 * t + seed_phase) * math.sin(TAU * 9.0 * t)
    return math.sin(sweep_phase(f0, f1, length, t)) * stutter * envelope(t, length, 0.05, 0.2)


def wood_open():
    length = 1.1
    noise = Noise(131)

    def f(t):
        return creak(t, length, 180.0, 330.0) * 0.7 + creak(t, length, 360.0, 640.0, 1.0) * 0.3 + noise.lowpass(0.8) * 0.4 * swell(t, length)
    return render(length, f)


def wood_close():
    length = 1.0
    noise = Noise(132)

    def f(t):
        return creak(t, 0.7, 330.0, 170.0) * (1.0 if t < 0.7 else 0.0) * 0.6 + thump(t, 0.7, 150.0, 60.0, 12.0) \
            + noise.white() * decay(max(0.0, t - 0.7), 40.0) * (1.0 if t > 0.7 else 0.0) * 0.4
    return render(length, f)


def wood_hit():
    length = 0.4
    noise = Noise(133)

    def f(t):
        return thump(t, 0.0, 220.0, 110.0, 16.0) + ring(t, 0.0, 420.0, 20.0, (1.0, 1.6)) * 0.4 + noise.white() * decay(t, 70.0) * 0.4
    return render(length, f)


def wood_break():
    length = 1.4
    noise = Noise(134)
    cracks = times(135, 12, 0.0, 0.9)

    def f(t):
        splinters = sum(clicks(t, [c], 900.0 + 60.0 * i, 60.0) for i, c in enumerate(cracks)) * 0.35
        crash = noise.lowpass(0.7) * 3.0 * decay(t, 4.0) + thump(t, 0.0, 160.0, 50.0, 7.0) * 1.2
        return splinters + crash
    return render(length, f)


def iron_open():
    length = 1.2
    noise = Noise(136)

    def f(t):
        grind = creak(t, 0.9, 110.0, 190.0) * 0.5 + noise.lowpass(0.9) * 1.5 * swell(t, 0.9) * (1.0 if t < 0.9 else 0.0)
        return grind + ring(t, 0.95, 520.0, 9.0) * 0.8 + thump(t, 0.95, 120.0, 55.0, 10.0)
    return render(length, f)


def iron_close():
    length = 1.1

    def f(t):
        return thump(t, 0.0, 130.0, 50.0, 8.0) * 1.2 + ring(t, 0.0, 480.0, 8.0) + ring(t, 0.06, 760.0, 10.0, (1.0, 2.3)) * 0.5
    return render(length, f)


def iron_hit():
    length = 0.8
    noise = Noise(137)

    def f(t):
        return ring(t, 0.0, 610.0, 10.0) + thump(t, 0.0, 140.0, 70.0, 14.0) * 0.8 + noise.white() * decay(t, 60.0) * 0.5
    return render(length, f)


def iron_break():
    length = 1.6
    noise = Noise(138)
    clangs = times(139, 6, 0.0, 0.8)

    def f(t):
        rubble = noise.lowpass(0.75) * 3.0 * decay(t, 3.5)
        clang = sum(ring(t, c, 400.0 + 130.0 * i, 7.0) for i, c in enumerate(clangs)) * 0.4
        return rubble + clang + thump(t, 0.0, 120.0, 40.0, 6.0) * 1.2
    return render(length, f)


def steel_open():
    length = 1.4
    noise = Noise(140)

    def f(t):
        slide = noise.lowpass(0.65) * 2.5 * swell(t, 1.0) * (1.0 if t < 1.0 else 0.0)
        whine = math.sin(sweep_phase(300.0, 520.0, 1.0, t)) * 0.2 * swell(t, 1.0) * (1.0 if t < 1.0 else 0.0)
        return slide + whine + thump(t, 1.05, 90.0, 45.0, 9.0) * 1.2 + ring(t, 1.05, 700.0, 12.0, (1.0, 2.5)) * 0.4
    return render(length, f)


def steel_close():
    length = 1.3

    def f(t):
        return thump(t, 0.0, 100.0, 40.0, 7.0) * 1.5 + ring(t, 0.0, 330.0, 6.0, (1.0, 2.0, 3.1)) * 0.8
    return render(length, f)


def steel_hit():
    length = 1.2

    def f(t):
        return ring(t, 0.0, 330.0, 4.0, (1.0, 2.0, 2.76, 5.4)) + thump(t, 0.0, 110.0, 55.0, 12.0) * 0.8
    return render(length, f)


def steel_break():
    length = 1.9
    noise = Noise(141)
    rings = times(142, 5, 0.1, 1.0)

    def f(t):
        crash = noise.lowpass(0.6) * 3.5 * decay(t, 3.0) + thump(t, 0.0, 90.0, 35.0, 5.0) * 1.5
        metal = sum(ring(t, r, 300.0 + 90.0 * i, 5.0, (1.0, 2.76, 5.4)) for i, r in enumerate(rings)) * 0.3
        return crash + metal
    return render(length, f)


def barricade_hit():
    length = 0.5
    noise = Noise(143)

    def f(t):
        planks = clicks(t, [0.0, 0.05, 0.11], 260.0, 25.0) + clicks(t, [0.02, 0.09], 480.0, 40.0) * 0.6
        return planks + noise.lowpass(0.7) * decay(t, 20.0) * 1.5
    return render(length, f)


def barricade_break():
    length = 1.7
    noise = Noise(144)
    planks = times(145, 14, 0.0, 1.0)

    def f(t):
        clatter = sum(clicks(t, [p], 240.0 + 70.0 * (i % 5), 30.0) for i, p in enumerate(planks)) * 0.4
        return clatter + noise.lowpass(0.7) * 3.0 * decay(t, 3.5) + thump(t, 0.0, 140.0, 55.0, 6.0)
    return render(length, f)


def secret_open():
    length = 1.6
    noise = Noise(146)

    def f(t):
        grind = noise.lowpass(0.93) * 5.0 * swell(t, length) ** 0.7
        low = math.sin(TAU * 50.0 * t) * 0.5 * swell(t, length) * (0.7 + 0.3 * math.sin(TAU * 8.0 * t))
        return grind + low
    return render(length, f)


def secret_close():
    length = 1.3
    noise = Noise(147)

    def f(t):
        grind = noise.lowpass(0.93) * 4.0 * swell(t, 0.8) * (1.0 if t < 0.8 else 0.0)
        return grind + thump(t, 0.8, 100.0, 40.0, 8.0) * 1.3
    return render(length, f)


def secret_hit():
    length = 0.5
    noise = Noise(148)

    def f(t):
        return thump(t, 0.0, 120.0, 55.0, 14.0) + noise.lowpass(0.9) * 2.0 * decay(t, 18.0)
    return render(length, f)


def secret_break():
    length = 1.8
    noise = Noise(149)
    chunks = times(150, 10, 0.1, 1.2)

    def f(t):
        crumble = noise.lowpass(0.9) * 5.0 * decay(t, 2.5) * min(1.0, t / 0.03)
        rocks = sum(thump(t, c, 180.0, 70.0, 18.0) for c in chunks) * 0.35
        return crumble + rocks + thump(t, 0.0, 100.0, 35.0, 5.0) * 1.2
    return render(length, f)


def rune_open():
    length = 1.2

    def f(t):
        rise = math.sin(sweep_phase(300.0, 1400.0, length, t)) * 0.5 + math.sin(sweep_phase(450.0, 2100.0, length, t)) * 0.25
        shimmer = math.sin(TAU * 3200.0 * t) * math.sin(TAU * 13.0 * t) * 0.15
        return (rise + shimmer) * envelope(t, length, 0.05, 0.4) + ring(t, 1.0, 1568.0, 6.0, (1.0, 2.0)) * 0.3
    return render(length, f)


def rune_close():
    length = 1.0

    def f(t):
        fall = math.sin(sweep_phase(1400.0, 260.0, length, t)) * 0.5 + math.sin(sweep_phase(2100.0, 390.0, length, t)) * 0.25
        return fall * envelope(t, length, 0.02, 0.4) + thump(t, 0.85, 120.0, 60.0, 14.0) * 0.5
    return render(length, f)


def rune_hit():
    length = 0.6
    noise = Noise(151)

    def f(t):
        zap = noise.white() * decay(t, 35.0) * 0.6
        return zap + math.sin(TAU * 1800.0 * t) * math.sin(TAU * 70.0 * t) * decay(t, 9.0) * 0.6 + ring(t, 0.0, 900.0, 10.0, (1.0, 2.0)) * 0.4
    return render(length, f)


def rune_break():
    length = 1.6
    noise = Noise(152)
    shards = times(153, 12, 0.0, 0.5)

    def f(t):
        glass = sum(ring(t, s, 2000.0 + 380.0 * (i % 5), 12.0, (1.0, 1.7, 2.9)) for i, s in enumerate(shards)) * 0.25
        zap = noise.white() * decay(t, 20.0) * 0.5
        fizz = math.sin(sweep_phase(1800.0, 200.0, length, t)) * decay(t, 3.0) * 0.3
        return glass + zap + fizz + thump(t, 0.0, 120.0, 45.0, 8.0) * 0.8
    return render(length, f)


def door_sold():
    """A door taken down: a dull knock, a creak and a short clatter of planks and fittings."""
    length = 1.1
    noise = Noise(160)
    clatter = times(161, 6, 0.15, 0.7)

    def f(t):
        creak = math.sin(sweep_phase(260.0, 140.0, 0.4, min(t, 0.4))) * swell(t, 0.4) * 0.3 * (1.0 if t < 0.4 else 0.0)
        wood = sum(thump(t, c, 210.0, 90.0, 22.0) for c in clatter) * 0.4
        dust = noise.lowpass(0.9) * 2.0 * decay(t, 4.0) * min(1.0, t / 0.02)
        return creak + wood + dust * 0.6 + thump(t, 0.0, 140.0, 55.0, 9.0) * 0.9 + ring(t, 0.5, 1200.0, 20.0, (1.0, 2.3)) * 0.12
    return render(length, f)


def trap_sold():
    """A trap taken apart: a metallic clank, a spring release and a few loose parts falling."""
    length = 0.9
    noise = Noise(162)
    parts = times(163, 5, 0.1, 0.6)

    def f(t):
        clank = ring(t, 0.0, 1100.0, 14.0, (1.0, 2.4, 4.1)) * 0.4 + ring(t, 0.12, 760.0, 16.0, (1.0, 2.6)) * 0.3
        spring = math.sin(sweep_phase(900.0, 300.0, 0.25, min(t, 0.25))) * decay(t, 12.0) * 0.25
        bits = sum(ring(t, c, 1800.0 + 250.0 * i, 30.0, (1.0, 2.2)) for i, c in enumerate(parts)) * 0.15
        return clank + spring + bits + noise.white() * decay(t, 25.0) * 0.2 + thump(t, 0.0, 130.0, 60.0, 12.0) * 0.6
    return render(length, f)


TRAP_SOUNDS = (
    ("Spike", "Fire", spike_fire), ("Spike", "Idle", spike_idle), ("Spike", "Reload", spike_reload),
    ("Cannon", "Idle", cannon_idle), ("Cannon", "Reload", cannon_reload),
    ("Boulder", "Fire", boulder_fire), ("Boulder", "Idle", boulder_idle), ("Boulder", "Reload", boulder_reload),
    ("Alarm", "Fire", alarm_fire), ("Alarm", "Idle", alarm_idle), ("Alarm", "Reload", alarm_reload),
    ("Fear", "Fire", fear_fire), ("Fear", "Idle", fear_idle), ("Fear", "Reload", fear_reload),
    ("Gas", "Fire", gas_fire), ("Gas", "Idle", gas_idle), ("Gas", "Reload", gas_reload),
    ("Lightning", "Fire", lightning_fire), ("Lightning", "Idle", lightning_idle), ("Lightning", "Reload", lightning_reload),
    ("Fireburst", "Fire", fireburst_fire), ("Fireburst", "Idle", fireburst_idle), ("Fireburst", "Reload", fireburst_reload),
    ("Freeze", "Fire", freeze_fire), ("Freeze", "Idle", freeze_idle), ("Freeze", "Reload", freeze_reload),
    ("WatchBanner", "Fire", banner_fire), ("WatchBanner", "Idle", banner_idle),
    ("Trigger", "Fire", trigger_fire), ("Trigger", "Idle", trigger_idle), ("Trigger", "Reload", trigger_reload),
    ("Trap", "Sold", trap_sold),
)

DOOR_SOUNDS = (
    ("Wooden", "Open", wood_open), ("Wooden", "Close", wood_close), ("Wooden", "Hit", wood_hit), ("Wooden", "Break", wood_break),
    ("Ironbound", "Open", iron_open), ("Ironbound", "Close", iron_close), ("Ironbound", "Hit", iron_hit),
    ("Ironbound", "Break", iron_break),
    ("Steel", "Open", steel_open), ("Steel", "Close", steel_close), ("Steel", "Hit", steel_hit), ("Steel", "Break", steel_break),
    ("Barricade", "Hit", barricade_hit), ("Barricade", "Break", barricade_break),
    ("Secret", "Open", secret_open), ("Secret", "Close", secret_close), ("Secret", "Hit", secret_hit),
    ("Secret", "Break", secret_break),
    ("Runed", "Open", rune_open), ("Runed", "Close", rune_close), ("Runed", "Hit", rune_hit), ("Runed", "Break", rune_break),
    ("Door", "Sold", door_sold),
)


def write_group(ffmpeg, folder, group, sounds):
    for kind, role, make in sounds:
        wav_path = os.path.join(folder, kind + role + ".wav")
        # Idle sounds are meant to stay in the background, reload sounds are softer than the shot
        gain = {"Idle": 0.35, "Reload": 0.65}.get(role, 1.0)
        write_wav(wav_path, [s * gain for s in make()])
        target_dir = os.path.join(ROOT, "sounds", "Spatial", group, kind, role)
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, "Fx%s%s01.ogg" % (kind, role))
        subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
                               "-c:a", "libvorbis", "-q:a", "3", target])
        print("wrote", os.path.relpath(target, ROOT), os.path.getsize(target), "bytes")


def main():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found in PATH")
        return 1
    folder = tempfile.mkdtemp()
    try:
        write_group(ffmpeg, folder, "Traps", TRAP_SOUNDS)
        write_group(ffmpeg, folder, "Doors", DOOR_SOUNDS)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
