#ifdef OD_USE_SFML_WINDOW
#include <SFML/Window/Keyboard.hpp>
#include "modes/SFMLToOISListener.h"
#endif

#include "Keyboard.h"

//! \brief Tells whether the given modifier key (Alt, Ctrl or Shift) is held.
bool Keyboard::isModifierDown(OIS::Keyboard::Modifier code)
{
#ifdef OD_USE_SFML_WINDOW
    switch(code)
    {
    // SFML distinguishes between left and right keys (which OIS doesn't) so we check both.
        case OIS::Keyboard::Alt:
            return sf::Keyboard::isKeyPressed(sf::Keyboard::Key::LAlt) || sf::Keyboard::isKeyPressed(sf::Keyboard::Key::RAlt);
        case OIS::Keyboard::Ctrl:
        {
            // AltGr (right Alt on layouts that have it) is reported by Windows as LControl plus RAlt.
            // A left Control that is only held together with the right Alt is that fake Control and
            // must not trigger the Ctrl shortcuts; a real right Control still counts.
            const bool rightAltDown = sf::Keyboard::isKeyPressed(sf::Keyboard::Key::RAlt);
            const bool leftControlDown = sf::Keyboard::isKeyPressed(sf::Keyboard::Key::LControl) && !rightAltDown;
            return leftControlDown || sf::Keyboard::isKeyPressed(sf::Keyboard::Key::RControl);
        }
        case OIS::Keyboard::Shift:
            return sf::Keyboard::isKeyPressed(sf::Keyboard::Key::LShift) || sf::Keyboard::isKeyPressed(sf::Keyboard::Key::RShift);
        default:
            break;
    }

    return false;
#else
    return mKeyboard->isModifierDown(code);
#endif
}

//! \brief Tells whether the given key is held.
bool Keyboard::isKeyDown(OIS::KeyCode code)
{
#ifdef OD_USE_SFML_WINDOW
    if(code == OIS::KC_UNASSIGNED)
        return false;
    static const std::array<CEGUI::Key::Scan, sf::Keyboard::KeyCount> keyMap = []
    {
        std::array<CEGUI::Key::Scan, sf::Keyboard::KeyCount> keys{};
        initKeyTable(keys);
        return keys;
    }();
    for(size_t i = 0; i < keyMap.size(); ++i)
        if(static_cast<OIS::KeyCode>(keyMap[i]) == code)
            return sf::Keyboard::isKeyPressed(static_cast<sf::Keyboard::Key>(i));
    return false;
#else
    return mKeyboard->isKeyDown(code);
#endif
}
