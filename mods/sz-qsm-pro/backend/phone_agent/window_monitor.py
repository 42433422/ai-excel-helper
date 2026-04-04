"""
微信电话窗口监控模块
功能：
1. 监控微信电话窗口类名（含 Qt 来电条、窄条通知）
2. 标题 + 子控件文案匹配（「邀请你语音通话」常在客户区而非标题栏）
3. 自动接听：控件文案优先，窄条浮层用右侧「绿钮」几何兜底
"""

import logging
import re
import time
from enum import Enum
from typing import Optional, Dict, List, Tuple
import threading

logger = logging.getLogger(__name__)

from .win32_com_thread import com_init_apartment_thread, com_uninit_apartment_thread

try:
    import win32gui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("Win32 API not available, window monitoring disabled")


class MonitorState(Enum):
    """监控状态枚举"""
    INIT = "init"
    WINDOW_DETECTED = "window_detected"
    TITLE_MATCHED = "title_matched"
    BUTTON_FOUND = "button_found"
    READY = "ready"


class PhoneWindowMonitor:
    """微信电话窗口监控器"""

    WECHAT_WINDOW_CLASSES = [
        "WeChatMainWndForPC",
        "WeChat",
        "ChatWnd",
        "Qt5QWindowIcon",
        "Qt515QWindowIcon",
        "Qt616QWindowIcon",
        "Qt6QWindowIcon",
        # 部分版本内嵌 Chromium / 新壳
        "Chrome_WidgetWin_1",
        "Chrome_WidgetWin_0",
    ]

    # 窄条来电浮层常见像素范围（高分屏 / 不同 DPI 下会略宽或略高）
    TOAST_W_MIN = 200
    TOAST_W_MAX = 1280
    TOAST_H_MIN = 56
    TOAST_H_MAX = 520

    INCOMING_KEYWORDS = [
        "电话",
        "通话",
        "来电",
        "呼叫",
        "语音",
        "视频",
        "邀请",
        "加入",
        "video",
        "voice",
        "incoming",
        "facetime",
        "calling",
        "ringing",
        "invite",
        "join",
        "accept",
    ]

    def __init__(self):
        self.state = MonitorState.INIT
        self._running = False
        self._monitor_thread = None
        self._template_thread = None
        self._callback = None
        self._event_sink = None
        self._detected_window = None
        self._lock_count = 0
        self._last_detection_time = 0.0
        self._last_fallback_scan_ts = 0.0
        self._debug_lock = threading.Lock()
        self._debug_status = {
            "template_loop_ready": False,
            "audio_gate_active": False,
            "wechat_minimized": False,
            "audio_session_active": False,
            "audio_gate_elapsed_ms": 0,
            "debug_updated_at_ms": None,
        }
        # 接听成功后：检测「通话中」窗口消失 → 视为挂断，通知 manager 清空任务面板状态
        self._call_session_lock = threading.Lock()
        self._call_session_thread = None
        self._call_session_active = False
        self._call_answered_at = 0.0
        self._call_consecutive_absent = 0
        self._call_ever_saw_in_call_ui = False

    def set_event_sink(self, sink):
        """可选：PhoneAgentManager 注入，用于向前端 /status 上报「识别弹窗 / 点击接听」步骤。"""
        self._event_sink = sink

    def _emit_phone_ui_event(self, payload: dict) -> None:
        if not self._event_sink:
            return
        try:
            self._event_sink(payload)
        except Exception:
            pass

    def _update_debug_status(self, **kwargs) -> None:
        with self._debug_lock:
            self._debug_status.update(kwargs)
            self._debug_status["debug_updated_at_ms"] = int(time.time() * 1000)

    def get_debug_status(self) -> Dict:
        with self._debug_lock:
            return dict(self._debug_status)

    def start(self, callback=None):
        """启动监控"""
        if not WIN32_AVAILABLE:
            logger.error("Cannot start monitor: Win32 API not available")
            return False

        if self._running:
            logger.warning("Monitor already running")
            return True

        self._callback = callback
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        # 并行启用屏幕模板兜底：当窗口类名/层级变化导致 Win32 枚举失效时，仍可按模板识别并点击接听。
        self._template_thread = threading.Thread(target=self._screen_template_loop, daemon=True)
        self._template_thread.start()
        self._call_session_thread = threading.Thread(target=self._call_session_watch_loop, daemon=True)
        self._call_session_thread.start()
        logger.info("Phone window monitor started")
        return True

    def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        if self._template_thread and self._template_thread.is_alive():
            self._template_thread.join(timeout=1.5)
        self._template_thread = None
        if self._call_session_thread and self._call_session_thread.is_alive():
            self._call_session_thread.join(timeout=2.0)
        self._call_session_thread = None
        logger.info("Phone window monitor stopped")

    def _screen_template_loop(self):
        """并行：微信音频会话 Active 持续超过阈值后，才对全屏模板 image.png 做匹配并点击接听。"""
        com_inited = com_init_apartment_thread()
        try:
            from . import template_screen_watcher as tsw
            from .wechat_audio_gate import WechatAudioGate
        except Exception:
            self._update_debug_status(template_loop_ready=False)
            return
        self._update_debug_status(template_loop_ready=True)
        audio_gate = WechatAudioGate(threshold_sec=2.0)
        try:
            while self._running:
                try:
                    audio_allowed = audio_gate.update_and_should_run_template()
                    self._update_debug_status(
                        audio_gate_active=bool(audio_allowed),
                        audio_session_active=bool(audio_gate.is_audio_session_active()),
                        audio_gate_elapsed_ms=int(audio_gate.active_elapsed_sec() * 1000),
                    )
                    if not audio_allowed:
                        time.sleep(0.2)
                        continue
                    # 仅允许在「微信主窗口最小化」时自动点击模板命中点；否则交给人工接听。
                    minimized = self._is_wechat_minimized()
                    self._update_debug_status(wechat_minimized=bool(minimized))
                    if not minimized:
                        time.sleep(0.25)
                        continue
                    info = tsw.try_match_template_and_click_answer()
                    if info:
                        at_ms = int(time.time() * 1000)
                        self._emit_phone_ui_event(
                            {
                                "kind": "popup_detected",
                                "at_ms": at_ms,
                                "source": "screen_template",
                                "title": "template_match",
                                "class_name": "screen_template",
                                "template_score": info.get("score"),
                            }
                        )
                        self._emit_phone_ui_event(
                            {
                                "kind": "click_attempt",
                                "at_ms": at_ms,
                                "ok": True,
                                "method": str(info.get("method") or "screen_template"),
                                "x": info.get("x"),
                                "y": info.get("y"),
                            }
                        )
                        logger.info("Incoming call handled via screen template match")
                        if self._callback:
                            try:
                                self._callback(
                                    {
                                        "hwnd": None,
                                        "title": "template_match",
                                        "class": "screen_template",
                                    }
                                )
                            except Exception as e:
                                logger.error(f"Callback error (template): {e}")
                except Exception as e:
                    logger.debug("screen template loop: %s", e)
                time.sleep(0.35)
        finally:
            com_uninit_apartment_thread(com_inited)

    def _is_wechat_main_window_class(self, class_name: str) -> bool:
        cn = class_name or ""
        if "WeChatMainWndForPC" in cn:
            return True
        if "WeixinMainWnd" in cn or ("Weixin" in cn and "Wnd" in cn):
            return True
        if "WeChat" in cn:
            return True
        return False

    def _wechat_main_put_away(self, hwnd: int) -> bool:
        """
        主窗口是否已「收起」：任务栏最小化 / 最小化状态 / 常见「收进托盘」导致的不可见。
        """
        try:
            if win32gui.IsIconic(hwnd):
                return True
            pl = win32gui.GetWindowPlacement(hwnd)
            if pl and pl[1] == win32con.SW_SHOWMINIMIZED:
                return True
        except Exception:
            pass
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
        except Exception:
            pass
        return False

    def _is_wechat_minimized(self) -> bool:
        """
        判断微信主窗口是否已收起（最小化或托盘隐藏等）。
        约定：至少发现一个主窗且全部满足 _wechat_main_put_away；找不到主窗时返回 False。
        """
        if not WIN32_AVAILABLE:
            return False
        found = False
        all_put_away = True

        def enum_callback(hwnd, _):
            nonlocal found, all_put_away
            try:
                if not win32gui.IsWindow(hwnd):
                    return True
                class_name = win32gui.GetClassName(hwnd) or ""
                if not self._is_wechat_main_window_class(class_name):
                    return True
                found = True
                if not self._wechat_main_put_away(hwnd):
                    all_put_away = False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            return False
        return found and all_put_away

    def _monitor_loop(self):
        """监控主循环"""
        logger.info("Monitor loop started")

        com_inited = com_init_apartment_thread()
        try:
            while self._running:
                try:
                    self._scan_windows()
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Monitor loop error: {e}")
                    time.sleep(0.5)
        finally:
            com_uninit_apartment_thread(com_inited)

    def _scan_windows(self):
        """扫描所有窗口"""
        windows = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                class_name = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
                w, h = self._window_rect_size(hwnd)

                if self._class_matches_wechat(class_name):
                    windows.append({
                        'hwnd': hwnd,
                        'class': class_name,
                        'title': title,
                    })
                # 文案常为自绘，GetWindowText/子控件读不到「邀请你语音通话」——仅靠尺寸+类名纳入候选
                elif self._may_be_wechat_voice_toast(class_name, w, h):
                    logger.debug(
                        "Candidate voice toast (no title text needed): class=%r %sx%s title=%r",
                        (class_name or "")[:64],
                        w,
                        h,
                        (title or "")[:40],
                    )
                    windows.append({
                        'hwnd': hwnd,
                        'class': class_name,
                        'title': title,
                    })
            return True

        win32gui.EnumWindows(enum_callback, None)

        # 某些微信版本来电浮层类名不稳定，且标题栏可能为空；做低频兜底扫描。
        now = time.time()
        if now - self._last_fallback_scan_ts >= 0.8:
            self._last_fallback_scan_ts = now
            self._append_fallback_invite_windows(windows)

        for window in windows:
            self._check_window(window)

    def _append_fallback_invite_windows(self, windows: List[Dict]) -> None:
        """当类名筛选漏检时，按尺寸+文案做一次兜底枚举。"""
        seen = {int(w.get("hwnd") or 0) for w in windows}

        def enum_callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                if hwnd in seen:
                    return True
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w < 200 or h < 60 or w > 1300 or h > 700:
                    return True
                cn = win32gui.GetClassName(hwnd)
                text_ok = self._window_has_voice_invite_text(hwnd)
                toast_ok = self._may_be_wechat_voice_toast(cn, w, h)
                if not text_ok and not toast_ok:
                    return True
                windows.append(
                    {
                        "hwnd": hwnd,
                        "class": cn,
                        "title": win32gui.GetWindowText(hwnd),
                    }
                )
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            logger.debug("Fallback invite window scan failed: %s", e)

    def _class_matches_wechat(self, class_name: str) -> bool:
        if any(cls in class_name for cls in self.WECHAT_WINDOW_CLASSES):
            return True
        cn = class_name or ""
        if "QWindowIcon" in cn and cn.startswith("Qt") and "WeChat" in cn:
            return True
        if "QWindowIcon" in cn and "WeChat" in cn:
            return True
        return False

    def _is_compact_voice_toast_dimensions(self, w: int, h: int) -> bool:
        if w <= 0 or h <= 0:
            return False
        return (
            self.TOAST_W_MIN <= w <= self.TOAST_W_MAX
            and self.TOAST_H_MIN <= h <= self.TOAST_H_MAX
        )

    def _class_suggests_wechat_or_qt(self, class_name: str) -> bool:
        cn = (class_name or "").lower()
        if any(x in cn for x in ("wechat", "weixin", "micromessenger")):
            return True
        if "qwindowicon" in cn or "qt5qwindow" in cn or "qt6qwindow" in cn:
            return True
        if "chrome_widget" in cn or "chromium" in cn or "cef" in cn:
            return True
        if cn.startswith("qt") and "window" in cn:
            return True
        return False

    def _class_is_likely_excluded(self, class_name: str) -> bool:
        cn = (class_name or "").lower()
        bad = (
            "notepad",
            "mspaint",
            "devenv",
            "applicationframewindow",
            "shell_traywnd",
            "progman",
            "workerw",
        )
        return any(x in cn for x in bad)

    def _may_be_wechat_voice_toast(self, class_name: str, w: int, h: int) -> bool:
        if not self._is_compact_voice_toast_dimensions(w, h):
            return False
        if not self._class_suggests_wechat_or_qt(class_name):
            return False
        if self._class_is_likely_excluded(class_name):
            return False
        return True

    def _check_window(self, window: Dict):
        """检查窗口是否符合条件"""
        current_time = time.time()

        lock1_passed = self._check_lock1_window_class(window)
        if not lock1_passed:
            self._reset_state()
            return

        self.state = MonitorState.WINDOW_DETECTED

        lock2_passed = self._check_lock2_incoming_signal(window)
        if not lock2_passed:
            return

        self.state = MonitorState.TITLE_MATCHED

        lock3_passed = self._check_lock3_incoming_window(window)
        if not lock3_passed:
            return

        self.state = MonitorState.BUTTON_FOUND

        if self._verify_triple_lock(current_time):
            self.state = MonitorState.READY
            self._on_incoming_call(window)

    def _check_lock1_window_class(self, window: Dict) -> bool:
        """锁定1: 窗口类名验证（含无标题文案时的窄条 Qt/壳 来电条）"""
        cn = window.get("class") or ""
        if self._class_matches_wechat(cn):
            return True
        hwnd = window.get("hwnd")
        if not hwnd:
            return False
        w, h = self._window_rect_size(hwnd)
        return self._may_be_wechat_voice_toast(cn, w, h)

    def _window_rect_size(self, hwnd: int) -> tuple:
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            return w, h
        except Exception:
            return 0, 0

    def _collect_child_texts(self, hwnd: int, out: List[str], depth: int, max_depth: int, max_parts: int) -> None:
        if depth > max_depth or len(out) >= max_parts:
            return
        try:
            def child_cb(ch, _):
                try:
                    t = (win32gui.GetWindowText(ch) or "").strip()
                    if t and len(t) < 400:
                        out.append(t)
                except Exception:
                    pass
                if len(out) < max_parts:
                    self._collect_child_texts(ch, out, depth + 1, max_depth, max_parts)
                return True

            win32gui.EnumChildWindows(hwnd, child_cb, None)
        except Exception:
            pass

    def _window_has_voice_invite_text(self, hwnd: int) -> bool:
        """客户区常见文案：邀请你语音通话（不一定在标题栏）"""
        parts: List[str] = []
        try:
            t = (win32gui.GetWindowText(hwnd) or "").strip()
            if t:
                parts.append(t)
        except Exception:
            pass
        self._collect_child_texts(hwnd, parts, 0, 12, 80)
        blob = "\n".join(parts)
        cn_needles = ("邀请", "语音通话", "语音", "视频通话", "电话", "来电", "呼叫", "接听")
        for s in cn_needles:
            if s in blob:
                return True
        bl = blob.lower()
        for s in ("voice", "incoming", "calling", "video call", "facetime", "answer"):
            if s in bl:
                return True
        return False

    def _check_lock2_incoming_signal(self, window: Dict) -> bool:
        """标题关键词 或 子控件/可见文案含「邀请」「语音通话」等"""
        raw_title = window['title'] or ""
        title = raw_title.lower()
        if any(keyword in title for keyword in self.INCOMING_KEYWORDS):
            return True
        if any(k in raw_title for k in ("电话", "通话", "语音", "视频", "来电", "邀请")):
            return True
        hwnd = window['hwnd']
        if self._window_has_voice_invite_text(hwnd):
            logger.debug("Lock2: matched via child/title blob (voice invite text)")
            return True
        return self._check_lock2_incoming_heuristic(window)

    def _check_lock2_incoming_heuristic(self, window: Dict) -> bool:
        """无文案时：典型 Qt/微信壳 来电浮层或窄条尺寸"""
        hwnd = window['hwnd']
        w, h = self._window_rect_size(hwnd)
        if w < 180 or h < 64:
            return False
        if w > 1300:
            return False
        class_name = window['class'] or ""
        if self._is_compact_voice_toast_dimensions(w, h) and self._class_suggests_wechat_or_qt(
            class_name
        ):
            if not self._class_is_likely_excluded(class_name):
                logger.info(
                    "Lock2 heuristic: compact call toast (no readable text) %sx%s class=%r hwnd=%s",
                    w,
                    h,
                    (class_name or "")[:64],
                    hwnd,
                )
                return True
        return False

    def _check_lock3_incoming_window(self, window: Dict) -> bool:
        """尺寸：大对话框 或 窄条来电通知（修正常见截图高度 < 300）"""
        hwnd = window['hwnd']
        w, h = self._window_rect_size(hwnd)
        if w >= 200 and h >= 300:
            return True
        if self._is_compact_voice_toast_dimensions(w, h):
            return True
        return False

    def _verify_triple_lock(self, current_time: float) -> bool:
        min_gap = 0.22
        if current_time - self._last_detection_time < min_gap:
            return False

        self._lock_count += 1
        self._last_detection_time = current_time

        if self._lock_count >= 2:
            self._lock_count = 0
            return True

        return False

    def _reset_state(self):
        """重置状态"""
        self.state = MonitorState.INIT
        self._lock_count = 0
        self._detected_window = None

    def _on_incoming_call(self, window: Dict):
        """来电事件处理"""
        logger.info(f"Incoming call detected! Window: {window['title']!r} class={window.get('class')!r}")
        self._detected_window = window

        hwnd = window.get("hwnd")
        w, h = self._window_rect_size(hwnd) if hwnd else (0, 0)
        self._emit_phone_ui_event(
            {
                "kind": "popup_detected",
                "at_ms": int(time.time() * 1000),
                "source": "win32_window",
                "title": str(window.get("title") or "")[:220],
                "class_name": str(window.get("class") or "")[:160],
                "hwnd": hwnd,
                "width": w,
                "height": h,
            }
        )

        self._auto_answer(window)

        if self._callback:
            try:
                self._callback(window)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _find_answer_click_point(self, hwnd: int) -> Optional[tuple]:
        """
        枚举子控件，查找含「接听」等文案的按钮中心。
        自绘圆形绿钮常无文字，返回 None 后由几何兜底。
        """
        if not WIN32_AVAILABLE:
            return None

        matches: List[tuple] = []

        def consider_control(w: int) -> None:
            try:
                if not win32gui.IsWindowVisible(w):
                    return
                title = (win32gui.GetWindowText(w) or "").strip()
                if not title or len(title) > 120:
                    return
                tl = title.lower()
                if (
                    "接听" in title
                    or "接受" in title
                    or "answer" in tl
                    or ("accept" in tl and "decline" not in tl)
                ):
                    rect = win32gui.GetWindowRect(w)
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    matches.append((cx, cy, title))
            except Exception:
                pass

        def enum_recursive(w: int) -> None:
            consider_control(w)
            try:
                def child_cb(ch, _):
                    enum_recursive(ch)
                    return True

                win32gui.EnumChildWindows(w, child_cb, None)
            except Exception:
                pass

        try:
            enum_recursive(hwnd)
        except Exception as e:
            logger.debug(f"Enum controls for answer button: {e}")

        if not matches:
            return None
        for cx, cy, title in matches:
            if "接听" in title:
                logger.info(f"Auto-answer: matched control {title!r} at ({cx}, {cy})")
                return (cx, cy)
        cx, cy, title = matches[0]
        logger.info(f"Auto-answer: first text match {title!r} at ({cx}, {cy})")
        return (cx, cy)

    def _fallback_answer_click_xy(self, rect: tuple) -> tuple:
        """无文案按钮时：窄条为右侧绿钮，大窗为右下角偏移。"""
        left, top, right, bottom = rect[0], rect[1], rect[2], rect[3]
        w = right - left
        h = bottom - top
        # 与你截图类似的窄条：红左绿右，绿钮偏右下
        if h <= 420 and w >= 200:
            x = left + int(w * 0.86)
            y = top + int(h * 0.72)
            logger.info(f"Auto-answer: compact toast fallback (green-right) at ({x}, {y})")
            return x, y
        x = right - 80
        y = bottom - 40
        logger.info(f"Auto-answer: large window fallback at ({x}, {y})")
        return x, y

    def _incoming_popup_recheck_ok(self, window: Dict) -> bool:
        """
        在最小化门控失败时做二次复核：
        既然已走到 _auto_answer（三锁通过），再按当前弹窗 hwnd 的尺寸/类名快速确认一次，
        确认是来电弹窗则允许继续点击，避免主窗最小化状态误判导致漏接。
        """
        hwnd = window.get("hwnd")
        if not hwnd:
            return False
        w, h = self._window_rect_size(hwnd)
        cls = str(window.get("class") or "")
        if self._is_compact_voice_toast_dimensions(w, h) and self._class_suggests_wechat_or_qt(cls):
            return True
        if w >= 200 and h >= 300:
            return True
        return False

    def _auto_answer(self, window: Dict):
        """自动接听"""
        hwnd = window.get("hwnd")
        if not hwnd:
            self._emit_phone_ui_event(
                {
                    "kind": "click_attempt",
                    "at_ms": int(time.time() * 1000),
                    "ok": False,
                    "method": "no_hwnd",
                    "x": None,
                    "y": None,
                    "error": "no_hwnd",
                }
            )
            return
        # 用户策略：既然窗口三锁已判定来电，则直接执行点击，不再由最小化门控拦截。
        minimized = self._is_wechat_minimized()
        if not minimized:
            logger.info(
                "Auto-answer continue: wechat main is not minimized, but incoming popup already verified by locks"
            )
        method = None
        click_x = None
        click_y = None
        try:
            rect = win32gui.GetWindowRect(hwnd)
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
            except Exception as e:
                logger.debug(f"Bring call window to foreground: {e}")

            pt = self._find_answer_click_point(hwnd)
            if pt:
                click_x, click_y = pt
                method = "control_text"
            else:
                click_x, click_y = self._fallback_answer_click_xy(rect)
                method = "fallback_geometry"

            self._click_at_position(click_x, click_y)
            logger.info(f"Auto-answer clicked at ({click_x}, {click_y})")
            self._emit_phone_ui_event(
                {
                    "kind": "click_attempt",
                    "at_ms": int(time.time() * 1000),
                    "ok": True,
                    "method": method,
                    "x": int(click_x),
                    "y": int(click_y),
                    "error": None,
                }
            )

        except Exception as e:
            logger.error(f"Auto-answer failed: {e}")
            self._emit_phone_ui_event(
                {
                    "kind": "click_attempt",
                    "at_ms": int(time.time() * 1000),
                    "ok": False,
                    "method": method,
                    "x": int(click_x) if click_x is not None else None,
                    "y": int(click_y) if click_y is not None else None,
                    "error": str(e)[:500],
                }
            )

    def _click_at_position(self, x: int, y: int):
        """在指定位置点击"""
        old_pos = win32api.GetCursorPos()

        win32api.SetCursorPos((x, y))
        time.sleep(0.06)

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

        win32api.SetCursorPos(old_pos)

    def mark_voice_call_answered(self, popup_hwnd: Optional[int]) -> None:
        """
        接听成功后由 PhoneAgentManager 调用：开始「通话中」窗口监测，挂断后上报 call_ended。
        popup_hwnd 可为 None（例如纯模板路径）。
        """
        with self._call_session_lock:
            self._call_session_active = True
            self._call_answered_at = time.time()
            self._call_consecutive_absent = 0
            self._call_ever_saw_in_call_ui = False
        _ = popup_hwnd
        logger.info("[奇士美 PRO] 通话会话跟踪已启动（挂断后将清空任务面板电话步骤）")

    def _call_session_watch_loop(self) -> None:
        com_inited = com_init_apartment_thread()
        try:
            while self._running:
                try:
                    with self._call_session_lock:
                        active = self._call_session_active
                    if active and WIN32_AVAILABLE:
                        self._tick_call_session()
                except Exception as e:
                    logger.debug("call_session_watch: %s", e)
                time.sleep(1.0)
        finally:
            com_uninit_apartment_thread(com_inited)

    def _tick_call_session(self) -> None:
        """接听后：宽限期内不判挂断；之后若连续若干秒未发现通话中界面则视为已挂断。"""
        now = time.time()
        with self._call_session_lock:
            if not self._call_session_active:
                return
            answered_at = self._call_answered_at
        # 接听后给界面切换留时间（来电条关闭、通话窗出现）
        if now < answered_at + 4.0:
            return

        in_call = self._detect_in_call_window()
        with self._call_session_lock:
            if not self._call_session_active:
                return
            if in_call:
                self._call_ever_saw_in_call_ui = True
                self._call_consecutive_absent = 0
                return
            self._call_consecutive_absent += 1
            absent = self._call_consecutive_absent
            ever = self._call_ever_saw_in_call_ui

        if ever:
            if absent >= 3:
                self._finish_call_session("in_call_ui_gone")
            return
        # 从未识别到通话窗（部分环境标题/子控件不同）：较宽超时后仍清空面板，避免永久卡住
        if absent >= 12:
            self._finish_call_session("in_call_ui_never_detected_timeout")

    def _find_in_call_window_hwnd(self) -> Optional[int]:
        """
        查找当前微信语音通话进行中窗口（与 _detect_in_call_window 判定一致），供自动挂断点击使用。
        """
        if not WIN32_AVAILABLE:
            return None
        duration_re = re.compile(r"\b\d{1,2}:\d{2}\b")
        found: Optional[int] = None

        def cb(hwnd: int, _) -> bool:
            nonlocal found
            if found is not None:
                return True
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                cn = win32gui.GetClassName(hwnd) or ""
                if not (
                    self._class_matches_wechat(cn)
                    or self._class_suggests_wechat_or_qt(cn)
                ):
                    return True
                title = win32gui.GetWindowText(hwnd) or ""
                w, h = self._window_rect_size(hwnd)
                if w < 160 or h < 100:
                    return True
                if duration_re.search(title):
                    found = hwnd
                    return True
                parts: List[str] = []
                self._collect_child_texts(hwnd, parts, 0, 10, 60)
                blob = "\n".join(parts)
                if "挂断" in blob and (
                    "麦克风" in blob
                    or "扬声器" in blob
                    or "麦克风已开" in blob
                    or "扬声器已开" in blob
                ):
                    found = hwnd
                    return True
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            pass
        return found

    def _detect_in_call_window(self) -> bool:
        """
        粗略判断是否存在微信语音通话进行中窗口：
        - 标题含 mm:ss 时长；或
        - 子控件文案同时含「挂断」与「麦克风/扬声器」等（与常见通话条一致）。
        """
        return self._find_in_call_window_hwnd() is not None

    def is_call_session_active(self) -> bool:
        """接听成功后、本机判定挂断前，为 True。"""
        with self._call_session_lock:
            return bool(self._call_session_active)

    def is_in_call_ui_visible(self) -> bool:
        """当前是否存在微信通话中界面（含手动接听、未上报来电弹窗的路径）。"""
        return bool(self._detect_in_call_window())

    def _find_hangup_click_point(self, hwnd: int) -> Optional[Tuple[int, int]]:
        """枚举子控件，查找含「挂断」等文案的按钮中心（自绘红钮常无字，返回 None 后走几何兜底）。"""
        if not WIN32_AVAILABLE:
            return None
        matches: List[Tuple[int, int, str]] = []

        def consider_control(w: int) -> None:
            try:
                if not win32gui.IsWindowVisible(w):
                    return
                title = (win32gui.GetWindowText(w) or "").strip()
                if not title or len(title) > 120:
                    return
                tl = title.lower()
                if (
                    "挂断" in title
                    or "结束通话" in title
                    or "hang up" in tl
                    or "end call" in tl
                ):
                    rect = win32gui.GetWindowRect(w)
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    matches.append((cx, cy, title))
            except Exception:
                pass

        def enum_recursive(w: int) -> None:
            consider_control(w)
            try:
                def child_cb(ch, _):
                    enum_recursive(ch)
                    return True

                win32gui.EnumChildWindows(w, child_cb, None)
            except Exception:
                pass

        try:
            enum_recursive(hwnd)
        except Exception as e:
            logger.debug("Enum controls for hangup: %s", e)

        if not matches:
            return None
        for cx, cy, title in matches:
            if "挂断" in title:
                logger.info("Hangup: matched control %r at (%s, %s)", title, cx, cy)
                return (cx, cy)
        cx, cy, title = matches[0]
        logger.info("Hangup: first text match %r at (%s, %s)", title, cx, cy)
        return (cx, cy)

    def _fallback_hangup_click_xy(self, rect: tuple) -> Tuple[int, int]:
        """无文案按钮时：窄条红钮偏左；大窗偏左下。"""
        left, top, right, bottom = rect[0], rect[1], rect[2], rect[3]
        w = right - left
        h = bottom - top
        if h <= 420 and w >= 200:
            x = left + int(w * 0.14)
            y = top + int(h * 0.72)
            logger.info("Hangup: compact bar fallback (red-left) at (%s, %s)", x, y)
            return x, y
        x = left + 72
        y = bottom - 52
        logger.info("Hangup: large window fallback at (%s, %s)", x, y)
        return x, y

    def try_click_hangup_in_active_call(self) -> bool:
        """
        若存在通话中窗口，前置窗口并尝试点击挂断。
        成功发出左键点击返回 True（不保证系统一定结束通话）。
        """
        if not WIN32_AVAILABLE:
            return False
        hwnd = self._find_in_call_window_hwnd()
        if not hwnd:
            logger.warning("[奇士美 PRO] 自动挂断：未找到通话中窗口")
            return False
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.12)
        except Exception as e:
            logger.debug("Hangup bring foreground: %s", e)

        click_x: int
        click_y: int
        method: str
        try:
            pt = self._find_hangup_click_point(hwnd)
            if pt:
                click_x, click_y = pt
                method = "control_text"
            else:
                rect = win32gui.GetWindowRect(hwnd)
                click_x, click_y = self._fallback_hangup_click_xy(rect)
                method = "fallback_geometry"
            self._click_at_position(click_x, click_y)
            logger.info(
                "[奇士美 PRO] 自动挂断已点击 (%s, %s) method=%s hwnd=%s",
                click_x,
                click_y,
                method,
                hwnd,
            )
            return True
        except Exception as e:
            logger.warning("[奇士美 PRO] 自动挂断点击失败: %s", e)
            return False

    def _finish_call_session(self, reason: str) -> None:
        with self._call_session_lock:
            if not self._call_session_active:
                return
            self._call_session_active = False
            self._call_consecutive_absent = 0
            self._call_ever_saw_in_call_ui = False
        self._emit_phone_ui_event(
            {
                "kind": "call_ended",
                "at_ms": int(time.time() * 1000),
                "reason": reason,
            }
        )
        logger.info("[奇士美 PRO] 通话已结束（%s），已通知清空电话 UI 快照", reason)

    def get_state(self) -> MonitorState:
        """获取当前状态"""
        return self.state

    def is_available(self) -> bool:
        """检查是否可用"""
        return WIN32_AVAILABLE
