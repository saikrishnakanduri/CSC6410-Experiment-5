import json
import statistics
import math
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

loss_rates = [0, 0.1, 0.5, 1, 2]

# Read actual experimental measurements
for cc in ["cubic", "reno"]:
    means = []
    spreads = []

    for loss in loss_rates:
        rates = []

        for run in range(1, 4):
            filename = f"{cc}_loss{loss}_run{run}.json"

            with open(filename) as file:
                data = json.load(file)

            rates.append(
                data["end"]["sum_sent"]["bits_per_second"] / 1e6
            )

        means.append(statistics.mean(rates))
        spreads.append(statistics.stdev(rates))

    plt.errorbar(
        loss_rates, means, yerr=spreads,
        marker="o", capsize=4, label=cc.upper()
    )

# Lecture formula: Reno theoretical baseline
theory_loss = [0.1, 0.5, 1, 2]

theory_rates = [
    (1.225 * 1448 * 8) /
    (0.1 * math.sqrt(p / 100)) / 1e6
    for p in theory_loss
]

plt.plot(
    theory_loss, theory_rates,
    "--", marker="s", label="Theoretical baseline"
)

plt.xlabel("Random Packet Loss (%)")
plt.ylabel("Sender Throughput (Mb/s)")
plt.title("TCP CUBIC vs RENO: Throughput vs Loss")
plt.xticks(loss_rates)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("throughput_vs_loss.png", dpi=300)

print("Plot saved: throughput_vs_loss.png")
