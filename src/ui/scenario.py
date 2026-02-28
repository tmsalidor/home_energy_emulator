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
    if not SCENARIOS_DIR.exists():
        return []
    return sorted([f.name for f in SCENARIOS_DIR.glob("*.csv")])

def _load_csv_data(filename: str) -> list[dict[str, Any]]:
    path = SCENARIOS_DIR / filename
    if not path.exists():
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                val = {"_id": i}
                val["time"] = row.get("time", "")
                val["load_w"] = float(row.get("load_w", 0))
                val["solar_w"] = float(row.get("solar_w", 0))
                val["notes"] = row.get("notes", "")
                rows.append(val)
    except Exception as e:
        ui.notify(f"Failed to load CSV: {e}", type="negative")
    return rows

def _save_csv_data(filename: str, rows: list[dict[str, Any]]) -> None:
    path = SCENARIOS_DIR / filename
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["time", "load_w", "solar_w", "notes"])
            writer.writeheader()
            for r in rows:
                writer.writerow({
                    "time": r["time"], "load_w": r["load_w"], "solar_w": r["solar_w"], "notes": r["notes"]
                })
    except Exception as e:
        ui.notify(f"Failed to save CSV: {e}", type="negative")

def _get_echart_option(rows: list[dict[str, Any]]) -> dict:
    if not rows:
        return {}
    times = [r["time"] for r in rows]
    loads = [r["load_w"] for r in rows]
    solars = [r["solar_w"] for r in rows]
    
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Load (W)", "Solar (W)"], "top": 0},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "top": "40px", "containLabel": True},
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": times,
            "name": "Time",
            "nameLocation": "middle",
            "nameGap": 25
        },
        "yAxis": {"type": "value", "name": "Power (W)"},
        "series": [
            {
                "name": "Load (W)",
                "type": "line",
                "smooth": True,
                "data": loads,
                "itemStyle": {"color": "#3b82f6"}
            },
            {
                "name": "Solar (W)",
                "type": "line",
                "smooth": True,
                "data": solars,
                "areaStyle": {"opacity": 0.3},
                "itemStyle": {"color": "#10b981"}
            },
        ],
    }

# ---------------------------------------------------------------------------
# Controller クラス（UIロジックと状態管理をカプセル化）
# ---------------------------------------------------------------------------

