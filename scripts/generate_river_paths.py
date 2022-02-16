import os
import sys
import numpy as np
sys.path.append("../river-trace")
from rivertrace.main import trace
from rivertrace.functions import log, parse_netcdf, plot_matrix, classify_river, plot_matrix_select

folder_t = "/media/jamesrunnalls/JamesSSD/Eawag/EawagRS/Sencast/build/DIAS/output_data/Tshikapa_L1C_S2_tshikapa_{}_{}_{}_{}/L2ACOLITE"
out_folder = "../data/paths"
water_parameter = "TUR_Dogliotti2015"
rough_river = "../data/river.geojson"
direction = "N"
buffer = 0.01
plot = True

# inputs = [["ldq", 2], ["ldr", 4], ["mds", 3], ["mdt", 4], ["mdu", 3]]
inputs = [["mdu", 4], ["mdv", 1], ["mev", 1], ["mdv", 2], ["mdv", 3], ["mda", 1]]
dates = ["2021-07-20", "2021-07-25", "2021-07-30", "2021-08-04"]

runs = []
for i in inputs:
    for s in range(1, i[1] + 1):
        for d in dates:
            runs.append({"d": d, "s": s, "i": i[0]})

for run in runs:
    try:
        folder = folder_t.format(run["i"], run["s"], run["d"], run["d"])
        files = list(filter(lambda file: "L2ACOLITE" in file, os.listdir(folder)))
        out_file_name = "path_" + "_".join([str(run["i"]), str(run["s"]), str(run["d"].split("-")[-1])]) + ".json"
        if os.path.isfile(os.path.join(out_folder, out_file_name)):
            log("Skipping path {} as it already exists".format(out_file_name))
            continue
        for file in files:
            log("Reading data from file {}".format(file))
            matrix, lat, lon = parse_netcdf(os.path.join(folder, file), water_parameter, "lat", "lon")
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
            boolean, start, end = classify_river(boolean, lat, lon, rough_river, buffer=buffer, direction=direction)
            if plot:
                plot_matrix(boolean, title="River classification plot")

            log("Manually remove any incorrectly classified water pixels")
            boolean = plot_matrix_select(boolean)

            path = trace(boolean, start, end, save_path=os.path.join(out_folder, out_file_name))

            if plot:
                output = boolean.copy()
                output = output.astype(float)
                for p in path:
                    output[p[0], p[1]] = 2
                output[output == 0] = np.nan
                plot_matrix(output, title="River classification plot")
    except Exception as e:
        print("Failed on run: ".format(run))
        print(e)








