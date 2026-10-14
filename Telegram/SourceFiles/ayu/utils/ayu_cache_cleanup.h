/*
This file is part of AyuGram / SyyngramDesktop.
Phase 0 scaffolding; Phase 1 implements startup cache removal.
*/
#pragma once

#include <QtCore/QString>

namespace Ayu::CacheCleanup {

struct Options {
	bool clearCache = true;
	bool clearEmoji = false;
	bool clearAyuDatabase = false;
};

struct Result {
	int removed = 0;
	int skipped = 0;
};

// Phase 0: no-op returning zeros. Phase 1 deletes cache/media_cache/temp.
[[nodiscard]] Result run(const QString &workingDir, const Options &options);

} // namespace Ayu::CacheCleanup
