import os
import pandas as pd
from app.app import App
import pickle


class BaselineGenerator(App):

    def __init__(self, input_path):

        self.data = pd.read_pickle(input_path)

    BASELINE_DIR = 'baseline_collection'

    def generate_tracks(self, data):

        base_tracks = App.get_tracks(App, self.data)
        base_tracks.to_pickle(os.path.join(self.BASELINE_DIR, 'Tracks_baseline.pickle'))

    def generate_points(self):
        base_points = self.get_points(App, self.data)
        base_points.to_pickle(os.path.join(self.BASELINE_DIR, 'Points_baseline.pickle'))

    def generate_buffers(self):

        base_buffers = self.get_buffers(self.data)

        # Save polygon to disc
        with open('./Buffers_baseline', "wb") as poly_file:
            pickle.dump(base_buffers, poly_file, pickle.HIGHEST_PROTOCOL)

    def generate_roads(self, buffers):

        base_roads = self.get_roads(buffers)
        base_roads.to_pickle(os.path.join(self.BASELINE_DIR, 'Roads_baseline.pickle'))

    def generate_crossing_points(self, roads):

        base_crossings = App.find_crossings(roads, self.get_tracks(App, self.data))
        base_crossings.to_pickle(os.path.join(self.BASELINE_DIR, 'Crossings_baseline.pickle'))

    def generate_output(self, data, crossings):

        new_baseline = self.insertCrossings(self, self.get_points(self, self.data), crossings, data)
        pd.to_pickle(new_baseline, os.path.join(self.BASELINE_DIR, 'Output_baseline.pickle'))

    def generate_map(self, roads, crossings):
        m = self.createMap(self.get_tracks(self, self.data), roads, crossings)
        m.save(os.path.join(self.BASELINE_DIR, 'Map_baseline.html'))
    # Need to refactor these before using in baselines


    # App.saveGeopackage(App.get_tracks(data))

BASELINE_INPUT = 'input1.pickle'



generate = BaselineGenerator(BASELINE_INPUT)