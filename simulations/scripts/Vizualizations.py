import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
import sqlite3
import atexit

root_path = "/home/blackstone/PycharmProjects/NIH/AsymmetricDivisions/simulations/data/local_experiments"


class Visualizator:
    def __init__(self,
                 root_path: str,
                 run_id,
                 color="blue", label=""):
        if Path(root_path + f"/{run_id}/params.txt").exists():
            with open(root_path + f"/{run_id}/params.txt", "r") as fl:
                self.params = json.load(fl)
        else:
            with open(root_path + f"/{run_id}/params.json", "r") as fl:
                self.params = json.load(fl)
        self.color = color
        self.label = (label + f" ({run_id})").strip()
        self.history_tables = []
        self.cell_tables = []
        self.genealogy_tables = []

    def plot(self, x_feature, y_feature, show=True, axis=None, label=None):
        # yy_sorted = []
        # for x in xx:
        #     yy = np.array([list(self.history_tables[i].loc[self.history_tables[i][x_feature] == x,
        #                                                    y_feature])[0] for i in range(len(self.history_tables))])
        #     yy_sorted.append(np.array(sorted(yy)))
        # plt.fill_between(xx,
        #                  [el[int(len(yy_sorted[0])*0.2)-1] for el in yy_sorted],
        #                  [el[int(len(yy_sorted[0])*0.8)-1] for el in yy_sorted], color=self.color,
        #                  alpha=0.1, label=self.label)
        # plt.plot(xx, [el.mean() for el in yy_sorted], color=self.color)
        if not label:
            label = self.label
        if axis:
            convolution_step = 400
            for i in range(len(self.history_tables)):
                yy = self.history_tables[i][y_feature]
                yy = list(yy)[:int(convolution_step/2)] + list(np.convolve(yy, np.ones(convolution_step)/convolution_step, 'valid'))
                if i == len(self.history_tables)-1:
                    axis.plot(yy, label=label, color=self.color)
                else:
                    axis.plot(yy, color=self.color)
            axis.set_xlabel(" ".join(x_feature.split("_")))
            axis.set_ylabel(" ".join(y_feature.split("_")))
        else:
            xx = self.history_tables[0][x_feature]
            plt.plot(xx, self.history_tables[0][y_feature], label=label)
            plt.xlabel(" ".join(x_feature.split("_")))
            plt.ylabel(" ".join(y_feature.split("_")))
        if show:
            plt.grid()
            plt.legend()
            plt.show()

    def plot_age_distribution(self):
        for cell_table in self.cell_tables:
            xx = list(range(cell_table.generation.min(), cell_table.generation.max()+1))
            for x in xx:
                yy = cell_table.loc[cell_table.generation == x].cell_age
                plt.hist(yy, alpha=x/xx[-1], color="blue")
        plt.show()

    def plot_growth_rate(self):
        for cell_table in self.cell_tables:
            xx = list(range(cell_table.time_step.min(), cell_table.time_step.max() + 1))
            yy = []
            for x in xx:
                denominator = cell_table.loc[(cell_table.time_step == x) & (~cell_table.has_died)]
                numerator = denominator.loc[denominator.has_divided]
                yy.append(len(numerator)/len(denominator))
            print(np.array(yy[30:]).mean())
            plt.plot(xx, yy)
        plt.show()

    def plot_mean_feature(self, feature, condition=True, show=True):
        yy_sorted = []
        xx = sorted(self.cell_tables[0]["time_step"].unique())
        # for x in xx:
        #     if x % 100 == 0:
        #         print(x)
        #     yy = [self.cell_tables[i].
        #           loc[(self.cell_tables[i].time_step == x) & condition, feature].mean()
        #           for i in range(len(self.history_tables))]
        #     yy_sorted.append(sorted(yy))
        # plt.fill_between(xx,
        #                  [el[int(len(yy_sorted[0]) * 0.2) - 1] for el in yy_sorted],
        #                  [el[int(len(yy_sorted[0]) * 0.8) - 1] for el in yy_sorted],
        #                  color=self.color, alpha=0.1, label=self.label)
        yy = self.cell_tables[0].groupby("time_step").aggregate(np.mean)
        plt.plot(xx, yy[feature])
        # plt.xlabel("time_step")
        plt.ylabel(f"mean {feature}")
        if show:
            plt.grid()
            plt.legend()
            plt.show()


