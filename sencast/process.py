#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Load Sencast Functions
from main import hindcast
from utils.auxil import load_params

dates = ["2021-07-20", "2021-07-25", "2021-07-30", "2021-08-04"]
sections = ["tshikapa_ldq_1", "tshikapa_ldq_2", "tshikapa_ldr_1", "tshikapa_ldr_2", "tshikapa_ldr_3", "tshikapa_ldr_4",
            "tshikapa_mds_1", "tshikapa_mds_2", "tshikapa_mds_3", "tshikapa_mdt_1", "tshikapa_mdt_2", "tshikapa_mdt_3",
            "tshikapa_mdt_4", "tshikapa_mdu_1", "tshikapa_mdu_2", "tshikapa_mdu_3"]

for section in sections:
    for date in dates:
        params, params_file = load_params("Tshikapa/Tshikapa_L1C_S2.ini")
        finalStart = "{}T00:00:00.000Z".format(date)
        finalEnd = "{}T23:59:59.999Z".format(date)
        params['General']['start'] = finalStart
        params['General']['end'] = finalEnd
        params['General']['wkt_name'] = section
        with open(params_file, "w") as f:
            params.write(f)
        hindcast(params_file, max_parallel_downloads=1, max_parallel_processors=1, max_parallel_adapters=1)
