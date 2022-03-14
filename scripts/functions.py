import netCDF4
import numpy as np
import geopandas as gp
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
from math import radians, cos, sin, asin, sqrt, floor
from shapely.geometry import LineString, Point, shape
from datetime import datetime


def log(text, indent=0):
    text = str(text).split(r"\n")
    for t in text:
        if t != "":
            out = datetime.now().strftime("%H:%M:%S.%f") + (" " * 3 * (indent + 1)) + t
            print(out)


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r


def nan_helper(y):
    return np.isnan(y), lambda z: z.nonzero()[0]


def smooth(x, window_len=11, window='hanning'):
    x = np.array(x)
    nans, y = nan_helper(x)
    x[nans] = np.interp(y(nans), y(~nans), x[~nans])
    s = np.r_[x[window_len - 1:0:-1], x, x[-2:-window_len - 1:-1]]
    if window == 'flat':  # moving average
        w = np.ones(window_len, 'd')
    else:
        w = eval('np.' + window + '(window_len)')
    y = np.convolve(w / w.sum(), s, mode='valid')
    return y


def get_pixel_values(path, matrix, group=0, max="None", min="None"):
    v = []
    for i in range(len(path)):
        if group > 0:
            values = matrix[path[i][0] - group:path[i][0] + group, path[i][1] - group:path[i][1] + group]
            if max != "None":
                values = values[values <= max]
            if min != "None":
                values = values[values >= min]
            if len(values) == 0:
                v.append(np.nan)
            else:
                v.append(np.nanmedian(values))
        else:
            v.append(matrix[path[i][0], path[i][1]])
    return v


def find_index_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def find_closest_cell(y_arr, x_arr, y, x):
    if len(y_arr.shape) == 1:
        idy = (np.abs(y_arr - y)).argmin()
        idx = (np.abs(x_arr - x)).argmin()
    else:
        dist = ((y_arr - y)**2 + (x_arr - x)**2)**2
        idy, idx = divmod(dist.argmin(), dist.shape[1])
    return idy, idx


def plot_graph(path, file_out, mask):
    fig, ax = plt.subplots(len(file_out), 1, figsize=(18, 15))
    fig.subplots_adjust(hspace=0.5)
    x = range(len(path))
    for i in range(len(file_out)):
        matrix, lat, lon, mask = parse_netcdf(file_out[i]["file"], file_out[i]["variable"], mask=mask)
        y = get_pixel_values(path, matrix)
        ax[i].plot(x, y)
        ax[i].set_xlabel("Pixel Length")
        ax[i].set_ylabel(file_out[i]["variable"])
    plt.show()


def plot_matrix(matrix, title=False, cmap='viridis'):
    fig, ax = plt.subplots(figsize=(18, 15))
    ax.imshow(matrix, interpolation='nearest', cmap=cmap)
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_matrix_select(matrix):
    fig, ax = plt.subplots(figsize=(18, 15))
    plot = ax.imshow(matrix, interpolation='nearest', picker=True)
    plt.title("Manually select any cells which you want to remove from water classification.")

    def onpick(verts):
        selection = Path(verts)
        extents = selection.get_extents()
        for i in range(floor(extents.y0), floor(extents.y1) + 1):
            for j in range(floor(extents.x0), floor(extents.x1) + 1):
                if selection.contains_point((j, i)):
                    matrix[i, j] = False
        plot.set_data(matrix)
        fig.canvas.draw()
        fig.canvas.flush_events()

    lasso = LassoSelector(ax, onpick)
    plt.tight_layout()
    plt.show()
    return matrix


def parse_netcdf(file, var, lat, lon):
    log("Parsing NetCDF: "+file)
    nc = netCDF4.Dataset(file, mode='r', format='NETCDF4_CLASSIC')
    lat = np.array(nc.variables[lat][:])
    lon = np.array(nc.variables[lon][:])
    matrix = np.array(nc.variables[var][:])
    nc.close()
    return matrix, lat, lon


def classify_water(matrix, threshold):
    log("Classify water pixels")
    binary = matrix.copy()
    if str(threshold).isnumeric():
        binary[binary < threshold] = np.nan
    binary[~np.isnan(binary)] = True
    binary[np.isnan(binary)] = False
    return binary.astype(bool)


def get_intersections(lines):
    point_intersections = []
    line_intersections = []
    lines_len = len(lines)
    for i in range(lines_len):
        for j in range(i+1, lines_len):
            l1, l2 = lines[i], lines[j]
            if l1.intersects(l2):
                intersection = l1.intersection(l2)
                if isinstance(intersection, LineString):
                    line_intersections.append(intersection)
                elif isinstance(intersection, Point):
                    point_intersections.append(intersection)
                else:
                    raise Exception('What happened?')


def inside_matrix(point, lat, lon):
    return np.min(lon) < point.x < np.max(lon) and np.min(lat) < point.y < np.max(lat)


def get_start_end(y1, x1, y2, x2, direction):
    if direction not in ["N", "S", "E", "W"]:
        raise ValueError("Unrecognised direction {} please choose from N, E, S, W.".format(direction))
    start, end = [y1, x1], [y2, x2]
    if direction == "N" and y2 > y1:
        start, end = [y2, x2], [y1, x1]
    elif direction == "S" and y2 < y1:
        start, end = [y2, x2], [y1, x1]
    elif direction == "E" and x2 < x1:
        start, end = [y2, x2], [y1, x1]
    elif direction == "W" and x2 > x1:
        start, end = [y2, x2], [y1, x1]
    return start, end


def classify_river(matrix, lat, lon, river, buffer=0.01, direction="N"):
    log("Classify water pixels as river or non river")
    log("Reading river data from : {}".format(river), indent=1)
    r = gp.read_file(river)
    if len(lat.shape) > 1:
        x, y = lon, lat
    else:
        x, y = np.meshgrid(lon, lat)
    x, y = x[matrix], y[matrix]
    points = np.vstack((x, y)).T
    l1 = LineString([(np.min(lon), np.max(lat)), (np.max(lon), np.max(lat)), (np.max(lon), np.min(lat)), (np.min(lon), np.min(lat)), (np.min(lon), np.max(lat))])
    l2 = r["geometry"][0]
    log("Calculating intersection between river and image boundary...", indent=1)
    it = l2.intersection(l1)
    if it.type == "GeometryCollection":
        s, e = l2.boundary
        y1, x1 = find_closest_cell(lat, lon, s.y, s.x)
        y2, x2 = find_closest_cell(lat, lon, e.y, e.x)
    if it.type == "Point":
        s, e = l2.boundary
        y1, x1 = find_closest_cell(lat, lon, it.y, it.x)
        if inside_matrix(s, lat, lon):
            y2, x2 = find_closest_cell(lat, lon, s.y, s.x)
        else:
            y2, x2 = find_closest_cell(lat, lon, e.y, e.x)
    elif it.type == "MultiPoint":
        y1, x1 = find_closest_cell(lat, lon, it[-2].y, it[-2].x)
        y2, x2 = find_closest_cell(lat, lon, it[-1].y, it[-1].x)

    start, end = get_start_end(y1, x1, y2, x2, direction)

    log("Located intersects: ({}, {}) and ({}, {})".format(y1, x1, y2, x2), indent=1)
    log("Creating buffer around river path...", indent=1)
    p = Path(r["geometry"][0].buffer(buffer).exterior.coords)
    log("Flagging {} grid points as inside or outside river buffer area...".format(len(points)), indent=1)
    grid = p.contains_points(points)
    matrix[matrix] = grid
    return matrix, start, end


