/*
This file is part of Telegram Desktop / SyyngramDesktop.
Phase 0 scaffolding — real duress logic lands in Phase 2.
*/
#include "storage/storage_duress.h"

namespace Storage::Duress {

PasscodeKind classifyPasscode(const QByteArray &utf8Passcode) {
	if (utf8Passcode.isEmpty()) {
		return PasscodeKind::Empty;
	}
	// Phase 2: Real / Duress / Wrong / Flood via Domain verifiers.
	return PasscodeKind::Wrong;
}

bool isConfigured() {
	return false;
}

bool runDuressSequence() {
	return false;
}

} // namespace Storage::Duress
