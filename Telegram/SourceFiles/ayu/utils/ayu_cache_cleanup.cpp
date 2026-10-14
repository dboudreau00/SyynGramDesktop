/*
This file is part of AyuGram / SyyngramDesktop.
Phase 0 scaffolding — Phase 1 implements deletion via SecureWipe::UnlinkOnly.
*/
#include "ayu/utils/ayu_cache_cleanup.h"

namespace Ayu::CacheCleanup {

Result run(const QString &workingDir, const Options &options) {
	Q_UNUSED(workingDir);
	Q_UNUSED(options);
	return {};
}

} // namespace Ayu::CacheCleanup
