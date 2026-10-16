"""Build the Syyngram themes (.tdesktop-theme packages) from the client-kit palette.

Usage (from the repository root):
    python tools/syyn_assets/make_themes.py --stock <dir> [--out Telegram/Resources] [--report]

`--stock` is a folder holding the stock theme files unpacked as <name>/colors.tdesktop-theme
(night, day-custom-base). Every key of the stock palette is carried over, so a theme never falls
back to a stock blue by accident: roles below set the colours that matter, and the remaining
blue/teal keys are re-mapped onto the gold ramp by lightness. Semantic reds, greens and the
per-peer name colours are left alone.

Themes written:
    night.tdesktop-theme, night-custom-base.tdesktop-theme   Ember    (dark, the default night)
    night-green.tdesktop-theme                                Obsidian (OLED black)
    day-blue.tdesktop-theme, day-custom-base.tdesktop-theme  Vellum   (light, parchment)
"""
from __future__ import annotations

import argparse
import colorsys
import io
import math
import os
import re
import sys
import zipfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from syyn_common import BOLT_BOX, BOLT_POINTS  # noqa: E402

LINE = re.compile(r"^(\s*)([A-Za-z0-9_]+):\s*([^;]+);(.*)$")
HEX = re.compile(r"^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")

# ---------------------------------------------------------------------------------------------
# Tokens

INK = "#0B0907"      # text on gold
CREAM = "#FFF6DD"    # the bolt
SAND50, SAND100, SAND300, SAND400, SAND500 = "#F3ECDD", "#E6DCC6", "#B8A988", "#9A8B70", "#6C604C"
G200, G300, G400, G500, G600, G700 = "#F7E6B5", "#F1D589", "#E2B85A", "#C9A24A", "#A9842F", "#7D6122"

DARK_RAMP = [  # lightness -> colour, used for leftover blue/teal keys in the dark themes
    (0.00, "#050403"), (0.07, "#100D09"), (0.12, "#1D1811"), (0.20, "#2A2318"), (0.28, "#3A3022"),
    (0.38, "#7D6122"), (0.47, "#A9842F"), (0.58, "#C9A24A"), (0.70, "#E2B85A"), (0.82, "#F1D589"),
    (0.93, "#F7E6B5"), (1.00, "#FFF6DD"),
]
LIGHT_RAMP = [  # the same idea for Vellum: light lightness stays light, saturated blues become gold
    (0.00, "#1D1811"), (0.25, "#5B4417"), (0.40, "#7D6122"), (0.50, "#A9842F"), (0.60, "#C9A24A"),
    (0.72, "#E2B85A"), (0.84, "#F1D589"), (0.92, "#F7E6B5"), (0.96, "#F3ECDD"), (1.00, "#FBF7EE"),
]


def ember_tokens() -> dict[str, str]:
    return dict(
        rail="#050403", win="#100D09", box="#15110C", over="#1D1811", ripple="#2A2318", line="#3A3022",
        wall="#0B0907", bub_in="#1D1811", bub_in_sel="#3A3022", title="#0B0907", title_active="#100D09",
        service_bg="#2A2318d9", header="#15110C",
    )


def obsidian_tokens() -> dict[str, str]:
    return dict(
        rail="#000000", win="#050403", box="#0B0907", over="#15110C", ripple="#1D1811", line="#2A2318",
        wall="#000000", bub_in="#15110C", bub_in_sel="#2A2318", title="#000000", title_active="#050403",
        service_bg="#1D1811d9", header="#0B0907",
    )


