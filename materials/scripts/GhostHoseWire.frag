#version 330 core
in vec4 hoseColour;
out vec4 fragColour;

//! \brief Saturated wire colours remain readable regardless of the room lights.
void main()
{
    fragColour = vec4(hoseColour.rgb, 1.0);
}
