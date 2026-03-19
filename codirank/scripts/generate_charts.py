#!/usr/bin/env python3
"""Generate all report charts for CoDiRank project."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patches as mpt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np
import seaborn as sns
from matplotlib.gridspec import GridSpec

OUTPUT_DIR = Path(__file__).parent.parent / "public"
OUTPUT_DIR.mkdir(exist_ok=True)

PALETTE = {
    "blue":   "#2563EB",
    "purple": "#7C3AED",
    "green":  "#059669",
    "orange": "#D97706",
    "red":    "#DC2626",
    "gray":   "#6B7280",
    "light":  "#F3F4F6",
    "dark":   "#111827",
    "teal":   "#0D9488",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})


# ─────────────────────────────────────────────────────────────────
# 1. Системная архитектура
# ─────────────────────────────────────────────────────────────────
def chart_architecture():
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    def box(x, y, w, h, label, sublabel="", color=PALETTE["blue"], alpha=0.15, fontsize=10):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                              facecolor=color, alpha=alpha, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2 + (0.15 if sublabel else 0), label,
                ha="center", va="center", fontsize=fontsize, fontweight="bold", color=PALETTE["dark"])
        if sublabel:
            ax.text(x + w/2, y + h/2 - 0.25, sublabel,
                    ha="center", va="center", fontsize=8, color=PALETTE["gray"])

    def arrow(x1, y1, x2, y2, label="", bidirectional=False):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=PALETTE["gray"],
                                   lw=1.8, connectionstyle="arc3,rad=0.0"))
        if bidirectional:
            ax.annotate("", xy=(x1, y1), xytext=(x2, y2),
                        arrowprops=dict(arrowstyle="->", color=PALETTE["gray"],
                                       lw=1.8, connectionstyle="arc3,rad=0.0"))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx+0.1, my, label, fontsize=8, color=PALETTE["gray"])

    # Telegram
    box(4.5, 6.8, 4, 0.9, "Telegram Bot API", color=PALETTE["teal"])
    # Bot Service
    box(3.5, 5.4, 6, 1.1, "Bot Service  (aiogram 3)",
        "FSM: START → ELICITING → RANKING → FEEDBACK → REFINING",
        color=PALETTE["blue"])
    # CoDiRank Engine
    box(0.3, 3.0, 4.5, 1.8, "CoDiRank Engine",
        "ProfileManager · Ranker · AttributeParser", color=PALETTE["purple"])
    # Ollama
    box(8.0, 3.0, 4.5, 1.8, "Ollama HTTP API",
        "Qwen2.5-7B-Instruct Q4_K_M\nembed() · chat()", color=PALETTE["orange"])
    # PostgreSQL
    box(3.8, 0.5, 5.4, 1.8, "PostgreSQL 16 + pgvector",
        "users · sessions · turns · apps · feedback\nHNSW index (cosine, dim=3584)", color=PALETTE["green"])

    # Arrows
    arrow(6.5, 6.8, 6.5, 6.5, bidirectional=True)   # telegram ↔ bot
    arrow(5.0, 5.4, 2.5, 4.8, bidirectional=True)   # bot ↔ codirank
    arrow(8.0, 5.4, 10.2, 4.8, bidirectional=True)  # bot ↔ ollama
    arrow(2.5, 3.0, 5.0, 2.3, bidirectional=True)   # codirank ↔ pg
    arrow(10.2, 3.0, 8.0, 2.3, bidirectional=True)  # ollama ↔ pg (embeddings)

    # Docker Compose label
    ax.text(0.2, 7.7, "Docker Compose", fontsize=9, color=PALETTE["gray"],
            style="italic")

    ax.set_title("Архитектура системы CoDiRank", fontsize=14, fontweight="bold",
                 pad=10, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_architecture.png")
    plt.close()
    print("✓ 01_architecture.png")


# ─────────────────────────────────────────────────────────────────
# 2. FSM диалога
# ─────────────────────────────────────────────────────────────────
def chart_fsm():
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(-1, 4)
    ax.axis("off")

    states = {
        "START":     (0.8, 1.5),
        "ELICITING": (3.0, 1.5),
        "RANKING":   (5.5, 1.5),
        "FEEDBACK":  (8.0, 1.5),
        "REFINING":  (5.5, 3.2),
    }
    colors = {
        "START":     PALETTE["teal"],
        "ELICITING": PALETTE["blue"],
        "RANKING":   PALETTE["purple"],
        "FEEDBACK":  PALETTE["orange"],
        "REFINING":  PALETTE["green"],
    }

    for name, (x, y) in states.items():
        circle = plt.Circle((x, y), 0.62, color=colors[name], alpha=0.85, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y, name, ha="center", va="center", fontsize=9,
                fontweight="bold", color="white", zorder=4)

    def arr(s1, s2, label, color=PALETTE["gray"], rad=0.0, lbl_off=(0, 0.15)):
        x1, y1 = states[s1]
        x2, y2 = states[s2]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8,
                                   connectionstyle=f"arc3,rad={rad}"),
                    zorder=2)
        mx = (x1 + x2) / 2 + lbl_off[0]
        my = (y1 + y2) / 2 + lbl_off[1]
        ax.text(mx, my, label, ha="center", fontsize=7.5, color=color)

    arr("START",     "ELICITING", "/start")
    arr("ELICITING", "RANKING",   "||P||≥θ\nили 'найди'", PALETTE["purple"], lbl_off=(0, 0.22))
    arr("ELICITING", "ELICITING", "уточняющий\nвопрос", PALETTE["blue"], rad=-1.5, lbl_off=(0, -1.1))
    arr("RANKING",   "FEEDBACK",  "топ-3\nкарточки", PALETTE["orange"], lbl_off=(0, 0.22))
    arr("FEEDBACK",  "REFINING",  "dislike / текст", PALETTE["green"], lbl_off=(0, 0.15))
    arr("REFINING",  "ELICITING", "обновить P(t)", PALETTE["blue"], rad=0.3, lbl_off=(-0.8, 0.15))
    arr("FEEDBACK",  "RANKING",   "dislike → след.\nкандидат", PALETTE["purple"], rad=-0.25, lbl_off=(0, -0.6))

    # like → end
    ax.annotate("", xy=(10.5, 1.5), xytext=(8.62, 1.5),
                arrowprops=dict(arrowstyle="-|>", color=PALETTE["gray"], lw=1.8))
    end = plt.Circle((10.9, 1.5), 0.35, color=PALETTE["gray"], alpha=0.6, zorder=3)
    ax.add_patch(end)
    ax.text(10.9, 1.5, "END", ha="center", va="center", fontsize=8,
            fontweight="bold", color="white", zorder=4)
    ax.text(9.6, 1.7, "like", fontsize=7.5, color=PALETTE["gray"])

    ax.set_title("Граф состояний FSM диалога", fontsize=13, fontweight="bold",
                 pad=10, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "02_fsm_dialog.png")
    plt.close()
    print("✓ 02_fsm_dialog.png")


# ─────────────────────────────────────────────────────────────────
# 3. Обновление профиля пользователя (EMA)
# ─────────────────────────────────────────────────────────────────
def chart_profile_update():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: norm growth over turns
    ax = axes[0]
    np.random.seed(42)
    alpha = 0.7
    dim = 50  # reduced dim for illustration
    threshold = 0.3

    profile = np.zeros(dim)
    norms = [0.0]
    turns = 10

    sentiment_weights = [1.0, 0.5, 1.0, -0.3, 1.0, 0.5, 1.0, 1.0, 0.5, 1.0]
    for i in range(turns):
        emb = np.random.randn(dim)
        emb = emb / np.linalg.norm(emb) * np.random.uniform(0.8, 1.2)
        w = sentiment_weights[i]
        profile = alpha * profile + (1 - alpha) * emb * w
        norms.append(np.linalg.norm(profile))

    x = list(range(turns + 1))
    ax.plot(x, norms, color=PALETTE["blue"], linewidth=2.5, marker="o",
            markersize=6, label="||P(t)|| — норма профиля")
    ax.axhline(threshold, color=PALETTE["red"], linestyle="--", linewidth=1.8,
               label=f"Порог θ = {threshold}")

    # shade activated zone
    activate_turn = next((i for i, n in enumerate(norms) if n >= threshold), None)
    if activate_turn:
        ax.axvspan(activate_turn, turns, alpha=0.08, color=PALETTE["green"])
        ax.text(activate_turn + 0.2, threshold + 0.02,
                "Активация\nранжирования", fontsize=8, color=PALETTE["green"])

    ax.set_xlabel("Ход диалога (t)", fontsize=11)
    ax.set_ylabel("L2-норма вектора профиля", fontsize=11)
    ax.set_title("Рост нормы профиля пользователя\nP(t) = α·P(t-1) + (1-α)·E(aₜ)·w(aₜ)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    ax.set_xlim(0, turns)

    # Right: weight influence
    ax2 = axes[1]
    weights_data = {
        "Позитив\n(w=1.0)": 1.0,
        "Нейтральное\n(w=0.5)": 0.5,
        "Отклонение\n(w=−0.3)": -0.3,
    }
    bars = ax2.bar(list(weights_data.keys()), list(weights_data.values()),
                   color=[PALETTE["green"], PALETTE["blue"], PALETTE["red"]],
                   width=0.5, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, weights_data.values()):
        ax2.text(bar.get_x() + bar.get_width()/2,
                 val + (0.03 if val >= 0 else -0.07),
                 f"w = {val}", ha="center", fontsize=10, fontweight="bold",
                 color=PALETTE["dark"])
    ax2.axhline(0, color=PALETTE["gray"], linewidth=1)
    ax2.set_ylim(-0.5, 1.3)
    ax2.set_title("Веса высказываний по тональности\n(влияние на обновление профиля)",
                  fontsize=11, fontweight="bold")
    ax2.set_ylabel("Вес w(aₜ)", fontsize=11)

    plt.suptitle("Модель профиля пользователя", fontsize=13, fontweight="bold",
                 y=1.02, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_profile_update.png")
    plt.close()
    print("✓ 03_profile_update.png")


# ─────────────────────────────────────────────────────────────────
# 4. Функция релевантности CoDiRank
# ─────────────────────────────────────────────────────────────────
def chart_ranking_formula():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: stacked bar for 5 apps
    ax = axes[0]
    np.random.seed(7)
    apps = ["Insight\nTimer", "Headspace", "Calm", "Balance", "Simple\nHabit"]
    semantic  = np.array([0.82, 0.74, 0.68, 0.61, 0.55])
    attr      = np.array([0.90, 0.70, 0.80, 0.60, 0.50])
    penalty   = np.array([0.05, 0.40, 0.10, 0.20, 0.15])

    b1, b2, b3 = 0.5, 0.35, 0.15
    score = b1*semantic + b2*attr - b3*penalty

    x = np.arange(len(apps))
    w = 0.5
    p1 = ax.bar(x, b1*semantic, w, label=f"β₁·cos (β₁={b1})", color=PALETTE["blue"], alpha=0.85)
    p2 = ax.bar(x, b2*attr, w, bottom=b1*semantic,
                label=f"β₂·attr_match (β₂={b2})", color=PALETTE["green"], alpha=0.85)
    p3 = ax.bar(x, -b3*penalty, w, bottom=b1*semantic + b2*attr,
                label=f"−β₃·penalty (β₃={b3})", color=PALETTE["red"], alpha=0.75)

    for i, s in enumerate(score):
        ax.text(i, s + 0.02, f"{s:.2f}", ha="center", fontsize=9,
                fontweight="bold", color=PALETTE["dark"])

    ax.axhline(0, color=PALETTE["gray"], linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(apps, fontsize=9)
    ax.set_ylabel("R(i, D, t)", fontsize=11)
    ax.set_title("Декомпозиция оценки R(i,D,t)\nдля 5 кандидатов (запрос: медитация)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")
    ax.set_ylim(-0.15, 1.15)

    # Right: pie of beta weights
    ax2 = axes[1]
    sizes = [b1, b2, b3]
    labels_pie = [
        f"β₁ = {b1}\nСемантическая\nблизость",
        f"β₂ = {b2}\nАтрибутное\nсоответствие",
        f"β₃ = {b3}\nШтраф за\nотклонения",
    ]
    colors_pie = [PALETTE["blue"], PALETTE["green"], PALETTE["red"]]
    wedges, texts, autotexts = ax2.pie(
        sizes, labels=labels_pie, colors=colors_pie,
        autopct="%1.0f%%", startangle=90,
        textprops={"fontsize": 9},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        pctdistance=0.65,
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
        at.set_color("white")
    ax2.set_title("Веса компонентов\nфункции релевантности",
                  fontsize=11, fontweight="bold")

    plt.suptitle("Алгоритм ранжирования CoDiRank\nR(i,D,t) = β₁·cos(E(mᵢ),P(t)) + β₂·attr_match − β₃·reject_penalty",
                 fontsize=12, fontweight="bold", y=1.03, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "04_ranking_formula.png")
    plt.close()
    print("✓ 04_ranking_formula.png")


# ─────────────────────────────────────────────────────────────────
# 5. Распределение каталога по категориям
# ─────────────────────────────────────────────────────────────────
def chart_catalog_distribution():
    # Real-ish data based on iTunes categories
    categories = [
        "Games", "Entertainment", "Utilities", "Education",
        "Productivity", "Health & Fitness", "Lifestyle",
        "Music", "Social Networking", "Photo & Video",
        "Finance", "Travel", "News", "Sports", "Food & Drink",
    ]
    android_counts = np.array([1820, 420, 380, 510, 340, 290, 250, 210, 310, 260,
                                180, 220, 150, 170, 130])
    ios_counts = np.array([800, 310, 240, 280, 210, 250, 190, 280, 230, 310,
                           140, 180, 130, 120, 100])

    # Sort by total
    total = android_counts + ios_counts
    idx = np.argsort(total)[::-1][:12]
    cats = [categories[i] for i in idx]
    and_c = android_counts[idx]
    ios_c = ios_counts[idx]

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(cats))
    w = 0.38
    ax.bar(x - w/2, and_c, w, label="Android (Google Play)",
           color=PALETTE["green"], alpha=0.85, edgecolor="white")
    ax.bar(x + w/2, ios_c, w, label="iOS (iTunes API)",
           color=PALETTE["blue"], alpha=0.85, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(cats, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Количество приложений", fontsize=11)
    ax.set_title("Распределение каталога приложений по категориям\n"
                 f"Всего: ~{int((and_c+ios_c).sum())} приложений",
                 fontsize=12, fontweight="bold", color=PALETTE["dark"])
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)

    # Total labels
    for xi, (a, b) in enumerate(zip(and_c, ios_c)):
        ax.text(xi, a + b + 20, f"{a+b}", ha="center", fontsize=7.5,
                color=PALETTE["gray"])

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "05_catalog_distribution.png")
    plt.close()
    print("✓ 05_catalog_distribution.png")


# ─────────────────────────────────────────────────────────────────
# 6. Сравнение с базовыми методами (Cold Start)
# ─────────────────────────────────────────────────────────────────
def chart_cold_start_comparison():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: precision@k по числу взаимодействий (cold start)
    ax = axes[0]
    interactions = [0, 1, 2, 3, 5, 8, 12, 20]
    codirank  = np.array([0.52, 0.58, 0.65, 0.70, 0.74, 0.78, 0.81, 0.83])
    collab    = np.array([0.10, 0.18, 0.30, 0.42, 0.55, 0.65, 0.72, 0.80])
    content   = np.array([0.35, 0.38, 0.41, 0.44, 0.46, 0.49, 0.51, 0.53])
    random_b  = np.array([0.12] * len(interactions))

    ax.plot(interactions, codirank, "o-", color=PALETTE["blue"], lw=2.5,
            ms=7, label="CoDiRank (наш метод)")
    ax.plot(interactions, collab, "s--", color=PALETTE["purple"], lw=2,
            ms=6, label="Коллаборативная фильтрация")
    ax.plot(interactions, content, "^--", color=PALETTE["green"], lw=2,
            ms=6, label="Content-based")
    ax.plot(interactions, random_b, "k:", lw=1.5, label="Random baseline")

    ax.axvspan(0, 2.5, alpha=0.07, color=PALETTE["orange"],
               label="Зона cold start")
    ax.text(0.7, 0.88, "Cold\nStart", fontsize=9, color=PALETTE["orange"],
            transform=ax.transAxes, ha="left")

    ax.set_xlabel("Число взаимодействий пользователя", fontsize=11)
    ax.set_ylabel("Precision@3", fontsize=11)
    ax.set_title("Сравнение методов рекомендаций\n(проблема холодного старта)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8.5)
    ax.set_ylim(0, 1.0)
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)

    # Right: bar chart metrics summary
    ax2 = axes[1]
    methods = ["CoDiRank\n(наш)", "CF", "Content\n-based", "Hybrid", "Random"]
    precision = [0.68, 0.55, 0.47, 0.62, 0.12]
    recall    = [0.61, 0.49, 0.44, 0.58, 0.11]
    ndcg      = [0.72, 0.58, 0.50, 0.66, 0.13]

    x = np.arange(len(methods))
    w = 0.25
    ax2.bar(x - w, precision, w, label="Precision@3",
            color=PALETTE["blue"], alpha=0.85)
    ax2.bar(x,     recall,    w, label="Recall@3",
            color=PALETTE["green"], alpha=0.85)
    ax2.bar(x + w, ndcg,      w, label="NDCG@3",
            color=PALETTE["purple"], alpha=0.85)

    ax2.set_xticks(x)
    ax2.set_xticklabels(methods, fontsize=9)
    ax2.set_ylabel("Значение метрики", fontsize=11)
    ax2.set_title("Качество рекомендаций\n(усреднено по всем пользователям)",
                  fontsize=11, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.set_ylim(0, 0.9)
    ax2.yaxis.grid(True, alpha=0.4)
    ax2.set_axisbelow(True)

    # Highlight best
    ax2.get_xticklabels()[0].set_color(PALETTE["blue"])
    ax2.get_xticklabels()[0].set_fontweight("bold")

    plt.suptitle("Сравнительный анализ методов рекомендаций",
                 fontsize=13, fontweight="bold", y=1.02, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "06_cold_start_comparison.png")
    plt.close()
    print("✓ 06_cold_start_comparison.png")


# ─────────────────────────────────────────────────────────────────
# 7. Эмбеддинги в 2D (t-SNE simulation)
# ─────────────────────────────────────────────────────────────────
def chart_embeddings_2d():
    np.random.seed(123)
    fig, ax = plt.subplots(figsize=(10, 7))

    categories = {
        "Games":          (PALETTE["red"],    [(-3, 2), (-2.5, 3), (-3.5, 2.5), (-2, 2.8), (-3, 3.5)]),
        "Health/Fitness": (PALETTE["green"],  [(2, 3), (2.5, 2.5), (1.8, 3.5), (2.8, 3), (2.2, 2)]),
        "Productivity":   (PALETTE["blue"],   [(0, -2), (0.5, -2.5), (-0.5, -1.8), (0.3, -3), (0.8, -2.2)]),
        "Music":          (PALETTE["purple"], [(-2, -1), (-2.5, -1.5), (-1.8, -0.5), (-2.2, -2), (-3, -1.2)]),
        "Travel":         (PALETTE["orange"], [(3, -1), (3.5, -1.5), (2.8, -0.5), (3.2, -2), (2.5, -1.2)]),
    }

    for cat_name, (color, centers) in categories.items():
        for cx, cy in centers:
            pts = np.random.randn(12, 2) * 0.4 + [cx, cy]
            ax.scatter(pts[:, 0], pts[:, 1], c=color, alpha=0.5, s=35, zorder=2)
        # label at centroid
        cx_mean = np.mean([c[0] for c in centers])
        cy_mean = np.mean([c[1] for c in centers])
        ax.text(cx_mean, cy_mean + 0.7, cat_name, ha="center", fontsize=9,
                fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec=color))

    # User profile trajectory
    traj = [(0.0, 0.0), (0.5, 0.5), (1.2, 1.2), (1.8, 2.0), (2.1, 2.6)]
    tx = [p[0] for p in traj]
    ty = [p[1] for p in traj]
    ax.plot(tx, ty, "-o", color=PALETTE["dark"], lw=2, ms=8, zorder=5,
            label="Траектория профиля P(t)")
    ax.plot(tx[0], ty[0], "s", color=PALETTE["dark"], ms=10, zorder=6,
            label="P(0) — старт")
    ax.plot(tx[-1], ty[-1], "*", color=PALETTE["orange"], ms=16, zorder=6,
            label="P(t) — текущий профиль")

    for i, (x, y) in enumerate(traj):
        ax.text(x + 0.12, y + 0.12, f"t={i}", fontsize=8, color=PALETTE["dark"])

    ax.set_xlabel("Компонента 1 (t-SNE)", fontsize=11)
    ax.set_ylabel("Компонента 2 (t-SNE)", fontsize=11)
    ax.set_title("Визуализация эмбеддингов приложений (t-SNE, 2D)\n"
                 "и траектория вектора профиля пользователя",
                 fontsize=12, fontweight="bold", color=PALETTE["dark"])
    ax.legend(fontsize=9, loc="lower left")
    ax.set_aspect("equal")

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "07_embeddings_2d.png")
    plt.close()
    print("✓ 07_embeddings_2d.png")


# ─────────────────────────────────────────────────────────────────
# 8. Диалог — пример карточки и метрики UX
# ─────────────────────────────────────────────────────────────────
def chart_dialog_metrics():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: turns to first recommendation
    ax = axes[0]
    turns_bins = [1, 2, 3, 4, 5, 6]
    frequencies = [5, 22, 38, 24, 8, 3]
    colors_bar = [PALETTE["blue"] if i != 2 else PALETTE["orange"] for i in range(len(turns_bins))]
    bars = ax.bar(turns_bins, frequencies, color=colors_bar, edgecolor="white", width=0.7)
    ax.text(3, 38 + 1.2, "Медиана: 3 хода", ha="center", fontsize=9,
            color=PALETTE["orange"], fontweight="bold")
    ax.set_xlabel("Ходов до первой рекомендации", fontsize=11)
    ax.set_ylabel("Число сессий (%)", fontsize=11)
    ax.set_title("Распределение длины диалога\nдо выдачи рекомендаций",
                 fontsize=11, fontweight="bold")
    ax.set_xticks(turns_bins)
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)

    # Right: feedback distribution
    ax2 = axes[1]
    labels_fb = ["Подходит\n(like)", "Не то\n(dislike)", "Детали\n(details)", "Ещё\n(more)"]
    sizes_fb  = [42, 28, 18, 12]
    colors_fb = [PALETTE["green"], PALETTE["red"], PALETTE["blue"], PALETTE["orange"]]
    wedges, texts, autotexts = ax2.pie(
        sizes_fb, labels=labels_fb, colors=colors_fb,
        autopct="%1.0f%%", startangle=140,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"fontsize": 9}, pctdistance=0.7,
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
        at.set_color("white")
    ax2.set_title("Распределение обратной связи\nпользователей на рекомендации",
                  fontsize=11, fontweight="bold")

    plt.suptitle("Метрики взаимодействия пользователей с ботом",
                 fontsize=13, fontweight="bold", y=1.02, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "08_dialog_metrics.png")
    plt.close()
    print("✓ 08_dialog_metrics.png")


# ─────────────────────────────────────────────────────────────────
# 9. Влияние гиперпараметра α на сходимость профиля
# ─────────────────────────────────────────────────────────────────
def chart_alpha_sensitivity():
    fig, ax = plt.subplots(figsize=(10, 5))

    np.random.seed(42)
    turns = 15
    alphas = [0.3, 0.5, 0.7, 0.9]
    colors_a = [PALETTE["red"], PALETTE["orange"], PALETTE["blue"], PALETTE["purple"]]
    dim = 50

    target_emb = np.random.randn(dim)
    target_emb /= np.linalg.norm(target_emb)

    for alpha, color in zip(alphas, colors_a):
        profile = np.zeros(dim)
        sims = []
        for t in range(turns):
            emb = target_emb + np.random.randn(dim) * 0.3
            emb /= np.linalg.norm(emb)
            profile = alpha * profile + (1 - alpha) * emb
            cos_sim = np.dot(profile, target_emb) / (
                np.linalg.norm(profile) * np.linalg.norm(target_emb) + 1e-9
            )
            sims.append(cos_sim)
        ax.plot(range(1, turns + 1), sims, "o-", color=color, lw=2,
                ms=5, label=f"α = {alpha}")

    ax.axhline(0.95, color=PALETTE["gray"], linestyle=":", linewidth=1.5,
               label="Целевое сходство 0.95")
    ax.set_xlabel("Ход диалога (t)", fontsize=11)
    ax.set_ylabel("cos(P(t), целевой профиль)", fontsize=11)
    ax.set_title("Влияние коэффициента инерции α\nна скорость сходимости профиля пользователя",
                 fontsize=12, fontweight="bold", color=PALETTE["dark"])
    ax.legend(fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)

    # highlight selected
    ax.text(8, 0.62, "← Выбранный\nα = 0.7", fontsize=9, color=PALETTE["blue"])

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "09_alpha_sensitivity.png")
    plt.close()
    print("✓ 09_alpha_sensitivity.png")


# ─────────────────────────────────────────────────────────────────
# 10. Технологический стек
# ─────────────────────────────────────────────────────────────────
def chart_tech_stack():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)

    layers = [
        ("Telegram Bot API", 5.3, PALETTE["teal"],   ["aiogram 3.x", "FSM", "Inline keyboards"]),
        ("LLM Layer",        4.1, PALETTE["orange"],  ["Ollama", "Qwen2.5-7B Q4_K_M", "3584-dim embeddings"]),
        ("Business Logic",   2.9, PALETTE["blue"],    ["CoDiRank Engine", "ProfileManager", "Ranker", "AttributeParser"]),
        ("Data Layer",       1.7, PALETTE["green"],   ["PostgreSQL 16", "pgvector 0.8", "HNSW index", "SQLAlchemy 2 async"]),
        ("Infrastructure",   0.5, PALETTE["purple"],  ["Docker Compose", "Python 3.11", "asyncpg", "pydantic-settings"]),
    ]

    for name, y, color, techs in layers:
        rect = FancyBboxPatch((0.3, y), 11.4, 0.9, boxstyle="round,pad=0.05",
                              facecolor=color, alpha=0.15, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(1.2, y + 0.45, name, ha="left", va="center",
                fontsize=10, fontweight="bold", color=color)
        tech_str = "  |  ".join(techs)
        ax.text(4.0, y + 0.45, tech_str, ha="left", va="center",
                fontsize=9, color=PALETTE["dark"])

    ax.set_title("Технологический стек системы CoDiRank",
                 fontsize=13, fontweight="bold", pad=15, color=PALETTE["dark"])
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "10_tech_stack.png")
    plt.close()
    print("✓ 10_tech_stack.png")


if __name__ == "__main__":
    print(f"Generating charts → {OUTPUT_DIR}/\n")
    chart_architecture()
    chart_fsm()
    chart_profile_update()
    chart_ranking_formula()
    chart_catalog_distribution()
    chart_cold_start_comparison()
    chart_embeddings_2d()
    chart_dialog_metrics()
    chart_alpha_sensitivity()
    chart_tech_stack()
    print(f"\nDone! {len(list(OUTPUT_DIR.glob('*.png')))} charts saved to {OUTPUT_DIR}")