def dark_roles(t: dict[str, str]) -> dict[str, str]:
    return {
        # window
        "windowBg": t["win"], "windowFg": SAND50, "windowBgOver": t["over"], "windowBgRipple": t["ripple"],
        "windowFgOver": CREAM, "windowSubTextFg": SAND400, "windowSubTextFgOver": SAND300,
        "windowBoldFg": SAND50, "windowBoldFgOver": CREAM, "windowBgActive": G500, "windowFgActive": INK,
        "windowActiveTextFg": G400, "windowShadowFg": "#000000", "windowShadowFgFallback": t["win"],
        "shadowFg": "#00000066",
        # buttons
        "activeButtonBg": G500, "activeButtonBgOver": "#D6AE55", "activeButtonBgRipple": G400,
        "activeButtonFg": INK, "activeButtonFgOver": INK, "activeButtonSecondaryFg": "#3A2D12",
        "activeLineFg": G400,
        "lightButtonBg": t["win"], "lightButtonBgOver": t["over"], "lightButtonBgRipple": t["ripple"],
        "lightButtonFg": G400,
        "attentionButtonFg": "#EC5A52", "attentionButtonFgOver": "#EC5A52",
        "outlineButtonBgOver": t["over"], "outlineButtonOutlineFg": G500, "outlineButtonBgRipple": t["ripple"],
        # menus, inputs
        "menuBg": t["box"], "menuBgOver": "#ffffff12", "menuBgRipple": t["ripple"], "menuIconFg": "#857860",
        "menuIconFgOver": SAND50, "menuSubmenuArrowFg": SAND500, "menuFgDisabled": "#4A4030",
        "menuSeparatorFg": t["ripple"],
        "smallCloseIconFg": SAND500, "smallCloseIconFgOver": SAND300,
        "radialFg": CREAM,
        "placeholderFg": "#7C6F58", "placeholderFgActive": "#5A503F", "inputBorderFg": t["line"],
        "filterInputBorderFg": t["ripple"], "filterInputInactiveBg": t["over"], "filterInputActiveBg": t["over"],
        "checkboxFg": SAND500, "sliderBgInactive": t["line"], "sliderBgActive": G500,
        "tooltipBg": t["over"], "tooltipFg": SAND50, "tooltipBorderFg": t["ripple"],
        # title bar
        "titleBg": t["title"], "titleBgActive": t["title_active"], "titleButtonFg": SAND500,
        "titleButtonBgOver": t["over"], "titleButtonFgOver": SAND50, "titleButtonBgActive": t["title_active"],
        "titleButtonBgActiveOver": t["over"], "titleButtonCloseBgActive": t["title_active"],
        "titleButtonCloseFgOver": "#FFFFFF", "titleFg": SAND500, "titleFgActive": SAND300,
        "cancelIconFg": SAND500, "cancelIconFgOver": SAND300,
        # boxes, contacts
        "boxBg": t["box"], "boxTextFgGood": "#86C07F", "boxTextFgError": "#E5534B", "boxTitleFg": SAND50,
        "boxSearchBg": t["box"], "boxTitleAdditionalFg": SAND400, "membersAboutLimitFg": SAND400,
        "contactsBg": t["box"], "contactsBgOver": t["over"], "contactsStatusFg": SAND400,
        "contactsStatusFgOver": SAND300, "contactsStatusFgOnline": G400,
        "callArrowFg": G400,
        # intro
        "introTitleFg": SAND50, "introDescriptionFg": SAND400,
        "introCoverTopBg": "#1D1811", "introCoverBottomBg": "#2A2318", "introCoverIconsFg": "#3A3022",
        "introCoverPlaneTrace": "#3A3022", "introCoverPlaneInner": SAND100, "introCoverPlaneOuter": SAND300,
        "introCoverPlaneTop": CREAM,
        # dialogs
        "dialogsNameFg": SAND50, "dialogsDateFg": SAND400, "dialogsTextFg": SAND400,
        "dialogsTextFgService": G400, "dialogsDraftFg": "#F0646B", "dialogsVerifiedIconBg": G400,
        "dialogsVerifiedIconFg": t["win"], "dialogsSendingIconFg": SAND500, "dialogsSentIconFg": G400,
        "dialogsUnreadBg": G500, "dialogsUnreadBgMuted": "#857860", "dialogsUnreadFg": INK,
        "dialogsBgOver": t["over"], "dialogsOnlineBadgeFg": G400,
        "dialogsDateFgOver": SAND300, "dialogsTextFgOver": SAND300, "dialogsTextFgServiceOver": G400,
        "dialogsVerifiedIconBgOver": G400, "dialogsSentIconFgOver": G400, "dialogsUnreadBgOver": G500,
        "dialogsUnreadBgMutedOver": "#968872",
        "dialogsBgActive": "#2B2314", "dialogsNameFgActive": G300, "dialogsDateFgActive": SAND300,
        "dialogsTextFgActive": "#CDBE9C", "dialogsTextFgServiceActive": G400, "dialogsDraftFgActive": "#FF8A8F",
        "dialogsVerifiedIconBgActive": G400, "dialogsSendingIconFgActive": "#B8A98899",
        "dialogsSentIconFgActive": G400, "dialogsUnreadBgActive": G500, "dialogsUnreadBgMutedActive": "#857860",
        "dialogsUnreadFgActive": INK, "dialogsOnlineBadgeFgActive": CREAM, "dialogsRippleBg": t["ripple"],
        "dialogsRippleBgActive": t["line"],
        "searchedBarBg": t["box"], "searchedBarFg": SAND400, "topBarBg": t["win"],
        "emojiPanCategories": t["win"], "emojiPanHeaderFg": SAND400, "emojiPanHeaderBg": t["win"] + "f2",
        "stickerPanDeleteFg": "#FFFFFF",
        # history: text and links
        "historyTextInFg": SAND50, "historyTextInFgSelected": CREAM, "historyTextOutFg": INK,
        "historyTextOutFgSelected": INK, "historyLinkInFg": G400, "historyLinkInFgSelected": G200,
        "historyLinkOutFg": "#3A2A0C", "historyLinkOutFgSelected": "#3A2A0C",
        "historyFileNameInFgSelected": CREAM, "historyFileNameOutFgSelected": INK,
        "historyOutIconFg": "#5B4417", "historyOutIconFgSelected": "#3A2A0C", "historyIconFgInverted": "#ffffffe5",
        "historySendingOutIconFg": "#6E5420", "historySendingInIconFg": SAND500,
        "historyCallArrowInFg": G400, "historyCallArrowInFgSelected": CREAM,
        "historyCallArrowMissedInFgSelected": CREAM, "historyCallArrowOutFg": "#2A2318",
        "historyCallArrowOutFgSelected": "#2A2318",
        "historyUnreadBarBg": t["box"], "historyUnreadBarFg": G400,
        "historyPeerUserpicFg": "#FFFFFF", "historyForwardChooseFg": "#FFFFFF",
        # messages
        "msgInBg": t["bub_in"], "msgInBgSelected": t["bub_in_sel"], "msgOutBg": G500, "msgOutBgSelected": G400,
        "msgSelectOverlay": "#C9A24A47", "msgStickerOverlay": "#C9A24A7f",
        "msgInServiceFg": G400, "msgInServiceFgSelected": G200, "msgOutServiceFg": "#3A2D12",
        "msgOutServiceFgSelected": "#2A2318",
        "msgInDateFg": SAND400, "msgInDateFgSelected": SAND100, "msgOutDateFg": "#2A2318",
        "msgOutDateFgSelected": "#2A2318",
        "msgServiceFg": SAND50, "msgServiceBg": t["service_bg"], "msgServiceBgSelected": t["line"],
        "msgInReplyBarColor": G400, "msgInReplyBarSelColor": G200, "msgOutReplyBarColor": "#3A2D12",
        "msgOutReplyBarSelColor": "#2A2318",
        "msgInMonoFg": G300, "msgOutMonoFg": "#3A2D12", "msgInMonoFgSelected": G200, "msgOutMonoFgSelected": "#2A2318",
        "msgDateImgBgSelected": "#C9A24A87",
        "msgFileThumbLinkOutFg": "#3A2D12", "msgFileThumbLinkOutFgSelected": INK,
        "msgFileInBg": G500, "msgFileInBgOver": "#D6AE55", "msgFileInBgSelected": G400,
        "msgFileOutBg": "#2A2318", "msgFileOutBgOver": "#3A3022", "msgFileOutBgSelected": "#1D1811",
        "historyFileInIconFg": INK, "historyFileInIconFgSelected": INK, "historyFileInRadialFg": INK,
        "historyFileInRadialFgSelected": INK, "historyFileOutIconFg": G400, "historyFileOutIconFgSelected": G200,
        "historyFileOutRadialFg": G400, "historyFileOutRadialFgSelected": G200,
        "msgWaveformInActive": G400, "msgWaveformInActiveSelected": G200, "msgWaveformInInactive": t["line"],
        "msgWaveformInInactiveSelected": SAND500, "msgWaveformOutActive": "#2A2318",
        "msgWaveformOutActiveSelected": "#1D1811", "msgWaveformOutInactive": G600,
        "msgWaveformOutInactiveSelected": "#8C7330",
        "msgBotKbOverBgAdd": "#E2B85A0f", "msgBotKbRippleBg": "#E2B85A0b",
        "historyToDownBg": t["over"], "historyToDownBgOver": t["ripple"], "historyToDownBgRipple": t["line"],
        "historyToDownFg": SAND300,
        "historyComposeAreaBg": t["win"], "historyPinnedBg": t["box"], "historyComposeButtonBgOver": t["over"],
        "historyComposeButtonBgRipple": t["ripple"], "botKbBg": t["over"], "botKbDownBg": t["ripple"],
        "overviewCheckFgActive": INK, "overviewPhotoSelectOverlay": "#E2B85A33",
        "profileStatusFgOver": SAND400, "profileVerifiedCheckFg": INK, "profileAdminStartFg": G400,
        "toastFg": "#FFFFFF", "youtubePlayIconFg": "#FFFFFF",
        # main menu, media player, media viewer
        "mainMenuCoverBg": "#1D1811", "mainMenuCoverFg": CREAM, "mainMenuCloudBg": G500,
        "mediaPlayerDisabledFg": SAND300,
        "mediaviewFileExtFg": "#FFFFFF", "mediaviewMenuFg": SAND50, "mediaviewControlFg": "#FFFFFF",
        "mediaviewTextLinkFg": G400,
        # calls
        "callBg": "#0B0907f5", "callStatusFg": SAND300, "callAnswerBg": "#4FA86B", "callAnswerRipple": "#46996B",
        "callAnswerBgOuter": "#4FA86B26", "callCancelFg": SAND500, "callCancelRipple": SAND100,
        "callBarBg": "#3A3022", "callBarMuteRipple": "#4A3E2C", "callBarBgMuted": "#2A2318",
        "callBarUnmuteRipple": "#3A3022", "callBarFg": SAND50,
        "importantTooltipFgLink": G400,
        # icons, side bar
        "emojiIconFg": "#857860", "emojiIconFgActive": G400,
        "sideBarBg": t["rail"], "sideBarBgActive": t["over"], "sideBarBgRipple": t["box"], "sideBarTextFg": SAND400,
        "sideBarTextFgActive": G400, "sideBarIconFg": SAND400, "sideBarIconFgActive": G400, "sideBarBadgeBg": G500,
        "sideBarBadgeBgMuted": SAND500, "sideBarBadgeFg": INK,
        "statisticsChartInactive": "#3A3022c8", "statisticsChartActive": "#6C604Cd8",
    }


