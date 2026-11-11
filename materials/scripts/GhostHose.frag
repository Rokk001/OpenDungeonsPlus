#version 330 core
uniform sampler2D rubberMap;
in vec4 hoseColour;
in vec2 hoseUV;
out vec4 fragColour;

//! \brief Preserve the dark rubber grain and the CPU shading of each corrugation.
void main()
{
    fragColour = vec4(texture(rubberMap, hoseUV).rgb * hoseColour.rgb, 1.0);
}
