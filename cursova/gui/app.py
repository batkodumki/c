from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cursova.core import (
    AVAILABLE_SCALES,
    build_pairwise_matrix,
    compute_weights,
    evaluate_consistency,
)
from cursova.core.consistency import generate_recommendations
from cursova.core.scales import ScaleDefinition
from cursova.core.pcm import default_ratio


class ComparisonApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Метод попарних порівнянь")
        self.geometry("1080x720")

        self.alternatives: List[str] = []
        self.judgments: Dict[Tuple[str, str], Tuple[float, float, str, str]] = {}
        self.pairs: List[Tuple[str, str]] = []
        self.pair_index: int = 0
        self.scale_list = list(AVAILABLE_SCALES.values())

        self._build_layout()
        self._update_state()

    # --- побудова інтерфейсу ---
    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)

        self._build_alternative_panel(container)
        self._build_comparison_panel(container)
        self._build_results_panel(container)

    def _build_alternative_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Введення альтернатив")
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        ttk.Label(frame, text="Назва альтернативи:").pack(anchor=tk.W, pady=(8, 2))
        input_row = ttk.Frame(frame)
        input_row.pack(fill=tk.X, padx=4)

        self.alt_entry = ttk.Entry(input_row)
        self.alt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(input_row, text="Додати", command=self._add_alternative).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        ttk.Button(frame, text="Імпорт CSV", command=self._import_csv).pack(
            anchor=tk.W, padx=4, pady=(6, 6)
        )

        self.alt_listbox = tk.Listbox(frame, height=12)
        self.alt_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 4))

        ttk.Button(frame, text="Видалити", command=self._remove_selected).pack(
            anchor=tk.W, padx=4, pady=(0, 8)
        )

    def _build_comparison_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Попарні порівняння")
        frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        self.pair_label = ttk.Label(frame, text="Додайте щонайменше дві альтернативи")
        self.pair_label.pack(anchor=tk.W, pady=(8, 6))

        ttk.Label(frame, text="Обрана шкала:").pack(anchor=tk.W)
        self.scale_var = tk.StringVar()
        self.scale_combo = ttk.Combobox(
            frame,
            textvariable=self.scale_var,
            state="readonly",
            values=[scale.name for scale in self.scale_list],
        )
        self.scale_combo.pack(fill=tk.X, padx=4, pady=(0, 8))
        self.scale_combo.bind("<<ComboboxSelected>>", self._on_scale_change)

        ttk.Label(frame, text="Градація переваги:").pack(anchor=tk.W)
        self.option_var = tk.StringVar()
        self.option_combo = ttk.Combobox(frame, textvariable=self.option_var, state="readonly")
        self.option_combo.pack(fill=tk.X, padx=4, pady=(0, 12))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(4, 4))

        ttk.Button(buttons, text="Назад", command=self._go_back).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(buttons, text="Пропустити", command=self._skip_pair).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(buttons, text="Підтвердити", command=self._confirm_pair).pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress.pack(fill=tk.X, padx=4, pady=(12, 8))

    def _build_results_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Результати")
        frame.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)

        columns = ("rank", "alternative", "weight")
        self.result_table = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=12,
        )
        self.result_table.heading("rank", text="Місце")
        self.result_table.heading("alternative", text="Альтернатива")
        self.result_table.heading("weight", text="Вага")
        self.result_table.column("rank", width=60, anchor=tk.CENTER)
        self.result_table.column("alternative", anchor=tk.W)
        self.result_table.column("weight", width=120, anchor=tk.E)
        self.result_table.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 8))

        self.lambda_var = tk.StringVar(value="λ_max: —")
        self.ci_var = tk.StringVar(value="CI: —")
        self.cr_var = tk.StringVar(value="CR: —")

        ttk.Label(frame, textvariable=self.lambda_var).pack(anchor=tk.W, padx=4)
        ttk.Label(frame, textvariable=self.ci_var).pack(anchor=tk.W, padx=4)
        ttk.Label(frame, textvariable=self.cr_var).pack(anchor=tk.W, padx=4)

        ttk.Button(frame, text="Експорт", command=self._export_results).pack(
            anchor=tk.E, padx=4, pady=(12, 4)
        )

    # --- взаємодія з альтернативами ---
    def _add_alternative(self) -> None:
        name = self.alt_entry.get().strip()
        if not name:
            return
        if name in self.alternatives:
            messagebox.showinfo("Увага", "Альтернатива вже існує у списку")
            return
        self.alternatives.append(name)
        self.alt_entry.delete(0, tk.END)
        self._refresh_alt_list()
        self._prepare_pairs()

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть CSV з альтернативами",
            filetypes=(("CSV файли", "*.csv"), ("Усі файли", "*.*")),
        )
        if not path:
            return
        try:
            df = pd.read_csv(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Помилка", f"Не вдалося прочитати файл: {exc}")
            return
        column = df.columns[0]
        names = [str(val).strip() for val in df[column].dropna().tolist() if str(val).strip()]
        if not names:
            messagebox.showwarning("Попередження", "Файл не містить жодної альтернативи")
            return
        self.alternatives = names
        self._refresh_alt_list()
        self._prepare_pairs()

    def _remove_selected(self) -> None:
        selection = self.alt_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        removed = self.alt_listbox.get(index)
        self.alternatives = [alt for alt in self.alternatives if alt != removed]
        # Очистити пов'язані судження
        self.judgments = {
            pair: data for pair, data in self.judgments.items() if removed not in pair
        }
        self._refresh_alt_list()
        self._prepare_pairs()

    def _refresh_alt_list(self) -> None:
        self.alt_listbox.delete(0, tk.END)
        for alt in self.alternatives:
            self.alt_listbox.insert(tk.END, alt)

    # --- управління парами ---
    def _prepare_pairs(self) -> None:
        self.pairs = []
        for i, alt_i in enumerate(self.alternatives):
            for alt_j in self.alternatives[i + 1 :]:
                self.pairs.append((alt_i, alt_j))
        self.pair_index = 0
        self.progress.configure(maximum=max(len(self.pairs), 1))
        self.progress['value'] = 0
        self._update_state()

    def _current_pair(self) -> Optional[Tuple[str, str]]:
        if 0 <= self.pair_index < len(self.pairs):
            return self.pairs[self.pair_index]
        return None

    def _on_scale_change(self, event: Optional[tk.Event] = None) -> None:  # noqa: ARG002
        scale = self._selected_scale()
        if not scale:
            self.option_combo['values'] = []
            self.option_var.set("")
            return
        self.option_combo['values'] = [option.label for option in scale.options]
        self.option_var.set("")

    def _selected_scale(self) -> Optional[ScaleDefinition]:
        name = self.scale_var.get()
        for scale in self.scale_list:
            if scale.name == name:
                return scale
        return None

    def _record_judgment(self, pair: Tuple[str, str], cardinal: float, ratio: float, scale_key: str, choice_label: str) -> None:
        ai, aj = pair
        self.judgments[(ai, aj)] = (cardinal, ratio, scale_key, choice_label)

    def _go_back(self) -> None:
        if self.pair_index > 0:
            self.pair_index -= 1
            self._update_state()

    def _skip_pair(self) -> None:
        if self.pair_index < len(self.pairs) - 1:
            self.pair_index += 1
        else:
            self.pair_index = len(self.pairs)
        self._update_state()

    def _confirm_pair(self) -> None:
        pair = self._current_pair()
        if not pair:
            return
        scale = self._selected_scale()
        if not scale:
            messagebox.showwarning("Попередження", "Оберіть шкалу для оцінювання")
            return
        choice_label = self.option_var.get()
        if not choice_label:
            messagebox.showwarning("Попередження", "Оберіть градацію переваги")
            return
        cardinal = scale.to_cardinal(choice_label)
        ratio = default_ratio(cardinal)
        self._record_judgment(pair, cardinal, ratio, scale.key, choice_label)
        self.pair_index += 1
        self._update_state()

    def _update_state(self) -> None:
        pair = self._current_pair()
        total = len(self.pairs)
        processed = len(self.judgments)
        if pair:
            ai, aj = pair
            self.pair_label.config(text=f"Пара: {ai} ⇔ {aj}")
        elif total == 0:
            self.pair_label.config(text="Додайте щонайменше дві альтернативи")
        else:
            self.pair_label.config(text="Усі пари оцінено або пропущено")
            self._calculate_results()
        self.progress.configure(value=min(processed, total))

    # --- розрахунки ---
    def _calculate_results(self) -> None:
        if len(self.alternatives) < 2 or not self.judgments:
            self._clear_results()
            return
        matrix, log = build_pairwise_matrix(self.alternatives, self.judgments)
        weights = compute_weights(matrix)
        report = evaluate_consistency(matrix)
        recommendations = generate_recommendations(report, self.alternatives)
        self._update_results_table(weights)
        self._update_metrics(report)
        self._last_log = log
        self._last_weights = weights
        self._last_report = report
        self._last_recommendations = recommendations

    def _clear_results(self) -> None:
        for item in self.result_table.get_children():
            self.result_table.delete(item)
        self.lambda_var.set("λ_max: —")
        self.ci_var.set("CI: —")
        self.cr_var.set("CR: —")
        self._last_log = []
        self._last_weights = None
        self._last_report = None
        self._last_recommendations = []

    def _update_results_table(self, weights) -> None:
        for item in self.result_table.get_children():
            self.result_table.delete(item)
        ranking = sorted(zip(self.alternatives, weights), key=lambda x: x[1], reverse=True)
        for idx, (alt, weight) in enumerate(ranking, start=1):
            self.result_table.insert("", tk.END, values=(idx, alt, f"{weight:.4f}"))

    def _update_metrics(self, report) -> None:
        self.lambda_var.set(f"λ_max: {report.lambda_max:.3f}")
        self.ci_var.set(f"CI: {report.ci:.3f}")
        self.cr_var.set(f"CR: {report.cr:.3f} (поріг {report.threshold:.2f})")

    # --- експорт ---
    def _export_results(self) -> None:
        if not getattr(self, "_last_weights", None):
            messagebox.showinfo("Увага", "Немає результатів для експорту")
            return
        output_dir = Path("out")
        output_dir.mkdir(exist_ok=True)

        ranking = sorted(
            zip(self.alternatives, self._last_weights),
            key=lambda x: x[1],
            reverse=True,
        )
        df = pd.DataFrame(ranking, columns=["Альтернатива", "Вага"])
        df.to_csv(output_dir / "weights.csv", index=False)

        report_data = {
            "lambda_max": self._last_report.lambda_max,
            "consistency_index": self._last_report.ci,
            "consistency_ratio": self._last_report.cr,
            "threshold": self._last_report.threshold,
            "is_consistent": self._last_report.is_consistent(),
        }
        (output_dir / "consistency.json").write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        suggestions = [
            {"title": rec.title, "details": rec.details}
            for rec in getattr(self, "_last_recommendations", [])
        ]
        (output_dir / "suggestions.json").write_text(
            json.dumps(suggestions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        log_payload = [
            {
                "alternative_i": entry.alternative_i,
                "alternative_j": entry.alternative_j,
                "scale": entry.scale,
                "choice": entry.choice,
                "cardinal_value": entry.cardinal_value,
                "ratio_value": entry.ratio_value,
            }
            for entry in getattr(self, "_last_log", [])
        ]
        (output_dir / "scale_transformations.json").write_text(
            json.dumps(log_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        messagebox.showinfo("Готово", f"Файли збережено у {output_dir.resolve()}")


def run() -> None:
    app = ComparisonApp()
    app.mainloop()


if __name__ == "__main__":
    run()

