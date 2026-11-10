#version 330 core
#extension GL_ARB_explicit_uniform_location : enable
#extension GL_ARB_shading_language_include : enable

layout (location = 0) in vec4 position;
layout (location = 1) in vec4 blendWeights;
layout (location = 2)  in vec4 normal;
layout (location = 7) in vec4 blendIndices;

// Hardware skinning: the bone matrices (world_matrix_array_3x4) are in object space in OGRE 14,
// so the skinned position and normal are moved into world space with worldMatrix.
uniform    mat4 viewProjectionMatrix;
uniform    mat4 viewMatrix;
uniform    mat4 worldMatrix;
uniform    vec4 boneMatrices[768];
// width, height, 1/width, 1/height of the viewport in pixels
uniform    vec4 viewportSize;
// Thickness of the contour in screen pixels
uniform    float pixelWidth;

void main(void)
{
  // Thin contour: the vertex keeps its place and moves a constant number of SCREEN pixels
  // outwards (a world-space offset covered thin parts and close-up bodies in red).
  vec4 weights = vec4(blendWeights.xyz, max(0.0, 1.0 - blendWeights.x - blendWeights.y - blendWeights.z));
  vec3 P = vec3(0.0);
  vec3 N = vec3(0.0);
  vec4 pos = vec4(position.xyz, 1.0);
  vec4 nrm = vec4(normal.xyz, 0.0);
  for(int i = 0; i < 4; ++i)
  {
      int idx = int(blendIndices[i]) * 3;
      P += weights[i] * vec3(dot(boneMatrices[idx], pos), dot(boneMatrices[idx + 1], pos), dot(boneMatrices[idx + 2], pos));
      N += weights[i] * vec3(dot(boneMatrices[idx], nrm), dot(boneMatrices[idx + 1], nrm), dot(boneMatrices[idx + 2], nrm));
  }
  vec4 clip = viewProjectionMatrix * (worldMatrix * vec4(P, 1.0));
  vec2 dir = (viewMatrix * (worldMatrix * vec4(N, 0.0))).xy;
  float len = length(dir);
  dir = len > 0.0001 ? dir / len : vec2(0.0);
  clip.xy += dir * pixelWidth * 2.0 * viewportSize.zw * clip.w;
  gl_Position = clip;
}
