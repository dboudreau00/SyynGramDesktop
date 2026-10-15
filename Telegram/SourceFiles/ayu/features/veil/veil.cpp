/*
This file is part of Telegram Desktop / SyyngramDesktop.
The privacy veil: a calm screen over the chats while the window is out of focus.
*/
#include "ayu/features/veil/veil.h"

#include "ayu/ayu_settings.h"
#include "base/timer.h"
#include "core/application.h"
#include "lottie/lottie_icon.h"
#include "main/main_domain.h"
#include "settings/settings_common.h"
#include "storage/storage_domain.h"
#include "ui/effects/animations.h"
#include "ui/painter.h"
#include "ui/rp_widget.h"
#include "window/window_controller.h"
#include "lang_auto.h"
#include "mainwindow.h"

#include "styles/style_ayu_styles.h"

#include <algorithm>
#include <array>

#include <QtCore/QPointer>
#include <QtGui/QGuiApplication>
#include <QtGui/QKeyEvent>
#include <QtGui/QRadialGradient>

namespace Syyn::Veil {
namespace {

constexpr auto kFadeDuration = crl::time(180);
constexpr auto kKeepOnTopEach = crl::time(250);
constexpr auto kGlowAlpha = 26;

class Overlay final : public Ui::RpWidget {
public:
	explicit Overlay(not_null<Ui::RpWidget*> body);

	void dismiss();

protected:
	void paintEvent(QPaintEvent *e) override;
	void mousePressEvent(QMouseEvent *e) override;
	void keyPressEvent(QKeyEvent *e) override;

private:
	void layoutContent();

