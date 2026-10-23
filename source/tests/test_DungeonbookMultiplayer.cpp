/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
// Two clients and a late joiner receive the actual appearance token carried by creature snapshots.
// Whole images are selected by the same permanent number; no client composes, tints or rolls a portrait.
#define BOOST_TEST_MODULE DungeonbookMultiplayer
#include "BoostTestTargetConfig.h"
#include "game/CreatureAppearance.h"
#include "network/ODPacket.h"
#include "render/PortraitCatalog.h"
#include "render/DungeonbookQuirks.h"
#include <map>
#include <sstream>

namespace
{
typedef std::map<std::string, CreatureAppearance> ClientAppearances;

//! \brief Selects the first available image so snapshot fixtures stay deterministic.
uint32_t chooseFirstImage(uint32_t lower, uint32_t)
{
    return lower;
}

//! \brief Writes the same name/token pairs used by full creature data on join and load.
void writeSnapshot(ODPacket& packet, const ClientAppearances& server)
{
    packet << static_cast<uint32_t>(server.size());
    for(const ClientAppearances::value_type& creature : server)
        packet << creature.first << CreatureAppearanceLogic::toToken(creature.second);
}

//! \brief Reads server-owned image numbers; an empty token retains the unchanged fallback.
void readSnapshot(ODPacket& packet, ClientAppearances& client)
{
    uint32_t count = 0;
    BOOST_REQUIRE(packet >> count);
    for(uint32_t n = 0; n < count; ++n)
    {
        std::string name, token;
        BOOST_REQUIRE(packet >> name >> token);
        CreatureAppearance appearance;
        if(!token.empty())
            BOOST_REQUIRE(CreatureAppearanceLogic::fromToken(token, appearance));
        client[name] = appearance;
    }
}

//! \brief Requires identical server-selected image paths and stable painted-tag remarks.
void checkSameView(const PortraitCatalog& catalog, const DungeonbookQuirks& quirks,
    const ClientAppearances& server, const ClientAppearances& client)
{
    BOOST_REQUIRE(server == client);
    for(const ClientAppearances::value_type& creature : server)
    {
        if(creature.second.isEmpty())
            continue;
        const CreatureAppearance& received = client.find(creature.first)->second;
        BOOST_CHECK_EQUAL(catalog.findImage(received.getImageNumber())->mPath,
            catalog.findImage(creature.second.getImageNumber())->mPath);
        BOOST_CHECK(DungeonbookQuirkLogic::selectRemarks(quirks, catalog, received, creature.first) ==
            DungeonbookQuirkLogic::selectRemarks(quirks, catalog, creature.second, creature.first));
    }
}
}

//! \brief Keeps initial clients, late appearance notifications and late join/load snapshots identical.
BOOST_AUTO_TEST_CASE(two_clients_and_late_join_snapshot)
{
    PortraitCatalog catalog;
    std::istringstream images("1\t01.jpg\thair-swept,eyepatch\n2\t02.jpg\thair-braided,cigar\n");
    BOOST_REQUIRE(catalog.loadFromStream(images, "whole/Goblin.mesh/", "fixture"));
    DungeonbookQuirks quirks;
    std::istringstream texts("eyepatch\tDistrusts the other eye.\ncigar\tCounts smoke as strategy.\n");
    quirks.loadFromStream(texts, "fixture");
    ClientAppearances server;
    std::vector<CreatureAppearance> taken;
    for(uint32_t n = 0; n < 2; ++n)
    {
        CreatureAppearance next = CreatureAppearanceLogic::pickRandom(catalog, "Goblin.mesh",
            chooseFirstImage, taken);
        taken.push_back(next);
        server["Goblin" + std::to_string(n)] = next;
    }
    server["Plain"] = CreatureAppearance();
    ODPacket snapshot;
    writeSnapshot(snapshot, server);
    ODPacket second = snapshot;
    ClientAppearances a, b, late;
    readSnapshot(snapshot, a);
    readSnapshot(second, b);
    checkSameView(catalog, quirks, server, a);
    checkSameView(catalog, quirks, server, b);
    server["Latecomer"] = CreatureAppearanceLogic::pickStable(catalog, "Goblin.mesh", "Latecomer");
    ODPacket notification;
    notification << std::string("Latecomer") << CreatureAppearanceLogic::toToken(server["Latecomer"]);
    std::string notifiedName, token;
    BOOST_REQUIRE(notification >> notifiedName >> token);
    BOOST_REQUIRE(CreatureAppearanceLogic::fromToken(token, a[notifiedName]));
    ODPacket join;
    writeSnapshot(join, server);
    readSnapshot(join, late);
    checkSameView(catalog, quirks, server, late);
    BOOST_CHECK(a == late);
    BOOST_CHECK(late["Plain"].isEmpty());
}
