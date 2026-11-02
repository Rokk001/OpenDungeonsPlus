// Scene values are linear light with exposure already included in the authored lights.
// Each channel rolls off towards a white point of 4 so saturated fire turns warm instead of clipping red,
// then the result is encoded for the display target, which applies no gamma of its own.
void MenuDisplay_Encode(inout vec4 colour)
{
    vec3 light = max(colour.rgb, vec3(0.0));
    vec3 mapped = light * (vec3(1.0) + light / 16.0) / (vec3(1.0) + light);
    colour.rgb = pow(min(mapped, vec3(1.0)), vec3(1.0 / 2.2));
}