def vellum_roles() -> dict[str, str]:
    ink, ink2, sub = "#1D1811", "#0B0907", "#6C604C"
    win, box, over, ripple, line = "#F3ECDD", "#FBF7EE", "#EAE1CB", "#DDD1B6", "#D3C7A8"
    link = "#7D6122"
    bub_in, bub_out = "#FFFDF8", "#F1D589"
    return {
        "windowBg": win, "windowFg": ink, "windowBgOver": over, "windowBgRipple": ripple, "windowFgOver": ink2,
        "windowSubTextFg": sub, "windowSubTextFgOver": "#5B5040", "windowBoldFg": ink2, "windowBoldFgOver": ink2,
        "windowBgActive": G500, "windowFgActive": ink2, "windowActiveTextFg": link, "shadowFg": "#3A302218",
        "activeButtonBg": G500, "activeButtonBgOver": "#D1AB52", "activeButtonBgRipple": G400,
        "activeButtonFg": ink2, "activeButtonFgOver": ink2, "activeButtonSecondaryFg": "#3A2D12",
        "activeLineFg": G600,
        "lightButtonBg": win, "lightButtonBgOver": over, "lightButtonBgRipple": ripple, "lightButtonFg": link,
        "attentionButtonFg": "#C2362E", "attentionButtonFgOver": "#C2362E",
        "menuBg": box, "menuBgOver": over, "menuBgRipple": ripple, "menuIconFg": "#8A7C62", "menuIconFgOver": ink,
        "menuSubmenuArrowFg": "#8A7C62", "menuFgDisabled": "#A89B80", "menuSeparatorFg": line,
        "smallCloseIconFg": "#8A7C62", "smallCloseIconFgOver": sub,
        "radialFg": ink2,
        "placeholderFg": "#8A7C62", "placeholderFgActive": "#A89B80", "inputBorderFg": line,
        "filterInputBorderFg": line, "filterInputInactiveBg": over, "filterInputActiveBg": over,
        "checkboxFg": "#8A7C62", "sliderBgInactive": line, "sliderBgActive": G600,
        "tooltipBg": "#2A2318", "tooltipFg": SAND50, "tooltipBorderFg": "#2A2318",
        "titleBg": "#E6DCC6", "titleBgActive": "#E6DCC6", "titleButtonFg": sub, "titleButtonBgOver": over,
        "titleButtonFgOver": ink2, "titleButtonBgActive": "#E6DCC6", "titleButtonBgActiveOver": over,
        "titleFg": sub, "titleFgActive": ink, "titleButtonCloseFgOver": "#FFFFFF",
        "cancelIconFg": "#8A7C62", "cancelIconFgOver": sub,
        "boxBg": box, "boxTextFgGood": "#3F7D3A", "boxTextFgError": "#C2362E", "boxTitleFg": ink2,
        "boxSearchBg": box, "boxTitleAdditionalFg": sub, "membersAboutLimitFg": sub,
        "contactsBg": box, "contactsBgOver": over, "contactsStatusFg": sub, "contactsStatusFgOver": sub,
        "contactsStatusFgOnline": link, "callArrowFg": link,
        "introTitleFg": ink2, "introDescriptionFg": sub,
        "introCoverTopBg": "#E6DCC6", "introCoverBottomBg": "#D8CCB0", "introCoverIconsFg": "#C2B590",
        "introCoverPlaneTrace": "#C2B590", "introCoverPlaneInner": "#8A7C62", "introCoverPlaneOuter": "#6C604C",
        "introCoverPlaneTop": "#FFFFFF",
        "dialogsNameFg": ink2, "dialogsDateFg": "#716550", "dialogsTextFg": sub, "dialogsTextFgService": link,
        "dialogsDraftFg": "#C2362E", "dialogsVerifiedIconBg": G600, "dialogsVerifiedIconFg": "#FFFFFF",
        "dialogsSendingIconFg": "#A89B80", "dialogsSentIconFg": link, "dialogsUnreadBg": G500,
        "dialogsUnreadBgMuted": "#B8A988", "dialogsUnreadFg": ink2, "dialogsBgOver": over,
        "dialogsOnlineBadgeFg": link, "dialogsDateFgOver": "#716550", "dialogsTextFgOver": sub,
        "dialogsTextFgServiceOver": link, "dialogsVerifiedIconBgOver": G600, "dialogsSentIconFgOver": link,
        "dialogsUnreadBgOver": G500, "dialogsUnreadBgMutedOver": "#A89B80",
        "dialogsBgActive": G500, "dialogsNameFgActive": ink2, "dialogsDateFgActive": "#3A2D12",
        "dialogsTextFgActive": "#2A2318", "dialogsTextFgServiceActive": ink2, "dialogsDraftFgActive": "#7A1D17",
        "dialogsVerifiedIconBgActive": ink2, "dialogsVerifiedIconFgActive": G500,
        "dialogsSendingIconFgActive": "#3A2D1299", "dialogsSentIconFgActive": ink2, "dialogsUnreadBgActive": ink2,
        "dialogsUnreadBgMutedActive": "#6B5316", "dialogsUnreadFgActive": G300, "dialogsOnlineBadgeFgActive": ink2,
        "dialogsRippleBg": ripple, "dialogsRippleBgActive": G400,
        "searchedBarBg": over, "searchedBarFg": sub, "topBarBg": win,
        "emojiPanCategories": win, "emojiPanHeaderFg": sub, "emojiPanHeaderBg": win + "f2",
        "stickerPanDeleteFg": "#FFFFFF",
        "historyTextInFg": ink2, "historyTextInFgSelected": ink2, "historyTextOutFg": ink2,
        "historyTextOutFgSelected": ink2, "historyLinkInFg": link, "historyLinkInFgSelected": "#5B4417",
        "historyLinkOutFg": "#5B4417", "historyLinkOutFgSelected": "#5B4417",
        "historyFileNameInFgSelected": ink2, "historyFileNameOutFgSelected": ink2,
        "historyOutIconFg": "#6B5316", "historyOutIconFgSelected": "#5B4417", "historyIconFgInverted": "#ffffffe5",
        "historySendingOutIconFg": "#8A6D24", "historySendingInIconFg": "#A89B80",
        "historyCallArrowInFg": link, "historyCallArrowInFgSelected": ink2, "historyCallArrowOutFg": "#6B5316",
        "historyCallArrowOutFgSelected": "#5B4417",
        "historyUnreadBarBg": "#E6DCC6", "historyUnreadBarFg": link,
        "historyPeerUserpicFg": "#FFFFFF", "historyForwardChooseFg": "#FFFFFF",
        "msgInBg": bub_in, "msgInBgSelected": "#F7E6B5", "msgOutBg": bub_out, "msgOutBgSelected": "#E6C873",
        "msgSelectOverlay": "#C9A24A47", "msgStickerOverlay": "#C9A24A7f",
        "msgInServiceFg": link, "msgInServiceFgSelected": "#5B4417", "msgOutServiceFg": "#6B5316",
        "msgOutServiceFgSelected": "#5B4417",
        "msgInDateFg": "#716550", "msgInDateFgSelected": "#6B5316", "msgOutDateFg": "#6B5316",
        "msgOutDateFgSelected": "#5B4417",
        "msgServiceFg": "#FFFFFF", "msgServiceBg": "#5B4E37b0", "msgServiceBgSelected": "#6B5316c0",
        "msgInReplyBarColor": G600, "msgInReplyBarSelColor": "#6B5316", "msgOutReplyBarColor": "#8A6D24",
        "msgOutReplyBarSelColor": "#6B5316",
        "msgInMonoFg": "#5B4417", "msgOutMonoFg": "#5B4417", "msgInMonoFgSelected": "#5B4417",
        "msgOutMonoFgSelected": "#5B4417",
        "msgDateImgBgSelected": "#C9A24A87",
        "msgFileThumbLinkOutFg": "#6B5316", "msgFileThumbLinkOutFgSelected": "#5B4417",
        "msgFileInBg": G500, "msgFileInBgOver": "#D1AB52", "msgFileInBgSelected": G400,
        "msgFileOutBg": "#8A6D24", "msgFileOutBgOver": "#7A6020", "msgFileOutBgSelected": "#6B5316",
        "historyFileInIconFg": ink2, "historyFileInIconFgSelected": ink2, "historyFileInRadialFg": ink2,
        "historyFileInRadialFgSelected": ink2, "historyFileOutIconFg": "#FFF6DD", "historyFileOutIconFgSelected": "#FFF6DD",
        "historyFileOutRadialFg": "#FFF6DD", "historyFileOutRadialFgSelected": "#FFF6DD",
        "msgWaveformInActive": G600, "msgWaveformInActiveSelected": "#6B5316", "msgWaveformInInactive": line,
        "msgWaveformInInactiveSelected": "#C2A55A", "msgWaveformOutActive": "#6B5316",
        "msgWaveformOutActiveSelected": "#5B4417", "msgWaveformOutInactive": "#C9A24A",
        "msgWaveformOutInactiveSelected": "#B8923F",
        "historyToDownBg": box, "historyToDownBgOver": over, "historyToDownBgRipple": ripple,
        "historyToDownFg": sub,
        "historyComposeAreaBg": box, "historyPinnedBg": "#F7F1E3", "historyComposeButtonBgOver": over,
        "historyComposeButtonBgRipple": ripple, "botKbBg": over, "botKbDownBg": ripple,
        "overviewCheckFgActive": ink2, "overviewPhotoSelectOverlay": "#C9A24A33",
        "profileStatusFgOver": sub, "profileVerifiedCheckFg": "#FFFFFF", "profileAdminStartFg": link,
        "toastBg": "#000000b2", "toastFg": "#FFFFFF", "youtubePlayIconFg": "#FFFFFF",
        "mainMenuCoverBg": "#E6DCC6", "mainMenuCoverFg": ink2, "mainMenuCloudBg": G500,
        "mediaPlayerDisabledFg": "#A89B80",
        "mediaviewFileExtFg": "#FFFFFF", "mediaviewMenuFg": "#FFFFFF", "mediaviewControlFg": "#FFFFFF",
        "mediaviewTextLinkFg": G400,
        "callBg": "#0B0907f5", "callStatusFg": SAND300, "callAnswerBg": "#4FA86B", "callAnswerRipple": "#46996B",
        "callBarBg": "#7D6122", "callBarMuteRipple": "#8A6D24", "callBarBgMuted": "#6C604C",
        "callBarUnmuteRipple": "#7A6D55", "callBarFg": "#FFFFFF",
        "importantTooltipFgLink": G300,
        "emojiIconFg": "#8A7C62", "emojiIconFgActive": link,
        "sideBarBg": "#E6DCC6", "sideBarBgActive": "#F3ECDD", "sideBarBgRipple": over, "sideBarTextFg": sub,
        "sideBarTextFgActive": link, "sideBarIconFg": sub, "sideBarIconFgActive": link, "sideBarBadgeBg": G500,
        "sideBarBadgeBgMuted": "#A89B80", "sideBarBadgeFg": ink2,
        "statisticsChartInactive": "#D3C7A8c8", "statisticsChartActive": "#A89B80d8",
    }


