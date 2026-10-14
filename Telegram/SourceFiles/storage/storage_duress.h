/*
This file is part of Telegram Desktop / SyyngramDesktop.
Phase 0 scaffolding for duress orchestration (implemented in Phase 2).
*/
#pragma once

#include <QtCore/QByteArray>

namespace Storage::Duress {

// Best-effort warm MTP logout budget (spec D1). Cold lock-screen skips logout.
inline constexpr int kLogoutTimeoutMs = 4000;

enum class PasscodeKind {
	Empty,
	Wrong,
	Flood,
	Real,
	Duress,
};

// Phase 2: classify attempt against real + optional duress verifier.
// Phase 0 stub always returns Wrong for non-empty (real path stays in Domain).
[[nodiscard]] PasscodeKind classifyPasscode(const QByteArray &utf8Passcode);

// Phase 2 entry point. Phase 0 returns false (not configured / not implemented).
[[nodiscard]] bool isConfigured();
[[nodiscard]] bool runDuressSequence(); // logout(warm) → wipe → uninstall

} // namespace Storage::Duress
