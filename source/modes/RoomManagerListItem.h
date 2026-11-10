// Copyright (C) 2026 OpenDungeons Team
// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef ROOMMANAGERLISTITEM_H
#define ROOMMANAGERLISTITEM_H

#include <CEGUI/CEGUI.h>
#include <CEGUI/ImageManager.h>
#include <CEGUI/widgets/ListboxTextItem.h>
#include <algorithm>
#include <cstdint>
#include <vector>
#include "traps/TrapType.h"

//! \brief An owner-data row with artwork, a short value and an optional health or production bar.
class RoomManagerListItem : public CEGUI::ListboxTextItem
{
public:
    //! \brief Keeps images owned by CEGUI and clamps progress to the visible bar.
    RoomManagerListItem(const std::string& text, uint32_t id,
        const std::vector<const CEGUI::Image*>& images, float progress = -1.0f, bool tile = false, uint32_t progressColour = 0xFF9BAA35) :
        CEGUI::ListboxTextItem(text, id), mImages(images), mProgress(progress), mTile(tile), mProgressColour(progressColour)
    {
        setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
        setTextParsingEnabled(false);
        setTextColours(CEGUI::Colour(0xFFF2C860));
    }
    //! \brief Scales row and priority tile height with their owning page.
    CEGUI::Sizef getPixelSize() const override
    {
        const float width = getOwnerWindow() == nullptr ? 480.0f : getOwnerWindow()->getPixelSize().d_width;
        return CEGUI::Sizef(mTile ? width * 0.22f : width * 0.95f, width * (mTile ? 0.22f : 0.17f));
    }
    //! \brief Draws portraits and item pictures beside the values, with progress below.
    void draw(CEGUI::GeometryBuffer& buffer, const CEGUI::Rectf& target, float alpha,
        const CEGUI::Rectf* clipper) const override
    {
        const float height = getPixelSize().d_height;
        const float side = std::min(height * 0.72f, target.getWidth() * (mTile ? 0.9f : 0.16f));
        float x = target.left() + height * 0.04f;
        CEGUI::ColourRect colours(0xFFFFFFFF);
        colours.setAlpha(alpha);
        for(const CEGUI::Image* picture : mImages)
        {
            if(picture != nullptr)
                picture->render(buffer, CEGUI::Rectf(x, target.top(), x + side, target.top() + side), clipper, colours);
            x += side + height * 0.04f;
        }
        CEGUI::Rectf textArea(target);
        if(mTile)
            textArea.d_min.d_y += side;
        else
            textArea.d_min.d_x = x;
        CEGUI::ListboxTextItem::draw(buffer, textArea, alpha, clipper);
        if(mProgress >= 0.0f)
        {
            const CEGUI::Image& brush = CEGUI::ImageManager::getSingleton().get("OpenDungeonsSkin/SelectionBrush");
            const float left = mTile ? target.left() : x;
            const float right = target.right() - height * 0.06f;
            const float top = target.top() + height * 0.70f;
            CEGUI::ColourRect background(0xFF302820);
            background.setAlpha(alpha);
            brush.render(buffer, CEGUI::Rectf(left, top, right, top + height * 0.12f), clipper, background);
            CEGUI::ColourRect fill(mProgressColour);
            fill.setAlpha(alpha);
            brush.render(buffer, CEGUI::Rectf(left, top, left + (right-left) * std::max(0.0f, std::min(1.0f, mProgress)),
                top + height * 0.12f), clipper, fill);
        }
    }
private:
    std::vector<const CEGUI::Image*> mImages;
    float mProgress;
    bool mTile;
    uint32_t mProgressColour;
};

//! \brief Returns an existing shared image without manufacturing a missing asset.
inline const CEGUI::Image* roomManagerImage(const std::string& name)
{
    CEGUI::ImageManager& images = CEGUI::ImageManager::getSingleton();
    return images.isDefined(name) ? &images.get(name) : nullptr;
}
//! \brief Uses the same existing trap icon as the build bar for every production order.
inline const CEGUI::Image* roomManagerTrapImage(TrapType type)
{
    static const char* const names[] = {"", "CannonButton", "SpikeTrapButton", "BoulderTrapButton",
        "WoodenDoorTrapButton", "IronboundDoorTrapButton", "SteelDoorTrapButton", "BarricadeTrapButton",
        "AlarmTrapButton", "FearTrapButton", "GasTrapButton", "LightningTrapButton", "FireburstTrapButton",
        "WatchBannerTrapButton", "SecretDoorTrapButton", "RunedDoorTrapButton", "TriggerTrapButton", "FreezeTrapButton"};
    const uint32_t index = static_cast<uint32_t>(type);
    return index > 0 && index < 18 ? roomManagerImage(std::string("OpenDungeonsIcons/") + names[index]) : nullptr;
}
//! \brief Frames the selected purse while keeping both short payer labels visible.
inline void roomManagerPayer(CEGUI::Window* page, bool keeper)
{
    page->getChild("Keeper")->setProperty("FrameEnabled", keeper ? "True" : "False");
    page->getChild("Creature")->setProperty("FrameEnabled", keeper ? "False" : "True");
    page->getChild("Keeper")->setAlpha(keeper ? 1.0f : 0.45f);
    page->getChild("Creature")->setAlpha(keeper ? 0.45f : 1.0f);
}
#endif