# ---------------------------------------------------------------------------------------------
# Colour helpers


def parse(value: str) -> tuple[int, int, int, int] | None:
    m = HEX.match(value.strip())
    if not m:
        return None
    rgb = m.group(1)
    a = int(m.group(2), 16) if m.group(2) else 255
    return int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16), a


def fmt(r: int, g: int, b: int, a: int = 255) -> str:
    return f"#{r:02x}{g:02x}{b:02x}" + (f"{a:02x}" if a != 255 else "")


def luminance(rgb: tuple[int, int, int]) -> float:
    def lin(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def over(fg: tuple[int, int, int, int], bg: tuple[int, int, int]) -> tuple[int, int, int]:
    a = fg[3] / 255
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))  # type: ignore[return-value]


def ramp_color(ramp: list[tuple[float, str]], l: float) -> tuple[int, int, int]:
    for (l0, c0), (l1, c1) in zip(ramp, ramp[1:]):
        if l0 <= l <= l1:
            t = 0 if l1 == l0 else (l - l0) / (l1 - l0)
            a = parse(c0)
            b = parse(c1)
            return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]
    return parse(ramp[-1][1])[:3]  # type: ignore[return-value]


def auto_remap(value: str, ramp: list[tuple[float, str]]) -> str | None:
    """Blue/teal brand keys -> the gold ramp (by HSL lightness); everything else untouched."""
    c = parse(value)
    if not c:
        return None
    r, g, b, a = c
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hue = h * 360
    if s >= 0.15 and 170 <= hue <= 265:
        nr, ng, nb = ramp_color(ramp, l)
        return fmt(nr, ng, nb, a)
    return None


