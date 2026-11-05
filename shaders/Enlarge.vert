#version 330 core
#extension GL_ARB_explicit_uniform_location : enable
#extension GL_ARB_shading_language_include : enable

layout (location = 0) in vec4 position;
layout (location = 2)  in vec4 normal;

uniform    mat4 worldViewProj;
uniform    float width;

void main(void)
{
  // Thin contour shell: every vertex moves a small distance along its normal
  vec3 enlarged = position.xyz + normalize(normal.xyz) * width;
  gl_Position =worldViewProj * vec4(enlarged,1.0);
}
