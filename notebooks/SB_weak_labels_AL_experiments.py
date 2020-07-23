# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# +
# %load_ext autoreload
# %autoreload 2

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd
import random
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm_notebook as tqdm

sys.path.append(os.path.abspath("../activelearning"))
from data import sample_clusters
from final_model import fit_predict_fm
from label_model import get_properties, fit_predict_lm, get_overall_accuracy
from pipeline import AL_pipeline
from plot import plot_probs, plot_accuracies
# -


# # Create clusters

# +
N_1 = 5000
N_2 = 5000
centroid_1 = np.array([0.1, 1.3])
centroid_2 = np.array([-0.8, -0.5])

# X, p, y = sample_clusters(N_1, N_2, centroid_1, centroid_2, std = 0.5, scaling_factor = 4)

# +
p_z = 0.5
y = np.random.binomial(1, p_z, N_1+N_2)

X = np.zeros((N_1+N_2,2))
X[y==0, :] = np.random.normal(loc=centroid_1, scale=np.array([0.5,0.5]), size=(len(y[y==0]),2))
X[y==1, :] = np.random.normal(loc=centroid_2, scale=np.array([0.5,0.5]), size=(len(y[y==1]),2))
# -

df = pd.DataFrame({'x1': X[:,0], 'x2': X[:,1], 'y': y})

plot_probs(df, y.astype(str), soft_labels=False)

# # Create weak labels

df.loc[:, "wl1"] = (X[:,1]<0)*1
df.loc[:, "wl2"] = (X[:,0]<-0.3)*1
df.loc[:, "wl3"] = (X[:,0]<-1)*1

print("Accuracy wl1:", (df["y"] == df["wl1"]).sum()/len(y))
print("Accuracy wl2:", (df["y"] == df["wl2"]).sum()/len(y))
print("Accuracy wl3:", (df["y"] == df["wl3"]).sum()/len(y))

label_matrix = np.array(df[["wl1", "wl2", "wl3", "y"]])

# # Compare approaches

N_total, nr_wl, y_set, y_dim = get_properties(label_matrix)

# +
label_model_kwargs = dict(n_epochs=200,
                        class_balance=np.array([0.5,0.5]),
                        lr=1e-1)

al_kwargs = dict(it=100)

final_model_kwargs = dict(input_dim=2,
                      output_dim=2,
                      lr=1e-3,
                      batch_size=256,
                      n_epochs=200)
# -

accuracies = {}
n_runs = 10

# +
# label model without active learning

label_model_kwargs["cliques"] = [[1,2]]

accuracies["no_LM"] = []
# accuracies["no_final"] = []

for i in tqdm(range(n_runs)):
    L = label_matrix[:,:-1]
    
    _, Y_probs, _ = fit_predict_lm(L, y_al=None, label_model_kwargs=label_model_kwargs, al=False)
#     _, probs = fit_predict_fm(df[["x1", "x2"]].values, Y_probs, **final_model_kwargs, soft_labels=True)

    accuracies["no_LM"].append(get_overall_accuracy(Y_probs, df["y"]))
#     accuracies["no_final"].append(get_overall_accuracy(probs, df["y"]))
# -

accuracies

# +
# label model with active learning

label_model_kwargs["cliques"] = [[0,3],[1,2,3]]

wl_al = np.full_like(df["y"], -1)

# ["yes_LM"] = []
# accuracies["yes_final"] = []

for i in tqdm(range(n_runs)):
#     L = np.concatenate([label_matrix[:,:-1], wl_al.reshape(len(wl_al),1)], axis=1)
    L = label_matrix[:,:-1]
    
    Y_probs_al, _, _, probs_dict, prob_label_dict = AL_pipeline(L, df, label_model_kwargs, final_model_kwargs, **al_kwargs)
    _, probs_al = fit_predict_fm(df[["x1", "x2"]].values, Y_probs_al, **final_model_kwargs, soft_labels=True)

#     accuracies["yes_LM"].append(get_overall_accuracy(Y_probs_al, df["y"]))
#     accuracies["yes_final"].append(get_overall_accuracy(probs_al, df["y"]))

# +
# final model ground truth labels
_, probs_up = fit_predict_fm(df[["x1", "x2"]].values, df["y"].values, **final_model_kwargs, soft_labels=False)

accuracy_up = get_overall_accuracy(probs_up, df["y"])

# accuracies_it["supervised"] = [accuracy_up] * len(accuracies_it["prob_labels"])
accuracies["supervised"] = [accuracy_up] * n_runs
# -

