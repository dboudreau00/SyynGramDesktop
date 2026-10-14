/*
This file is part of AyuGram / SyyngramDesktop.
Phase 0: read a few flags from tdata/ayu_settings.json before full AyuSettings load.
*/
#pragma once

#include <QtCore/QString>

namespace AyuSettingsEarly {

struct Flags {
	bool clearCacheOnStartup = false;
	bool clearEmojiCacheOnStartup = false;
	bool clearAyuDatabaseOnStartup = false;
	bool strictDataFolder = false;
	// Scaffolding: duress itself lives in the domain key file (Phase 2).
	// This flag is only a settings-UI placeholder / “feature enabled in builds”.
	bool duressFeatureReady = false;
};

// settingsPath empty → cWorkingDir() + "tdata/ayu_settings.json"
[[nodiscard]] Flags read(const QString &settingsPath = {});

[[nodiscard]] QString defaultSettingsPath();

} // namespace AyuSettingsEarly
