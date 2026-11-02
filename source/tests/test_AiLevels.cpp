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

#include "ai/AiMath.h"
#include "ai/AiSaveFormat.h"

#include <sstream>

#define BOOST_TEST_MODULE AiLevels
#include "BoostTestTargetConfig.h"

//! \brief Player ids follow the enum value of the five levels and the sixth id is the first human.
BOOST_AUTO_TEST_CASE(test_AiLevelPlayerIds)
{
    BOOST_CHECK_EQUAL(KeeperAITypes::toPlayerId(KeeperAIType::easy), 1);
    BOOST_CHECK_EQUAL(KeeperAITypes::toPlayerId(KeeperAIType::normal), 2);
    BOOST_CHECK_EQUAL(KeeperAITypes::toPlayerId(KeeperAIType::hard), 3);
    BOOST_CHECK_EQUAL(KeeperAITypes::toPlayerId(KeeperAIType::medium), 4);
    BOOST_CHECK_EQUAL(KeeperAITypes::toPlayerId(KeeperAIType::hell), 5);
    BOOST_CHECK_EQUAL(KeeperAITypes::toPlayerId(KeeperAIType::nbAI), 6);
}

//! \brief The aiLevel line is read when present and leaves the next token behind; old saves give nbAI.
BOOST_AUTO_TEST_CASE(test_AiLevelPeek)
{
    std::istringstream with("aiLevel hell next");
    std::string next;
    BOOST_CHECK(KeeperAITypes::readOptionalAiLevel(with, next) == KeeperAIType::hell);
    BOOST_CHECK_EQUAL(next, "next");

    std::istringstream without("next other");
    BOOST_CHECK(KeeperAITypes::readOptionalAiLevel(without, next) == KeeperAIType::nbAI);
    BOOST_CHECK_EQUAL(next, "next");
}

//! \brief The spell cooldown block round-trips, including the empty list.
BOOST_AUTO_TEST_CASE(test_SpellCooldownsRoundTrip)
{
    std::vector<std::pair<std::string, uint32_t>> written;
    written.push_back(std::make_pair(std::string("heal"), 12u));
    written.push_back(std::make_pair(std::string("tremor"), 340u));
    std::ostringstream out;
    SaveFormat::writeSpellCooldowns(out, written);
    std::istringstream in(out.str());
    std::string tag;
    in >> tag;
    std::vector<std::pair<std::string, uint32_t>> read;
    BOOST_CHECK(SaveFormat::readSpellCooldowns(in, read));
    BOOST_CHECK(read == written);

    std::ostringstream emptyOut;
    SaveFormat::writeSpellCooldowns(emptyOut, std::vector<std::pair<std::string, uint32_t>>());
    std::istringstream emptyIn(emptyOut.str());
    emptyIn >> tag;
    std::vector<std::pair<std::string, uint32_t>> emptyRead;
    BOOST_CHECK(SaveFormat::readSpellCooldowns(emptyIn, emptyRead));
    BOOST_CHECK(emptyRead.empty());
}

//! \brief Builds one saved AI state line from a tag and its tokens.
static AiMath::AiStateLine makeLine(const std::string& tag, const std::string& tokens)
{
    AiMath::AiStateLine line;
    line.tag = tag;
    std::istringstream input(tokens);
    std::string token;
    while(input >> token)
        line.tokens.push_back(token);
    return line;
}

//! \brief One line of every tag of the saved AI state survives format then parse; an unknown tag is rejected.
BOOST_AUTO_TEST_CASE(test_AiStateRoundTrip)
{
    std::vector<AiMath::AiStateLine> lines;
    lines.push_back(makeLine("look", "B01 12.5 1"));
    lines.push_back(makeLine("event", "alert 3.5 1 4 5 - -1 0 0 B02"));
    lines.push_back(makeLine("action", "build 2.5 B01 4 5 -"));
    lines.push_back(makeLine("click", "1.5 2"));
    lines.push_back(makeLine("hand", "0.5 3.5"));
    lines.push_back(makeLine("draw", "F01 trapWantDivided 1"));
    lines.push_back(makeLine("war", "tunnel digging 0.4 1 2 3 4 -1"));
    lines.push_back(makeLine("war", "assault moving running 10 -1"));
    lines.push_back(makeLine("war", "group 0 main 0 -1 -1 -1 5 6 2 Orc1 Orc2"));
    lines.push_back(makeLine("war", "target 0 0 7 8"));
    lines.push_back(makeLine("war", "defence rallying 9 10"));
    lines.push_back(makeLine("sighting", "seat 2 30 1 1 1 1 1 1"));
    lines.push_back(makeLine("sighting", "creature 2 Orc3 50 4"));
    lines.push_back(makeLine("sighting", "spell 2 60"));

    std::vector<AiMath::AiStateLine> parsed;
    BOOST_REQUIRE(AiMath::parseAiState(AiMath::formatAiState(lines), parsed));
    BOOST_REQUIRE_EQUAL(parsed.size(), lines.size());
    for(std::size_t i = 0; i < lines.size(); ++i)
    {
        BOOST_CHECK_EQUAL(parsed[i].tag, lines[i].tag);
        BOOST_CHECK(parsed[i].tokens == lines[i].tokens);
    }

    std::vector<std::string> unknown(1, "bogus\t1");
    std::vector<AiMath::AiStateLine> rejected;
    BOOST_CHECK(!AiMath::parseAiState(unknown, rejected));
}

//! \brief The mistake probability is base x row x level clipped into [min, max]; internal delays are zero.
BOOST_AUTO_TEST_CASE(test_MistakeFormulaAndDelays)
{
    BOOST_CHECK_CLOSE(AiMath::mistakeProbability(0.1, 2.0, 0.5, 0.004, 0.85), 0.1, 1e-9);
    BOOST_CHECK_CLOSE(AiMath::mistakeProbability(0.0001, 1.0, 1.0, 0.004, 0.85), 0.004, 1e-9);
    BOOST_CHECK_CLOSE(AiMath::mistakeProbability(0.5, 4.0, 1.0, 0.004, 0.85), 0.85, 1e-9);

    AiMath::DelayParams params = {20.0, 0.5, 60.0, 0.5, 5.0, 0.72, 0.217};
    AiMath::Uniform01 half = []() { return 0.5; }; // allowed-lambda: typed test stub
    BOOST_CHECK_EQUAL(AiMath::reactionDelay(AiMath::ReactionKind::internal, params, half), 0.0);
    BOOST_CHECK_EQUAL(AiMath::reactionDelay(AiMath::ReactionKind::hardLimit, params, half), 0.0);
    BOOST_CHECK(AiMath::reactionDelay(AiMath::ReactionKind::alert, params, half) > 0.0);
    BOOST_CHECK(AiMath::reactionDelay(AiMath::ReactionKind::symptom, params, half) > 0.0);
}
