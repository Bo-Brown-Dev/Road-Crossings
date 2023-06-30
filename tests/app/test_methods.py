import unittest
from app.app import App
from sdk.moveapps_io import MoveAppsIo
from tests.config.definitions import ROOT_DIR
from app.RoadCrossings import get_points, get_tracks, get_buffers, get_roads
from app.RoadCrossings import find_crossings, insert_crossings, create_map
from shapely.testing import assert_geometries_equal
from pandas.testing import assert_frame_equal
from shapely.geometry import Polygon
import os
import pandas as pd
import osmnx as ox
from folium import Map


class TestApp(unittest.TestCase):

    def setUp(self) -> None:
        os.environ['APP_ARTIFACTS_DIR'] = os.path.join(ROOT_DIR, r'tests/resources/output')
        self.sut = App(moveapps_io=MoveAppsIo())

        self.case_input = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/input1.pickle'
                         ))


        self.expected_points = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/points_gabs_23.pickle'
                         )
        )

        self.expected_tracks = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/tracks_gabs_23.pickle'
                         )
        )

        ox.settings.use_cache = False
        self.expected_buffer = pd.read_pickle(
        os.path.join(ROOT_DIR, r'tests/resources/local_app_files/provided_only/provided-app-files/buffers_gabs_23.pickle'
                   ))

        self.expected_roads = pd.read_pickle(
            os.path.join(ROOT_DIR, r'tests/resources/local_app_files/provided_only/provided-app-files/roads_gabs_23.pickle')
        )

        self.expected_crossings = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/crossings_gabs_23.pickle'

        ))

        self.given_roads = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/roads_gabs_23.pickle'
                         )
        )
        self.expected_output = pd.read_pickle(
            os.path.join(ROOT_DIR,
                         r'tests/resources/local_app_files/provided_only/provided-app-files/TracksPostInsert_gabs_23.pickle'
                         )
        )

    """
    Because the alternate method for acquiring roads uses a different buffer method, using the same buffer
    and checking for an exact match would result in a brittle test that would be subject to a change in a node or edge
    at the edge of the buffer. 

    Instead, we query our baseline roads by a larger buffer and check that our function is contained by the set.

    """

    def test_getTracks(self):
        tracksGen = get_tracks(self.case_input)
        testTracks = next(tracksGen)

        assert_frame_equal(testTracks, self.expected_tracks)



    def test_getPoints(self):
        pointsGen = get_points(self.case_input)
        testPoints = next(pointsGen)

        assert_frame_equal(testPoints, self.expected_points)


    def test_getBuffers(self):
        buffersGen = get_buffers(self.case_input)
        testBuffers = next(buffersGen)

        self.assertIsInstance(testBuffers, Polygon)
        assert_geometries_equal(testBuffers, self.expected_buffer)

    def test_getRoads(self):
        buffers = self.expected_buffer
        testRoads = get_roads(buffers)

        assert_frame_equal(testRoads, self.expected_roads)


    def test_getCrossingPoints(self):
        testTracks = self.expected_tracks
        testCrossings = find_crossings(self.expected_roads, testTracks)

        assert_frame_equal(testCrossings, self.expected_crossings)

    def test_insertCrossing(self):
        testOutput = insert_crossings(self.expected_points, self.expected_crossings, self.case_input.trajectories[0])

        assert_frame_equal(testOutput.to_point_gdf(), self.expected_output.to_point_gdf())




    def test_drawMap(self):
        roads = self.expected_roads
        crossings = self.expected_crossings
        data = self.case_input
        m = create_map(data, roads, crossings)

        self.assertIsInstance(m, Map)


    def test_writeGeopackage(self):
        self.skipTest('Geopackage manually tested but build-ready unit-test is still in development')
        pass

if __name__ == '__main__':
    unittest.main()
