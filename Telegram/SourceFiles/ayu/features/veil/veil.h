/*
This file is part of Telegram Desktop / SyyngramDesktop.
The privacy veil: a calm screen over the chats while the window is out of focus.
*/
#pragma once

namespace Syyn::Veil {

// Watches the application state and covers the windows after the configured delay.
void Start();

// Covers every window now, whatever the setting says.
void Cover();

[[nodiscard]] bool Covered();

} // namespace Syyn::Veil
