#version 330  core
#extension GL_ARB_shading_language_include : enable
#include "ShadowMapping.glsl"
#include "LocalLighting.glsl"


uniform sampler2D decalmap;
uniform sampler2D normalmap;
uniform sampler2D shadowmap;

uniform vec4 ambientLightColour;
uniform vec4 cameraPosition;
uniform vec4 diffuseSurface;
uniform bool shadowingEnabled;
uniform float veinTime;
uniform float veinGain;
in vec2 out_UV0;
in vec2 out_UV1;
in vec3 FragPos;
in vec4 VertexPos;
in mat3 TBN;
 
out vec4 color;

void main (void)  
{  
    vec3 texelColor = texture(decalmap, out_UV0.st).rgb;
    // compute Normal
    vec3 Normal = texture(normalmap, out_UV1.st).rgb;
    Normal.xyz = 2 * Normal.xyz - (1.0,1.0,1.0);
    Normal =  normalize(TBN * Normal); 
    
    
    vec3 result;
    
    
    // precompute the lighting term
    vec4 shadow = vec4(1.0);
    if(shadowingEnabled)
        shadow = vec4(sampleShadow(shadowmap, VertexPos));
    vec3 lightingTerm = getLocalLighting(FragPos, Normal, cameraPosition.xyz, shadow.r) + ambientLightColour.rgb;
    
    if(diffuseSurface.rgb != vec3(1.0,1.0,1.0))
        result =  lightingTerm * mix(texelColor, diffuseSurface.rgb,0.5);
    else
        result =  lightingTerm * texelColor;

    // Brighter gold veins with a slow glint that wanders over the bright flecks
    float luma = dot(texelColor, vec3(0.299, 0.587, 0.114));
    float wave = sin(FragPos.x * 9.0 + FragPos.y * 7.0 + FragPos.z * 11.0 + veinTime * 1.7)
               * sin(FragPos.x * 5.0 - FragPos.y * 6.0 + FragPos.z * 8.0 - veinTime * 1.1);
    float glint = pow(max(wave, 0.0), 10.0) * smoothstep(0.4, 0.75, luma);
    result = result * veinGain + glint * vec3(1.0, 0.86, 0.45);
    color = vec4(result.xyz,  1.0);
       
}    
