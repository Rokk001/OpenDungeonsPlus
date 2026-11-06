#version 330 core
#extension GL_ARB_explicit_uniform_location : enable
#extension GL_ARB_shading_language_include : enable

layout (location = 0) in vec4 position;
layout (location = 2)  in vec4 normal;

uniform    mat4 worldViewProj;
uniform    mat4 worldView;
// width, height, 1/width, 1/height of the viewport in pixels
uniform    vec4 viewportSize;
// Thickness of the contour in screen pixels
uniform    float pixelWidth;

void main(void)
{
  // Thin contour: the vertex keeps its place and moves a constant number of SCREEN pixels
  // outwards. A world-space offset was as thick as thin parts (bones, wing membranes, legs)
  // and as close-up bodies are large, so the contour covered the creature in red.
  vec4 clip = worldViewProj * vec4(position.xyz, 1.0);
  vec2 dir = (worldView * vec4(normal.xyz, 0.0)).xy;
  float len = length(dir);
  dir = len > 0.0001 ? dir / len : vec2(0.0);
  clip.xy += dir * pixelWidth * 2.0 * viewportSize.zw * clip.w;
  gl_Position = clip;
}
