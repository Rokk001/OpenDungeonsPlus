#version 330  core
#extension GL_ARB_shading_language_include : enable
#include "ShadowMapping.glsl"
#include "LocalLighting.glsl"

uniform sampler2D decalmap;
uniform sampler2D normalmap;
uniform sampler2D shadowmap;

#ifdef DORMITORY_FLOOR
uniform sampler2D dormitoryEdge;
uniform sampler2D dormitoryCorner;
// UV boundaries: U=0, V=0, U=1, V=1; one denotes an exposed room edge.
uniform vec4 dormitoryBorders;

vec3 dormitoryFloor(vec2 uv)
{
    bool right = uv.x > 0.5;
    bool top = uv.y < 0.5;
    bool side = (right ? dormitoryBorders.z : dormitoryBorders.x) > 0.5;
    bool end = (top ? dormitoryBorders.y : dormitoryBorders.w) > 0.5;
    if(side && end)
        return texture(dormitoryCorner, vec2(right ? uv.x : 1.0 - uv.x,
            top ? uv.y : 1.0 - uv.y)).rgb;
    if(side)
        return texture(dormitoryEdge, vec2(uv.y, right ? uv.x : 1.0 - uv.x)).rgb;
    if(end)
        return texture(dormitoryEdge, vec2(uv.x, top ? 1.0 - uv.y : uv.y)).rgb;
    return texture(decalmap, uv).rgb;
}
#endif

uniform vec4 ambientLightColour;
uniform vec4 cameraPosition;
uniform bool shadowingEnabled;
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
    vec3 lightingTerm = getLocalLighting(FragPos, Normal, cameraPosition.xyz, shadow.r) + ambientLightColour.rgb;
    vec3 texelColor = texture(decalmap, out_UV0.st).rgb;
#ifdef DORMITORY_FLOOR
    texelColor = dormitoryFloor(out_UV0.st);
#endif
    result =  lightingTerm * texelColor;

    color  = vec4(enhanceDungeonColour(result),  1.0);

       
}    