class ScenarioController:
    def __init__(self):
        self.all_files = _list_scenario_files()
        configured_fname = Path(settings.simulation.scenario_file).name
        self.initial_fname = configured_fname if configured_fname in self.all_files else (self.all_files[0] if self.all_files else "")
        self.current_rows = [_load_csv_data(self.initial_fname)] if self.initial_fname else [[]]
        self.active_file = [self.initial_fname]
        
        # 30分刻みの時刻リスト
        self.time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

        # UI コンポーネントへの参照（render実行時にセットされる）
        self.scenario_select = None
        self.active_label = None
        self.chart = None
        self.table = None

    def render(self):
        with ui.column().classes("w-full p-4 gap-4"):
            ui.label("Scenario Management").classes("text-3xl font-bold")
            self._render_scenario_selector()
            self._render_chart()
            self._render_data_editor()

    # ------------------------------------------------------------------
    # セクション 1: シナリオ一覧 & アクション
    # ------------------------------------------------------------------
    def _render_scenario_selector(self):
        with ui.card().classes("w-full p-4"):
            ui.label("Scenarios").classes("text-xl font-bold mb-2")
            with ui.column().classes("w-full gap-3"):
                # --- 0行目: Active scenario 表示 ---
                with ui.row().classes("items-baseline gap-2"):
                    ui.label("Active scenario:").classes("text-sm text-gray-500")
                    self.active_label = ui.label().classes("text-sm font-bold text-green-600")
                self._update_active_label()

                # --- 1行目: ドロップダウン + Set as Active ---
                with ui.row().classes("w-full items-end gap-4 flex-wrap"):
                    self.scenario_select = ui.select(
                        label="Scenario File",
                        options=_list_scenario_files(),
                        value=self.initial_fname,
                        on_change=lambda e: self._on_scenario_changed(e.value),
                    ).classes("flex-grow min-w-52")

                    ui.button("▶ Set as Active", on_click=self._on_apply).props("color=primary")

                # --- 2行目: ファイル操作ボタン ---
                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button("✏ Rename", on_click=self._on_rename).props("color=secondary flat")
                    ui.button("🗑 Delete", on_click=self._on_delete).props("color=negative flat")
                    ui.button("📋 Duplicate", on_click=self._on_duplicate).props("color=secondary flat")

    def _update_active_label(self):
        if self.active_label:
            self.active_label.set_text(self.active_file[0])

    def _refresh_select(self):
        if self.scenario_select:
            self.scenario_select.options = _list_scenario_files()
            self.scenario_select.update()

    def _on_apply(self):
        fname = self.scenario_select.value
        if not fname:
            ui.notify("Please select a scenario.", type="warning")
            return
        path = str(SCENARIOS_DIR / fname)
        engine.switch_scenario(path)
        self.active_file[0] = fname
        settings.simulation.scenario_file = path
        settings.save_to_yaml()
        self._update_active_label()
        ui.notify(f"Set '{fname}' as active scenario.", type="positive")

    def _on_rename(self):
        fname = self.scenario_select.value
        if not fname:
            ui.notify("Please select a scenario.", type="warning")
            return
        stem = Path(fname).stem
        with ui.dialog() as dlg, ui.card().classes("p-6 min-w-80"):
            ui.label("Rename Scenario").classes("text-lg font-bold mb-4")
            inp = ui.input("New filename (without .csv)", value=stem).classes("w-full")
            with ui.row().classes("mt-4 gap-2 justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                def do_rename():
                    new_stem = inp.value.strip()
                    if not new_stem:
                        ui.notify("Please enter a filename.", type="warning")
                        return
                    new_name = new_stem if new_stem.endswith(".csv") else f"{new_stem}.csv"
                    if (SCENARIOS_DIR / new_name).exists():
                        ui.notify(f"'{new_name}' already exists.", type="negative")
                        return
                    (SCENARIOS_DIR / fname).rename(SCENARIOS_DIR / new_name)
                    if fname == self.active_file[0]:
                        self.active_file[0] = new_name
                        settings.simulation.scenario_file = str(SCENARIOS_DIR / new_name)
                        settings.save_to_yaml()
                        self._update_active_label()
                    ui.notify(f"Renamed '{fname}' → '{new_name}'.", type="positive")
                    self._refresh_select()
                    self.scenario_select.value = new_name
                    dlg.close()
                ui.button("Rename", on_click=do_rename).props("color=primary")
        dlg.open()

    def _on_delete(self):
        fname = self.scenario_select.value
        if not fname:
            ui.notify("Please select a scenario.", type="warning")
            return
        if fname == self.active_file[0]:
            ui.notify("Cannot delete the active scenario.", type="negative")
            return
        path = SCENARIOS_DIR / fname
        if path.exists():
            path.unlink()
            ui.notify(f"Deleted '{fname}'.", type="warning")
            self._refresh_select()
            if self.scenario_select.options:
                self.scenario_select.value = self.scenario_select.options[0]

    def _on_duplicate(self):
        fname = self.scenario_select.value
        if not fname:
            ui.notify("Please select a scenario.", type="warning")
            return
        stem = Path(fname).stem
        new_name = f"{stem}_copy.csv"
        counter = 1
        while (SCENARIOS_DIR / new_name).exists():
            new_name = f"{stem}_copy{counter}.csv"
            counter += 1
        shutil.copy(SCENARIOS_DIR / fname, SCENARIOS_DIR / new_name)
        ui.notify(f"Duplicated as '{new_name}'.", type="positive")
        self._refresh_select()
        self.scenario_select.value = new_name

    def _on_scenario_changed(self, fname: str):
        if not fname:
            return
        rows = _load_csv_data(fname)
        self.current_rows[0] = rows
        self._sync_table(rows)
        self._refresh_chart(rows)

    # ------------------------------------------------------------------
    # セクション 2: グラフ
    # ------------------------------------------------------------------
    def _render_chart(self):
        with ui.card().classes("w-full p-4"):
            ui.label("Chart").classes("text-xl font-bold mb-2")
            self.chart = ui.echart(_get_echart_option(self.current_rows[0])).classes("w-full h-64")

    def _refresh_chart(self, rows: list[dict[str, Any]]):
        if self.chart:
            self.chart.options.clear()
            self.chart.options.update(_get_echart_option(rows))
            self.chart.update()

    # ------------------------------------------------------------------
    # セクション 3: テーブル編集
    # ------------------------------------------------------------------
    def _render_data_editor(self):
        with ui.card().classes("w-full p-4"):
            ui.label("Data Editor").classes("text-xl font-bold mb-2")
            ui.label("Click a row to edit. Use buttons below to add or delete rows.").classes("text-xs text-gray-400 mb-2")

            columns = [
                {"name": "time",    "label": "Time (HH:MM)", "field": "time",    "align": "left",   "sortable": True},
                {"name": "load_w",  "label": "Load (W)",     "field": "load_w",  "align": "right",  "sortable": True},
                {"name": "solar_w", "label": "Solar (W)",    "field": "solar_w", "align": "right",  "sortable": True},
                {"name": "notes",   "label": "Notes",        "field": "notes",   "align": "left"},
            ]

            self.table = ui.table(
                columns=columns,
                rows=self.current_rows[0],
                row_key="_id",
                selection="single",
            ).classes("w-full").style("max-height: 320px; overflow-y: auto;")
            self.table.on("rowClick", self._on_row_click)

            with ui.row().classes("gap-2 mt-3 flex-wrap"):
                ui.button("+ Add Row", on_click=self._on_add_row).props("color=primary flat size=sm")
                ui.button("- Delete Row", on_click=self._on_delete_selected).props("color=negative flat size=sm")
                ui.button("💾 Save Scenario file", on_click=self._on_save).props("color=primary size=sm")
                ui.label("Hint: Click a row to open the edit dialog.").classes("text-xs text-gray-400 self-center")

    def _sync_table(self, rows: list[dict[str, Any]]):
        if self.table:
            self.table.rows.clear()
            self.table.rows.extend(rows)
            self.table.update()

    def _on_row_click(self, e):
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
        self._open_edit_dialog(row, is_new=False)

    def _on_add_row(self):
        new_id = max((r.get("_id", -1) for r in self.current_rows[0]), default=-1) + 1
        self._open_edit_dialog(
            {"_id": new_id, "time": "00:00", "load_w": 0.0, "solar_w": 0.0, "notes": ""},
            is_new=True,
        )

    def _on_delete_selected(self):
        selected = self.table.selected
        if not selected:
            ui.notify("Select a row to delete (click a row).", type="warning")
            return
        sel_ids = {s.get("_id") for s in selected}
        rows = [r for r in self.current_rows[0] if r.get("_id") not in sel_ids]
        self.current_rows[0] = rows
        self._sync_table(rows)
        self._refresh_chart(rows)
        self.table.selected.clear()

    def _on_save(self):
        fname = self.scenario_select.value
        if not fname:
            ui.notify("Please select a scenario.", type="warning")
            return
        rows = list(self.current_rows[0])
        rows.sort(key=lambda r: r["time"])
        _save_csv_data(fname, rows)
        self.current_rows[0] = rows
        self._sync_table(rows)
        self._refresh_chart(rows)
        ui.notify(f"Saved '{fname}'.", type="positive", position="top")
        if fname == self.active_file[0]:
            engine.switch_scenario(str(SCENARIOS_DIR / fname))

    def _open_edit_dialog(self, row: dict[str, Any], is_new: bool = False):
        row_id = row.get("_id")
        if not is_new:
            idx = next((i for i, r in enumerate(self.current_rows[0]) if r.get("_id") == row_id), None)
            if idx is None:
                return
        else:
            idx = None

        with ui.dialog() as dlg, ui.card().classes("p-6 min-w-80"):
            ui.label("Add Row" if is_new else "Edit Row").classes("text-lg font-bold mb-4")

            current_time = row["time"]
            time_opts = self.time_options if current_time in self.time_options else [current_time] + self.time_options
            inp_time = ui.select(
                label="Time", options=time_opts, value=current_time, with_input=True
            ).classes("w-full")

            inp_load  = ui.number("Load (W)",  value=row["load_w"],  format="%.0f", step=10)
            inp_solar = ui.number("Solar (W)", value=row["solar_w"], format="%.0f", step=10)
            inp_notes = ui.input("Notes",      value=row["notes"])

            with ui.row().classes("mt-4 gap-2 justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")

                def on_ok():
                    new_time = inp_time.value
                    existing_times = {r["time"] for r in self.current_rows[0]}

                    if is_new:
                        if new_time in existing_times:
                            ui.notify(f"Time '{new_time}' already exists.", type="negative")
                            return
                        new_id = max((r.get("_id", -1) for r in self.current_rows[0]), default=-1) + 1
                        new_row = {"_id": new_id, "time": new_time, "load_w": float(inp_load.value or 0), "solar_w": float(inp_solar.value or 0), "notes": inp_notes.value}
                        rows = list(self.current_rows[0]) + [new_row]
                    else:
                        other_times = {r["time"] for r in self.current_rows[0] if r.get("_id") != row_id}
                        if new_time in other_times:
                            ui.notify(f"Time '{new_time}' already exists.", type="negative")
                            return
                        rows = list(self.current_rows[0])
                        rows[idx] = {"_id": row_id, "time": new_time, "load_w": float(inp_load.value or 0), "solar_w": float(inp_solar.value or 0), "notes": inp_notes.value}

                    rows.sort(key=lambda r: r["time"])
                    self.current_rows[0] = rows
                    self._sync_table(rows)
                    self._refresh_chart(rows)
                    dlg.close()

                ui.button("OK", on_click=on_ok).props("color=primary")
        dlg.open()

# ---------------------------------------------------------------------------
# モジュール公開の render 関数
# ---------------------------------------------------------------------------
def render():
    controller = ScenarioController()
    controller.render()
