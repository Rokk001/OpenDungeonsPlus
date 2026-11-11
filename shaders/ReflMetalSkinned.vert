#version 330 core
#extension GL_ARB_explicit_uniform_location : enable
#extension GL_ARB_shading_language_include : enable

// Hardware skinned variant of ReflMetal.vert for the metal parts of animated creatures.
// The bone matrices (world_matrix_array_3x4) are in object space in OGRE 14, so the skinned
// position and normal are moved into world space with worldMatrix, as ReflMetal.vert does.
uniform    mat4 viewProjectionMatrix;
uniform    mat4 worldMatrix;
uniform    vec4 boneMatrices[768];

layout (location = 0) in vec4 position;
layout (location = 1) in vec4 blendWeights;
layout (location = 2) in vec3 normal;
layout (location = 7) in vec4 blendIndices;

out vec3 out_FragPos;
out vec3 out_Normal;

void main() {
    vec4 weights = vec4(blendWeights.xyz, max(0.0, 1.0 - blendWeights.x - blendWeights.y - blendWeights.z));
    vec4 pos = vec4(position.xyz, 1.0);
    vec3 P = vec3(0.0);
    vec3 skinNormal = vec3(0.0);
    for(int i = 0; i < 4; ++i)
    {
        int idx = int(blendIndices[i]) * 3;
        vec4 row0 = boneMatrices[idx];
        vec4 row1 = boneMatrices[idx + 1];
        vec4 row2 = boneMatrices[idx + 2];
        P += weights[i] * vec3(dot(row0, pos), dot(row1, pos), dot(row2, pos));
        skinNormal += weights[i] * vec3(dot(row0.xyz, normal), dot(row1.xyz, normal), dot(row2.xyz, normal));
    }
    P = (worldMatrix * vec4(P, 1.0)).xyz;
    out_Normal = mat3(worldMatrix) * skinNormal;
    gl_Position = viewProjectionMatrix * vec4(P, 1.0);
    out_FragPos = P;
}
