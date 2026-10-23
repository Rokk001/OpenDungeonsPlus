/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "render/PortraitCatalog.h"

#include <algorithm>
#include <fstream>
#include <set>
#include <sstream>

namespace
{
//! \brief Orders images by their permanent number.
bool imageNumberLess(const PortraitCatalog::Image& a, const PortraitCatalog::Image& b)
{
    return a.mNumber < b.mNumber;
}

//! \brief Reads a positive decimal uint32 without overflow.
bool parseImageNumber(const std::string& text, uint32_t& number)
{
    if(text.empty())
        return false;
    uint64_t value = 0;
    for(char ch : text)
    {
        if(ch < '0' || ch > '9')
            return false;
        value = value * 10 + static_cast<uint32_t>(ch - '0');
        if(value > UINT32_MAX)
            return false;
    }
    number = static_cast<uint32_t>(value);
    return number != 0;
}
}

//! \brief Loads an index and verifies that every referenced JPEG exists.
bool PortraitCatalog::loadFromFile(const std::string& path)
{
    mImages.clear();
    mErrors.clear();
    std::ifstream file(path.c_str());
    if(!file)
    {
        mErrors.push_back("Cannot open portrait catalog: " + path);
        return false;
    }
    std::string::size_type slash = path.find_last_of("/\\");
    const std::string directory = slash == std::string::npos ? std::string() : path.substr(0, slash + 1);
    if(!loadFromStream(file, directory, path))
        return false;
    for(const Image& image : mImages)
    {
        std::ifstream picture(image.mPath.c_str(), std::ios::binary);
        if(!picture.good())
            mErrors.push_back("Missing portrait image: " + image.mPath);
    }
    if(!mErrors.empty())
        mImages.clear();
    return !mImages.empty();
}

//! \brief Parses a complete catalog, rejecting duplicate IDs, unsafe paths and malformed tags.
bool PortraitCatalog::loadFromStream(std::istream& stream, const std::string& directory, const std::string& source)
{
    mImages.clear();
    mErrors.clear();
    std::set<uint32_t> numbers;
    std::set<std::string> filenames;
    std::string line;
    uint32_t lineNumber = 0;
    while(std::getline(stream, line))
    {
        ++lineNumber;
        if(!line.empty() && line.back() == '\r')
            line.pop_back();
        if(line.empty() || line[0] == '#')
            continue;
        std::string::size_type first = line.find('\t');
        std::string::size_type second = first == std::string::npos ? first : line.find('\t', first + 1);
        Image image;
        bool valid = first != std::string::npos && second != std::string::npos &&
            parseImageNumber(line.substr(0, first), image.mNumber);
        std::string filename = valid ? line.substr(first + 1, second - first - 1) : std::string();
        valid = valid && filename.size() > 4 &&
            filename.substr(filename.size() - 4) == ".jpg" &&
            filename.find_first_not_of("0123456789.jpg") == std::string::npos &&
            filename.find("..") == std::string::npos;
        uint32_t fileNumber = 0;
        valid = valid && parseImageNumber(filename.substr(0, filename.size() - 4), fileNumber) &&
            fileNumber == image.mNumber;
        if(valid)
        {
            image.mPath = directory + filename;
            const std::string tagList = line.substr(second + 1);
            valid = !tagList.empty() && tagList.back() != ',';
            std::istringstream tags(tagList);
            std::string tag;
            std::set<std::string> uniqueTags;
            while(std::getline(tags, tag, ','))
            {
                if(tag.empty() || tag.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789-") != std::string::npos ||
                    !uniqueTags.insert(tag).second)
                {
                    valid = false;
                    break;
                }
                image.mTags.push_back(tag);
            }
            valid = valid && !image.mTags.empty() && numbers.insert(image.mNumber).second &&
                filenames.insert(filename).second;
        }
        if(!valid)
            mErrors.push_back(source + ":" + std::to_string(lineNumber) + ": invalid portrait index row");
        else
            mImages.push_back(image);
    }
    if(mImages.empty() || !mErrors.empty())
    {
        mImages.clear();
        return false;
    }
    std::sort(mImages.begin(), mImages.end(), imageNumberLess);
    return true;
}

//! \brief Finds the image with a permanent number.
const PortraitCatalog::Image* PortraitCatalog::findImage(uint32_t number) const
{
    for(const Image& image : mImages)
        if(image.mNumber == number)
            return &image;
    return nullptr;
}
