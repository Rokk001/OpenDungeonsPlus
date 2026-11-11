#version 330 core
uniform mat4 worldViewProj;
layout(location = 0) in vec4 vertex;
layout(location = 3) in vec4 colour;
layout(location = 8) in vec2 uv0;
out vec4 hoseColour;
out vec2 hoseUV;

//! \brief Pass the procedural vertex colours through without room lighting or generated shader substitutions.
void main()
{
    gl_Position = worldViewProj * vertex;
    hoseColour = colour;
    hoseUV = uv0;
}
