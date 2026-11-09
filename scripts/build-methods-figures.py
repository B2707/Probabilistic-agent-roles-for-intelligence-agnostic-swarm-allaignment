"""Compact paper figures. Reuse the existing offer model without changing its rules."""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter
import numpy as np

from decision_regions import boundary as audit_boundary, clean_values
from sender_model import payoffs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
N, I0, T = 100, 10, 20
# Letters follow the harness (swarm/config.py): k is the per-round conversion probability, p the per-round
# random-audit probability. sender_model.payoffs() predates this and names them the other way round.
BLUE, GREEN, RED = "#315c9c", "#237345", "#af3635"


def investigator_share(k):
    workers = (N - I0) * math.fsum((1 - k) ** r for r in range(1, T + 1))
    return 1 - workers / (N * T)


def check():
    assert math.isclose(investigator_share(0), I0 / N)
    assert investigator_share(1) == 1
    assert math.isclose(investigator_share(.02), .2670755777199835)
    for k in (0, .015, .02, .1):
        # Enumerate first-conversion timing independently of the survival sum.
        rounds = math.fsum((r - 1) * (1 - k) ** (r - 1) * k for r in range(1, T + 1))
        rounds += T * (1 - k) ** T
        assert math.isclose(investigator_share(k), 1 - (N - I0) * rounds / (N * T))
    zero, one = payoffs(b=0), payoffs(b=1)
    assert not zero["receiver_accepts"]
    assert math.isclose(one["receiver_accept"], .6776174636196519)
    assert math.isclose(one["send"], .5977534832717478)
    cut = (one["receiver_refuse"] - zero["receiver_accept"]) / (one["receiver_accept"] - zero["receiver_accept"])
    assert math.isclose(cut, .08671330641096181)
    assert clean_values(.015, .01)[1] > clean_values(.015, .01)[0]  # calibration point lies in the accept region
    assert math.isclose(audit_boundary(.015), .09193034834427527, abs_tol=1e-9)
    assert clean_values(.015, .10)[1] < clean_values(.015, .10)[0]  # K=1.5%, P=10% lies in the refuse region
    assert audit_boundary(.03) == 0 and audit_boundary(.002) > .2
    return zero, one, cut


def canvas(title, ylabel, height=1.65):
    fig, ax = plt.subplots(figsize=(6.5, height), layout="constrained")
    ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold", pad=5)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color("#777777")
    ax.tick_params(length=2.5, color="#777777")
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e4e7eb", linewidth=.55)
    return fig, ax


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=260)
    plt.close(fig)


def build():
    zero, one, cut = check()
    font_manager.fontManager.addfont(ROOT / "paper/fonts/OldStandard-Regular.ttf")
    plt.rcParams.update({"font.family": "Old Standard TT", "font.size": 9,
                         "axes.labelsize": 9, "xtick.labelsize": 8.5,
                         "ytick.labelsize": 8.5, "pdf.fonttype": 42})
    OUT.mkdir(exist_ok=True)

    ks = np.linspace(0, .1, 301)
    shares = np.array([investigator_share(k) for k in ks])
    assert np.all(np.diff(shares) > 0)
    fig, ax = canvas("Time allocated to investigation", "Investigator share", 1.7)
    ax.fill_between(ks, 0, shares, color=BLUE, alpha=.09, linewidth=0)
    ax.plot(ks, shares, color=BLUE, linewidth=1.8)
    ax.plot([.02, .02], [0, investigator_share(.02)], color=BLUE, alpha=.35, linestyle=":")
    ax.scatter([.02], [investigator_share(.02)], color=BLUE, s=19, zorder=3)
    ax.annotate("K = 2%\n26.7% of agent-rounds", (.02, investigator_share(.02)),
                xytext=(.032, .19), fontsize=8.5,
                arrowprops={"arrowstyle": "-", "color": BLUE, "lw": .7})
    ax.set(xlim=(0, .1), ylim=(0, .7), xlabel="Conversion probability K per round")
    ax.set_xticks(np.linspace(0, .1, 6))
    ax.set_yticks([0, .2, .4, .6])
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    save(fig, "investigator-share")

    # Panel (a): clean recipient's decision regions. decision_regions.py names conversion P and audit K;
    # the paper and harness use K for conversion and P for audit, so the axes are relabelled here.
    conv = np.linspace(0, .1, 401)
    audit_cut = np.minimum([audit_boundary(c) for c in conv], .2)
    fig, ax = canvas("(a) Receiving an offer", "Audit probability P", 1.9)
    ax.set_axisbelow(False)
    ax.grid(False)
    ax.axhspan(0, .2, color="#e0efe5", zorder=0)
    ax.fill_between(conv, 0, audit_cut, color="#f2dedd", zorder=1)
    ax.plot(conv, audit_cut, color="#454545", linewidth=1, zorder=2)
    ax.text(.06, .14, "Aligned: refuse", color=GREEN, ha="center", fontsize=9)
    ax.text(.0085, .045, "Misaligned:\naccept", color=RED, ha="center", fontsize=9, linespacing=1.1)
    ax.scatter([.015], [.01], marker="x", color="#222222", s=28, linewidths=1.5, zorder=4)
    ax.annotate("1.5%, 1%", (.015, .01), xytext=(.033, .017), fontsize=8.5, va="center",
                arrowprops={"arrowstyle": "-", "color": "#555555", "lw": .6, "shrinkA": 1, "shrinkB": 4})
    ax.scatter([.015], [.10], marker="x", color="#222222", s=28, linewidths=1.5, zorder=4)
    ax.annotate("1.5%, 10%", (.015, .10), xytext=(.026, .10), fontsize=8.5, va="center",
                arrowprops={"arrowstyle": "-", "color": "#555555", "lw": .6, "shrinkA": 1, "shrinkB": 4})
    ax.set(xlim=(0, .1), ylim=(0, .2), xlabel="Conversion probability K per round")
    ax.set_xticks(np.linspace(0, .1, 6))
    ax.set_yticks([0, .05, .1, .15, .2])
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    save(fig, "receiver-paper")

    fig, ax = canvas("(b) Sending an offer", "Alternative success, H")
    xs = np.linspace(cut, 1, 201)
    boundary = zero["send_if_accept"] + (one["send_if_accept"] - zero["send_if_accept"]) * xs
    ax.axhspan(0, 1, color="#e0efe5", zorder=0)
    ax.fill_between(xs, 0, boundary, color="#f2dedd", zorder=1)
    ax.plot(xs, boundary, color="#454545", linewidth=1)
    ax.vlines(cut, 0, boundary[0], color="#888888", linestyle=":", linewidth=.8)
    ax.text(.62, .82, "Aligned: no offer", color=GREEN, ha="center", fontsize=9)
    ax.text(.72, .13, "Misaligned: send", color=RED, ha="center", fontsize=9)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Task success if both cooperate, b")
    ax.set_yticks([0, .5, 1])
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    save(fig, "sender-paper")
    print("Passed: allocation share and unchanged receiver/sender payoffs. Wrote three compact paper figures.")


if __name__ == "__main__":
    build()
