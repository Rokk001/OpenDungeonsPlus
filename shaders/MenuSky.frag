#version 330 core

uniform vec4 surfaceEmission;
uniform int atmosphereKind;
uniform sampler2D moonMap;
in vec3 skyPosition;
in vec2 skyUV;
out vec4 fragColour;

// Return a repeatable lattice value without a texture dependency.
float cloudHash(vec3 cell)
{
    return fract(sin(dot(cell, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

// Interpolate the eight lattice corners to make cloud density continuous in world space.
float cloudNoise(vec3 point)
{
    vec3 cell = floor(point);
    vec3 weight = fract(point);
    weight = weight * weight * (3.0 - 2.0 * weight);
    float lower = mix(mix(cloudHash(cell), cloudHash(cell + vec3(1, 0, 0)), weight.x),
        mix(cloudHash(cell + vec3(0, 1, 0)), cloudHash(cell + vec3(1, 1, 0)), weight.x), weight.y);
    float upper = mix(mix(cloudHash(cell + vec3(0, 0, 1)), cloudHash(cell + vec3(1, 0, 1)), weight.x),
        mix(cloudHash(cell + vec3(0, 1, 1)), cloudHash(cell + vec3(1, 1, 1)), weight.x), weight.y);
    return mix(lower, upper, weight.z);
}

// Transfer the authored five cloud octaves and roughness from the atmosphere to the game.
float cloudDensity(vec3 point)
{
    float density = 0.0;
    float weight = 1.0;
    float totalWeight = 0.0;
    for(int octave = 0; octave < 5; ++octave)
    {
        density += cloudNoise(point) * weight;
        totalWeight += weight;
        weight *= 0.78;
        point *= 2.0;
    }
    return smoothstep(0.28, 0.78, density / totalWeight);
}

// Shade self-lit atmosphere independently of scene lights, shadows and missing vertex colours.
void main()
{
    vec3 linearColour = surfaceEmission.rgb;
    float alpha = 1.0;
    if(atmosphereKind < 2)
    {
        vec3 point = skyPosition * 0.055;
        // The same world-space distortion and height fade keep the layered horizon continuous.
        point += vec3(cloudNoise(point)) * 2.8;
        linearColour = mix(vec3(0.002, 0.0025, 0.002), linearColour, cloudDensity(point));
        if(atmosphereKind == 1)
            linearColour *= mix(1.0, 0.03, clamp((skyPosition.z - 12.0) / (38.0 - 12.0), 0.0, 1.0));
    }
    else if(atmosphereKind == 2)
        alpha = 0.0; // Cloud volumes belong to the particle layers, as in the authored atmosphere.
    else
        linearColour *= texture(moonMap, skyUV).rgb;

    // The atmosphere is authored in linear light at exposure one; the game target is not sRGB.
    linearColour *= 2.0;
    fragColour = vec4(pow(max(linearColour, vec3(0.0)), vec3(1.0 / 2.2)), alpha);
}
