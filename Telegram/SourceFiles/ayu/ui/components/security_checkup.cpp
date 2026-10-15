/*
This file is part of Telegram Desktop / SyyngramDesktop.
A short list of the protections this install has on, with a bar that fills as they are switched on.
*/
#include "ayu/ui/components/security_checkup.h"

#include "ayu/ayu_settings.h"
#include "core/application.h"
#include "core/core_settings.h"
#include "lottie/lottie_icon.h"
#include "main/main_domain.h"
#include "settings/settings_common.h"
#include "storage/storage_domain.h"
#include "storage/storage_duress.h"
#include "storage/storage_vault.h"
#include "ui/painter.h"
#include "lang_auto.h"
#include "settings.h"

#include "styles/style_ayu_styles.h"

#include <algorithm>

namespace {

constexpr auto kRefreshEach = crl::time(1500);

} // namespace

SecurityCheckup::SecurityCheckup(QWidget *parent)
: RpWidget(parent) {
	refresh();

	const auto &padding = st::syynSecurityPadding;
	const auto icon = st::syynSecurityIconSize;
	auto lottie = Settings::CreateLottieIcon(
		this,
		{
			.name = u"syyn_bolt_lock"_q,
			.sizeOverride = QSize(icon, icon),
		});
	_icon = std::move(lottie.widget);
	_animate = std::move(lottie.animate);
	_icon->setAttribute(Qt::WA_TransparentForMouseEvents);
	_icon->move(padding.left(), padding.top());
	_icon->show();

	setFixedHeight(padding.top()
		+ icon
		+ st::syynSecuritySkip
		+ int(_rows.size()) * st::syynSecurityRowHeight
		+ padding.bottom());

	shownValue(
	) | rpl::filter([](bool shown) {
		return shown;
	}) | rpl::take(1) | rpl::on_next([=] {
		_animate(anim::repeat::once);
	}, lifetime());

	const auto &ayu = AyuSettings::getInstance();
	rpl::merge(
		ayu.clearCacheOnStartupChanges() | rpl::to_empty,
		ayu.clearEmojiCacheOnStartupChanges() | rpl::to_empty,
		ayu.clearAyuDatabaseOnStartupChanges() | rpl::to_empty,
		ayu.strictDataFolderChanges() | rpl::to_empty,
		ayu.veilDelayChanges() | rpl::to_empty,
		Core::App().domain().local().localPasscodeChanged()
	) | rpl::on_next([=] {
		refresh();
	}, lifetime());

	// The duress password is set from a box and has no change signal of its own.
	_timer.setCallback([=] { refresh(); });
	_timer.callEach(kRefreshEach);
}

void SecurityCheckup::refresh() {
	const auto &ayu = AyuSettings::getInstance();
	const auto passcode = Core::App().domain().local().hasLocalPasscode();
	auto rows = std::vector<Row>{
		{ tr::syyn_CheckPasscode(tr::now), passcode },
		{
			tr::syyn_CheckAutoLock(tr::now),
			passcode && (Core::App().settings().autoLock() > 0),
		},
		{ tr::syyn_CheckDuress(tr::now), Storage::Duress::isConfigured() },
		{
			tr::syyn_CheckCache(tr::now),
			ayu.clearCacheOnStartup()
				|| ayu.clearEmojiCacheOnStartup()
				|| ayu.clearAyuDatabaseOnStartup(),
		},
		{ tr::syyn_CheckFolder(tr::now), ayu.strictDataFolder() },
		{ tr::syyn_CheckVeil(tr::now), (ayu.veilDelay() >= 0) },
		{ tr::syyn_CheckVault(tr::now), Storage::Vault::IsEnabled(cWorkingDir()) },
		{ tr::syyn_CheckWipe(tr::now), ayu.wipeAfterFailures() },
	};
	if (rows != _rows) {
		_rows = std::move(rows);
		update();
	}
}

int SecurityCheckup::doneCount() const {
	return int(std::count_if(_rows.begin(), _rows.end(), [](const Row &row) {
		return row.on;
	}));
}

void SecurityCheckup::mousePressEvent(QMouseEvent *e) {
	_animate(anim::repeat::once);
}

void SecurityCheckup::paintEvent(QPaintEvent *e) {
	auto p = QPainter(this);
	auto hq = PainterHighQualityEnabler(p);

	const auto &padding = st::syynSecurityPadding;
	const auto icon = st::syynSecurityIconSize;
	const auto textLeft = padding.left() + icon + st::syynSecuritySkip;
	const auto textWidth = width() - textLeft - padding.right();
	const auto done = doneCount();
	const auto total = int(_rows.size());

	const auto &titleFont = st::syynSecurityTitleFont;
	const auto block = titleFont->height
		+ st::syynSecurityBarSkip
		+ st::syynSecurityBarHeight;
	const auto titleTop = padding.top() + (icon - block) / 2;
	p.setFont(titleFont);
	p.setPen(st::windowBoldFg);
	p.drawText(
		textLeft,
		titleTop + titleFont->ascent,
		(done == total)
			? tr::syyn_SecurityAllOn(tr::now)
			: tr::syyn_SecuritySummary(
				tr::now,
				lt_done,
				QString::number(done),
				lt_total,
				QString::number(total)));

	const auto barTop = titleTop
		+ titleFont->height
		+ st::syynSecurityBarSkip;
	const auto radius = st::syynSecurityBarHeight / 2.;
	p.setPen(Qt::NoPen);
	p.setBrush(st::windowBgRipple);
	p.drawRoundedRect(
		QRectF(textLeft, barTop, textWidth, st::syynSecurityBarHeight),
		radius,
		radius);
	if (total > 0 && done > 0) {
		p.setBrush(st::windowBgActive);
		p.drawRoundedRect(
			QRectF(
				textLeft,
				barTop,
				textWidth * done / float64(total),
				st::syynSecurityBarHeight),
			radius,
			radius);
	}

	const auto &font = st::normalFont;
	auto y = padding.top() + icon + st::syynSecuritySkip;
	const auto dot = st::syynSecurityDot;
	for (const auto &row : _rows) {
		const auto middle = y + st::syynSecurityRowHeight / 2;
		const auto dotRect = QRectF(
			padding.left(),
			middle - dot / 2.,
			dot,
			dot);
		if (row.on) {
			p.setPen(Qt::NoPen);
			p.setBrush(st::windowBgActive);
		} else {
			p.setPen(QPen(st::windowSubTextFg, st::lineWidth));
			p.setBrush(Qt::NoBrush);
		}
		p.drawEllipse(dotRect);

		const auto baseline = y
			+ (st::syynSecurityRowHeight - font->height) / 2
			+ font->ascent;
		p.setFont(font);
		p.setPen(st::windowFg);
		p.drawText(padding.left() + dot + st::syynSecurityDotSkip, baseline, row.label);

		const auto status = row.on
			? tr::syyn_StatusOn(tr::now)
			: tr::syyn_StatusOff(tr::now);
		p.setPen(row.on ? st::windowActiveTextFg : st::windowSubTextFg);
		p.drawText(
			width() - padding.right() - font->width(status),
			baseline,
			status);
		y += st::syynSecurityRowHeight;
	}
}
