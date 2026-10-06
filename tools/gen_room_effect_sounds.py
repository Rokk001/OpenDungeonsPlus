#!/usr/bin/env python3
"""Synthesizes the sounds of the casino and the arena crowd and writes them as .ogg files.

    python tools/gen_room_effect_sounds.py

Same method as tools/gen_spell_sounds.py: sine waves, noise and simple envelopes only (no recordings, no
samples), fixed random seeds, so the same files come out every time. ffmpeg (libvorbis) must be in the PATH.
Files go to
    sounds/Spatial/Rooms/Casino/Win/FxCasinoWin01.ogg      a bright run of chimes and coins
    sounds/Spatial/Rooms/Casino/Loss/FxCasinoLoss01.ogg    a falling groan of a few voices
    sounds/Spatial/Rooms/Arena/Cheer/FxArenaCheer01.ogg    a crowd shouting and clapping
    sounds/Spatial/Rooms/Prison/Clang/FxPrisonClang01.ogg  an iron door falling shut, bars ringing
    sounds/Spatial/Rooms/Torture/Shackles/FxTortureShackles01.ogg  a flash crack and chains falling
    sounds/Spatial/Rooms/Crypt/Raise/FxCryptRaise01.ogg    earth shifting and a rising spirit tone
    sounds/Spatial/Rooms/WavePortal/Surge/FxWavePortalSurge01.ogg  a deep boom and a rising shockwave
    sounds/Spatial/Rooms/Heart/Hit/FxHeartHit01.ogg        a hard double heartbeat

With room names as arguments (for example "Prison Crypt") only the sounds of those rooms are written.
"""

import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

from gen_spell_sounds import TAU, Noise, decay, render, write_wav

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Centre frequencies of the vowel-like peaks of a voice (an open "ah" and a darker "oh")
FORMANTS_AH = ((700.0, 1.0), (1150.0, 0.7), (2500.0, 0.25))
FORMANTS_OH = ((450.0, 1.0), (800.0, 0.6), (2400.0, 0.12))


def swell(t, length):
    return math.sin(math.pi * min(1.0, max(0.0, t / length)))


def chime(t, start, freq, rate):
    """A struck bell: a few inharmonic partials that die away."""
    if t < start:
        return 0.0
    local = t - start
    value = math.sin(TAU * freq * local) + 0.5 * math.sin(TAU * freq * 2.76 * local) * decay(local, rate)
    value += 0.25 * math.sin(TAU * freq * 5.4 * local) * decay(local, rate * 2.0)
    return value * decay(local, rate) * min(1.0, local / 0.002)


def coin_clink(t, start, freq):
    """A short high metal tick."""
    if t < start:
        return 0.0
    local = t - start
    return (math.sin(TAU * freq * local) + 0.6 * math.sin(TAU * freq * 1.5 * local)) * decay(local, 40.0)


def voice(t, f0, formants, phase):
    """One voice: harmonics of f0 weighted by how close they are to the vowel peaks."""
    value = 0.0
    harmonic = 1
    while f0 * harmonic < 3500.0:
        freq = f0 * harmonic
        weight = 0.0
        for centre, gain in formants:
            weight += gain * math.exp(-((freq - centre) / (0.22 * centre)) ** 2)
        value += weight * math.sin(TAU * freq * t + phase * harmonic) / (harmonic ** 0.5)
        harmonic += 1
    return value


def casino_win():
    length = 1.3
    notes = (880.0, 1108.7, 1318.5, 1760.0)
    noise = Noise(301)
    rng = random.Random(302)
    clinks = sorted(rng.uniform(0.15, 1.0) for _ in range(14))
    freqs = [rng.uniform(3200.0, 5200.0) for _ in clinks]

    def f(t):
        value = 0.0
        for index, freq in enumerate(notes):
            value += chime(t, 0.05 + 0.09 * index, freq, 4.5) * 0.6
        for start, freq in zip(clinks, freqs):
            value += coin_clink(t, start, freq) * 0.25
        return value + noise.white() * decay(t, 25.0) * 0.1
    return render(length, f)


def casino_loss():
    length = 1.2
    noise = Noise(311)
    rng = random.Random(312)
    singers = [(rng.uniform(150.0, 230.0), rng.uniform(0.0, 0.25), rng.uniform(0.0, TAU), rng.uniform(4.0, 6.0))
               for _ in range(3)]

    def f(t):
        value = 0.0
        for base, offset, phase, vibrato in singers:
            local = t - offset
            if local < 0.0:
                continue
            # The pitch drops over the groan, the voice wavers a little
            f0 = base * (1.0 - 0.35 * min(1.0, local / 0.9)) * (1.0 + 0.012 * math.sin(TAU * vibrato * local))
            e = swell(local, length - offset) ** 0.7
            value += voice(local, f0, FORMANTS_OH, phase) * e
        return value + noise.lowpass(0.7) * 0.15 * swell(t, length)
    return render(length, f)


