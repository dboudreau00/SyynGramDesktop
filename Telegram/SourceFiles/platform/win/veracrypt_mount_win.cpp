/*
This file is part of Telegram Desktop / SyyngramDesktop.
Phase 4: VeraCrypt CLI mount helper (Windows).
*/
#include "platform/win/veracrypt_mount_win.h"

#include "logs.h"

#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QProcess>
#include <QtCore/QStandardPaths>

namespace Platform::VeraCrypt {
namespace {

[[nodiscard]] QStringList candidatePaths() {
	QStringList out;
	const auto pf = qEnvironmentVariable("ProgramFiles");
	const auto pf86 = qEnvironmentVariable("ProgramFiles(x86)");
	for (const auto &base : { pf, pf86 }) {
		if (!base.isEmpty()) {
			out.push_back(base + QStringLiteral("/VeraCrypt/VeraCrypt.exe"));
		}
	}
	out.push_back(QStringLiteral("C:/Program Files/VeraCrypt/VeraCrypt.exe"));
	out.push_back(QStringLiteral("C:/Program Files (x86)/VeraCrypt/VeraCrypt.exe"));
	return out;
}

} // namespace

QString findExecutable() {
	for (const auto &path : candidatePaths()) {
		if (QFileInfo::exists(path)) {
			return QDir::toNativeSeparators(path);
		}
	}
	const auto onPath = QStandardPaths::findExecutable(
		QStringLiteral("VeraCrypt.exe"));
	if (!onPath.isEmpty()) {
		return QDir::toNativeSeparators(onPath);
	}
	return {};
}

MountResult mountVolume(const MountRequest &request) {
	auto exe = request.veracryptExe;
	if (exe.isEmpty()) {
		exe = findExecutable();
	}
	if (exe.isEmpty()) {
		return { false, QStringLiteral("VeraCrypt.exe not found") };
	}
	if (request.volumePath.isEmpty() || request.driveLetter.isEmpty()) {
		return { false, QStringLiteral("Volume and drive letter required") };
	}
	auto letter = request.driveLetter;
	letter.remove(QLatin1Char(':'));
	letter = letter.left(1).toUpper();

	// /q /s quiet; password via VeraCrypt UI (no /p).
	const auto args = QStringList{
		QStringLiteral("/v"),
		QDir::toNativeSeparators(request.volumePath),
		QStringLiteral("/l"),
		letter,
		QStringLiteral("/q"),
		QStringLiteral("/s"),
	};
	LOG(("VeraCrypt: launching mount helper"));
	if (!QProcess::startDetached(exe, args)) {
		return { false, QStringLiteral("Failed to launch VeraCrypt") };
	}
	return { true, QStringLiteral("VeraCrypt mount started") };
}

} // namespace Platform::VeraCrypt