class TSVVisualizator(Visualizator):
    def __init__(self,
                 root_path: str,
                 run_id: int,
                 color="blue", label=""):
        super().__init__(root_path, run_id, color, label)
        files = [file.stem for file in Path(f"{root_path}/{run_id}").glob("*.tsv")]

        n_threads = max([int(file.split("_")[-1]) for file in files])
        self.history_tables = [pd.read_csv(f"{root_path}/{run_id}/history_{run_id}_{i}.tsv", sep="\t")
                               for i in range(1, n_threads+1)]
        try:
            self.cell_tables = [pd.read_csv(f"{root_path}/{run_id}/cells_{run_id}_{i}.tsv", sep="\t")
                                for i in range(1, n_threads+1)]
        except FileNotFoundError:
            self.cell_tables = []
        try:
            self.genealogy_tables = [pd.read_csv(f"{root_path}/{run_id}/genealogy_{run_id}_{i}.tsv", sep="\t")
                                     for i in range(1, n_threads + 1)]
        except FileNotFoundError:
            self.genealogy_tables = []


class SQLVisualizator(Visualizator):
    def __init__(self,
                 root_path: str,
                 run_id,
                 color="blue", label=""):
        super().__init__(root_path, run_id, color, label)
        self.folder = f"{root_path}/{run_id}"
        self.run_id = str(run_id).split("_")[0]
        files = [str(file) for file in Path(self.folder).glob("*.sqlite")]
        self.connections = [sqlite3.connect(file) for file in files]
        for con in self.connections:
            atexit.register(con.close)
        self.history_tables = [pd.read_sql_query("SELECT * FROM history", con) for con in self.connections]
        # self.cell_tables = [pd.read_sql_query("SELECT * FROM cells", con) for con in connections]
        # self.genealogy_tables = [pd.read_sql_query("SELECT * FROM genealogy", con) for con in connections]

    def plot_mean_feature(self, feature, condition=True, show=True):
        self.cell_tables = [pd.read_sql_query(f"SELECT time_step, {feature} FROM cells", con)
                            for con in self.connections]
        super().plot_mean_feature(feature, condition, show)

    def make_interactive_mode_figure(self, show=False):
        _, ax = plt.subplots(3, 1)
        color = self.color
        self.color = "blue"
        self.plot("time_step", "n_cells", show=False, axis=ax[0])
        self.color = "grey"
        self.plot("time_step", "mean_damage", show=False, axis=ax[1])
        self.color = "green"
        self.plot("time_step", "mean_asymmetry", show=False, axis=ax[2], label="asymmetry")
        self.color = "red"
        self.plot("time_step", "mean_repair", show=False, axis=ax[2], label="repair")
        self.color = color
        ax[2].set_ylabel("mean asymmetry \n & repair")
        plt.legend()
        if show:
            plt.show()

    def make_figure_report(self):
        figures_folder = f"{self.folder}/{self.run_id}_figures"
        Path(figures_folder).mkdir(exist_ok=True)
        for feature, figure_name in zip(["n_cells",
                                         "mean_asymmetry",
                                         "mean_damage",
                                         "mean_repair"],
                                        ["population_size_dynamics",
                                         "asymmetry_dynamics",
                                         "damage_dynamics",
                                         "repair_dynamics"]):
            _, ax = plt.subplots()
            self.plot("time_step", feature, show=False, axis=ax)
            ax.set_title(" ".join([el.capitalize() for el in figure_name.split("_")]))
            plt.savefig(f"{figures_folder}/{figure_name}.png")
        self.make_interactive_mode_figure()
        plt.savefig(f"{figures_folder}/interactive_mode_figure.png")



