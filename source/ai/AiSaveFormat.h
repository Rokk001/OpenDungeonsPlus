#ifndef AI_SAVE_FORMAT_H
#define AI_SAVE_FORMAT_H

#include "ai/KeeperAIType.h"
#include <cstdint>
#include <iosfwd>
#include <string>
#include <utility>
#include <vector>

namespace KeeperAITypes
{
//! \brief Maps an AI level to its player ID, including the first human ID.
int32_t toPlayerId(KeeperAIType type);
//! \brief Reads an optional saved AI level and returns the next token.
KeeperAIType readOptionalAiLevel(std::istream& is, std::string& nextToken);
}
namespace SaveFormat
{
//! \brief Writes the saved spell cooldown block.
void writeSpellCooldowns(std::ostream& os, const std::vector<std::pair<std::string, uint32_t>>& cooldowns);
//! \brief Reads a spell cooldown block after its opening tag.
bool readSpellCooldowns(std::istream& is, std::vector<std::pair<std::string, uint32_t>>& cooldowns);
//! \brief Reads lines through the specified closing tag.
bool readBlockLines(std::istream& is, const std::string& endTag, std::vector<std::string>& lines);
}
#endif
