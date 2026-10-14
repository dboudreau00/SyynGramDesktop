/*
This file is part of Telegram Desktop / SyyngramDesktop.
Phase 2: duress password classify / wipe / purge orchestration.
*/
#pragma once

#include <QtCore/QByteArray>
#include <QtCore/QString>

namespace Storage::Duress {

inline constexpr int kLogoutTimeoutMs = 4000;
inline constexpr char kVerifierFileName[] = "syyngram_dv";

enum class PasscodeKind {
	Empty,
	Wrong,
	Flood,
	Real,
	Duress,
};

// Opaque verifier under tdata/ (does not alter key_* format for older builds).
[[nodiscard]] QString verifierPath();
[[nodiscard]] bool isConfigured();
[[nodiscard]] bool setDuressPasscode(
	const QByteArray &realPasscode,
	const QByteArray &duressPasscode);
[[nodiscard]] bool clearDuressPasscode(const QByteArray &realPasscode);
[[nodiscard]] bool matchesDuress(const QByteArray &utf8Passcode);

// Classify without side effects. Real check uses Domain when available.
[[nodiscard]] PasscodeKind classifyPasscode(const QByteArray &utf8Passcode);

// Warm MTP logout for all accounts, bounded by kLogoutTimeoutMs. Cold = no-op.
void bestEffortWarmLogout();

// Crypto-erase keys in memory when present, 1-pass wipe inventory, then
// schedule Windows self-uninstall helper and quit. Confined to inventory roots.
[[nodiscard]] bool runDuressSequence();

} // namespace Storage::Duress
