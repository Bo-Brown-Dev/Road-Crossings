import osmnx._errors

from sdk.moveapps_spec import hook_impl
from movingpandas import TrajectoryCollection, Trajectory
from app.RoadCrossings import get_roads, get_points, get_tracks, get_buffers, create_map
from app.RoadCrossings import find_crossings, insert_crossings, memory_check
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
import osmnx as ox
import logging


class App(object):

    def __init__(self, moveapps_io,):
        self.moveapps_io = moveapps_io

        # artifact paths:
        self.csv_path = self.moveapps_io.create_artifacts_file('crossing_points.csv')
        self.gpkg_path = self.moveapps_io.create_artifacts_file('crossings.gpkg')
        self.map_path = self.moveapps_io.create_artifacts_file('crossings_map.html')

    common_crs = 4326
    proj_crs = 3857


    @hook_impl
    def execute(self, data: TrajectoryCollection, config: dict) -> TrajectoryCollection:
        """Your app code goes here"""

        ox.settings.use_cache = False
        ox.settings.log_console = True

        buffers = get_buffers(data)
        roads = get_roads(buffers)

        tracks_gen = get_tracks(data)

        track_points = get_points(data)

        crossings = gpd.GeoDataFrame()

        new_trajectory_list = []


        for track in data:

            tracks = next(tracks_gen)

            traj_crossings = find_crossings(roads, tracks)

            traj_crossings.to_csv(self.csv_path, mode='a')

            crossings = pd.concat([crossings, traj_crossings])

            new_trajectory_list.append(
                insert_crossings(next(track_points), traj_crossings, track)
            )
            # memory_check('each loop')

        # memory_check('final loop')

        m = create_map(
                data,
                roads,
                crossings)

        m.save_to_html(data = None, file_name=self.map_path, center_map=True)

        # memory_check('map')

        self.save_geopackage(
            data,
            roads,
            crossings)

        return TrajectoryCollection(new_trajectory_list)

    def save_geopackage(self, collection: TrajectoryCollection, roads: GeoDataFrame, crossings: GeoDataFrame) -> None:
        logging.info('Writing to Geopackage')

        dtype_conversion = {'prev_t': str, 't': str, }
        traj_id_col = collection.get_traj_id_col()
        tracks = collection.to_line_gdf()[
            [traj_id_col,
             't',
             'prev_t',
             'geometry'
             ]
        ].astype(
            dtype_conversion
        ).set_crs(collection.trajectories[0].crs)

        crossings.to_file(self.gpkg_path
            , layer='Intersection_Points'
            , driver='GPKG'
        )

        roads.to_file(
            self.gpkg_path
            , layer='roads'
            , driver='GPKG'
        )

        tracks.to_file(
            self.gpkg_path
            , layer='track_lines'
            , driver='GPKG'
        )





