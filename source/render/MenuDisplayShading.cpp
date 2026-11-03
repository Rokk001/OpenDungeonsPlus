/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "render/MenuDisplayShading.h"

#include <OgreColourValue.h>
#include <OgreMaterial.h>
#include <OgrePass.h>
#include <OgreTechnique.h>

#include <RTShaderSystem/OgreShaderFFPRenderState.h>
#include <RTShaderSystem/OgreShaderFunction.h>
#include <RTShaderSystem/OgreShaderFunctionAtom.h>
#include <RTShaderSystem/OgreShaderGenerator.h>
#include <RTShaderSystem/OgreShaderParameter.h>
#include <RTShaderSystem/OgreShaderProgram.h>
#include <RTShaderSystem/OgreShaderProgramSet.h>
#include <RTShaderSystem/OgreShaderRenderState.h>
#include <RTShaderSystem/OgreShaderSubRenderState.h>

//! Unique shader generator name of the menu display stage.
static const Ogre::String MENU_DISPLAY_TYPE = "MenuDisplayEncoding";
//! Only materials of the menu scene carry this name prefix.
static const Ogre::String MENU_MATERIAL_PREFIX = "Menu";
//! Shader library file, without extension, that holds the encoding function.
static const Ogre::String MENU_DISPLAY_LIBRARY = "MenuDisplay";
//! Must match the factor in MenuDisplay.glsl. Surface colours enter the lighting at a quarter and the encoding restores them.
static const Ogre::Real MENU_LIGHT_HEADROOM = 4.0f;
//! Without these defines the generated lighting clamps each light sum per colour channel. A strong red light near a surface
//! then clips red and green together, so red ground turns olive. The encoding rolls each channel off towards its white point instead, and
//! TARGET_CONSUMES_LINEAR keeps the generator from adding its own gamma step on top of that encoding.
static const Ogre::String MENU_UNCLAMPED_LIGHTING_DEFINES = "USE_LINEAR_COLOURS,TARGET_CONSUMES_LINEAR";

//! \brief Scales a surface colour into the lighting headroom, keeping its alpha.
static Ogre::ColourValue toLightingHeadroom(const Ogre::ColourValue& colour)
{
    return Ogre::ColourValue(colour.r / MENU_LIGHT_HEADROOM, colour.g / MENU_LIGHT_HEADROOM,
        colour.b / MENU_LIGHT_HEADROOM, colour.a);
}

//! \brief Encodes the final colour of lit menu scene passes for the display target.
class MenuDisplaySubRenderState : public Ogre::RTShader::SubRenderState
{
public:
    //! \brief Returns the shader generator name of this stage.
    const Ogre::String& getType() const override
    { return MENU_DISPLAY_TYPE; }

    //! \brief Runs after lighting, texturing and fog have produced the final colour.
    int getExecutionOrder() const override
    { return Ogre::RTShader::FFP_POST_PROCESS; }

    //! \brief Copies nothing because the stage has no state.
    void copyFrom(const Ogre::RTShader::SubRenderState&) override
    {}

    //! \brief Accepts only lit passes of menu materials; unlit decals and the hand keep their colours.
    //! The generated pass enters the lighting with scaled surface colours, always derived from the source pass.
    bool preAddToRenderState(const Ogre::RTShader::RenderState*, Ogre::Pass* srcPass, Ogre::Pass* dstPass) override
    {
        const Ogre::String& materialName = srcPass->getParent()->getParent()->getName();
        if(!srcPass->getLightingEnabled()
            || materialName.compare(0, MENU_MATERIAL_PREFIX.size(), MENU_MATERIAL_PREFIX) != 0)
            return false;
        dstPass->setAmbient(toLightingHeadroom(srcPass->getAmbient()));
        dstPass->setDiffuse(toLightingHeadroom(srcPass->getDiffuse()));
        dstPass->setSpecular(toLightingHeadroom(srcPass->getSpecular()));
        dstPass->setSelfIllumination(toLightingHeadroom(srcPass->getSelfIllumination()));
        return true;
    }

    //! \brief Lifts the per-channel clamp of the light sums and calls the encoding function on the fragment output.
    bool createCpuSubPrograms(Ogre::RTShader::ProgramSet* programSet) override
    {
        Ogre::RTShader::Program* fragmentProgram = programSet->getCpuProgram(Ogre::GPT_FRAGMENT_PROGRAM);
        fragmentProgram->addPreprocessorDefines(MENU_UNCLAMPED_LIGHTING_DEFINES);
        fragmentProgram->addDependency(MENU_DISPLAY_LIBRARY);
        Ogre::RTShader::Function* fragmentMain = fragmentProgram->getMain();
        Ogre::RTShader::ParameterPtr colour =
            fragmentMain->resolveOutputParameter(Ogre::RTShader::Parameter::SPC_COLOR_DIFFUSE);
        fragmentMain->getStage(Ogre::RTShader::FFP_PS_POST_PROCESS).callFunction("MenuDisplay_Encode",
            Ogre::RTShader::InOut(colour));
        return true;
    }
};

//! \brief Creates the menu display stage for the shader generator.
class MenuDisplaySubRenderStateFactory : public Ogre::RTShader::SubRenderStateFactory
{
public:
    //! \brief Returns the shader generator name of the created stage.
    const Ogre::String& getType() const override
    { return MENU_DISPLAY_TYPE; }

protected:
    //! \brief Creates one stage instance owned by this factory.
    Ogre::RTShader::SubRenderState* createInstanceImpl() override
    { return new MenuDisplaySubRenderState(); }
};

void registerMenuDisplayShading(Ogre::RTShader::ShaderGenerator& shaderGenerator)
{
    // The generator keeps using the factory and its instances until it shuts down, so the factory stays allocated.
    shaderGenerator.addSubRenderStateFactory(new MenuDisplaySubRenderStateFactory());
    Ogre::RTShader::RenderState* renderState =
        shaderGenerator.getRenderState(Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME);
    renderState->addTemplateSubRenderState(shaderGenerator.createSubRenderState(MENU_DISPLAY_TYPE));
}
