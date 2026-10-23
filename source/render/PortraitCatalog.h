/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef PORTRAITCATALOG_H
#define PORTRAITCATALOG_H

#include <stdint.h>
#include <istream>
#include <string>
#include <vector>

//! \brief Numbered whole portraits and their visible feature tags, read from index.cfg.
class PortraitCatalog
{
public:
    //! \brief One permanently numbered image and the character details painted into it.
    struct Image
    {
        uint32_t mNumber;
        std::string mPath;
        std::vector<std::string> mTags;
    };

    //! \brief Loads an index and rejects missing image files.
    bool loadFromFile(const std::string& path);
    //! \brief Parses number, JPEG filename and comma-separated tags from TAB-separated rows.
    bool loadFromStream(std::istream& stream, const std::string& directory, const std::string& source);
    //! \brief Returns the images in permanent numeric order.
    const std::vector<Image>& getImages() const { return mImages; }
    //! \brief Finds a permanent image number, or returns nullptr if it was removed.
    const Image* findImage(uint32_t number) const;
    //! \brief Returns malformed-index or missing-file messages.
    const std::vector<std::string>& getErrors() const { return mErrors; }
private:
    std::vector<Image> mImages;
    std::vector<std::string> mErrors;
};
#endif