# Probabilistic labels without active learning
plot_probs(df, Y_probs)

# Probabilistic labels with active learning
plot_probs(df, Y_probs_al)

plot_probs(df, probs)

plot_probs(df, probs_al)

# +

df_res = pd.DataFrame(accuracies)

df_res.columns = ["no_al_LM", "no_al_final", "al_LM", "al_final", "supervised"]
# df_res.columns = ["no_al_LM", "no_al_final", "al_LM", "al_final"]

df_res.index.name = "run"

df_res.index = df_res.index + 1

df_res = df_res.stack().reset_index().rename(columns={"level_1": "type", 0: "accuracy"})

fig = px.line(df_res, x = "run", y = "accuracy", color="type", color_discrete_sequence=np.array(px.colors.diverging.Geyser)[[1,0,-2,-1,3]])
fig.update_yaxes(range=[0.7, 1])
fig.update_layout(template="plotly_white", width=1200, height=700)
fig.show()
# -

feature_matrix = df[["x1", "x2", "y"]]
df_inv_cov = pd.DataFrame(np.linalg.pinv(np.cov(feature_matrix.T)))
fig, ax = plt.subplots(figsize=(10,10))
sns.heatmap(df_inv_cov, ax=ax, vmin=-4, vmax=4, center=0, annot=True, linewidths=.5, cmap="RdBu_r", square=True, xticklabels=True, yticklabels=True, fmt='.3g')

wl_al = np.full_like(df["y"], -1)
L = np.concatenate([label_matrix[:,:-1], wl_al.reshape(len(wl_al),1)], axis=1)

pick_indices = np.random.choice(np.arange(N_total), size = (1, 8000), replace=False)

L[pick_indices[0], 3] = df.iloc[pick_indices[0]]["y"]

# +
tmp_L = np.concatenate([L, np.array(df["y"]).reshape(len(df["y"]),1)], axis=1)

tmp_L_onehot = ((y_set == tmp_L[..., None]) * 1).reshape(N_total, -1)

df_inv_cov = pd.DataFrame(np.linalg.pinv(np.cov(tmp_L_onehot.T)))

labels=[("L1", 0), ("L1", 1), ("L2", 0), ("L2", 1), ("L3", 0), ("L3", 1), ("L_AL", 0), ("L_AL", 1), ("Y", 0), ("Y", 1)]

df_inv_cov.columns = pd.MultiIndex.from_tuples(labels, names=["label", "class"])
df_inv_cov.index = pd.MultiIndex.from_tuples(labels, names=["label", "class"])
# -

idx1 = [6,7]
idx2 = [8,9]

lambda_al_Y = ((tmp_L_onehot[:, np.newaxis, idx1[0]:(idx1[-1]+1)]
                        * tmp_L_onehot[:, idx2[0]:(idx2[-1]+1), np.newaxis]).reshape(len(tmp_L_onehot), -1))

fig, ax = plt.subplots(figsize=(15,15))
sns.heatmap(df_inv_cov, ax=ax, vmin=-4, vmax=4, center=0, annot=True, linewidths=.5, cmap="RdBu_r", square=True, xticklabels=True, yticklabels=True, fmt='.3g')
fig.savefig("cov.png")

# +
tmp_L = np.concatenate([L, np.array(df["y"]).reshape(len(df["y"]),1)], axis=1)

tmp_L_onehot = np.concatenate([((y_set == tmp_L[..., None]) * 1).reshape(N_total, -1), lambda_al_Y], axis=1)

df_inv_cov = pd.DataFrame(np.linalg.pinv(np.cov(tmp_L_onehot.T)))

labels=[("L1", 0), ("L1", 1), ("L2", 0), ("L2", 1), ("L3", 0), ("L3", 1), ("L_AL", 0), ("L_AL", 1), ("Y", 0), ("Y", 1), ("L_AL_Y", "00"), ("L_AL_Y", "01"), ("L_AL_Y", "10"), ("L_AL_Y", "11")]

df_inv_cov.columns = pd.MultiIndex.from_tuples(labels, names=["label", "class"])
df_inv_cov.index = pd.MultiIndex.from_tuples(labels, names=["label", "class"])
# -

fig, ax = plt.subplots(figsize=(15,15))
sns.heatmap(df_inv_cov, ax=ax, vmin=-4, vmax=4, center=0, annot=True, linewidths=.5, cmap="RdBu_r", square=True, xticklabels=True, yticklabels=True, fmt='.3g')
fig.savefig("cov2.png")

