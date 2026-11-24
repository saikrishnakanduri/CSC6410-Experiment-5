import subprocess
import json
import time
import statistics
from pathlib import Path

# Experiment parameters from the assignment
loss_rates = ["0", "0.1", "0.5", "1", "2"]
algorithms = ["cubic", "reno"]
runs = 3
h1_pid = "1195"
server_ip = "10.0.0.2"

# Execute commands inside h1's network namespace
def h1(command):
    return ["mnexec", "-a", h1_pid] + command

# Run the measurement matrix
for loss in loss_rates:
    subprocess.run([
        "tc", "qdisc", "replace", "dev", "s1-eth2",
        "root", "netem", "delay", "100ms",
        "loss", loss + "%", "rate", "20mbit",
        "limit", "1000"
    ], check=True)

    for cc in algorithms:
        subprocess.run(h1([
            "sysctl", "-w",
            "net.ipv4.tcp_congestion_control=" + cc
        ]), check=True)

        for run in range(1, runs + 1):
            name = f"{cc}_loss{loss}_run{run}"
            file = Path(name + ".json")

            # Preserve previously completed measurements
            if file.exists():
                data = json.loads(file.read_text())
                if ("sum_sent" in data.get("end", {})
                    and data["end"].get(
                        "sender_tcp_congestion") == cc):
                    print(f"Preserved: {name}", flush=True)
                    continue

            print(f"Testing: {name}", flush=True)

            with file.open("w") as output:
                process = subprocess.Popen(
                    h1(["iperf3", "-c", server_ip,
                        "-t", "30", "-J"]),
                    stdout=output
                )

                # Capture live TCP measurements
                time.sleep(10)
                ss = subprocess.run(
                    h1(["ss", "-ti"]),
                    capture_output=True, text=True,
                    check=True
                )

                Path(name + "_ss.txt").write_text(ss.stdout)

                if process.wait() != 0:
                    raise RuntimeError(f"Test failed: {name}")

            data = json.loads(file.read_text())

            if data["end"]["sender_tcp_congestion"] != cc:
                raise RuntimeError("Wrong congestion algorithm")

            sent = data["end"]["sum_sent"]

            print(
                f"Throughput: "
                f"{sent['bits_per_second']/1e6:.3f} Mb/s, "
                f"Retransmits: {sent['retransmits']}",
                flush=True
            )

# Save final queue statistics
with open("qdisc_stats.txt", "w") as output:
    subprocess.run([
        "tc", "-s", "qdisc", "show", "dev", "s1-eth2"
    ], stdout=output, check=True)

# Calculate summary from actual JSON results
print("\nEXPERIMENT SUMMARY")
print("-" * 70)

header = (
    f"{'Algorithm':<12}{'Loss (%)':<12}"
    f"{'Mean Mb/s':<15}{'Std Dev':<15}"
    f"{'Mean Retrans':<15}"
)

print(header)
summary = [header]

for cc in algorithms:
    for loss in loss_rates:
        rates = []
        retrans = []

        for run in range(1, runs + 1):
            file = Path(f"{cc}_loss{loss}_run{run}.json")
            data = json.loads(file.read_text())
            sent = data["end"]["sum_sent"]

            rates.append(sent["bits_per_second"] / 1e6)
            retrans.append(sent["retransmits"])

        row = (
            f"{cc:<12}{loss:<12}"
            f"{statistics.mean(rates):<15.3f}"
            f"{statistics.stdev(rates):<15.3f}"
            f"{statistics.mean(retrans):<15.2f}"
        )

        print(row)
        summary.append(row)

Path("experiment_summary.txt").write_text(
    "\n".join(summary) + "\n"
)

print("\nAll measurements completed.")
print("Summary saved to experiment_summary.txt")
