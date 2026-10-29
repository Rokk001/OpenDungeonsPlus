#include "ai/AiSaveFormat.h"
#include <istream>
#include <ostream>

namespace KeeperAITypes
{
//! \brief Maps an AI level to its player ID, including the first human ID.
int32_t toPlayerId(KeeperAIType type) { return static_cast<int32_t>(type) + 1; }
//! \brief Reads an optional saved AI level and returns the next token.
KeeperAIType readOptionalAiLevel(std::istream& is, std::string& nextToken)
{
    if(!(is >> nextToken) || nextToken != "aiLevel")
        return KeeperAIType::nbAI;
    std::string name;
    if(!(is >> name >> nextToken))
        return KeeperAIType::nbAI;
    for(unsigned int i = 0; i < static_cast<unsigned int>(KeeperAIType::nbAI); ++i)
    {
        KeeperAIType type = static_cast<KeeperAIType>(i);
        if(name == nameOf(type)) return type;
    }
    return KeeperAIType::nbAI;
}
}
namespace SaveFormat
{
//! \brief Writes the saved spell cooldown block.
void writeSpellCooldowns(std::ostream& os, const std::vector<std::pair<std::string, uint32_t>>& cooldowns)
{
    os << "[SpellCooldowns]\t" << cooldowns.size() << "\n";
    for(const std::pair<std::string, uint32_t>& entry : cooldowns)
        os << entry.first << "\t" << entry.second << "\n";
    os << "[/SpellCooldowns]\n";
}
//! \brief Reads a spell cooldown block after its opening tag.
bool readSpellCooldowns(std::istream& is, std::vector<std::pair<std::string, uint32_t>>& cooldowns)
{
    size_t count;
    if(!(is >> count)) return false;
    for(size_t i = 0; i < count; ++i)
    {
        std::string name; uint32_t turns;
        if(!(is >> name >> turns)) return false;
        cooldowns.push_back(std::make_pair(name, turns));
    }
    std::string end;
    return static_cast<bool>(is >> end) && end == "[/SpellCooldowns]";
}
//! \brief Reads lines through the specified closing tag.
bool readBlockLines(std::istream& is, const std::string& endTag, std::vector<std::string>& lines)
{
    std::string line;
    std::getline(is, line);
    while(std::getline(is, line))
    {
        if(!line.empty() && line.back() == '\r') line.pop_back();
        if(line == endTag) return true;
        lines.push_back(line);
    }
    return false;
}
}