# folders = [int(str(p).split("/")[-1]) for p in Path(root_path).glob("*")]

# visualizator_1 = SQLVisualizator(root_path=root_path,
#                                run_id=1667692592700762,
#                                label="asymmetry not allowed",
#                                color="blue")

# plt.plot(visualizator_1.history_tables[0].n_cells, color="red", label="mutations")
# visualizator_2 = SQLVisualizator(root_path=root_path,
#                                run_id=1667691179152085,
#                                label="asymmetry allowed",
#                                color="red")

# plt.plot(visualizator_2.history_tables[0].n_cells, color="blue", label="no mutations")

# visualizator = TSVVisualizator(root_path=root_path, run_id=1665763892, color="green", label="L=40")
# visualizator.plot("time_step", "n_cells", show=False)
# visualizator.plot_mean_feature("cell_damage", show=False)

# colors = ["red", "orange", "green"]
# for run_id, color in zip([1668088386085591,
#                           1668091105066757,
#                           1668092457186757], colors):
#     visualizator = SQLVisualizator(root_path=root_path, run_id=run_id, color=color, label="")
#     visualizator.label = f'A={visualizator.params["cell_parameters"]["damage_accumulation_rate"]}'
#     visualizator.plot("time_step", "n_cells", show=False)
# visualizator.plot_mean_feature("cell_damage", show=False)

# visualizator = TSVVisualizator(root_path=root_path, run_id=1665763892, color='green', label="symmetry")
# visualizator.plot("time_step", "n_cells", show=False)
id_1 = 1669128159147082 # Mutation step = 0.05
id_2 = 1669128218000692 # Mutation step = 0.01
id_3 = 1669130957394782 # Mutation step = 0.05, mutation rate = 0.001
id_4 = 1669193798094970 # daec = 0.01
id_5 = 1669194873430621 # daec = 0, a=0
id_6 = 1669195448345880 # daec = 0, a=1
id_7 = 1669197993386483 # daec = 0, a=0.5
id_8 = 1669199773539028 # weird damage accumulation rate = 100
id_9 = 1669201571863388 # weird damage accumulation rate = 1000
id_10 = 1671481850523483 # story about asymmetry evolving in a population on the brink of extintion!
id_11 = 1671485681602655 # same, 10 runs, mutation rate = 0.02
id_12 = 1671660658135236 # asymmetry is better than multiplicative repair?
id_13 = 1671664065198253 # multiplicative repair
id_14 = 1671665041933698 # asymmetry is better than multiplicative repair?
id_15 = 1671726415351954 # additive repair

visualizator = SQLVisualizator(root_path=root_path, run_id=1671745458968505, color='blue')
visualizator.make_figure_report()
# visualizator.make_interactive_mode_figure(show=True)

# visualizator = SQLVisualizator(root_path=root_path, run_id=id_14, color='blue')
# fig, axis = plt.subplots(3, 1)
# visualizator.plot("time_step", "n_cells", show=False, axis=axis[0])
# visualizator.color = "green"
# visualizator.plot("time_step", "mean_asymmetry", show=False, axis=axis[1])
# visualizator.color = "blue"
# visualizator.plot("time_step", "mean_damage", show=False, axis=axis[2])
# visualizator.plot("time_step", "mean_repair", show=False, axis=axis[1])
#
# visualizator = SQLVisualizator(root_path=root_path, run_id=id_13, color='red')
# visualizator.plot("time_step", "n_cells", show=False, axis=axis[0])
# visualizator.color = "green"
# visualizator.plot("time_step", "mean_asymmetry", show=False, axis=axis[1])
# visualizator.color = "red"
# visualizator.plot("time_step", "mean_damage", show=False, axis=axis[2])
# visualizator.plot("time_step", "mean_repair", show=False, axis=axis[1])
# plt.show()



