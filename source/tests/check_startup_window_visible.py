#!/usr/bin/env python3
"""Check that the window created hidden at startup is shown again and that this is logged.

Ogre's RenderWindow::setVisible() does nothing on Win32; only setHidden(false) undoes the
"hidden" creation parameter. Without it the game runs with sound but shows no picture.

Note for the integrator: the deploy test must prove that the window is visible, not only
that the process runs. Required evidence: the line "window shown" in Opendungeons.log AND
the game window visible through Win32 (IsWindowVisible on its handle, or a screenshot).
"""
from pathlib import Path

SHOWN_LOG = 'OD_LOG_INF("window shown");'


# Verify the hidden creation is always followed by setHidden(false) and the log line.
def main():
    root = Path(__file__).resolve().parents[2]
    application = (root / "source/ODApplication.cpp").read_text(encoding="utf-8")
    hidden = application.index('misc["hidden"] = "true";')
    show = application.index("renderWindow->setHidden(false);", hidden)
    logged = application.index(SHOWN_LOG, show)
    assert application.count('misc["hidden"] = "true";') == 1, "unexpected second hidden window creation"
    assert application.count(SHOWN_LOG) == 1, "the line 'window shown' must be written exactly once"
    startup = application.index("LoadingScreen startupLoading(*renderWindow);", hidden)
    assert startup < show, "show the window only after the first loading frame exists"
    resources = application.index("resMgr.setupOgreResources(", show)
    assert startup < application.index('sf::WindowBase sfmlWindow(nativeHandle);') < show, "SFML must attach to the already painted hidden native window"
    assert "sf::RenderWindow sfmlWindow(" not in application, "SFML must not create a visible window before painting"
    assert show < application.index("LoadingScreen::presentStartup();", show) < logged, "repaint after showing the window"
    assert logged < application.index("if (!Ogre::RTShader::ShaderGenerator::initialize())"), "show before RTSS initialization"
    assert logged < resources, "the window must be shown before blocking resource initialization"
    assert application.count("renderWindow->setHidden(false);") == 1, "exactly one place may show the startup window"
    print("OK: hidden startup window is shown with setHidden(false) and logged as 'window shown'")


if __name__ == "__main__":
    main()
