#include "rooms/RoomInfirmary.h"
#include "entities/Creature.h"
#include "gamemap/GameMap.h"
#include "entities/Tile.h"
#include <iomanip>
#include <limits>
#include <istream>
#include <ostream>

//! \brief Saves cots, admissions and the incoming creature's current knockout countdown for reservations.
void RoomInfirmary::exportToStream(std::ostream& stream) const
{
    Room::exportToStream(stream);
    const std::streamsize precision = stream.precision();
    stream << std::setprecision(std::numeric_limits<double>::max_digits10);
    exportShamanToStream(stream);
    stream << "InfirmaryCots\t" << mCots.size() << '\n';
    std::map<size_t, size_t> indices;
    size_t index = 0;
    for(const std::pair<const size_t, CotInfo>& entry : mCots)
    {
        indices[entry.first] = index++;
        const CotInfo& cot = entry.second;
        stream << cot.size << '\t' << cot.x << '\t' << cot.y << '\t' << cot.rotation << '\n';
    }
    stream << "InfirmaryPatients\t" << mPatients.size() << '\n';
    for(const std::pair<const size_t, PatientInfo>& entry : mPatients)
    {
        const PatientInfo& patient = entry.second;
        const std::string name = patient.creature == nullptr ? patient.creatureName : patient.creature->getName();
        const std::string carrier = patient.reservedBy == nullptr ? patient.reservedByName : patient.reservedBy->getName();
        double storedCounter = patient.storedCounter;
        if(patient.creature == nullptr && !carrier.empty() && carrier != "none")
        {
            const Creature* incoming = getGameMap()->getCreature(name);
            if(incoming != nullptr)
                storedCounter = incoming->getKoTurnCounter();
        }
        stream << indices.at(entry.first) << '\t' << (name.empty() ? "none" : name) << '\t'
            << (carrier.empty() ? "none" : carrier) << '\t' << patient.admissionPaid << '\t'
            << patient.payer << '\t' << storedCounter << '\t' << patient.manual << '\n';
    }
    stream.precision(precision);
}

//! \brief Reads any order of optional room tags without consuming the next room's data.
bool RoomInfirmary::importFromStream(std::istream& stream)
{
    if(!Room::importFromStream(stream))
        return false;
    while(true)
    {
        const std::streampos position = stream.tellg();
        std::string tag;
        if(!(stream >> tag))
        {
            stream.clear();
            stream.seekg(position);
            break;
        }
        if(tag == "InfirmaryShaman")
        {
            stream.seekg(position);
            if(!importShamanFromStream(stream))
                return false;
        }
        else if(tag == "InfirmaryCots")
        {
            size_t count = 0;
            if(!(stream >> count))
                return false;
            mCots.clear();
            mNextCotId = 0;
            for(size_t index = 0; index < count; ++index)
            {
                CotInfo cot = {};
                if(!(stream >> cot.size >> cot.x >> cot.y >> cot.rotation) || cot.size < 1 || cot.size > 3)
                    return false;
                cot.width = cot.size == 3 ? 2 : 1;
                cot.height = cot.size == 1 ? 1 : 2;
                if(cot.size == 2 && (cot.rotation == 90.0 || cot.rotation == 270.0))
                {
                    cot.width = 2;
                    cot.height = 1;
                }
                for(int y = cot.y; y < cot.y + cot.height; ++y)
                    for(int x = cot.x; x < cot.x + cot.width; ++x)
                    {
                        Tile* tile = getGameMap()->getTile(x, y);
                        if(tile == nullptr)
                            return false;
                        cot.tiles.push_back(tile);
                    }
                mCots[mNextCotId++] = cot;
            }
            mLoadedCots = true;
        }
        else if(tag == "InfirmaryPatients")
        {
            size_t count = 0;
            if(!(stream >> count))
                return false;
            mPatients.clear();
            for(size_t index = 0; index < count; ++index)
            {
                size_t cot = 0;
                PatientInfo patient;
                if(!(stream >> cot >> patient.creatureName >> patient.reservedByName >> patient.admissionPaid >>
                    patient.payer >> patient.storedCounter >> patient.manual))
                    return false;
                if(patient.creatureName == "none") patient.creatureName.clear();
                if(patient.reservedByName == "none") patient.reservedByName.clear();
                mPatients[cot] = patient;
            }
        }
        else
        {
            stream.seekg(position);
            break;
        }
    }
    return true;
}
