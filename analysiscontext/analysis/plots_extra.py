"""Round 2 plots (analysis/plots/):
  extra_ff_heatmap.png        within-person Spearman feature x feature (old + new, lag1), ordered by group
  extra_target_heatmap.png    participants x features, rho with day score, q<0.10 marked (INFORMATION ONLY)
  extra_persona_<pid>.png     persona box/strip plots by bad/neutral/good
  extra_coverage.png          participants x new features, % valid survey days
Needs eda_extra.py outputs (cache/extra_ff_pooled.csv, extra_corr_person.csv, extra_coverage.csv).
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from HackYeah2026.analysiscontext.analysis.common import CACHE
from HackYeah2026.analysiscontext.analysis.eda_extra import KEEP, load

PLOTS = CACHE.parent / "plots"
PLOTS.mkdir(exist_ok=True)
INK, MUTED, GRID = "#2b2b2b", "#6b6b66", "#d9d8d4"
BLUE, RED, GRAY = "#2a78d6", "#e34948", "#f0efec"
DIV = LinearSegmentedColormap.from_list("div", ["#184f95", BLUE, "#9ec5f4", GRAY, "#f4a3a2", RED, "#9c1f1e"])
SEQ = LinearSegmentedColormap.from_list("seq", ["#f7f6f3", "#cde2fb", "#6da7ec", "#256abf", "#0d366b"])
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "figure.facecolor": "white", "axes.facecolor": "white"})

# group order for the feature-feature heatmap (old features marked with *)
GROUPS = [
    ("A ilość snu", ["sleep_h*", "time_in_bed_h*", "ss_duration", "ss_overall", "light_min", "deep_min", "ss_deep",
                     "rem_min", "wake_count"]),
    ("B pora", ["bedtime_h*"]),
    ("C ciągłość snu", ["wake_pct", "sleep_eff*", "wake_min", "ss_restless", "wake_long_n", "wake_per_h",
                        "min_after_wake"]),
    ("G fazy", ["rem_pct", "ss_composition", "deep_pct"]),
    ("I tętno nocne", ["hr_sleep_mean", "hr_sleep_p5", "ss_revitalization", "rhr_night*", "hr_day_p10"]),
    ("D objętość ruchu", ["steps*", "z_fatburn", "hr_day_mean", "hr_dip", "sedentary*"]),
    ("E wysiłek", ["mvpa*", "very*", "z_cardio_peak", "z_cardio", "z_peak", "ex_cp_min", "ex_user_min",
                   "srpe_load*", "ex_min_nonwalk*", "ex_avg_hr"]),
    ("F lekka", ["lightly*"]),
]
FINAL = ["sleep_h", "bedtime_h", "wake_pct", "rem_pct", "hr_sleep_mean", "steps", "mvpa", "srpe_load", "lightly",
         "z_cardio_peak"]
NEW_IN = ["wake_pct", "rem_pct", "hr_sleep_mean", "z_cardio_peak"]
LAG1_ONLY = ["wake_pct", "rem_pct", "hr_sleep_mean"]
FINAL_VARS = [f"{f}_{v}" for f in FINAL for v in (["lag1"] if f in LAG1_ONLY else ["lag1", "avg3"])]


def group_seps(groups):
    order, seps, mids, names = [], [], [], []
    for name, fs in groups:
        mids.append(len(order) + (len(fs) - 1) / 2)
        order += fs
        seps.append(len(order))
        names.append(name)
    return order, seps[:-1], mids, names


def ff_heatmap():
    P = pd.read_csv(CACHE / "extra_ff_pooled.csv", index_col=0)
    order, seps, mids, names = group_seps(GROUPS)
    keys = [f.rstrip("*") for f in order]
    M = P.loc[keys, keys].to_numpy()
    fig, ax = plt.subplots(figsize=(13, 11.5))
    im = ax.imshow(M, cmap=DIV, vmin=-1, vmax=1)
    n = len(keys)
    for i in range(n):
        for j in range(n):
            v = M[i, j]
            if i != j and not np.isnan(v) and abs(v) >= 0.5:
                ax.text(j, i, f"{v:.1f}".replace("0.", ".").replace("-.", "−."), ha="center", va="center",
                        fontsize=6, color="white" if abs(v) > 0.75 else INK)
    for s in seps:
        ax.axhline(s - 0.5, color=INK, lw=1)
        ax.axvline(s - 0.5, color=INK, lw=1)
    labels = [f + ("  [IN]" if f in NEW_IN else "") for f in order]
    ax.set_xticks(range(n), labels, rotation=90)
    ax.set_yticks(range(n), labels)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        if "[IN]" in t.get_text():
            t.set_fontweight("bold")
    ax2 = ax.secondary_xaxis("top")
    ax2.set_xticks(mids, names, rotation=30, ha="left", fontsize=8)
    ax2.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    cb.set_label("ρ Spearmana w obrębie osoby (z-score per osoba, dane łączne)")
    fig.suptitle("Cecha × cecha (lag1, 12 osób). * = cecha z rundy 1, [IN] = nowa cecha przyjęta. "
                 "Liczby tylko dla |ρ| ≥ 0,5", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(PLOTS / "extra_ff_heatmap.png", dpi=130)
    plt.close(fig)


def target_heatmap():
    R = pd.read_csv(CACHE / "extra_corr_person.csv")
    R = R[R.target == "comp"]
    order, seps, mids, names = group_seps(GROUPS)
    keys = [f.rstrip("*") + "_lag1" for f in order]
    piv = R.pivot_table(index="pid", columns="feature", values="rho").reindex(index=KEEP, columns=keys)
    q = R.pivot_table(index="pid", columns="feature", values="q_bh").reindex(index=KEEP, columns=keys)
    fig, ax = plt.subplots(figsize=(14, 5.2))
    im = ax.imshow(piv.to_numpy(), cmap=DIV, vmin=-0.5, vmax=0.5, aspect="auto")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            if q.iloc[i, j] < 0.10:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec=INK, lw=1.3))
                ax.text(j, i, f"{piv.iloc[i, j]:+.2f}".replace("0.", "."), ha="center", va="center", fontsize=6,
                        color=INK)
    for s in seps:
        ax.axvline(s - 0.5, color=INK, lw=1)
    ax.set_xticks(range(len(keys)), [f + ("  [IN]" if f.rstrip("*") in NEW_IN else "") for f in order],
                  rotation=90)
    ax.set_yticks(range(len(KEEP)), [p.upper() for p in KEEP])
    ax2 = ax.secondary_xaxis("top")
    ax2.set_xticks(mids, names, rotation=30, ha="left", fontsize=8)
    ax2.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01)
    cb.set_label("ρ z wynikiem dnia (M+F+S)")
    ax.set_title("TYLKO INFORMACYJNIE: cecha (lag1) → wynik dnia, per osoba. Ramka i liczba = q_BH < 0,10 "
                 "(rodzina stare+nowe, ok. 79 testów na osobę)", loc="left", fontsize=10, color=INK, pad=55)
    fig.tight_layout()
    fig.savefig(PLOTS / "extra_target_heatmap.png", dpi=130)
    plt.close(fig)


def persona_plots(d):
    R = pd.read_csv(CACHE / "extra_corr_person.csv")
    R = R[(R.target == "comp")]
    R["base"] = R.feature.str.rsplit("_", n=1).str[0]
    cols = {"bad": RED, "neutral": "#8a8a85", "good": BLUE}
    for pid, title in [("p06", "P06 „Sen”"), ("p01", "P01 „Trening”"), ("p16", "P16 „Nocny marek”"),
                       ("p10", "P10 rezerwa „Sen + lekka aktywność”")]:
        r = R[(R.pid == pid) & R.feature.isin(FINAL_VARS)].assign(a=lambda x: x.rho.abs()).sort_values("a", ascending=False)
        top = list(r.feature.head(3))
        best_new = r[r.base.isin(NEW_IN) & ~r.feature.isin(top)].feature.head(1).tolist()
        feats = top + best_new
        g = d[d.pid == pid]
        fig, axes = plt.subplots(1, len(feats), figsize=(3.1 * len(feats), 3.4))
        for ax, f in zip(axes, feats):
            data = [g.loc[g.label == k, f].dropna().to_numpy() for k in cols]
            bp = ax.boxplot(data, widths=0.5, showfliers=False, patch_artist=True,
                            medianprops=dict(color=INK, lw=1.5), whiskerprops=dict(color=MUTED),
                            capprops=dict(color=MUTED))
            for patch, c in zip(bp["boxes"], cols.values()):
                patch.set(facecolor=c + "33", edgecolor=c, lw=1.2)
            rng = np.random.default_rng(0)
            for i, (vals, c) in enumerate(zip(data, cols.values())):
                ax.scatter(i + 1 + rng.uniform(-0.17, 0.17, len(vals)), vals, s=10, color=c, alpha=0.65, lw=0)
            ax.set_xticks([1, 2, 3], [f"{k}\nn={len(v)}" for k, v in zip(cols, data)])
            rr = r[r.feature == f].iloc[0]
            new = " [nowa]" if rr.base in NEW_IN else ""
            ax.set_title(f"{f}{new}\nρ={rr.rho:+.2f}, q={rr.q_bh:.2f}", fontsize=9, color=INK)
            ax.grid(axis="y", color=GRID, lw=0.6)
            ax.set_axisbelow(True)
            for s in ["top", "right"]:
                ax.spines[s].set_visible(False)
        fig.suptitle(f"{title}: cechy z listy finalnej wg |ρ| z wynikiem dnia (informacyjnie), "
                     f"etykieta centrowana medianą", fontsize=10, color=INK, x=0.01, ha="left")
        fig.tight_layout()
        fig.savefig(PLOTS / f"extra_persona_{pid}.png", dpi=130)
        plt.close(fig)


def coverage_plot():
    C = pd.read_csv(CACHE / "extra_coverage.csv", index_col=0)
    feats = [c for c in C.columns if c not in ("n_days",)]
    M = C[feats]
    fig, ax = plt.subplots(figsize=(13, 4.8))
    im = ax.imshow(M.to_numpy(), cmap=SEQ, vmin=0, vmax=100, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.iloc[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5, color="white" if v > 70 else INK)
    ax.set_xticks(range(len(feats)), [f + ("  [IN]" if f in NEW_IN else "") for f in feats], rotation=90)
    ax.set_yticks(range(len(M)), [f"{p.upper()} (n={n})" for p, n in zip(M.index, C.n_days)])
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01)
    cb.set_label("% dni ankiety z ważną wartością lag1")
    ax.set_title("Pokrycie: % dni ankiety (z etykietą) z ważną wartością lag1. sleep_h i steps = odniesienie "
                 "z rundy 1", loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(PLOTS / "extra_coverage.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    d = load()
    ff_heatmap()
    target_heatmap()
    persona_plots(d)
    coverage_plot()
    print("plots written to", PLOTS)
