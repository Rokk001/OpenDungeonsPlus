#version 330 core
#extension GL_ARB_explicit_uniform_location : enable
#extension GL_ARB_shading_language_include : enable

// Hardware skinning: the bone matrices (world_matrix_array_3x4) already contain the world
// transform of the entity, so every position and direction below is in world space.
uniform    mat4 viewProjectionMatrix;
uniform    mat4 lightMatrix;
uniform    vec4 boneMatrices[768];
layout (location = 0) in vec4 position;
layout (location = 1) in vec4 blendWeights;
layout (location = 2)  in vec3 normal;
layout (location = 7) in vec4 blendIndices;
layout (location = 14) in vec3 tangent;

layout (location = 8) in vec2 uv0;
layout (location = 8) in vec2 uv1;
out vec2 out_UV0;
out vec2 out_UV1;
out vec3 FragPos;
out vec4 VertexPos;

out mat3 TBN;


void main() {
    // A mesh stores fewer than four weights per vertex as fewer components; the weights are
    // normalised, so the missing fourth weight is what the first three leave over.
    vec4 weights = vec4(blendWeights.xyz, max(0.0, 1.0 - blendWeights.x - blendWeights.y - blendWeights.z));
    vec4 pos = vec4(position.xyz, 1.0);

    // blend position, normal and tangent over the (up to four) bones of the vertex
    vec3 P = vec3(0.0);
    vec3 skinNormal = vec3(0.0);
    vec3 skinTangent = vec3(0.0);
    for(int i = 0; i < 4; ++i)
    {
        int idx = int(blendIndices[i]) * 3;
        vec4 row0 = boneMatrices[idx];
        vec4 row1 = boneMatrices[idx + 1];
        vec4 row2 = boneMatrices[idx + 2];
        P += weights[i] * vec3(dot(row0, pos), dot(row1, pos), dot(row2, pos));
        skinNormal += weights[i] * vec3(dot(row0.xyz, normal), dot(row1.xyz, normal), dot(row2.xyz, normal));
        skinTangent += weights[i] * vec3(dot(row0.xyz, tangent), dot(row1.xyz, tangent), dot(row2.xyz, tangent));
    }

    // compute world space tangent, bitangent
    vec3 T = normalize(skinTangent);
    vec3 B = normalize(cross(skinTangent, skinNormal));
    vec3 N = cross(B, T);
    TBN = mat3(T, B, N);

    gl_Position = viewProjectionMatrix * vec4(P, 1.0);
    FragPos = P;

    out_UV0 = uv0;
    out_UV1 = uv1;
    VertexPos = lightMatrix * vec4(P, 1.0);
}
