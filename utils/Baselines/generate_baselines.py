import os
import pandas as pd
from app.app import App
import pickle
from app.RoadCrossings import get_roads, get_buffers, get_points, get_tracks, find_crossings, create_map, insert_crossings


class BaselineGenerator(App):

    def __init__(self, input_path):

        self.data = pd.read_pickle(input_path)

    BASELINE_DIR = 'baseline_collection'

    def generate_tracks(self):

        base_tracks = get_tracks(self.data)
        return next(base_tracks)

    def generate_points(self):
        base_points = get_points(self.data)
        return next(base_points)

    def generate_buffers(self):

        base_buffers = get_buffers(self.data)


        return next(base_buffers)

    def generate_roads(self, buffers):

        base_roads = get_roads(buffers)
        base_roads.to_pickle(os.path.join(self.BASELINE_DIR, 'Roads_baseline.pickle'))
        return base_roads

    def generate_crossing_points(self, roads):

        base_tracks = get_tracks(self.data)
        base_crossings = find_crossings(roads, next(base_tracks))
        base_crossings.to_pickle(os.path.join(self.BASELINE_DIR, 'Crossings_baseline.pickle'))
        return base_crossings

    def generate_output(self, data, crossings):

        points = get_points(self.data)
        new_baseline = insert_crossings(next(points), crossings, data)
        pd.to_pickle(new_baseline, os.path.join(self.BASELINE_DIR, 'Output_baseline.pickle'))

    def generate_map(self, roads, crossings):
        m = create_map(self.data, roads, crossings)
        m.save(os.path.join(self.BASELINE_DIR, 'Map_baseline.html'))



BASELINE_INPUT = 'input1.pickle'



baseline = BaselineGenerator(BASELINE_INPUT)

points = baseline.generate_points()
points.to_pickle(os.path.join(baseline.BASELINE_DIR, 'Points_baseline.pickle'))

tracks = baseline.generate_tracks()
tracks.to_pickle(os.path.join(baseline.BASELINE_DIR, 'Tracks_baseline.pickle'))

buffers = baseline.generate_buffers()

# Save polygon to disc
with open('./baseline_collection/Buffers_baseline.pickle', "wb") as poly_file:
    pickle.dump(buffers, poly_file, pickle.HIGHEST_PROTOCOL)

roads = baseline.generate_roads(buffers)
crossings = baseline.generate_crossing_points(roads)
baseline.generate_output(baseline.data.trajectories[0], crossings, )
baseline.generate_map(roads, crossings)

