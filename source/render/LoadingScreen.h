#ifndef LOADINGSCREEN_H
#define LOADINGSCREEN_H

#include <OgreResourceGroupManager.h>

namespace CEGUI { class Window; }
namespace Ogre { class RenderWindow; class OverlaySystem; }

//! \brief Shows one session-selected loading picture and restores the previous presentation on failure.
class LoadingScreen : private Ogre::ResourceGroupListener
{
public:
    //! \brief Shows the loading picture and presents a frame before a blocking operation.
    explicit LoadingScreen(CEGUI::Window* existingStatus = nullptr);
    //! \brief Presents the same loading picture before the normal renderer and GUI exist.
    explicit LoadingScreen(Ogre::RenderWindow& startupWindow, Ogre::OverlaySystem& overlaySystem);
    //! \brief Removes the temporary startup viewport once the main menu scene is ready.
    static void finishStartup();
    //! \brief Pumps native events and presents only the startup picture during synchronous initialization.
    //! A fraction of 0 or more first raises the real startup progress to that value.
    static void presentStartup(float progress = -1.0f);
    //! \brief Converts a count of finished startup stages (a fraction of a stage is allowed) to the progress fraction.
    static float startupFraction(float stagesDone);
    //! \brief The steps of loading a map into the game, in the order they really finish.
    enum LoadStep
    {
        LOAD_LEVEL_READ = 1,
        LOAD_SERVER_LISTENING,
        LOAD_CONNECTED,
        LOAD_MAP_RECEIVED,
        LOAD_ENTITIES_CREATED,
        LOAD_MODE_REQUESTED,
        LOAD_RENDERER_READY,
        LOAD_STEP_COUNT = LOAD_RENDERER_READY
    };
    //! \brief Reports a finished map load step: raises the progress to the finished share of all steps and redraws.
    static void loadStepDone(LoadStep step);
    //! \brief Restores the presentation unless the asynchronous load is still in progress.
    ~LoadingScreen();
    //! \brief Keeps the picture until the client finishes loading or reports a failure.
    void continueLoading();
    //! \brief Restores the normal background and the existing interface after a load.
    static void finish();
    //! \brief Sets the real load progress (0 to 1, never decreasing) and redraws so that the ring visibly grows.
    static void setProgress(float fraction);
    //! \brief Lets the resource groups initialized next fill the ring from one progress value to another.
    static void beginGroupProgress(float from, float to);
    //! \brief Keeps the loading image fitted to the viewport while menus change or resize.
    static void update();

private:
    //! \brief Starts counting the scripts of a resource group that is being initialized in the running span.
    void resourceGroupScriptingStarted(const Ogre::String&, size_t scriptCount) override;
    //! \brief Counts a finished resource group of the running span.
    void resourceGroupScriptingEnded(const Ogre::String&) override;
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
