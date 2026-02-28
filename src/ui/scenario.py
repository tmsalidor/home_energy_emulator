"""シナリオ管理タブ UI モジュール"""
from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Any

from nicegui import ui

from src.core.engine import engine
from src.config.settings import settings

SCENARIOS_DIR = Path("data/scenarios")


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def _list_scenario_files() -> list[str]:
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(f.name for f in SCENARIOS_DIR.glob("*.csv"))


def _load_csv_data(filename: str) -> list[dict[str, Any]]:
    if not filename:
        return []
    path = SCENARIOS_DIR / filename
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rows.append({
                "_id":    i,
                "time":   row.get("time", ""),
                "load_w": float(row.get("load_w", 0)),
                "solar_w": float(row.get("solar_w", 0)),
                "notes":  row.get("notes", ""),
            })
    return rows


def _save_csv_data(filename: str, rows: list[dict[str, Any]]) -> None:
    path = SCENARIOS_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "load_w", "solar_w", "notes"])
        writer.writeheader()
        # _id は内部管理用なので保存しない
        writer.writerows({k: v for k, v in r.items() if k != "_id"} for r in rows)


def _get_echart_option(rows: list[dict[str, Any]]) -> dict:
    times = [r["time"] for r in rows]
    loads = [r["load_w"] for r in rows]
    solars = [r["solar_w"] for r in rows]
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["負荷 (W)", "太陽光 (W)"]},
        "grid": {"left": "5%", "right": "5%", "bottom": "10%", "containLabel": True},
        "xAxis": {"type": "category", "data": times, "name": "時刻"},
        "yAxis": {"type": "value", "name": "電力 (W)"},
        "series": [
            {
                "name": "負荷 (W)",
                "type": "line",
                "data": loads,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": "#ef4444"},
                "lineStyle": {"color": "#ef4444", "width": 2},
                "areaStyle": {"color": "rgba(239,68,68,0.08)"},
            },
            {
                "name": "太陽光 (W)",
                "type": "line",
                "data": solars,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": "#f59e0b"},
                "lineStyle": {"color": "#f59e0b", "width": 2},
                "areaStyle": {"color": "rgba(245,158,11,0.08)"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# メイン render 関数
# ---------------------------------------------------------------------------

def render():
    # ------------------------------------------------------------------
    # 状態変数
    # ------------------------------------------------------------------
    _all_files = _list_scenario_files()
    _configured_fname = Path(settings.simulation.scenario_file).name
    _initial_fname = _configured_fname if _configured_fname in _all_files else (_all_files[0] if _all_files else "")

    current_rows: list[list[dict[str, Any]]] = [_load_csv_data(_initial_fname)]
    active_file: list[str] = [_initial_fname]

    with ui.column().classes("w-full p-4 gap-4"):
        ui.label("シナリオ管理").classes("text-3xl font-bold")

        # ==============================================================
        # セクション 1: シナリオ一覧 & アクション
        # ==============================================================
        with ui.card().classes("w-full p-4"):
            ui.label("シナリオ一覧").classes("text-xl font-bold mb-2")

            with ui.row().classes("w-full items-end gap-4 flex-wrap"):

                scenario_select = ui.select(
                    label="シナリオファイル",
                    options=_list_scenario_files(),
                    value=_initial_fname,
                    on_change=lambda e: _on_scenario_changed(e.value),
                ).classes("flex-grow min-w-52")

                def refresh_select():
                    scenario_select.options = _list_scenario_files()
                    scenario_select.update()

                active_label = ui.label().classes("text-sm text-green-600 font-bold self-center")

                def update_active_label():
                    active_label.set_text(f"▶ 実行中: {active_file[0]}")

                update_active_label()

                def on_apply():
                    fname = scenario_select.value
                    if not fname:
                        ui.notify("シナリオを選択してください", type="warning")
                        return
                    path = str(SCENARIOS_DIR / fname)
                    engine.switch_scenario(path)
                    active_file[0] = fname
                    settings.simulation.scenario_file = path
                    settings.save_to_yaml()
                    update_active_label()
                    ui.notify(f"「{fname}」を実行シナリオに設定しました", type="positive")

                ui.button("▶ 実行シナリオに設定", on_click=on_apply).props("color=primary")

                # ---- リネーム ----
                def on_rename():
                    fname = scenario_select.value
                    if not fname:
                        ui.notify("シナリオを選択してください", type="warning")
                        return
                    stem = Path(fname).stem
                    with ui.dialog() as dlg, ui.card().classes("p-6 min-w-80"):
                        ui.label("シナリオ名を変更").classes("text-lg font-bold mb-4")
                        inp = ui.input("新しいファイル名 (.csv は不要)", value=stem).classes("w-full")
                        with ui.row().classes("mt-4 gap-2 justify-end"):
                            ui.button("キャンセル", on_click=dlg.close).props("flat")
                            def do_rename():
                                new_stem = inp.value.strip()
                                if not new_stem:
                                    ui.notify("ファイル名を入力してください", type="warning")
                                    return
                                new_name = new_stem if new_stem.endswith(".csv") else f"{new_stem}.csv"
                                if (SCENARIOS_DIR / new_name).exists():
                                    ui.notify(f"「{new_name}」はすでに存在します", type="negative")
                                    return
                                (SCENARIOS_DIR / fname).rename(SCENARIOS_DIR / new_name)
                                # 実行中ファイルの場合は設定更新
                                if fname == active_file[0]:
                                    active_file[0] = new_name
                                    settings.simulation.scenario_file = str(SCENARIOS_DIR / new_name)
                                    settings.save_to_yaml()
                                    update_active_label()
                                ui.notify(f"「{fname}」→「{new_name}」に変更しました", type="positive")
                                refresh_select()
                                scenario_select.value = new_name
                                dlg.close()
                            ui.button("変更", on_click=do_rename).props("color=primary")
                    dlg.open()

                ui.button("✏ 名前変更", on_click=on_rename).props("color=secondary flat")

                def on_delete():
                    fname = scenario_select.value
                    if not fname:
                        ui.notify("シナリオを選択してください", type="warning")
                        return
                    if fname == active_file[0]:
                        ui.notify("実行中のシナリオは削除できません", type="negative")
                        return
                    path = SCENARIOS_DIR / fname
                    if path.exists():
                        path.unlink()
                        ui.notify(f"「{fname}」を削除しました", type="warning")
                        refresh_select()
                        if scenario_select.options:
                            scenario_select.value = scenario_select.options[0]

                ui.button("🗑 削除", on_click=on_delete).props("color=negative flat")

                def on_duplicate():
                    fname = scenario_select.value
                    if not fname:
                        ui.notify("シナリオを選択してください", type="warning")
                        return
                    stem = Path(fname).stem
                    new_name = f"{stem}_copy.csv"
                    counter = 1
                    while (SCENARIOS_DIR / new_name).exists():
                        new_name = f"{stem}_copy{counter}.csv"
                        counter += 1
                    shutil.copy(SCENARIOS_DIR / fname, SCENARIOS_DIR / new_name)
                    ui.notify(f"「{new_name}」として複製しました", type="positive")
                    refresh_select()
                    scenario_select.value = new_name

                ui.button("📋 複製", on_click=on_duplicate).props("color=secondary flat")


        # ==============================================================
        # セクション 2: グラフ
        # ==============================================================
        with ui.card().classes("w-full p-4"):
            ui.label("グラフ表示").classes("text-xl font-bold mb-2")
            chart = ui.echart(_get_echart_option(current_rows[0])).classes("w-full h-64")

            def refresh_chart(rows: list[dict[str, Any]]):
                chart.options.clear()
                chart.options.update(_get_echart_option(rows))
                chart.update()

        # ==============================================================
        # セクション 3: テーブル編集（NiceGUI ネイティブ ui.table）
        # ==============================================================
        with ui.card().classes("w-full p-4"):
            ui.label("テーブル編集").classes("text-xl font-bold mb-2")
            ui.label("行をクリックして編集、追加・削除は下のボタンで行います").classes("text-xs text-gray-400 mb-2")

            columns = [
                {"name": "time",    "label": "時刻 (HH:MM)", "field": "time",    "align": "left",   "sortable": True},
                {"name": "load_w",  "label": "負荷 (W)",      "field": "load_w",  "align": "right",  "sortable": True},
                {"name": "solar_w", "label": "太陽光 (W)",    "field": "solar_w", "align": "right",  "sortable": True},
                {"name": "notes",   "label": "メモ",          "field": "notes",   "align": "left"},
            ]

            table = ui.table(
                columns=columns,
                rows=current_rows[0],
                row_key="_id",
                selection="single",
            ).classes("w-full").style("max-height: 320px; overflow-y: auto;")

            def sync_table(rows: list[dict[str, Any]]):
                """Python 側のデータを ui.table に同期する"""
                table.rows.clear()
                table.rows.extend(rows)
                table.update()

            # 30分刻みの時刻リスト
            _TIME_OPTIONS = [
                f"{h:02d}:{m:02d}"
                for h in range(24)
                for m in (0, 30)
            ]

            # ---- 行編集／追加ダイアログ（共通）----
            def open_edit_dialog(row: dict[str, Any], is_new: bool = False):
                """
                is_new=True : 新規行追加モード（row は初期値を持つ仮の dict）
                is_new=False: 既存行編集モード（row は実际のデータ）
                """
                row_id = row.get("_id")
                if not is_new:
                    idx = next((i for i, r in enumerate(current_rows[0]) if r.get("_id") == row_id), None)
                    if idx is None:
                        return
                else:
                    idx = None  # 追加モードでは未使用

                with ui.dialog() as dlg, ui.card().classes("p-6 min-w-80"):
                    ui.label("行を追加" if is_new else "行を編集").classes("text-lg font-bold mb-4")

                    current_time = row["time"]
                    time_opts = _TIME_OPTIONS if current_time in _TIME_OPTIONS else [current_time] + _TIME_OPTIONS
                    inp_time = ui.select(
                        label="時刻",
                        options=time_opts,
                        value=current_time,
                        with_input=True,
                    ).classes("w-full")

                    inp_load  = ui.number("負荷 (W)",   value=row["load_w"],  format="%.0f", step=10)
                    inp_solar = ui.number("太陽光 (W)", value=row["solar_w"], format="%.0f", step=10)
                    inp_notes = ui.input("メモ",        value=row["notes"])

                    with ui.row().classes("mt-4 gap-2 justify-end"):
                        ui.button("キャンセル", on_click=dlg.close).props("flat")

                        def on_ok():
                            new_time = inp_time.value
                            existing_times = {r["time"] for r in current_rows[0]}

                            if is_new:
                                # 追加モード: 重複チェック
                                if new_time in existing_times:
                                    ui.notify(f"時刻「{new_time}」はすでに存在します", type="negative")
                                    return
                                new_id = max((r.get("_id", -1) for r in current_rows[0]), default=-1) + 1
                                new_row = {
                                    "_id":    new_id,
                                    "time":   new_time,
                                    "load_w":  float(inp_load.value or 0),
                                    "solar_w": float(inp_solar.value or 0),
                                    "notes":  inp_notes.value,
                                }
                                rows = list(current_rows[0]) + [new_row]
                            else:
                                # 編集モード: 自分以外との重複チェック
                                other_times = {r["time"] for r in current_rows[0] if r.get("_id") != row_id}
                                if new_time in other_times:
                                    ui.notify(f"時刻「{new_time}」はすでに存在します", type="negative")
                                    return
                                rows = list(current_rows[0])
                                rows[idx] = {
                                    "_id":    row_id,
                                    "time":   new_time,
                                    "load_w":  float(inp_load.value or 0),
                                    "solar_w": float(inp_solar.value or 0),
                                    "notes":  inp_notes.value,
                                }

                            # 時刻でソート
                            rows.sort(key=lambda r: r["time"])
                            current_rows[0] = rows
                            sync_table(rows)
                            refresh_chart(rows)
                            dlg.close()

                        ui.button("OK", on_click=on_ok).props("color=primary")

                dlg.open()

            def on_row_click(e):
                """行クリック時に編集ダイアログを開く"""
                args = e.args
                row = None
                if isinstance(args, dict):
                    row = args
                elif isinstance(args, list):
                    for item in args:
                        if isinstance(item, dict) and "time" in item:
                            row = item
                            break
                if row is None:
                    return
                open_edit_dialog(row, is_new=False)

            table.on("rowClick", on_row_click)

            # ---- ボタン行 ----
            with ui.row().classes("gap-2 mt-3 flex-wrap"):

                def on_add_row():
                    # 追加ダイアログを空の初期値で開く
                    new_id = max((r.get("_id", -1) for r in current_rows[0]), default=-1) + 1
                    open_edit_dialog(
                        {"_id": new_id, "time": "00:00", "load_w": 0.0, "solar_w": 0.0, "notes": ""},
                        is_new=True,
                    )

                ui.button("＋ 行追加", on_click=on_add_row).props("color=primary flat size=sm")



                def on_delete_selected():
                    selected = table.selected
                    if not selected:
                        ui.notify("削除する行を選択してください（行をクリック）", type="warning")
                        return
                    sel_ids = {s.get("_id") for s in selected}
                    rows = [r for r in current_rows[0] if r.get("_id") not in sel_ids]
                    current_rows[0] = rows
                    sync_table(rows)
                    refresh_chart(rows)
                    table.selected.clear()

                ui.button("－ 行削除", on_click=on_delete_selected).props("color=negative flat size=sm")

                def on_save():
                    fname = scenario_select.value
                    if not fname:
                        ui.notify("シナリオを選択してください", type="warning")
                        return
                    rows = list(current_rows[0])
                    rows.sort(key=lambda r: r["time"])
                    _save_csv_data(fname, rows)
                    current_rows[0] = rows
                    sync_table(rows)
                    refresh_chart(rows)
                    ui.notify(f"「{fname}」を保存しました", type="positive", position="top")
                    if fname == active_file[0]:
                        engine.switch_scenario(str(SCENARIOS_DIR / fname))

                ui.button("💾 CSV 保存", on_click=on_save).props("color=primary size=sm")
                ui.label("ヒント: 行をクリックすると編集ダイアログが開きます").classes("text-xs text-gray-400 self-center")

        # ==============================================================
        # シナリオ選択変更時
        # ==============================================================
        def _on_scenario_changed(fname: str):
            if not fname:
                return
            rows = _load_csv_data(fname)
            current_rows[0] = rows
            sync_table(rows)
            refresh_chart(rows)

