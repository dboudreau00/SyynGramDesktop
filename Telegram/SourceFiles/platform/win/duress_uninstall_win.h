/*
This file is part of Telegram Desktop / SyyngramDesktop.
Phase 2: Windows self-uninstall / purge helper after duress wipe.
*/
#pragma once

#include <QtCore/QString>

namespace Platform::DuressUninstall {

// Stage a hidden helper in %TEMP%, pass intent paths, quit this process.
// Helper waits for PID exit then deletes install/AppData/shortcuts/registry
// for both AyuGram and Syyngram names. Never elevates (no UAC prompt).
void schedulePurge(
	const QString &workingDir,
	const QString &exeDir);

} // namespace Platform::DuressUninstall
