import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from active_weasul import ActiveWeaSuLPipeline


def process_metric_dict(metric_dict, strategy_string, remove_test=False):

    metric_df = (
        pd.DataFrame(metric_dict).stack().apply(pd.Series).stack().reset_index()
        .rename(columns={"level_0": "Number of labeled points", "level_1": "Model", "level_2": "Metric", 0: "Value"})
    )

    metric_df[["Model", "Set"]] = metric_df["Model"].str.split("_", expand=True)
    metric_df["Strategy"] = strategy_string

    if remove_test:
        metric_df = metric_df[metric_df["Set"] != "test"]

    return metric_df


def process_exp_dict(exp_dict, strategy_string):

    exp_df = pd.concat({i: process_metric_dict(exp_dict[i], strategy_string).drop(index=1) for i in exp_dict.keys()})

    return exp_df


def plot_metrics(metric_df, filter_metrics=["Accuracy"], plot_train=False):

    if not plot_train:
        metric_df = metric_df[metric_df.Set != "train"]

    lines = list(metric_df.Strategy.unique())

    colors = ["#2b4162", "#368f8b", "#ec7357", "#e9c46a"][:len(lines)]

    metric_df = metric_df[metric_df["Metric"].isin(filter_metrics)]

    sns.set(style="whitegrid")
    ax = sns.relplot(data=metric_df, x="Number of labeled points", y="Value", col="Model",
                     kind="line", hue="Strategy", estimator="mean", ci=68, n_boot=100, legend=False, palette=sns.color_palette(colors))

    show_handles = [ax.axes[0][0].lines[i] for i in range(len(lines))]
    show_labels = lines
    ax.axes[len(ax.axes)-1][len(ax.axes[0])-1].legend(handles=show_handles, labels=show_labels, loc="lower right")

    ax.set_ylabels("")
    ax.set_titles("{col_name}")

    return ax


def active_weasul_experiment(nr_trials, al_it, label_matrix, y_train, cliques,
                             class_balance, query_strategy, starting_seed=76, seeds=None, penalty_strength=1, batch_size=20,
                             final_model=None, train_dataset=None, test_dataset=None,
                             label_matrix_test=None, y_test=None, randomness=0):

    al_metrics = {}
    al_probs = {}

    if seeds is None:
        seeds = np.random.randint(0, 1000, nr_trials)

    for i in tqdm(range(nr_trials), desc="Trials"):
        seed = seeds[i]
        al = ActiveWeaSuLPipeline(it=al_it,
                                  penalty_strength=penalty_strength,
                                  query_strategy=query_strategy,
                                  randomness=randomness,
                                  final_model=final_model,
                                  batch_size=batch_size,
                                  starting_seed=starting_seed,
                                  seed=seed)

        _ = al.run_active_weasul(label_matrix=label_matrix,
                                 y_train=y_train,
                                 cliques=cliques,
                                 class_balance=class_balance,
                                 train_dataset=train_dataset,
                                 test_dataset=test_dataset,
                                 label_matrix_test=label_matrix_test,
                                 y_test=y_test)

        al_metrics[i] = al.metrics
        al_probs[i] = al.probs

        # plot_metrics(process_metric_dict(al.metrics, query_strategy, remove_test=True))
        # plot_probs(df, al.probs["Generative_train"][al_it-1], soft_labels=False, add_labeled_points=al.queried[:al_it-1]).show()

    return al_metrics, al.queried


# def active_learning_experiment():
