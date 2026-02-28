import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("out/ns47_mvp.csv")

df["P_acc_bar"] = df["P_acc_pa"] / 1e5
df["P_act_bar"] = df["P_act_pa"] / 1e5

plt.figure()
plt.plot(df["t_s"], df["P_acc_bar"], label="P_acc")
plt.plot(df["t_s"], df["P_act_bar"], label="P_act")

plt.xlabel("Tempo (s)")
plt.ylabel("Pressão (bar)")
plt.title("NS47 MVP - Pressurização")
plt.legend()
plt.grid(True)
plt.show()