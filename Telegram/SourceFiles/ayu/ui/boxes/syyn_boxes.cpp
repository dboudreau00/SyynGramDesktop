/*
This file is part of Telegram Desktop / SyyngramDesktop.
Boxes of the vault, the 7-Zip password and the program a duress wipe starts.
*/
#include "ayu/ui/boxes/syyn_boxes.h"

#include "ayu/ayu_settings.h"
#include "base/weak_ptr.h"
#include "core/file_utilities.h"
#include "storage/storage_vault.h"
#include "ui/layers/generic_box.h"
#include "ui/widgets/fields/input_field.h"
#include "ui/widgets/fields/password_input.h"
#include "ui/widgets/labels.h"
#include "ui/rp_widget.h"
#include "ui/ui_utility.h"
#include "window/window_controller.h"
#include "window/window_session_controller.h"
#include "lang_auto.h"
#include "settings.h"

#include "styles/style_boxes.h"
#include "styles/style_layers.h"

#include <QtCore/QDir>
#include <QtCore/QFileInfo>

namespace AyuUi {
namespace {

constexpr auto kMinimumPasswordLength = 8;
constexpr auto kMaximumPasswordLength = 256;

not_null<Ui::PasswordInput*> AddPasswordField(
		not_null<Ui::GenericBox*> box,
		const QString &placeholder) {
	const auto &st = st::defaultInputField;
	auto container = object_ptr<Ui::RpWidget>(box.get());
	container->resize(container->width(), st.heightMin);
	const auto field = Ui::CreateChild<Ui::PasswordInput>(
		container.data(),
		st,
		rpl::single(placeholder));
	container->geometryValue(
	) | rpl::on_next([=](const QRect &r) {
		field->resize(r.width(), field->height());
		field->moveToLeft(0, 0);
	}, container->lifetime());
	box->addRow(std::move(container));
	return field;
}

void AddNote(not_null<Ui::GenericBox*> box, const QString &text) {
	box->addRow(object_ptr<Ui::FlatLabel>(
		box.get(),
		rpl::single(text),
		st::boxLabel));
}

[[nodiscard]] bool IsProgram(const QString &path) {
	const auto info = QFileInfo(path);
#ifdef Q_OS_WIN
	return info.isFile()
		&& info.suffix().compare(QLatin1String("exe"), Qt::CaseInsensitive) == 0;
#else // Q_OS_WIN
	return info.isFile() && info.isExecutable();
#endif // !Q_OS_WIN
}

// Wiped before the program starts, so it would never run.
[[nodiscard]] bool IsInsideWipedFolder(const QString &path) {
	const auto clean = QDir::cleanPath(QDir::fromNativeSeparators(path));
	const auto inside = [&](const QString &root) {
		const auto base = QDir::cleanPath(QDir::fromNativeSeparators(root));
		return !base.isEmpty()
			&& clean.startsWith(base + '/', Qt::CaseInsensitive);
	};
	return inside(cWorkingDir()) || inside(cExeDir());
}

// 7-Zip reads the password from the console in the OEM code page, so keep to plain keyboard characters.
[[nodiscard]] bool IsPlainPassword(const QString &text) {
	for (const auto ch : text) {
		if (ch.unicode() < 0x20 || ch.unicode() > 0x7E) {
			return false;
		}
	}
	return true;
}

} // namespace

void VaultEnableBox(
		not_null<Ui::GenericBox*> box,
		not_null<Window::SessionController*> controller,
		Fn<void()> changed) {
	box->setTitle(rpl::single(QString("Encrypt data when closed")));
	AddNote(
		box,
		QString(
			"Your chats and your login are encrypted with this password when the app "
			"closes, and opened again when you start it. There is no recovery: if you "
			"forget the password you sign in again. If the app is killed instead of "
			"closed, the data stays readable until the next normal close."));
	const auto first = AddPasswordField(box, QString("New password"));
	const auto second = AddPasswordField(box, QString("Repeat the password"));
	const auto save = [=] {
		const auto text = first->getLastText();
		const auto password = text.toUtf8();
		if (text.size() < kMinimumPasswordLength) {
			first->showError();
			controller->showToast(QString("Use at least 8 characters."));
			return;
		} else if (text.size() > kMaximumPasswordLength) {
			first->showError();
			controller->showToast(QString("Use at most 256 characters."));
			return;
		} else if (password != second->getLastText().toUtf8()) {
			second->showError();
			return;
		}
		if (!Storage::Vault::Enable(cWorkingDir(), password)) {
			controller->showToast(QString("The vault could not be turned on."));
			return;
		}
		controller->showToast(QString("The vault is on. Your data is encrypted when you close the app."));
		box->closeBox();
		if (changed) {
			changed();
		}
	};
	box->addButton(tr::lng_settings_save(), save);
	box->addButton(tr::lng_cancel(), [=] { box->closeBox(); });
}

void VaultDisableBox(
		not_null<Ui::GenericBox*> box,
		not_null<Window::SessionController*> controller,
		Fn<void()> changed) {
	box->setTitle(rpl::single(QString("Turn the vault off")));
	AddNote(box, QString("Enter the vault password. Your data will stay readable on disk."));
	const auto field = AddPasswordField(box, QString("Vault password"));
	const auto save = [=] {
		if (!Storage::Vault::Disable(cWorkingDir(), field->getLastText().toUtf8())) {
			field->showError();
			return;
		}
		controller->showToast(QString("The vault is off."));
		box->closeBox();
		if (changed) {
			changed();
		}
	};
	box->addButton(tr::lng_settings_save(), save);
	box->addButton(tr::lng_cancel(), [=] { box->closeBox(); });
}

void ZipPasswordBox(
		not_null<Ui::GenericBox*> box,
		not_null<Window::SessionController*> controller) {
	box->setTitle(rpl::single(QString("Zip password")));
	AddNote(
		box,
		QString(
			"Files you save with Save As are packed into a .7z with this password and "
			"encrypted file names. It is kept in the settings file, so turn the vault "
			"on if the file must not be readable. Leave it empty to clear it."));
	const auto field = box->addRow(object_ptr<Ui::InputField>(
		box.get(),
		st::defaultInputField,
		rpl::single(QString("Password")),
		AyuSettings::getInstance().zipPassword()));
	const auto save = [=] {
		if (!IsPlainPassword(field->getLastText())) {
			field->showError();
			controller->showToast(QString("Use basic keyboard characters only."));
			return;
		}
		AyuSettings::getInstance().setZipPassword(field->getLastText());
		controller->showToast(QString(field->getLastText().isEmpty()
			? "Zip password cleared"
			: "Zip password saved"));
		box->closeBox();
	};
	box->addButton(tr::lng_settings_save(), save);
	box->addButton(tr::lng_cancel(), [=] { box->closeBox(); });
}

void DuressProgramBox(
		not_null<Ui::GenericBox*> box,
		not_null<Window::SessionController*> controller) {
	box->setTitle(rpl::single(QString("Program to start on duress")));
	AddNote(
		box,
		QString(
			"After a duress wipe this program is started on its own, then the app exits. "
			"Choose a program that is not inside the app's folders."));
	const auto current = AyuSettings::getInstance().duressLaunchPath();
	AddNote(box, current.isEmpty() ? QString("None chosen") : current);
	const auto weak = base::make_weak(box);
	box->addButton(rpl::single(QString("Choose program")), [=] {
		FileDialog::GetOpenPath(
			controller->window().widget().get(),
			QString("Choose a program"),
			QString("Programs (*.exe);;All files (*)"),
			[=](FileDialog::OpenResult &&result) {
				if (result.paths.isEmpty()) {
					return;
				}
				const auto path = QDir::toNativeSeparators(result.paths.front());
				if (!IsProgram(path)) {
					controller->showToast(QString("That is not a program."));
					return;
				} else if (IsInsideWipedFolder(path)) {
					controller->showToast(QString("Choose a program outside the app's folders."));
					return;
				}
				AyuSettings::getInstance().setDuressLaunchPath(path);
				controller->showToast(QString("Saved."));
				if (const auto strong = weak.get()) {
					strong->closeBox();
				}
			});
	});
	if (!current.isEmpty()) {
		box->addButton(rpl::single(QString("Remove")), [=] {
			AyuSettings::getInstance().setDuressLaunchPath(QString());
			controller->showToast(QString("Removed."));
			box->closeBox();
		});
	}
	box->addButton(tr::lng_close(), [=] { box->closeBox(); });
}

} // namespace AyuUi
