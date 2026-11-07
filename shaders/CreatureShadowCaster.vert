#version 330 core

// Shadow caster of the hardware skinned creature materials: only the skinned position is
// needed. The bone matrices (world_matrix_array_3x4) contain the world transform.
uniform    mat4 viewProjectionMatrix;
uniform    vec4 boneMatrices[768];
layout (location = 0) in vec4 position;
layout (location = 1) in vec4 blendWeights;
layout (location = 7) in vec4 blendIndices;

void main() {
    vec4 weights = vec4(blendWeights.xyz, max(0.0, 1.0 - blendWeights.x - blendWeights.y - blendWeights.z));
    vec4 pos = vec4(position.xyz, 1.0);
    vec3 P = vec3(0.0);
    for(int i = 0; i < 4; ++i)
    {
        int idx = int(blendIndices[i]) * 3;
        P += weights[i] * vec3(dot(boneMatrices[idx], pos), dot(boneMatrices[idx + 1], pos), dot(boneMatrices[idx + 2], pos));
    }
    gl_Position = viewProjectionMatrix * vec4(P, 1.0);
}