probs_df = pd.DataFrame.from_dict(probs_dict)
probs_df = probs_df.stack().reset_index().rename(columns={"level_0": "x", "level_1": "iteration", 0: "prob_y"})
probs_df = probs_df.merge(df, left_on = "x", right_index=True)

prob_label_df = pd.DataFrame.from_dict(prob_label_dict)
prob_label_df = prob_label_df.stack().reset_index().rename(columns={"level_0": "x", "level_1": "iteration", 0: "prob_y"})
prob_label_df = prob_label_df.merge(df, left_on = "x", right_index=True)

# +
# fig = px.scatter(probs_df, x="x1", y="x2", color="prob_y", animation_frame="iteration", color_discrete_sequence=np.array(px.colors.diverging.Geyser)[[0,-1]], color_continuous_scale=px.colors.diverging.Geyser, color_continuous_midpoint=0.5)
# fig.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1),
#                   width=1000, height=1000, xaxis_title="x1", yaxis_title="x2", template="plotly_white")

fig2 = px.scatter(prob_label_df, x="x1", y="x2", color="prob_y", animation_frame="iteration", color_discrete_sequence=np.array(px.colors.diverging.Geyser)[[0,-1]], color_continuous_scale=px.colors.diverging.Geyser, color_continuous_midpoint=0.5)
fig2.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1),
                  width=1000, height=1000, xaxis_title="x1", yaxis_title="x2", template="plotly_white")

# fig.show()

fig2.show()

# app = dash.Dash()
# app.layout = html.Div([
#     dcc.Graph(figure=fig),
#     dcc.Graph(figure=fig2)
# ])

# app.run_server(debug=True, use_reloader=False)

# +
x = list(range(len(accuracies_it["prob_labels"])))
x_gap = list(range(0, len(accuracies_it["prob_labels"]), 20))
x_gap_2 = list(range(0, len(accuracies_it["prob_labels"]), 100))


fig = go.Figure(data=go.Scatter(x=x, y=accuracies_it["prob_labels"], mode="lines", line_color=px.colors.diverging.Geyser[0], name="prob labels"))
# fig = go.Figure()

fig.add_trace(go.Scatter(x=x_gap, y=accuracies_it["final_labels"], mode="lines", line_color=px.colors.diverging.Geyser[-1], name="final labels"))

fig.add_trace(go.Scatter(x=x, y=accuracies_it["supervised"], mode="lines", line_color=px.colors.diverging.Geyser[3], name="supervised"))

# fig.add_trace(go.Scatter(x=x_gap_2, y=accuracies_it_random["final_labels"], mode="lines", line_color=px.colors.diverging.Geyser[-2], name="final labels random"))

# fig.add_trace(go.Scatter(x=x, y=accuracies_it_random["prob_labels"], mode="lines", line_color=px.colors.diverging.Geyser[1], name="prob labels random"))

fig.update_layout(template="plotly_white", xaxis_title="iteration", yaxis_title="accuracy", width=1200, height=700)
fig.update_yaxes(range=[0.7, 1])

fig.show()

# +
mean_accuracies = {keys: np.array(values).mean() for keys, values in accuracies.items()}

df_accuracies = pd.DataFrame.from_dict(mean_accuracies, orient="index", columns=["Mean accuracy"])
df_accuracies["Active learning"], df_accuracies["Labels"] = df_accuracies.index.str.split('_').str
df_accuracies.set_index(["Labels", "Active learning"]).sort_values(["Active learning"])
pd.pivot_table(df_accuracies, columns="Labels", index="Active learning")
# -

# # Train model on queried data points

queried = np.array(queried)

# +
_, probs_q = fit_predict_fm(df[["x1", "x2"]].values, df["y"].values, **final_model_kwargs, soft_labels=False, subset=queried)

get_overall_accuracy(probs_q, df["y"])
# -

plot_probs(df, probs_q, soft_labels=True, subset=queried)

# # Train model on random subset

random_idx = np.random.choice(range(N_total), al_kwargs["it"])

# +
_, probs_r = fit_predict_fm(df[["x1", "x2"]].values, df["y"].values, **final_model_kwargs, soft_labels=False, subset=random_idx)

get_overall_accuracy(probs_r, df["y"])
# -

plot_probs(df, probs_r, soft_labels=True, subset=random_idx)