def arena_cheer():
    length = 1.8
    noise = Noise(321)
    rng = random.Random(322)
    singers = []
    for _ in range(16):
        base = rng.uniform(170.0, 330.0)
        start = rng.uniform(0.0, 0.35)
        end = rng.uniform(1.0, 1.7)
        singers.append((base, start, end, rng.uniform(0.0, TAU), rng.uniform(5.0, 7.0), rng.uniform(0.0, 1.0)))
    claps = sorted(rng.uniform(0.2, 1.7) for _ in range(26))

    def f(t):
        value = 0.0
        for base, start, end, phase, vibrato, mix in singers:
            if t < start or t > end:
                continue
            local = t - start
            # The shout rises and then falls back
            f0 = base * (1.0 + 0.25 * math.sin(math.pi * min(1.0, local / (end - start)) * 0.8))
            f0 *= 1.0 + 0.01 * math.sin(TAU * vibrato * local)
            e = swell(local, end - start) ** 0.6
            formants = FORMANTS_AH if mix > 0.35 else FORMANTS_OH
            value += voice(local, f0, formants, phase) * e * 0.35
        for clap in claps:
            if t >= clap:
                local = t - clap
                value += noise.white() * decay(local, 60.0) * 0.5
        return value + noise.lowpass(0.5) * 0.4 * swell(t, length)
    return render(length, f)


def thump(t, start, freq, rate):
    """A short low knock that falls in pitch."""
    if t < start:
        return 0.0
    local = t - start
    return math.sin(TAU * (freq + 40.0 * decay(local, 30.0)) * local) * decay(local, rate) * min(1.0, local / 0.002)


def metal_ring(t, start, freq, rate):
    """A struck piece of iron: inharmonic partials that die away."""
    if t < start:
        return 0.0
    local = t - start
    value = math.sin(TAU * freq * local) + 0.6 * math.sin(TAU * freq * 2.32 * local) + 0.4 * math.sin(TAU * freq * 4.1 * local)
    return value * decay(local, rate) * min(1.0, local / 0.001)


def prison_clang():
    length = 1.4
    noise = Noise(331)

    def f(t):
        value = metal_ring(t, 0.0, 520.0, 5.0) * 0.8 + metal_ring(t, 0.03, 870.0, 7.0) * 0.5
        value += metal_ring(t, 0.45, 640.0, 9.0) * 0.25
        value += thump(t, 0.0, 90.0, 12.0) * 0.9
        value += noise.white() * decay(t, 40.0) * 0.4
        return value
    return render(length, f)


def torture_shackles():
    length = 1.5
    noise = Noise(341)
    rng = random.Random(342)
    links = sorted(rng.uniform(0.12, 1.1) for _ in range(12))
    freqs = [rng.uniform(1500.0, 3200.0) for _ in links]

    def f(t):
        crack = noise.white() * decay(t, 70.0) * 0.9 + math.sin(TAU * 1800.0 * t) * decay(t, 50.0) * 0.5
        value = crack
        for start, freq in zip(links, freqs):
            value += metal_ring(t, start, freq, 28.0) * 0.18
        value += thump(t, 0.9, 110.0, 14.0) * 0.5 + metal_ring(t, 0.9, 700.0, 12.0) * 0.3
        return value
    return render(length, f)


def crypt_raise():
    length = 2.0
    noise = Noise(351)

    def f(t):
        rumble = noise.lowpass(0.97) * 4.0 * swell(t, length) ** 0.8
        grind = math.sin(TAU * 48.0 * t) * 0.5 * swell(t, length)
        rise = 0.0
        if t > 0.5:
            local = t - 0.5
            rise = math.sin(sweep_phase_local(300.0, 880.0, 1.4, min(local, 1.4))) * swell(local, 1.5) * 0.35
            rise += math.sin(sweep_phase_local(450.0, 1320.0, 1.4, min(local, 1.4))) * swell(local, 1.5) * 0.15
        return rumble + grind + rise
    return render(length, f)


def sweep_phase_local(f0, f1, length, t):
    k = (f1 - f0) / length
    return TAU * (f0 * t + 0.5 * k * t * t)


def wave_portal_surge():
    length = 1.8
    noise = Noise(361)

    def f(t):
        boom = thump(t, 0.0, 55.0, 3.2) * 1.2 + thump(t, 0.0, 85.0, 5.0) * 0.6
        wave = math.sin(sweep_phase_local(140.0, 620.0, 1.2, min(t, 1.2))) * swell(t, 1.4) * 0.35
        wash = noise.lowpass(0.9) * 2.5 * decay(t, 2.2) * min(1.0, t / 0.01)
        return boom + wave + wash
    return render(length, f)


def heart_hit():
    length = 0.9

    def f(t):
        return (thump(t, 0.0, 70.0, 11.0) * 1.0 + thump(t, 0.22, 60.0, 12.0) * 0.8 +
                math.sin(TAU * 140.0 * t) * decay(t, 14.0) * 0.3)
    return render(length, f)


SOUNDS = (
    ("Casino", "Win", casino_win),
    ("Casino", "Loss", casino_loss),
    ("Arena", "Cheer", arena_cheer),
    ("Prison", "Clang", prison_clang),
    ("Torture", "Shackles", torture_shackles),
    ("Crypt", "Raise", crypt_raise),
    ("WavePortal", "Surge", wave_portal_surge),
    ("Heart", "Hit", heart_hit),
)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found in PATH")
        return 1
    folder = tempfile.mkdtemp()
    try:
        for room, role, make in SOUNDS:
            if len(sys.argv) > 1 and room not in sys.argv[1:]:
                continue
            wav_path = os.path.join(folder, room + role + ".wav")
            write_wav(wav_path, make())
            target_dir = os.path.join(ROOT, "sounds", "Spatial", "Rooms", room, role)
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, "Fx%s%s01.ogg" % (room, role))
            subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
                                   "-c:a", "libvorbis", "-q:a", "3", target])
            print("wrote", os.path.relpath(target, ROOT), os.path.getsize(target), "bytes")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