# xx = list(range(1000))
# yy = [1 + 1000/(x+1) for x in xx]
# plt.plot(xx, yy)
# plt.plot([0, 0], [0, max(yy)], color="red", linestyle="--")
# plt.plot([0, max(xx)], [1, 1], color="red", linestyle="--")

# visualizator = SQLVisualizator(root_path=root_path, run_id=id_6, color='red', label="step=0.01")
# visualizator.plot("time_step", "n_cells", show=False, axis=axis[0])
# visualizator.plot("time_step", "mean_asymmetry", show=False, axis=axis[1])
# visualizator.plot("time_step", "mean_damage", show=False, axis=axis[2])
#
# visualizator = SQLVisualizator(root_path=root_path, run_id=id_7, color='green', label="step=0.05, rate = 0.001")
# visualizator.plot("time_step", "n_cells", show=False, axis=axis[0])
# visualizator.plot("time_step", "mean_asymmetry", show=False, axis=axis[1])
# visualizator.plot("time_step", "mean_damage", show=False, axis=axis[2])


# visualizator = SQLVisualizator(root_path=root_path, run_id=id_4, color='blue', label="daec=0.01")
# visualizator.plot("time_step", "n_cells", show=False, axis=axis[0])
# visualizator.plot("time_step", "mean_asymmetry", show=False, axis=axis[1])
# visualizator.plot("time_step", "mean_damage", show=False, axis=axis[2])

# visualizator.plot_mean_feature("cell_asymmetry", show=False)
# visualizator.plot_mean_feature("cell_age", show=False)
# visualizator_1.plot_mean_feature("cell_damage", show=False)
# visualizator_2.plot_mean_feature("cell_damage", show=False)

# visualizator = Visualizator(root_path=root_path, run_id=1665763892, label="low damage threshold", color="green")
# visualizator = Visualizator(root_path=root_path, run_id=1665232310)
# visualizator.plot("time_step", "n_cells", show=False)
# visualizator.plot_mean_feature("cell_damage", show=False)
# visualizator.plot_mean_feature("cell_age", show=False)

# visualizator.plot_age_distribution()
# visualizator.plot_growth_rate()
# visualizator.plot_mean_feature("cell_damage")
# visualizator.plot_mean_feature("cell_age", visualizator.cell_table.has_divided == True, show=False)
# visualizator.plot_mean_feature("cell_age", show=False)
# visualizator.plot_mean_feature("cell_damage", visualizator.cell_table.has_divided == True, show=False)
# plt.plot([0, 10000], [40, 40], linestyle="--", color="green", alpha=0.5)
# plt.plot([0, 10000], [500, 500], linestyle="--", color="blue", alpha=0.5)
# visualizator.plot_mean_feature("cell_age", show=True)

# plt.grid()
# plt.legend()
# plt.show()



# Analysing population sizes with various asymmetry levels
def experiment_1():
    folders = [int(str(p).split("/")[-1]) for p in Path(root_path + "asymmetric_division_saves_population/").glob("*")]
    folders.sort()
    visualizators = [Visualizator(root_path=root_path+"asymmetric_division_saves_population/",
                                  run_id=folder) for folder in folders]
    visualizators.sort(key=lambda el: el.params["asymmetry"])

    asymmetries = [visualizator.params["asymmetry"] for visualizator in visualizators]
    print(asymmetries)
    stable_popsizes = [np.array([np.array(history_table.n_cells[:-100]).mean()
                                 for history_table in visualizator.history_tables])
                       for visualizator in visualizators]
    print(stable_popsizes)

    data = pd.DataFrame({asymmetry: popsize for asymmetry, popsize in zip(asymmetries, stable_popsizes)})
    data[asymmetries].plot(kind='box', title='Population size depending on the asymmetry level')
    plt.xticks(rotation=90)
    plt.xlabel("Asymmetry")
    plt.ylabel("Population size")
    plt.show()


