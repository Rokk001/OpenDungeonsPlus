#version 330 core
#extension GL_ARB_explicit_uniform_location : enable
#extension GL_ARB_shading_language_include : enable

layout (location = 0) in vec4 position;
layout (location = 1) in vec4 blendWeights;
layout (location = 2)  in vec4 normal;
layout (location = 7) in vec4 blendIndices;

// Hardware skinning: the bone matrices (world_matrix_array_3x4) contain the world transform.
uniform    mat4 viewProjectionMatrix;
uniform    vec4 boneMatrices[768];
uniform    float width;

void main(void)
{
  // Thin contour shell: every vertex moves a small distance along its normal
  vec3 shellOffset = normalize(normal.xyz) * width;
  vec4 enlarged = vec4(position.xyz + shellOffset, 1.0);
  vec4 weights = vec4(blendWeights.xyz, max(0.0, 1.0 - blendWeights.x - blendWeights.y - blendWeights.z));
  vec3 P = vec3(0.0);
  for(int i = 0; i < 4; ++i)
  {
      int idx = int(blendIndices[i]) * 3;
      P += weights[i] * vec3(dot(boneMatrices[idx], enlarged), dot(boneMatrices[idx + 1], enlarged), dot(boneMatrices[idx + 2], enlarged));
  }
  gl_Position = viewProjectionMatrix * vec4(P, 1.0);
}