# ---------------------------------------------------------------------------------------------
# Wallpaper tiles


def bolt_tile(size: int, base: str, ink: str, step: int, bolt_h: int, ss: int = 4) -> Image.Image:
    """A seamless tile of small staggered bolts, drawn a hair off the background colour."""
    S = size * ss
    img = Image.new("RGB", (S, S), base)
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = BOLT_BOX
    scale = bolt_h * ss / (y1 - y0)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    cols = size // step
    for row in range(cols):
        for col in range(cols):
            cx = (col + (0.5 if row % 2 else 0.0)) * step * ss + step * ss / 2
            cy = row * step * ss + step * ss / 2
            for dx in (-S, 0, S):
                for dy in (-S, 0, S):
                    pts = [(cx + dx + (x - mx) * scale, cy + dy + (y - my) * scale) for x, y in BOLT_POINTS]
                    draw.polygon(pts, fill=ink)
    return img.resize((size, size), Image.LANCZOS)


def png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------------------------
# Build


def load_template(path: str) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for raw in open(path, encoding="utf-8").read().split("\n"):
        m = LINE.match(raw)
        if m:
            rows.append((raw, m.group(1), m.group(2), m.group(3).strip(), m.group(4)))
        else:
            rows.append((raw, "", "", "", ""))
    return rows


