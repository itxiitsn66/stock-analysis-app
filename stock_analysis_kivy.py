"""
股票智能分析监控系统 - Kivy Android版
基于原 stock_analysis.py 改写，支持打包为 Android APK
注意：Python 3.14 需使用 Kivy 的 Python 3.14 分支或 Python 3.9.18，建议打包时使用 Python 3.9.18
"""

import os
import sys
import json
import requests
import threading
import time
from datetime import datetime
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.properties import ListProperty, StringProperty, BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.recycleview import RecycleView

# ============================================================
# 原业务逻辑（保留不动）
# ============================================================

class StockAPI:
    """股票数据获取"""

    @staticmethod
    def get_stock_price(stock_code):
        """获取股票价格"""
        try:
            code = stock_code
            if code.isdigit():
                if len(code) == 6:
                    if code.startswith('6'):
                        code = 'sh' + code
                    else:
                        code = 'sz' + code

            url = f"https://qt.gtimg.cn/q={code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://finance.qq.com'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'
            text = response.text

            if 'v_' not in text or '=' not in text:
                return None

            data_str = text.split('="')[1].split('"')[0]
            parts = data_str.split('~')

            if len(parts) < 40:
                return None

            name = parts[1] if len(parts) > 1 else '未知'
            stock_code_str = parts[2] if len(parts) > 2 else stock_code

            current_price = float(parts[3]) if parts[3] else 0
            prev_close = float(parts[4]) if parts[4] else 0
            open_price = float(parts[5]) if parts[5] else 0
            change = float(parts[31]) if len(parts) > 31 and parts[31] else 0
            change_pct = float(parts[32]) if len(parts) > 32 and parts[32] else 0

            if len(parts) > 16 and parts[15] and parts[16]:
                high_price = float(parts[15]) if parts[15] else 0
                low_price = float(parts[16]) if parts[16] else 0
            else:
                high_price = float(parts[9]) if len(parts) > 9 and parts[9] else 0
                low_price = float(parts[10]) if len(parts) > 10 and parts[10] else 0
            volume = float(parts[6]) if parts[6] else 0
            amount = float(parts[37]) * 10000 if len(parts) > 37 and parts[37] else 0
            volume_ratio = float(parts[38]) if len(parts) > 38 and parts[38] else 0

            is_st = 'ST' in name.upper() or '*ST' in name.upper() or 'S*' in name.upper()
            limit_pct = 5 if is_st else 10
            limit_up = round(prev_close * (1 + limit_pct / 100), 2) if prev_close else 0
            limit_down = round(prev_close * (1 - limit_pct / 100), 2) if prev_close else 0
            time_str = parts[30] if len(parts) > 30 and parts[30] else ''

            return {
                'name': name,
                'code': stock_code_str,
                'price': current_price,
                'change': change,
                'change_pct': change_pct,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'prev_close': prev_close,
                'limit_up': limit_up,
                'limit_down': limit_down,
                'is_st': is_st,
                'volume': volume,
                'volume_ratio': volume_ratio,
                'amount': amount,
                'time': time_str
            }
        except Exception as e:
            print(f"获取价格失败: {e}")
            return None

    @staticmethod
    def get_stock_news(stock_code):
        """获取股票新闻"""
        try:
            stock_data = StockAPI.get_stock_price(stock_code)
            if not stock_data:
                return []

            stock_name = stock_data.get('name', '')
            if not stock_name or stock_name == '未知':
                return []

            news_list = []
            try:
                search_url = f"https://searchapi.eastmoney.com/api/suggest/get?input={stock_name}&type=14&count=10"
                headers = {'User-Agent': 'Mozilla/5.0'}
                resp = requests.get(search_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if 'News' in data:
                        for item in data['News'][:5]:
                            news_list.append({
                                'title': item.get('Title', ''),
                                'time': item.get('DateTime', ''),
                                'url': item.get('Url', '')
                            })
            except:
                pass

            return news_list[:5]
        except:
            return []

    @staticmethod
    def get_kline_data(stock_code, days=60):
        """获取K线数据"""
        try:
            code = stock_code
            if code.isdigit():
                if len(code) == 6:
                    if code.startswith('6'):
                        code = 'sh' + code
                    else:
                        code = 'sz' + code

            url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{days},qfq"
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com'}
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            data = response.json()

            kline_list = []

            if 'data' in data and code in data['data']:
                stock_data = data['data'][code]
                if 'qfqday' in stock_data:
                    for item in stock_data['qfqday']:
                        try:
                            kline_list.append({
                                'date': item[0],
                                'open': float(item[1]),
                                'close': float(item[2]),
                                'high': float(item[3]),
                                'low': float(item[4]),
                                'volume': float(item[5])
                            })
                        except:
                            continue
                elif 'day' in stock_data:
                    for item in stock_data['day']:
                        try:
                            kline_list.append({
                                'date': item[0],
                                'open': float(item[1]),
                                'close': float(item[2]),
                                'high': float(item[3]),
                                'low': float(item[4]),
                                'volume': float(item[5])
                            })
                        except:
                            continue

            return kline_list
        except Exception as e:
            print(f"获取K线失败: {e}")
            return []

    @staticmethod
    def get_index_price(code):
        """获取大盘指数"""
        try:
            url = f"https://qt.gtimg.cn/q={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'
            text = response.text

            if 'v_' not in text or '=' not in text:
                return None

            data_str = text.split('="')[1].split('"')[0]
            parts = data_str.split('~')

            if len(parts) < 40:
                return None

            return {
                'name': parts[1] if len(parts) > 1 else '',
                'code': parts[2] if len(parts) > 2 else code,
                'price': float(parts[3]) if parts[3] else 0,
                'change': float(parts[31]) if len(parts) > 31 and parts[31] else 0,
                'change_pct': float(parts[32]) if len(parts) > 32 and parts[32] else 0,
            }
        except:
            return None

    @staticmethod
    def get_limit_stocks(limit_type='up', count=10):
        """获取涨停/跌停股票列表"""
        try:
            if limit_type == 'up':
                url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:80&fields=f2,f3,f4,f12,f14"
            else:
                url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=0&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:80&fields=f2,f3,f4,f12,f14"

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'diff' in data['data']:
                    stocks = []
                    for item in data['data']['diff']:
                        price = item.get('f2', 0)
                        change_pct = item.get('f3', 0)

                        if limit_type == 'up' and change_pct >= 9.9:
                            stocks.append({
                                'code': item.get('f12', ''),
                                'name': item.get('f14', ''),
                                'price': price,
                                'change_pct': change_pct
                            })
                        elif limit_type == 'down' and change_pct <= -9.9:
                            stocks.append({
                                'code': item.get('f12', ''),
                                'name': item.get('f14', ''),
                                'price': price,
                                'change_pct': change_pct
                            })

                        if len(stocks) >= count:
                            break
                    return stocks
            return []
        except Exception as e:
            print(f"获取涨跌停失败: {e}")
            return []


class MonitorDB:
    """监控数据存储（改用 JSON 文件）"""

    def __init__(self):
        self.json_path = os.path.join(os.path.dirname(__file__), 'stock_monitor_data.json')
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.json_path):
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump({'monitors': [], 'price_history': []}, f, ensure_ascii=False, indent=2)

    def _load(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'monitors': [], 'price_history': []}

    def _save(self, data):
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_stock(self, code, name='', alert_high=None, alert_low=None):
        data = self._load()
        for m in data['monitors']:
            if m['code'] == code:
                m['name'] = name
                m['alert_high'] = alert_high
                m['alert_low'] = alert_low
                self._save(data)
                return True
        data['monitors'].append({
            'code': code,
            'name': name,
            'alert_high': alert_high,
            'alert_low': alert_low,
            'enabled': True
        })
        self._save(data)
        return True

    def get_stocks(self):
        data = self._load()
        # 返回元组列表：(id, code, name, alert_high, alert_low, enabled)
        result = []
        for i, m in enumerate(data['monitors']):
            result.append((
                i + 1,
                m['code'],
                m['name'],
                m.get('alert_high'),
                m.get('alert_low'),
                1 if m.get('enabled', True) else 0
            ))
        return result

    def remove_stock(self, code):
        data = self._load()
        data['monitors'] = [m for m in data['monitors'] if m['code'] != code]
        self._save(data)

    def update_alert(self, code, alert_high=None, alert_low=None):
        data = self._load()
        for m in data['monitors']:
            if m['code'] == code:
                m['alert_high'] = alert_high
                m['alert_low'] = alert_low
                break
        self._save(data)

    def add_price_history(self, code, name, price, change, change_pct):
        data = self._load()
        data['price_history'].append({
            'code': code,
            'name': name,
            'price': price,
            'change': change,
            'change_pct': change_pct,
            'record_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        # 只保留最近1000条
        if len(data['price_history']) > 1000:
            data['price_history'] = data['price_history'][-1000:]
        self._save(data)

    def get_price_history(self, code, limit=50):
        data = self._load()
        records = [r for r in data['price_history'] if r['code'] == code]
        records = sorted(records, key=lambda x: x['record_time'], reverse=True)[:limit]
        # 转为元组
        return [(r['code'], r['name'], r['price'], r['change'], r['change_pct'], r['record_time']) for r in records]

    def get_all_history(self, limit=100):
        data = self._load()
        records = sorted(data['price_history'], key=lambda x: x['record_time'], reverse=True)[:limit]
        return [(r['code'], r['name'], r['price'], r['change'], r['change_pct'], r['record_time']) for r in records]


# ============================================================
# Kivy UI
# ============================================================

# 涨跌颜色常量
COLOR_UP = '#e74c3c'    # 上涨红色
COLOR_DOWN = '#27ae60' # 下跌绿色
COLOR_BG_DARK = '#1a2a3a'
COLOR_BG_MED = '#2c3e50'
COLOR_ACCENT = '#3498db'
COLOR_WARNING = '#f39c12'


def clr(change_pct):
    """根据涨跌幅返回颜色"""
    if change_pct > 0:
        return COLOR_UP
    elif change_pct < 0:
        return COLOR_DOWN
    return '#7f8c8d'


# ------------------------------------------------------------
# AnalysisScreen
# ------------------------------------------------------------

class StockAnalysisApp(App):
    """股票智能分析监控系统 Kivy 版"""

    def build(self):
        Window.softinput_mode = 'below_target'
        sm = ScreenManager()
        sm.add_widget(AnalysisScreen(name='analysis'))
        sm.add_widget(MarketScreen(name='market'))
        sm.add_widget(MonitorScreen(name='monitor'))
        return sm


class AnalysisScreen(Screen):
    """股票分析页面"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_data = None
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # --- 顶部标题栏 ---
        title_bar = BoxLayout(size_hint_y=None, height='50dp', padding=[10, 5])
        with title_bar.canvas.before:
            Color(0.1, 0.32, 0.46, 1)
            Rectangle(pos=title_bar.pos, size=title_bar.size)
        title_bar.bind(pos=self._update_rect, size=self._update_rect)

        lbl = Label(text='📈 股票智能分析监控系统', font_size='18sp', color=(1, 1, 1, 1),
                    bold=True, size_hint_x=0.7)
        title_bar.add_widget(lbl)

        self.time_lbl = Label(text='', font_size='11sp', color=(1, 1, 1, 0.8), size_hint_x=0.3)
        title_bar.add_widget(self.time_lbl)
        Clock.schedule_interval(self._update_time, 1)

        root.add_widget(title_bar)

        # --- 搜索区 ---
        search_bar = BoxLayout(size_hint_y=None, height='48dp', padding=10, spacing=8)
        with search_bar.canvas.before:
            Color(0.97, 0.98, 1, 1)
            Rectangle(pos=search_bar.pos, size=search_bar.size)
        search_bar.bind(pos=self._update_rect, size=self._update_rect)

        self.code_input = TextInput(hint_text='股票代码', multiline=False, font_size='14sp',
                                     size_hint_x=0.25, halign='center')
        self.code_input.bind(on_text_validate=lambda x: self.analyze())
        search_bar.add_widget(self.code_input)

        btn_analyze = Button(text='🔍 分析', background_color=COLOR_ACCENT, color=(1, 1, 1, 1),
                              font_size='13sp', on_press=lambda x: self.analyze())
        search_bar.add_widget(btn_analyze)

        btn_add = Button(text='➕ 监控', background_color=COLOR_WARNING, color=(1, 1, 1, 1),
                          font_size='13sp', on_press=lambda x: self.add_to_monitor())
        search_bar.add_widget(btn_add)

        self.status_lbl = Label(text='就绪', font_size='12sp', color=(0.5, 0.55, 0.6, 1),
                                  size_hint_x=0.35, halign='left', valign='middle')
        self.status_lbl.bind(width=self._update_lbl_width)
        search_bar.add_widget(self.status_lbl)

        root.add_widget(search_bar)

        # --- 快捷按钮 ---
        quick_bar = BoxLayout(size_hint_y=None, height='40dp', padding=5, spacing=4)
        with quick_bar.canvas.before:
            Color(0.93, 0.94, 0.95, 1)
            Rectangle(pos=quick_bar.pos, size=quick_bar.size)
        quick_bar.bind(pos=self._update_rect, size=self._update_rect)

        stocks = [('茅台', '600519'), ('五粮液', '000858'), ('平安', '601318'),
                  ('宁德', '300750'), ('比亚迪', '002594'), ('美的', '000333'),
                  ('招行', '600036'), ('中信', '600030')]
        for name, code in stocks:
            btn = Button(text=name, font_size='11sp', background_color=COLOR_ACCENT,
                          color=(1, 1, 1, 1), on_press=lambda x, c=code: self.quick_analyze(c),
                          size_hint_x=0.125)
            quick_bar.add_widget(btn)

        root.add_widget(quick_bar)

        # --- 结果区（左右两栏）---
        result_area = BoxLayout(padding=5, spacing=5)

        # 左侧：基本信息
        left_frame = self._make_card()
        left_title = Label(text='📋 基本信息', font_size='13sp', bold=True, color=COLOR_ACCENT,
                            size_hint_y=None, height='30dp', halign='left', valign='middle')
        left_title.bind(width=self._update_lbl_width)
        left_frame.add_widget(left_title)
        self.info_lbl = Label(text='股票名称: --\n\n输入股票代码后点击"分析"', font_size='12sp',
                                color=(0.2, 0.2, 0.2, 1), valign='top', halign='left', markup=True)
        self.info_lbl.bind(width=self._update_lbl_width)
        left_frame.add_widget(self.info_lbl)
        result_area.add_widget(left_frame)

        # 右侧：分析结果
        right_frame = self._make_card()
        right_title = Label(text='📊 分析结果', font_size='13sp', bold=True, color=COLOR_ACCENT,
                             size_hint_y=None, height='30dp', halign='left', valign='middle')
        right_title.bind(width=self._update_lbl_width)
        right_frame.add_widget(right_title)
        self.result_lbl = Label(text='暂无分析结果', font_size='12sp',
                                  color=(0.2, 0.2, 0.2, 1), valign='top', halign='left', markup=True)
        self.result_lbl.bind(width=self._update_lbl_width)
        right_frame.add_widget(self.result_lbl)
        result_area.add_widget(right_frame)

        root.add_widget(result_area)

        # --- 建议栏 ---
        self.recommend_lbl = Label(text='', font_size='15sp', bold=True, color=(1, 1, 1, 1),
                                     size_hint_y=None, height='40dp')
        self.recommend_bg = BoxLayout(size_hint_y=None, height='44dp', padding=5)
        with self.recommend_bg.canvas.before:
            Color(0.17, 0.24, 0.31, 1)
            Rectangle(pos=self.recommend_bg.pos, size=self.recommend_bg.size)
        self.recommend_bg.bind(pos=self._update_rect, size=self._update_rect)
        self.recommend_bg.add_widget(self.recommend_lbl)
        root.add_widget(self.recommend_bg)

        # --- 新闻区 ---
        news_card = self._make_card(size_hint_y=None, height='110dp')
        news_title = Label(text='📰 最新新闻', font_size='12sp', bold=True, color=COLOR_ACCENT,
                            size_hint_y=None, height='24dp')
        news_card.add_widget(news_title)
        sv = ScrollView(size_hint_y=1)
        self.news_lbl = Label(text='暂无相关新闻', font_size='11sp', color=(0.2, 0.2, 0.2, 1),
                               valign='top', halign='left', markup=True)
        self.news_lbl.bind(width=self._update_lbl_width)
        sv.add_widget(self.news_lbl)
        news_card.add_widget(sv)
        root.add_widget(news_card)

        self.add_widget(root)

    def _make_card(self, size_hint_y=1):
        from kivy.uix.anchorlayout import AnchorLayout
        card = BoxLayout(orientation='vertical', padding=8, spacing=4,
                          size_hint_y=size_hint_y)
        with card.canvas.before:
            Color(0.96, 0.97, 1.0, 1)
            Rectangle(pos=card.pos, size=card.size)
        card.bind(pos=self._update_rect, size=self._update_rect)
        return card

    def _update_rect(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            pass  # 动态更新由下面重绘完成，这里用 canvas.before 的方式需要保存颜色
        # 简化：用同一背景色的 canvas 指令写在 build 时绑定

    def _update_time(self, dt):
        self.time_lbl.text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _update_lbl_width(self, lbl, w):
        lbl.text_size = (w, None)

    def quick_analyze(self, code):
        self.code_input.text = code
        self.analyze()

    def analyze(self):
        code = self.code_input.text.strip()
        if not code:
            self.status_lbl.text = '请输入代码'
            return
        self.status_lbl.text = '分析中...'
        self.info_lbl.text = '加载中...'
        self.result_lbl.text = '加载中...'
        threading.Thread(target=self._analyze_thread, args=(code,), daemon=True).start()

    def _analyze_thread(self, code):
        data = StockAPI.get_stock_price(code)
        Clock.schedule_once(lambda dt: self._update_ui(data, code), 0)

    def _update_ui(self, data, code):
        if not data:
            self.status_lbl.text = '未找到股票'
            self.info_lbl.text = '未找到该股票，请检查代码'
            self.result_lbl.text = ''
            self.recommend_lbl.text = ''
            return

        self.current_data = data
        name = data['name']
        price = data['price']
        change = data['change']
        change_pct = data['change_pct']
        prev_close = data.get('prev_close', 0)
        limit_up = data.get('limit_up', 0)
        limit_down = data.get('limit_down', 0)
        is_st = data.get('is_st', False)
        limit_pct_str = "5%" if is_st else "10%"

        # 基本信息
        info_lines = [
            f"[b]股票代码:[/b] {data['code']}",
            f"[b]股票名称:[/b] {name}",
            f"[b]当前价格:[/b] [color={clr(change_pct)}]{price:.2f} 元[/color]",
            f"[b]涨跌额:[/b] [color={clr(change)}]{change:+.2f} 元[/color]",
            f"[b]涨跌幅:[/b] [color={clr(change_pct)}]{change_pct:+.2f}%[/color]",
            f"[b]开盘价:[/b] {data['open']:.2f} 元",
            f"[b]最高价:[/b] {data['high']:.2f} 元",
            f"[b]最低价:[/b] {data['low']:.2f} 元",
            f"[b]昨收盘:[/b] {prev_close:.2f} 元",
            f"[b]涨停价:[/b] {limit_up:.2f} 元 ({limit_pct_str})",
            f"[b]跌停价:[/b] {limit_down:.2f} 元 ({limit_pct_str})",
            f"[b]成交量:[/b] {data['volume'] / 10000:.2f} 万手",
            f"[b]量比:[/b] {data.get('volume_ratio', 0):.2f}",
            f"[b]成交额:[/b] {data['amount'] / 100000000:.2f} 亿元",
            f"[b]更新时间:[/b] {data['time']}",
        ]
        self.info_lbl.text = '\n'.join(info_lines)

        # 分析结果
        trend = "上涨" if change > 0 else ("下跌" if change < 0 else "持平")
        abs_pct = abs(change_pct)
        if abs_pct > 5:
            amplitude = "大幅波动"
            risk_score = 30
        elif abs_pct > 2:
            amplitude = "明显波动"
            risk_score = 15
        else:
            amplitude = "小幅波动"
            risk_score = 5

        if change_pct > 5:
            action = "建议止盈部分"
            score = 40
        elif change_pct < -5:
            action = "可考虑加仓"
            score = 70
        elif change_pct > 2:
            action = "继续持有"
            score = 55
        elif change_pct < -2:
            action = "可适当低吸"
            score = 65
        else:
            action = "观望为主"
            score = 50

        score = max(0, min(100, score - risk_score))

        if score >= 75:
            rec = "[color=#f1c40f]⭐⭐⭐ 强烈推荐买入[/color]"
            bg = COLOR_UP
        elif score >= 60:
            rec = "[color=#2ecc71]⭐⭐ 建议买入[/color]"
            bg = COLOR_ACCENT
        elif score >= 40:
            rec = "[color=#3498db]⭐ 持有观望[/color]"
            bg = COLOR_WARNING
        else:
            rec = "[color=#95a5a6]⚠️ 建议减仓[/color]"
            bg = '#7f8c8d'

        risk_str = "高" if risk_score > 20 else ("中" if risk_score > 10 else "低")
        self.result_lbl.text = (
            f"[b]【技术分析】[/b]\n"
            f"• 当前价格: {price:.2f}元\n"
            f"• 涨跌额: [color={clr(change)}]{change:+.2f}元[/color]\n"
            f"• 涨跌幅: [color={clr(change_pct)}]{change_pct:+.2f}%[/color]\n"
            f"• 今日振幅: {amplitude}\n"
            f"• 趋势判断: {trend}\n\n"
            f"[b]【风险评估】[/b]\n"
            f"• 风险等级: {risk_str}\n"
            f"• 风险因素: 行情波动风险、市场系统性风险\n\n"
            f"[b]【操作建议】[/b]\n"
            f"• 建议操作: {action}\n"
            f"• 操作评分: {score}/100\n\n"
            f"[b]【综合评价】[/b]\n"
            f"{name} 今日{trend} {abs_pct:.2f}%，"
            f"当前价格{price:.2f}元。"
            f"{'注意控制风险' if risk_score > 15 else '可适当关注'}。"
        )

        self.recommend_lbl.text = rec
        with self.recommend_bg.canvas.before:
            self.recommend_bg.canvas.before.children.clear()
        with self.recommend_bg.canvas.before:
            c = Color()
            if score >= 75:
                c.rgba = (0.91, 0.27, 0.24, 1)
            elif score >= 60:
                c.rgba = (0.18, 0.80, 0.44, 1)
            elif score >= 40:
                c.rgba = (0.20, 0.60, 0.86, 1)
            else:
                c.rgba = (0.58, 0.65, 0.65, 1)
            Rectangle(pos=self.recommend_bg.pos, size=self.recommend_bg.size)

        self.status_lbl.text = '分析完成 ✓'

        # 加载新闻
        threading.Thread(target=self._load_news, args=(code,), daemon=True).start()

    def _load_news(self, code):
        news_list = StockAPI.get_stock_news(code)
        Clock.schedule_once(lambda dt: self._update_news(news_list), 0)

    def _update_news(self, news_list):
        if news_list:
            lines = []
            for i, n in enumerate(news_list, 1):
                title = n.get('title', '无标题')[:50]
                t = n.get('time', '')
                lines.append(f"{i}. {title}")
                if t:
                    lines[-1] += f" ({t[:10]})"
            self.news_lbl.text = '\n'.join(lines)
        else:
            self.news_lbl.text = '暂无相关新闻'

    def add_to_monitor(self):
        if not self.current_data:
            self._show_popup('提示', '请先分析一只股票')
            return
        code = self.current_data.get('code', self.code_input.text.strip())
        name = self.current_data.get('name', '未知')
        self._show_add_dialog(code, name)


# ------------------------------------------------------------
# MarketScreen
# ------------------------------------------------------------

class MarketScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def on_enter(self):
        self.refresh()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # 标题
        bar = BoxLayout(size_hint_y=None, height='50dp', padding=10)
        with bar.canvas.before:
            Color(0.1, 0.32, 0.46, 1)
            Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=self._update_rect, size=self._update_rect)
        bar.add_widget(Label(text='📈 大盘行情', font_size='18sp', bold=True, color=(1, 1, 1, 1)))
        btn_refresh = Button(text='🔄 刷新', size_hint_x=0.2, background_color=COLOR_ACCENT,
                              color=(1, 1, 1, 1), on_press=lambda x: self.refresh())
        bar.add_widget(btn_refresh)
        root.add_widget(bar)

        # 指数区
        idx_bg = BoxLayout(size_hint_y=None, height='80dp', padding=8, spacing=6)
        with idx_bg.canvas.before:
            Color(0.94, 0.96, 1.0, 1)
            Rectangle(pos=idx_bg.pos, size=idx_bg.size)
        idx_bg.bind(pos=self._update_rect, size=self._update_rect)

        self.index_widgets = {}
        indices = [
            ('sh000001', '上证指数'),
            ('sz399001', '深证成指'),
            ('sz399006', '创业板指'),
            ('sh000300', '沪深300'),
            ('sh000016', '上证50'),
            ('sh000905', '中证500'),
        ]
        for code, name in indices:
            col = BoxLayout(orientation='vertical', size_hint_x=1/6, padding=4)
            lbl_name = Label(text=name, font_size='11sp', color=(0.4, 0.4, 0.4, 1), halign='center')
            lbl_price = Label(text='--', font_size='15sp', bold=True, color=(0.2, 0.2, 0.2, 1), halign='center')
            lbl_change = Label(text='--', font_size='11sp', halign='center')
            col.add_widget(lbl_name)
            col.add_widget(lbl_price)
            col.add_widget(lbl_change)
            idx_bg.add_widget(col)
            self.index_widgets[code] = {'name': lbl_name, 'price': lbl_price, 'change': lbl_change}

        root.add_widget(idx_bg)

        # 涨跌停区
        limit_area = BoxLayout(padding=5, spacing=5)

        # 涨停榜
        up_card = self._make_card()
        up_card.add_widget(Label(text='📈 涨停榜 TOP10', font_size='13sp', bold=True,
                                   color=COLOR_UP, size_hint_y=None, height='28dp'))
        up_sv = ScrollView(size_hint_y=1)
        up_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        up_layout.bind(minimum_height=up_layout.setter('height'))
        self.limit_up_items = up_layout
        up_sv.add_widget(up_layout)
        up_card.add_widget(up_sv)
        limit_area.add_widget(up_card)

        # 跌停榜
        down_card = self._make_card()
        down_card.add_widget(Label(text='📉 跌停榜 TOP10', font_size='13sp', bold=True,
                                     color=COLOR_DOWN, size_hint_y=None, height='28dp'))
        down_sv = ScrollView(size_hint_y=1)
        down_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        down_layout.bind(minimum_height=down_layout.setter('height'))
        self.limit_down_items = down_layout
        down_sv.add_widget(down_layout)
        down_card.add_widget(down_sv)
        limit_area.add_widget(down_card)

        root.add_widget(limit_area)
        self.add_widget(root)

    def _make_card(self, **kwargs):
        card = BoxLayout(orientation='vertical', padding=8, spacing=4)
        with card.canvas.before:
            Color(0.96, 0.97, 1.0, 1)
            Rectangle(pos=card.pos, size=card.size)
        card.bind(pos=self._update_rect, size=self._update_rect)
        return card

    def _update_rect(self, instance, value):
        pass

    def refresh(self):
        threading.Thread(target=self._refresh_thread, daemon=True).start()

    def _refresh_thread(self):
        # 指数
        for code in self.index_widgets:
            data = StockAPI.get_index_price(code)
            Clock.schedule_once(lambda dt, d=data, c=code: self._update_index(c, d), 0)

        # 涨停榜
        up_stocks = StockAPI.get_limit_stocks('up', 10)
        Clock.schedule_once(lambda dt, s=up_stocks: self._update_limit('up', s), 0)

        # 跌停榜
        down_stocks = StockAPI.get_limit_stocks('down', 10)
        Clock.schedule_once(lambda dt, s=down_stocks: self._update_limit('down', s), 0)

    def _update_index(self, code, data):
        if not data:
            return
        w = self.index_widgets[code]
        pct = data['change_pct']
        color = COLOR_UP if pct > 0 else (COLOR_DOWN if pct < 0 else '#7f8c8d')
        w['price'].text = f"{data['price']:.2f}"
        w['price'].color = self._hex_to_kivy(color)
        w['change'].text = f"{data['change']:+.2f}\n{pct:+.2f}%"
        w['change'].color = self._hex_to_kivy(color)

    def _update_limit(self, direction, stocks):
        target = self.limit_up_items if direction == 'up' else self.limit_down_items
        target.clear_widgets()
        color = COLOR_UP if direction == 'up' else COLOR_DOWN

        if not stocks:
            lbl = Label(text='暂无数据', font_size='12sp', color=(0.5, 0.5, 0.5, 1),
                        size_hint_y=None, height='30dp')
            target.add_widget(lbl)
            return

        for s in stocks:
            row = BoxLayout(size_hint_y=None, height='32dp', padding=[5, 2], spacing=5)
            with row.canvas.before:
                Color(0.96, 0.97, 1.0, 1)
                Rectangle(pos=row.pos, size=row.size)

            def make_lbl(text, bold=False, color_hex=color):
                l = Label(text=text, font_size='11sp', bold=bold,
                           color=self._hex_to_kivy(color_hex), halign='center', valign='middle')
                l.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
                return l

            row.add_widget(make_lbl(s['code'], bold=True, color_hex='#2c3e50'))
            row.add_widget(make_lbl(s['name'][:4], color_hex='#2c3e50'))
            row.add_widget(make_lbl(f"{s['price']:.2f}", color_hex=color))
            row.add_widget(make_lbl(f"{s['change_pct']:+.2f}%", color_hex=color))
            target.add_widget(row)

    def _hex_to_kivy(self, hex_color):
        """#e74c3c -> (0.906, 0.298, 0.235, 1)"""
        h = hex_color.lstrip('#')
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b, 1)


# ------------------------------------------------------------
# MonitorScreen
# ------------------------------------------------------------

class MonitorScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = MonitorDB()
        self.alert_triggered = set()
        self.monitoring = False
        self.monitor_event = None
        self.build_ui()

    def on_enter(self):
        self.load_monitors()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # 标题栏
        bar = BoxLayout(size_hint_y=None, height='50dp', padding=10)
        with bar.canvas.before:
            Color(0.1, 0.32, 0.46, 1)
            Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=self._update_rect, size=self._update_rect)
        bar.add_widget(Label(text='🔔 价格监控', font_size='18sp', bold=True, color=(1, 1, 1, 1)))
        self.monitor_btn = Button(text='▶ 开始监控', size_hint_x=0.3,
                                    background_color=COLOR_DOWN, color=(1, 1, 1, 1),
                                    on_press=lambda x: self.toggle_monitor())
        bar.add_widget(self.monitor_btn)
        root.add_widget(bar)

        # 添加监控区
        add_bar = BoxLayout(size_hint_y=None, height='48dp', padding=8, spacing=6)
        with add_bar.canvas.before:
            Color(0.96, 0.97, 1.0, 1)
            Rectangle(pos=add_bar.pos, size=add_bar.size)
        add_bar.bind(pos=self._update_rect, size=self._update_rect)

        add_bar.add_widget(Label(text='代码:', font_size='12sp', size_hint_x=0.08))
        self.monitor_code_input = TextInput(hint_text='000000', multiline=False, font_size='13sp',
                                             size_hint_x=0.22, input_type='number')
        add_bar.add_widget(self.monitor_code_input)

        add_bar.add_widget(Label(text='高价:', font_size='12sp', size_hint_x=0.08))
        self.monitor_high_input = TextInput(hint_text='高价', multiline=False, font_size='13sp',
                                             size_hint_x=0.18, input_type='number')
        add_bar.add_widget(self.monitor_high_input)

        add_bar.add_widget(Label(text='低价:', font_size='12sp', size_hint_x=0.08))
        self.monitor_low_input = TextInput(hint_text='低价', multiline=False, font_size='13sp',
                                            size_hint_x=0.18, input_type='number')
        add_bar.add_widget(self.monitor_low_input)

        add_btn = Button(text='添加', background_color=COLOR_DOWN, color=(1, 1, 1, 1),
                          size_hint_x=0.18, on_press=lambda x: self.add_monitor())
        add_bar.add_widget(add_btn)
        root.add_widget(add_bar)

        # 监控列表
        self.monitor_list = BoxLayout(orientation='vertical', padding=5, spacing=2)
        self.monitor_items_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self.monitor_items_layout.bind(minimum_height=self.monitor_items_layout.setter('height'))
        list_sv = ScrollView(size_hint_y=1)
        list_sv.add_widget(self.monitor_items_layout)
        self.monitor_list.add_widget(list_sv)
        root.add_widget(self.monitor_list)

        # 底部按钮
        btn_bar = BoxLayout(size_hint_y=None, height='46dp', padding=8, spacing=8)
        with btn_bar.canvas.before:
            Color(0.93, 0.94, 0.95, 1)
            Rectangle(pos=btn_bar.pos, size=btn_bar.size)
        btn_bar.bind(pos=self._update_rect, size=self._update_rect)

        btn_history = Button(text='📜 历史记录', background_color=COLOR_ACCENT, color=(1, 1, 1, 1),
                               on_press=lambda x: self.show_history())
        btn_bar.add_widget(btn_history)

        btn_kline = Button(text='📈 K线图', background_color='#9b59b6', color=(1, 1, 1, 1),
                             on_press=lambda x: self.show_kline_dialog())
        btn_bar.add_widget(btn_kline)

        self.monitor_status_lbl = Label(text='监控状态: 未启动', font_size='12sp', color=(0.5, 0.5, 0.5, 1))
        btn_bar.add_widget(self.monitor_status_lbl)

        root.add_widget(btn_bar)
        self.add_widget(root)

    def _update_rect(self, instance, value):
        pass

    def add_monitor(self):
        code = self.monitor_code_input.text.strip()
        if not code:
            self._show_popup('提示', '请输入股票代码')
            return
        try:
            high = float(self.monitor_high_input.text) if self.monitor_high_input.text else None
            low = float(self.monitor_low_input.text) if self.monitor_low_input.text else None
        except ValueError:
            self._show_popup('错误', '提醒价格必须是数字')
            return

        data = StockAPI.get_stock_price(code)
        if not data:
            self._show_popup('错误', '未找到该股票')
            return

        name = data.get('name', '未知')
        self.db.add_stock(code, name, high, low)
        self.monitor_code_input.text = ''
        self.monitor_high_input.text = ''
        self.monitor_low_input.text = ''
        self.load_monitors()

    def load_monitors(self):
        self.monitor_items_layout.clear_widgets()
        stocks = self.db.get_stocks()

        # 表头
        header = BoxLayout(size_hint_y=None, height='30dp', padding=[5, 0], spacing=2)
        for txt, w in [('代码', 0.14), ('名称', 0.14), ('现价', 0.12),
                       ('涨跌', 0.12), ('涨跌幅', 0.13), ('状态', 0.15),
                       ('操作', 0.20)]:
            lbl = Label(text=txt, font_size='11sp', bold=True, color=(0.3, 0.3, 0.3, 1),
                         halign='center')
            lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
            header.add_widget(lbl)
        self.monitor_items_layout.add_widget(header)

        if not stocks:
            empty = Label(text='暂无监控股票', font_size='13sp', color=(0.5, 0.5, 0.5, 1),
                           size_hint_y=None, height='50dp')
            self.monitor_items_layout.add_widget(empty)
            return

        for stock in stocks:
            _id, code, name, alert_high, alert_low, enabled = stock
            row = BoxLayout(size_hint_y=None, height='42dp', padding=[5, 2], spacing=2)
            with row.canvas.before:
                Color(0.96, 0.97, 1.0, 1)
                Rectangle(pos=row.pos, size=row.size)

            # 数据列
            for txt in [code, (name[:5] if name else '--')]:
                lbl = Label(text=str(txt), font_size='11sp', color=(0.2, 0.2, 0.2, 1),
                             halign='center', valign='middle')
                lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
                row.add_widget(lbl)

            for txt in ['--', '--', '--']:
                lbl = Label(text=txt, font_size='11sp', color=(0.5, 0.5, 0.5, 1),
                             halign='center', valign='middle')
                lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
                row.add_widget(lbl)

            status_lbl = Label(text='未监控', font_size='11sp', color=(0.5, 0.5, 0.5, 1),
                                halign='center', valign='middle')
            status_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
            row.add_widget(status_lbl)

            btn_box = BoxLayout(spacing=3)
            edit_btn = Button(text='✏', font_size='12sp', size_hint_x=0.5,
                               background_color=COLOR_ACCENT, color=(1, 1, 1, 1),
                               on_press=lambda x, c=code, ah=alert_high, al=alert_low:
                               self._show_edit_dialog(c, ah, al))
            del_btn = Button(text='🗑', font_size='12sp', size_hint_x=0.5,
                               background_color=COLOR_UP, color=(1, 1, 1, 1),
                               on_press=lambda x, c=code: self.delete_monitor(c))
            btn_box.add_widget(edit_btn)
            btn_box.add_widget(del_btn)
            row.add_widget(btn_box)

            self.monitor_items_layout.add_widget(row)

    def _show_edit_dialog(self, code, alert_high, alert_low):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        content.add_widget(Label(text=f'设置提醒 - {code}', font_size='14sp', bold=True))

        high_input = TextInput(text=str(alert_high) if alert_high else '',
                                hint_text='高价提醒', multiline=False, font_size='13sp',
                                size_hint_y=None, height='40dp', input_type='number')
        low_input = TextInput(text=str(alert_low) if alert_low else '',
                               hint_text='低价提醒', multiline=False, font_size='13sp',
                               size_hint_y=None, height='40dp', input_type='number')
        content.add_widget(high_input)
        content.add_widget(low_input)

        btn_row = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        btn_row.add_widget(Button(text='保存', background_color=COLOR_DOWN, color=(1, 1, 1, 1),
                                   on_press=lambda x: self._save_edit(code, high_input, low_input, popup)))
        btn_row.add_widget(Button(text='取消', background_color=(0.6, 0.6, 0.6, 1), color=(1, 1, 1, 1),
                                   on_press=popup.dismiss))
        content.add_widget(btn_row)

        popup = Popup(title='编辑提醒', content=content, size_hint=(0.8, 0.5),
                       auto_dismiss=True)
        popup.open()

    def _save_edit(self, code, high_input, low_input, popup):
        try:
            high = float(high_input.text) if high_input.text else None
            low = float(low_input.text) if low_input.text else None
        except ValueError:
            self._show_popup('错误', '请输入有效数字')
            return
        self.db.update_alert(code, high, low)
        # 清除已触发
        keys = [k for k in self.alert_triggered if k.startswith(code)]
        for k in keys:
            self.alert_triggered.discard(k)
        popup.dismiss()
        self.load_monitors()

    def delete_monitor(self, code):
        self.db.remove_stock(code)
        self.load_monitors()

    def toggle_monitor(self):
        self.monitoring = not self.monitoring
        if self.monitoring:
            self.monitor_btn.text = '⏹ 停止'
            self.monitor_btn.background_color = COLOR_UP
            self.monitor_status_lbl.text = '监控中 (每10秒刷新)'
            self.monitor_status_lbl.color = (0.18, 0.68, 0.35, 1)
            Clock.schedule_interval(self._update_monitor, 10)
        else:
            self.monitor_btn.text = '▶ 开始监控'
            self.monitor_btn.background_color = COLOR_DOWN
            self.monitor_status_lbl.text = '已停止'
            self.monitor_status_lbl.color = (0.9, 0.3, 0.24, 1)
            Clock.unschedule(self._update_monitor)
            self.alert_triggered.clear()

    def _update_monitor(self, dt):
        threading.Thread(target=self._update_monitor_thread, daemon=True).start()

    def _update_monitor_thread(self):
        stocks = self.db.get_stocks()
        for stock in stocks:
            _id, code, name, alert_high, alert_low, enabled = stock
            data = StockAPI.get_stock_price(code)
            if data:
                price = data['price']
                change = data['change']
                change_pct = data['change_pct']
                self.db.add_price_history(code, data['name'], price, change, change_pct)
                alert_key = f"{code}_{alert_high}_{alert_low}"
                if alert_high and price >= alert_high and alert_key not in self.alert_triggered:
                    Clock.schedule_once(lambda dt, c=code, n=name, t='高价', ap=alert_high, cp=price:
                                        self._show_alert(c, n, t, ap, cp), 0)
                    self.alert_triggered.add(alert_key)
                elif alert_low and price <= alert_low and alert_key not in self.alert_triggered:
                    Clock.schedule_once(lambda dt, c=code, n=name, t='低价', ap=alert_low, cp=price:
                                        self._show_alert(c, n, t, ap, cp), 0)
                    self.alert_triggered.add(alert_key)

        Clock.schedule_once(lambda dt: self.load_monitors(), 0)

    def _show_alert(self, code, name, alert_type, target_price, current_price):
        self._show_popup(f'🚨 {name} 价格提醒!',
                          f'股票: {name} ({code})\n'
                          f'提醒类型: {alert_type}\n'
                          f'目标价格: {target_price:.2f}元\n'
                          f'当前价格: {current_price:.2f}元')

    def show_history(self):
        records = self.db.get_all_history(100)
        content = BoxLayout(orientation='vertical', padding=10, spacing=5)
        content.add_widget(Label(text=f'📜 价格历史 (共 {len(records)} 条)', font_size='14sp', bold=True,
                                   size_hint_y=None, height='30dp'))
        sv = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        inner.bind(minimum_height=inner.setter('height'))

        # 表头
        hrow = BoxLayout(size_hint_y=None, height='28dp', spacing=2)
        for txt, fw in [('时间', 0.35), ('代码', 0.18), ('名称', 0.20), ('价格', 0.15), ('涨跌幅', 0.18)]:
            lbl = Label(text=txt, font_size='11sp', bold=True, color=(0.3, 0.3, 0.3, 1),
                         size_hint_x=fw, halign='center')
            hrow.add_widget(lbl)
        inner.add_widget(hrow)

        for r in records:
            row = BoxLayout(size_hint_y=None, height='26dp', spacing=2)
            pct = r[4]
            color = COLOR_UP if pct > 0 else (COLOR_DOWN if pct < 0 else '#7f8c8d')
            vals = [r[5][:16] if r[5] else '', r[0], r[1][:5] if r[1] else '',
                    f"{r[2]:.2f}" if r[2] else '', f"{pct:+.2f}%"]
            for i, (txt, fw) in enumerate(zip(vals, [0.35, 0.18, 0.20, 0.15, 0.18])):
                c = color if i == 4 else '#333333'
                lbl = Label(text=txt, font_size='10sp', color=self._hex_to_kivy(c),
                             size_hint_x=fw, halign='center', valign='middle')
                lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
                row.add_widget(lbl)
            inner.add_widget(row)

        sv.add_widget(inner)
        content.add_widget(sv)
        popup = Popup(title='价格历史记录', content=content, size_hint=(0.95, 0.85),
                       auto_dismiss=True)
        popup.open()

    def show_kline_dialog(self):
        """弹出K线图窗口（显示最近50天数据表格）"""
        selection_code = None
        # 简化：直接用监控列表第一只，或让用户输入代码
        stocks = self.db.get_stocks()
        if not stocks:
            self._show_popup('提示', '请先添加监控股票')
            return

        code_input = TextInput(hint_text='股票代码', multiline=False, font_size='13sp',
                                size_hint_y=None, height='40dp')
        name_input = Label(text='可选：输入代码查看K线', font_size='11sp', color=(0.5, 0.5, 0.5, 1),
                            size_hint_y=None, height='25dp')

        def load_kline(popup):
            code = code_input.text.strip()
            if not code:
                return
            popup.dismiss()
            self._show_kline_popup(code)

        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        content.add_widget(Label(text='📈 K线数据查看', font_size='14sp', bold=True))
        content.add_widget(code_input)
        content.add_widget(name_input)
        btn_row = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        btn_row.add_widget(Button(text='查看', background_color='#9b59b6', color=(1, 1, 1, 1),
                                   on_press=lambda x: load_kline(popup)))
        btn_row.add_widget(Button(text='取消', background_color=(0.6, 0.6, 0.6, 1), color=(1, 1, 1, 1),
                                   on_press=popup.dismiss))
        content.add_widget(btn_row)
        popup = Popup(title='选择股票', content=content, size_hint=(0.7, 0.45), auto_dismiss=True)
        popup.open()

    def _show_kline_popup(self, code):
        threading.Thread(target=self._load_kline_thread, args=(code,), daemon=True).start()

    def _load_kline_thread(self, code):
        kdata = StockAPI.get_kline_data(code, 50)
        Clock.schedule_once(lambda dt: self._display_kline(code, kdata), 0)

    def _display_kline(self, code, kdata):
        content = BoxLayout(orientation='vertical', padding=10, spacing=5)
        content.add_widget(Label(text=f'📊 {code} K线数据 (近50日)', font_size='14sp', bold=True,
                                   size_hint_y=None, height='30dp'))
        sv = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        inner.bind(minimum_height=inner.setter('height'))

        # 表头
        hrow = BoxLayout(size_hint_y=None, height='28dp', spacing=2)
        for txt, fw in [('日期', 0.22), ('开盘', 0.18), ('最高', 0.18), ('最低', 0.18), ('收盘', 0.18), ('成交量', 0.18)]:
            lbl = Label(text=txt, font_size='11sp', bold=True, color=(0.3, 0.3, 0.3, 1), halign='center')
            hrow.add_widget(lbl)
        inner.add_widget(hrow)

        if not kdata:
            inner.add_widget(Label(text='无K线数据', font_size='12sp', color=(0.5, 0.5, 0.5, 1),
                                    size_hint_y=None, height='40dp'))
        else:
            for d in kdata:
                row = BoxLayout(size_hint_y=None, height='24dp', spacing=2)
                prev_close = None
                for val, fw in [(d['date'], 0.22), (f"{d['open']:.2f}", 0.18),
                                 (f"{d['high']:.2f}", 0.18), (f"{d['low']:.2f}", 0.18),
                                 (f"{d['close']:.2f}", 0.18),
                                 (f"{d['volume']/10000:.2f}万", 0.18)]:
                    lbl = Label(text=str(val), font_size='10sp', color=(0.2, 0.2, 0.2, 1),
                                 size_hint_x=fw, halign='center', valign='middle')
                    row.add_widget(lbl)
                inner.add_widget(row)

        sv.add_widget(inner)
        content.add_widget(sv)
        popup = Popup(title=f'K线数据', content=content, size_hint=(0.95, 0.85), auto_dismiss=True)
        popup.open()

    def _show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(text=message, font_size='14sp', valign='middle', halign='center'))
        btn = Button(text='确定', size_hint_y=None, height='40dp',
                      background_color=COLOR_ACCENT, color=(1, 1, 1, 1),
                      on_press=lambda x: popup.dismiss())
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4), auto_dismiss=True)
        popup.open()

    def _hex_to_kivy(self, hex_color):
        h = hex_color.lstrip('#')
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b, 1)


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    StockAnalysisApp().run()
