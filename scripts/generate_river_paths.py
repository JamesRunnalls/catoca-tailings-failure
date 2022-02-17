import os
import json
import numpy as np
from rivertrace import trace
from rivertrace.functions import log, parse_netcdf, plot_matrix, classify_river, plot_matrix_select

config_file = "../data/kwamouth.json"

with open(config_file) as json_file:
    parameters = json.load(json_file)
    plot = False
    if parameters["plot"] == "True":
        plot = True

runs = []
for i in parameters["inputs"]:
        for d in parameters["dates"]:
            runs.append({"d": d, "i": i})

for run in runs:
    try:
        folder = parameters["folder_t"].format(run["i"], run["d"], run["d"])
        files = list(filter(lambda file: "L2ACOLITE" in file, os.listdir(folder)))
        out_file_name = "path_" + "_".join([str(run["i"]), str(run["d"])]) + ".json"
        if os.path.isfile(os.path.join(parameters["out_folder"], out_file_name)):
            log("Skipping path {} as it already exists".format(out_file_name))
            continue
        for file in files:
            if run["i"].split("_")[0].upper() in file:
                log("Reading data from file {}".format(file))
                matrix, lat, lon = parse_netcdf(os.path.join(folder, file), parameters["water_parameter"], "lat", "lon")
                log("Create boolean pixel map of water/ non-water pixels")
                boolean = matrix.copy()
                boolean[boolean == 0] = np.nan
                boolean[~np.isnan(boolean)] = True
                boolean[np.isnan(boolean)] = False
                boolean = boolean.astype(bool)
                if len(boolean[boolean]) == 0:
                    log("All pixels are NaN")
                    continue

                if plot:
                    plot_matrix(boolean, title="Water classification plot")

                log("Update boolean pixel map to river pixels by applying max distance from rough river path")
                boolean, start, end = classify_river(boolean, lat, lon, parameters["rough_river"],
                                                     buffer=parameters["buffer"], direction=parameters["direction"])
                if plot:
                    plot_matrix(boolean, title="River classification plot")

                log("Manually remove any incorrectly classified water pixels")
                boolean = plot_matrix_select(boolean)
                path = trace(boolean, start, end, save_path=os.path.join(parameters["out_folder"], out_file_name))

                if plot:
                    output = boolean.copy()
                    output = output.astype(float)
                    for p in path:
                        output[p[0], p[1]] = 2
                    output[output == 0] = np.nan
                    plot_matrix(output, title="River classification plot")
            else:
                log("Skipping file {} as it is not the correct image.".format(file))
    except Exception as e:
        print("Failed on run: ".format(run))
        print(e)









