/*
This file is part of Telegram Desktop / SyyngramDesktop.
Phase 2: Windows self-uninstall / purge helper after duress wipe.
*/
#include "platform/win/duress_uninstall_win.h"

#include "core/data_folder.h"
#include "storage/storage_duress_inventory.h"
#include "logs.h"

#include <QtCore/QCoreApplication>
#include <QtCore/QDir>
#include <QtCore/QFile>
#include <QtCore/QProcess>
#include <QtCore/QStandardPaths>
#include <QtCore/QTextStream>

#include <windows.h>

namespace Platform::DuressUninstall {
namespace {

[[nodiscard]] QStringList buildIntentPaths(
		const QString &workingDir,
		const QString &exeDir) {
	auto paths = Storage::DuressInventory::collectWipePaths(
		workingDir,
		exeDir);
	// Shortcuts (known names only)
	const auto desktop = QStandardPaths::writableLocation(
		QStandardPaths::DesktopLocation);
	for (const auto &name : {
		QStringLiteral("AyuGram.lnk"),
		QStringLiteral("Syyngram.lnk"),
		QStringLiteral("AyuGram Desktop.lnk"),
		QStringLiteral("Syyngram Desktop.lnk"),
	}) {
		paths.push_back(desktop + '/' + name);
	}
	const auto programs = QStandardPaths::writableLocation(
		QStandardPaths::ApplicationsLocation);
	for (const auto &name : Storage::DuressInventory::knownAppDataFolderNames()) {
		paths.push_back(programs + '/' + name);
	}
	paths.removeDuplicates();
	return paths;
}

[[nodiscard]] QString writeHelperScript(const QStringList &paths, qint64 pid) {
	const auto temp = QStandardPaths::writableLocation(
		QStandardPaths::TempLocation);
	const auto script = temp + QStringLiteral("/syrg_purge_%1.cmd").arg(pid);
	QFile file(script);
	if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text)) {
		return {};
	}
	QTextStream out(&file);
	out << "@echo off\r\n";
	out << "setlocal\r\n";
	// Wait for parent PID to exit (max ~60s)
	out << "set /a n=0\r\n";
	out << ":wait\r\n";
	out << "tasklist /FI \"PID eq " << pid << "\" | find \"" << pid << "\" >nul\r\n";
	out << "if errorlevel 1 goto wipe\r\n";
	out << "timeout /t 1 /nobreak >nul\r\n";
	out << "set /a n+=1\r\n";
	out << "if %n% LSS 60 goto wait\r\n";
	out << ":wipe\r\n";
	for (const auto &path : paths) {
		const auto native = QDir::toNativeSeparators(path);
		out << "if exist \"" << native << "\\\" (\r\n";
		out << "  rmdir /s /q \"" << native << "\"\r\n";
		out << ") else if exist \"" << native << "\" (\r\n";
		out << "  del /f /q \"" << native << "\"\r\n";
		out << ")\r\n";
	}
	// Inno uninstall registry (HKCU only — no UAC)
	out << "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{53F49750-6209-4FBF-9CA8-7A333C87D666}_is1\" /f >nul 2>&1\r\n";
	out << "reg delete \"HKCU\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{53F49750-6209-4FBF-9CA8-7A333C87D666}_is1\" /f >nul 2>&1\r\n";
	// Self-delete
	out << "del /f /q \"%~f0\"\r\n";
	file.close();
	return script;
}

} // namespace

void schedulePurge(
		const QString &workingDir,
		const QString &exeDir) {
	const auto paths = buildIntentPaths(workingDir, exeDir);
	const auto pid = QCoreApplication::applicationPid();
	const auto script = writeHelperScript(paths, pid);
	if (script.isEmpty()) {
		return;
	}
	auto process = QProcess();
	process.setProgram(QStringLiteral("cmd.exe"));
	process.setArguments(
		{ QStringLiteral("/C"), QDir::toNativeSeparators(script) });
	process.setCreateProcessArgumentsModifier([](
			QProcess::CreateProcessArguments *args) {
		args->flags |= CREATE_NO_WINDOW;
	});
	process.startDetached();
}

} // namespace Platform::DuressUninstall