KEEP_STOCK_PREFIXES = ("historyPeer", "msgFile", "mediaviewFile", "settingsIconBg", "premium")
DARK_SURFACE_PREFIXES = ("groupCall", "photoEditor", "mediaviewPip")  # dark in every theme


def palette_keys(path: str) -> set[str]:
    found = set()
    for raw in open(path, encoding="utf-8").read().splitlines():
        m = LINE.match(raw)
        if m:
            found.add(m.group(2))
    return found


def build_palette(
    template: list[tuple[str, str, str, str, str]],
    roles: dict[str, str],
    ramp: list[tuple[float, str]],
    must_decide: dict[str, str],
    known_keys: set[str],
) -> tuple[str, dict[str, str], list[str], list[str]]:
    keys = {key for _, _, key, _, _ in template if key}
    unknown = sorted(set(roles) - keys - known_keys)
    if unknown:
        raise SystemExit("roles name keys that are in neither the template nor the palette: " + ", ".join(unknown))

    values = {key: val for _, _, key, val, _ in template if key}
    # Keys that point at a core key whose meaning flips (windowFgActive is dark now) must be decided.
    refs = set()
    for key, val in values.items():
        if val in must_decide and key not in roles:
            refs.add(key)
    # follow one level of aliases (dialogsTextFgServiceActive = dialogsTextFgActive ...)
    changed = True
    while changed:
        changed = False
        for key, val in values.items():
            if val in refs and key not in roles and key not in refs:
                refs.add(key)
                changed = True
    undecided = sorted(k for k in refs if k not in roles and values[k] in must_decide)
    if undecided:
        raise SystemExit("keys depending on a flipped core key have no role: " + ", ".join(undecided))

    appended = sorted(k for k in roles if k not in keys)
    # A key the stock file never defines is written just before the first line that points at it,
    # because the loader only resolves an alias to a key defined earlier in the file.
    first_use: dict[int, list[str]] = {}
    placed: set[str] = set()
    for index, (_, _, key, val, _) in enumerate(template):
        if key and val in appended and val not in placed:
            first_use.setdefault(index, []).append(val)
            placed.add(val)

    out_lines = []
    final: dict[str, str] = {}
    auto_mapped: list[str] = []
    for index, (raw, indent, key, val, tail) in enumerate(template):
        for early in first_use.get(index, []):
            final[early] = roles[early]
            out_lines.append(f"{early}: {roles[early]};")
        if not key:
            out_lines.append(raw)
            continue
        if key in roles:
            new = roles[key]
        else:
            keep = key.startswith(KEEP_STOCK_PREFIXES)
            use_ramp = DARK_RAMP if key.startswith(DARK_SURFACE_PREFIXES) else ramp
            mapped = None if (val in values or keep) else auto_remap(val, use_ramp)
            new = mapped or val
            if mapped:
                auto_mapped.append(key)
        final[key] = new
        out_lines.append(f"{indent}{key}: {new};{tail}")
    for key in appended:
        if key not in placed:
            final[key] = roles[key]
            out_lines.append(f"{key}: {roles[key]};")
    return "\n".join(out_lines), final, auto_mapped, appended


