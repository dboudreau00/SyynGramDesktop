/*
This file is part of Telegram Desktop / SyyngramDesktop.
Boxes of the vault, the 7-Zip password and the program a duress wipe starts.
*/
#pragma once

namespace Ui {
class GenericBox;
} // namespace Ui

namespace Window {
class SessionController;
} // namespace Window

namespace AyuUi {

void VaultEnableBox(
	not_null<Ui::GenericBox*> box,
	not_null<Window::SessionController*> controller,
	Fn<void()> changed);

void VaultDisableBox(
	not_null<Ui::GenericBox*> box,
	not_null<Window::SessionController*> controller,
	Fn<void()> changed);

void ZipPasswordBox(
	not_null<Ui::GenericBox*> box,
	not_null<Window::SessionController*> controller);

void DuressProgramBox(
	not_null<Ui::GenericBox*> box,
	not_null<Window::SessionController*> controller);

} // namespace AyuUi
