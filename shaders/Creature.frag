#version 330  core
#extension GL_ARB_shading_language_include : enable
#include "ShadowMapping.glsl"
#include "LocalLighting.glsl"

uniform sampler2D decalmap;
uniform sampler2D normalmap;
uniform sampler2D shadowmap;

uniform vec4 ambientLightColour;
uniform vec4 cameraPosition;
uniform vec3 ambient;
uniform bool shadowingEnabled;
uniform float corpseDecay = 0.0;
in vec2 out_UV0;
in vec2 out_UV1;
in vec3 FragPos;
in vec4 VertexPos; 
in mat3 TBN;
 
out vec4 color;

void main (void)  
{  

    // compute Normal
    vec3 Normal = texture(normalmap, out_UV1.st).rgb;
    Normal.xyz = 2 * Normal.xyz - (1.0,1.0,1.0);
    Normal =  normalize(TBN * Normal); 
    
    vec4 shadow = vec4(1.0, 1.0, 1.0,1.0);
    
    // compute shadowmap
    if(shadowingEnabled)
        shadow = vec4(sampleShadow(shadowmap, VertexPos));
    
    
    vec3 result;
        
    // precompute the lighting term
    vec3 lightingTerm = getLocalLighting(FragPos, Normal, cameraPosition.xyz, shadow.r) + ambientLightColour.rgb * ambient;
    vec3 texelColor = texture(decalmap, out_UV0.st).rgb;
    if(corpseDecay > 0.0)
    {
        // Stable surface patches change only on corpses with a private material.
        vec2 cell = floor(out_UV0 * 48.0);
        float grain = fract(sin(dot(cell, vec2(12.9898, 78.233))) * 43758.5453);
        float rot = smoothstep(grain * 0.35, 0.55 + grain * 0.25, corpseDecay);
        float grey = dot(texelColor, vec3(0.299, 0.587, 0.114));
        texelColor = mix(texelColor, grey * vec3(0.48, 0.43, 0.28), rot);
        float loss = smoothstep(0.45, 1.0, corpseDecay);
        if(loss > grain)
            discard;
    }
    result =  lightingTerm * texelColor;

    color  = vec4(enhanceDungeonColour(result),  1.0);

       
}    