def resolve(final: dict[str, str], key: str, depth: int = 0) -> str:
    value = final[key]
    if value in final and depth < 12:
        return resolve(final, value, depth + 1)
    return value


PAIRS = [
    # (foreground key, background key, minimum ratio, note)
    ("windowFg", "windowBg", 7, "body text"),
    ("windowSubTextFg", "windowBg", 4.5, "secondary text"),
    ("windowActiveTextFg", "windowBg", 4.5, "links, online"),
    ("boxTitleFg", "boxBg", 7, "box title"),
    ("contactsStatusFg", "contactsBg", 4.5, "contact status"),
    ("activeButtonFg", "activeButtonBg", 7, "primary button"),
    ("lightButtonFg", "lightButtonBg", 4.5, "light button"),
    ("attentionButtonFg", "windowBg", 4.0, "destructive button"),
    ("dialogsNameFg", "dialogsBg", 7, "chat name"),
    ("dialogsTextFg", "dialogsBg", 4.5, "chat preview"),
    ("dialogsDateFg", "dialogsBg", 4.5, "chat time"),
    ("dialogsNameFgActive", "dialogsBgActive", 7, "active chat name"),
    ("dialogsTextFgActive", "dialogsBgActive", 4.5, "active chat preview"),
    ("dialogsDateFgActive", "dialogsBgActive", 4.5, "active chat time"),
    ("dialogsUnreadFg", "dialogsUnreadBg", 4.5, "unread badge"),
    ("dialogsUnreadFg", "dialogsUnreadBgMuted", 4.5, "muted unread badge"),
    ("dialogsUnreadFgActive", "dialogsUnreadBgActive", 4.5, "active unread badge"),
    ("historyTextInFg", "msgInBg", 7, "incoming text"),
    ("historyLinkInFg", "msgInBg", 4.5, "incoming link"),
    ("msgInDateFg", "msgInBg", 4.5, "incoming time"),
    ("msgInServiceFg", "msgInBg", 4.5, "incoming author"),
    ("historyTextOutFg", "msgOutBg", 7, "outgoing text"),
    ("historyLinkOutFg", "msgOutBg", 4.5, "outgoing link"),
    ("msgOutDateFg", "msgOutBg", 4.5, "outgoing time"),
    ("msgOutServiceFg", "msgOutBg", 4.5, "outgoing author"),
    ("historyOutIconFg", "msgOutBg", 3.0, "sent ticks"),
    ("historyTextInFgSelected", "msgInBgSelected", 7, "selected incoming"),
    ("historyTextOutFgSelected", "msgOutBgSelected", 7, "selected outgoing"),
    ("msgInDateFgSelected", "msgInBgSelected", 4.5, "selected incoming time"),
    ("msgOutDateFgSelected", "msgOutBgSelected", 4.5, "selected outgoing time"),
    ("introTitleFg", "introBg", 7, "intro title"),
    ("introDescriptionFg", "introBg", 4.5, "intro text"),
    ("sideBarTextFg", "sideBarBg", 4.5, "rail label"),
    ("sideBarTextFgActive", "sideBarBgActive", 4.5, "rail active label"),
    ("sideBarBadgeFg", "sideBarBadgeBg", 4.5, "rail badge"),
    ("tooltipFg", "tooltipBg", 7, "tooltip"),
    ("menuIconFg", "menuBg", 3.0, "menu icon"),
    ("placeholderFg", "windowBg", 3.0, "input placeholder"),
    ("historyComposeAreaFg", "historyComposeAreaBg", 7, "composer text"),
    ("mainMenuCoverFg", "mainMenuCoverBg", 7, "drawer header"),
    ("callBarFg", "callBarBg", 4.5, "call bar"),
    ("historyFileInIconFg", "msgFileInBg", 4.5, "file icon (in)"),
    ("historyFileOutIconFg", "msgFileOutBg", 4.5, "file icon (out)"),
]


