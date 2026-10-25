#version 330 core

uniform mat4 worldViewProj;
uniform mat4 worldMatrix;
layout(location = 0) in vec4 vertex;
layout(location = 8) in vec2 uv0;
out vec3 skyPosition;
out vec2 skyUV;

// Project the existing atmosphere geometry and retain world coordinates for continuous clouds.
void main()
{
    gl_Position = worldViewProj * vertex;
    skyPosition = (worldMatrix * vertex).xyz;
    skyUV = uv0;
}
