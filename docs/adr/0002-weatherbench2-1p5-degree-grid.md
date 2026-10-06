# All weather at WeatherBench 2's 1.5° grid

Every forecast source and the truth are read at 1.5° (240×121), not 0.25°. WeatherBench 2 stores its 0.25° data as one global field per chunk, so even a North Atlantic box costs about 30 MB per variable and step; 1.5° is also WeatherBench 2's headline evaluation grid, so the comparison between sources is fair. The cost is that the jet core is under-resolved, which the report states openly.