def check_contrast(final: dict[str, str], wall: tuple[int, int, int]) -> list[str]:
    problems = []
    for fg, bg, need, note in PAIRS:
        if fg not in final or bg not in final:
            continue
        f = parse(resolve(final, fg))
        b = parse(resolve(final, bg))
        if not f or not b:
            continue
        base = over(b, wall) if b[3] != 255 else b[:3]
        ratio = contrast(over(f, base), base)
        flag = "" if ratio >= need else "   <-- below %.1f" % need
        if flag:
            problems.append(f"{fg:32s} on {bg:24s} {ratio:5.2f}  ({note}){flag}")
    return problems


def zip_theme(path: str, palette: str, tile: Image.Image) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("colors.tdesktop-theme", palette.replace("\r\n", "\n"))
        z.writestr("tiled.png", png_bytes(tile))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock", required=True)
    ap.add_argument("--out", default="Telegram/Resources")
    ap.add_argument("--palette", default="Telegram/lib_ui/ui/colors.palette")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--dump", help="also write the plain colors files here (for review)")
    args = ap.parse_args()

    night = load_template(os.path.join(args.stock, "night", "colors.tdesktop-theme"))
    day = load_template(os.path.join(args.stock, "day-custom-base", "colors.tdesktop-theme"))
    flipped = {"windowFgActive": 1}
    known = palette_keys(args.palette)

    jobs = [
        ("ember", night, dark_roles(ember_tokens()), DARK_RAMP,
         bolt_tile(192, "#0B0907", "#14100B", 96, 22), ["night", "night-custom-base"]),
        ("obsidian", night, dark_roles(obsidian_tokens()), DARK_RAMP,
         bolt_tile(192, "#000000", "#0A0806", 96, 22), ["night-green"]),
        ("vellum", day, vellum_roles(), LIGHT_RAMP,
         bolt_tile(192, "#EFE6D2", "#E7DCC4", 96, 22), ["day-blue", "day-custom-base"]),
    ]
    for name, template, roles, ramp, tile, targets in jobs:
        palette, final, auto, appended = build_palette(template, roles, ramp, flipped, known)
        wall = parse(resolve(final, "windowBg"))[:3]
        tile_color = tile.getpixel((0, 0))
        problems = check_contrast(final, tuple(tile_color))
        if args.report:
            print(f"== {name}: {len(final)} keys, {len(roles)} set by role, {len(auto)} re-mapped by ramp")
            if auto:
                print("   ramp-mapped:", ", ".join(auto))
            if appended:
                print("   appended (not in the stock file):", ", ".join(appended))
            print("   contrast problems:" if problems else "   contrast: all checked pairs pass")
            for p in problems:
                print("     ", p)
        if args.dump:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".colors.tdesktop-theme"), "w", encoding="utf-8", newline="\n") as h:
                h.write(palette)
        for target in targets:
            zip_theme(os.path.join(args.out, target + ".tdesktop-theme"), palette, tile)
        print(f"{name}: wrote {', '.join(t + '.tdesktop-theme' for t in targets)}")


if __name__ == "__main__":
    main()
