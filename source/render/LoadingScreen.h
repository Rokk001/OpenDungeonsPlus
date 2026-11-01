#ifndef LOADINGSCREEN_H
#define LOADINGSCREEN_H

#include <OgreResourceGroupManager.h>

namespace CEGUI { class Window; }
namespace Ogre { class RenderWindow; }

//! \brief Shows one session-selected loading picture and restores the previous presentation on failure.
class LoadingScreen : private Ogre::ResourceGroupListener
{
public:
    //! \brief Shows the loading picture and presents a frame before a blocking operation.
    explicit LoadingScreen(CEGUI::Window* existingStatus = nullptr);
    //! \brief Presents the same loading picture before the normal renderer and GUI exist.
    explicit LoadingScreen(Ogre::RenderWindow& startupWindow);
    //! \brief Removes the temporary startup viewport once the main menu scene is ready.
    static void finishStartup();
    //! \brief Pumps native events and presents only the startup picture during synchronous initialization.
    static void presentStartup();
    //! \brief Restores the presentation unless the asynchronous load is still in progress.
    ~LoadingScreen();
    //! \brief Keeps the picture until the client finishes loading or reports a failure.
    void continueLoading();
    //! \brief Restores the normal background and the existing interface after a load.
    static void finish();
    //! \brief Keeps the loading image fitted to the viewport while menus change or resize.
    static void update();

private:
    //! \brief Refreshes the startup picture between resource scripts without rendering unfinished scenes.
    void scriptParseEnded(const Ogre::String&, bool) override;
    //! \brief Refreshes the startup picture between resources loaded as a group.
    void resourceLoadEnded() override;
    //! \brief Prevents copying the guard that owns completion of a loading stage.
    LoadingScreen(const LoadingScreen&) = delete;
    //! \brief Prevents assigning completion ownership between loading guards.
    LoadingScreen& operator=(const LoadingScreen&) = delete;
    bool mContinueLoading;
    bool mStartup;
};

#endif