	Ui::Animations::Simple _shown;
	base::Timer _keepOnTop;
	object_ptr<Ui::RpWidget> _icon = { nullptr };
	bool _closing = false;

};

void DrawWordmark(QPainter &p, int outerWidth, int top) {
	const auto &font = st::syynVeilNameFont;
	const auto yyn = u"YYN"_q;
	const auto gram = u"GRAM"_q;
	// The bolt stands in for the S: a little taller than the capitals and wide as a letter.
	const auto capHeight = font->metrics().capHeight();
	const auto boltHeight = capHeight * 115 / 100;
	const auto boltTop = top
		+ font->ascent
		- capHeight
		- (boltHeight - capHeight) / 2;
	const auto stretch = 1.8;
	const auto boltWidth = qRound(boltHeight * 16 / 54. * stretch);
	const auto skip = font->spacew / 2;
	const auto total = boltWidth + skip + font->width(yyn) + font->width(gram);
	auto x = (outerWidth - total) / 2;

	const auto points = std::array<QPointF, 7>{ {
		{ 15.5, 1. }, { 4., 31. }, { 11.6, 29.4 }, { 7., 55. },
		{ 20.5, 21. }, { 12.9, 22.8 }, { 18.6, 1. },
	} };
	const auto scale = boltHeight / 54.;
	auto path = QPainterPath();
	for (auto i = 0; i != int(points.size()); ++i) {
		const auto point = QPointF(
			x + (points[i].x() - 4.) * scale * stretch,
			boltTop + (points[i].y() - 1.) * scale);
		(i ? path.lineTo(point) : path.moveTo(point));
	}
	path.closeSubpath();
	auto hq = PainterHighQualityEnabler(p);
	p.setPen(Qt::NoPen);
	p.setBrush(st::windowActiveTextFg);
	p.drawPath(path);

	x += boltWidth + skip;
	p.setFont(font);
	p.setPen(st::windowFg);
	p.drawText(x, top + font->ascent, yyn);
	x += font->width(yyn);
	p.setPen(st::windowActiveTextFg);
	p.drawText(x, top + font->ascent, gram);
}

[[nodiscard]] std::vector<QPointer<Overlay>> &Overlays() {
	static auto result = std::vector<QPointer<Overlay>>();
	return result;
}

Overlay::Overlay(not_null<Ui::RpWidget*> body)
: RpWidget(body) {
	setFocusPolicy(Qt::StrongFocus);

	auto icon = Settings::CreateLottieIcon(
		this,
		{
			.name = u"syyn_bolt_pulse"_q,
			.sizeOverride = QSize(st::syynVeilIconSize, st::syynVeilIconSize),
		});
	_icon = std::move(icon.widget);
	_icon->setAttribute(Qt::WA_TransparentForMouseEvents);

	body->sizeValue(
	) | rpl::on_next([=](QSize size) {
		setGeometry(QRect(QPoint(), size));
		layoutContent();
	}, lifetime());

	// A box or a toast opened while the veil is up must not end up above it.
	_keepOnTop.setCallback([=] { raise(); });
	_keepOnTop.callEach(kKeepOnTopEach);

	show();
	raise();
	setFocus();
	_icon->show();
	icon.animate(anim::repeat::loop);
	_shown.start([=] { update(); }, 0., 1., kFadeDuration);
}

void Overlay::layoutContent() {
	const auto content = st::syynVeilIconSize
		+ st::syynVeilNameSkip
		+ st::syynVeilNameFont->height
		+ st::syynVeilHintSkip
		+ st::normalFont->height;
	const auto top = std::max((height() - content) / 2, 0);
	_icon->move((width() - _icon->width()) / 2, top);
}

void Overlay::paintEvent(QPaintEvent *e) {
	auto p = QPainter(this);
	p.setOpacity(_shown.value(_closing ? 0. : 1.));
	p.fillRect(rect(), st::windowBg);

	const auto center = QPointF(width() / 2., height() / 2.);
	auto glow = QRadialGradient(center, st::syynVeilGlowRadius);
	auto accent = st::windowBgActive->c;
	accent.setAlpha(kGlowAlpha);
	glow.setColorAt(0., accent);
	accent.setAlpha(0);
	glow.setColorAt(1., accent);
	p.fillRect(rect(), glow);

	const auto nameTop = _icon->y() + _icon->height() + st::syynVeilNameSkip;
	DrawWordmark(p, width(), nameTop);

	const auto hintTop = nameTop
		+ st::syynVeilNameFont->height
		+ st::syynVeilHintSkip;
	p.setFont(st::normalFont);
	p.setPen(st::windowSubTextFg);
	p.drawText(
		QRect(0, hintTop, width(), st::normalFont->height),
		Qt::AlignHCenter | Qt::AlignTop,
		tr::syyn_VeilHint(tr::now));
}

void Overlay::mousePressEvent(QMouseEvent *e) {
	dismiss();
}

void Overlay::keyPressEvent(QKeyEvent *e) {
	dismiss();
}

void Overlay::dismiss() {
	if (_closing) {
		return;
	}
	_closing = true;
	_shown.start([=] {
		update();
		if (!_shown.animating()) {
			deleteLater();
		}
	}, 1., 0., kFadeDuration);
	if (const auto window = Core::App().activeWindow()) {
		window->widget()->setInnerFocus();
	}
}

} // namespace

bool Covered() {
	auto &all = Overlays();
	all.erase(
		std::remove_if(all.begin(), all.end(), [](const QPointer<Overlay> &o) {
			return o.isNull();
		}),
		all.end());
	return !all.empty();
}

void Cover() {
	if (!Core::IsAppLaunched()
		|| Core::Quitting()
		|| Core::App().passcodeLocked()) {
		return;
	}
	Core::App().enumerateWindows([&](not_null<Window::Controller*> window) {
		const auto body = window->widget()->bodyWidget();
		if (!body) {
			return;
		}
		for (const auto &existing : Overlays()) {
			if (existing && existing->parentWidget() == body) {
				return;
			}
		}
		Overlays().push_back(QPointer<Overlay>(new Overlay(body)));
	});
	const auto &settings = AyuSettings::getInstance();
	if (settings.veilLock()
		&& Core::App().domain().local().hasLocalPasscode()) {
		Core::App().lockByPasscode();
	}
}

void Start() {
	// WHY: lives until the process ends; a static would be destroyed after the QApplication is gone.
	const auto timer = new base::Timer([] {
		if (QGuiApplication::applicationState() != Qt::ApplicationActive) {
			Cover();
		}
	});
	QObject::connect(
		qGuiApp,
		&QGuiApplication::applicationStateChanged,
		qGuiApp,
		[=](Qt::ApplicationState state) {
			timer->cancel();
			if (state == Qt::ApplicationActive) {
				return;
			}
			const auto delay = AyuSettings::getInstance().veilDelay();
			if (delay < 0) {
				return;
			} else if (delay == 0) {
				Cover();
			} else {
				timer->callOnce(delay * crl::time(1000));
			}
		});
}

} // namespace Syyn::Veil
