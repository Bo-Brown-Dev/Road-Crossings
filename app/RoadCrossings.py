from keplergl import KeplerGl
from movingpandas import TrajectoryCollection, Trajectory
from geopandas import GeoDataFrame, GeoSeries
import pandas as pd
import geopandas as gpd
import movingpandas as mpd
import osmnx as ox
import shapely

import tracemalloc
import logging
import json
import os

from app.Crossings_Kepler import extract_line_coordinates





def get_tracks(data) -> GeoDataFrame:
    """
    A generator used to retrieve LineString GeoDataFrame
    from TrajectoryCollection in a memory efficient way

    :param data: -- A MovingPandas TrajectoryCollection
    :return: -- iterable generator of GeoDataFrames with geometry of type LineString
    """

    dtype_conversion = {'prev_t': str, 't': str, 'timestamps': str}

    logging.info('getting tracks')
    for track in data:
        yield track.to_line_gdf()[
        ['timestamps',
         'trackId',
         't',
         'prev_t',
         'geometry'
         ]
        ].astype(
        dtype_conversion
        ).set_crs(track.crs)

def get_points(data) -> GeoDataFrame:
    """
     A generator used to retrieve Point GeoDataFrame
    from TrajectoryCollection in a memory efficient way

    :param data: -- A MovingPandas TrajectoryCollection
    :return: -- iterable generator of GeoDataFrames with geometry of type Point

    """

    logging.info('getting points')
    for track in data:
        yield track.to_point_gdf()[
        ['timestamps',
         'trackId',
         'geometry'
         ]
        ].set_crs(data.trajectories[0].crs)

def get_buffers(data: TrajectoryCollection):
    """
    Function returns a generator is used to generate minimum concave polygons in a memory efficient way

    :param data: -- A  movingpandas TrajectoryCollection
    :return: -- Shapely Polygon or MultiPolygon
    """
    logging.info('---- Getting Convex Hull ----')
    for track in data:
        logging.info('getting track as line gdf')
        line = track.to_line_gdf()
        logging.info('collecting line geometry')
        line = GeoSeries(gpd.tools.collect(line.geometry), crs=4326)

        logging.info('getting convex hull polygon')
        hull = line.concave_hull()[0]
        logging.info('Got buffer')
        yield hull



def get_roads(buffers: shapely.Polygon):
    """
    Queries roads from OpenStreetMap via Overpass using OSMnx

    :param buffers: -- Polygon used to narrow the query
    :return: -- A GeoDataFrame of Roads
    """
    logging.info('---- Querying roads within buffer ----')

    graph = ox.graph_from_polygon(
        buffers,
        network_type='all_private',  # includes all roads, private or not
        truncate_by_edge=True,  # includes roads that are not fully contained in geometry
        retain_all=True,
        clean_periphery=True,
        simplify=False)  # curves of roads and self-intersections will be nodes, but
        # we don't include nodes in our map, so the function is to reduce length of lines in resulting set of roads

    logging.info('converting graph to GeoDataFrame')

    roads = ox.utils_graph.graph_to_gdfs(graph, nodes=False)

    logging.info('Roads Retrieved')
    return roads

def find_crossings(roads, tracks):
    """
    Finds locations where MovingPandas Trajectory intersects with a GeoDataFrame of roads

    :param roads: -- A GeoDataFrame of roads, geometry should be LineString
    :param tracks: -- The result of a MovingPandas Trajectory to_line_gdf()
    :return:  -- A GeoDataFrame of points where animal paths crossed the road
    """

    common_crs = 4326
    logging.info('---- Finding Crossing Points ----')
    logging.info('\t Overlaying Geometries')


    crossings = gpd.overlay(
        roads.to_crs(crs = common_crs),
        tracks.to_crs(crs = common_crs),
        how='intersection',
        keep_geom_type=False
    )

    logging.info('\t Extracting Crossing Points')

    crossings.geometry = crossings.geometry.apply(
        lambda x: shapely.geometry.MultiPoint(list(x.coords)))
    crossings = crossings.explode(index_parts=True).drop_duplicates(subset=['t', 'osmid',])

    logging.info('\t Calculating timestamp midpoints')

    crossings['crossing_point'] = True
    half_timestamp_range = (
            (pd.to_datetime(crossings['t']) - pd.to_datetime(crossings['prev_t'])) / 2
    )
    crossings['mid_t'] = (pd.to_datetime(crossings['prev_t']) + half_timestamp_range).astype('datetime64[ns]')
    return crossings

def create_map(collection: TrajectoryCollection, roads: GeoDataFrame, crossings: GeoDataFrame) -> KeplerGl:
    """
    Creates an interactive map to visualize the animal paths, roads, and crossings

    :param collection: -- the source TrajectoryCollection
    :param roads: -- A GeoDataFrame of roads, geometry should be LineString
    :param crossings: -- A GeoDataFrame of points where animal paths crossed the road
    :return: -- A keplergl map object
    """

    crossings['longitude'] = crossings.geometry.x
    crossings['latitude'] = crossings.geometry.y

    # converting datetime to string, prevents json error
    dtype_conversion = {'prev_t': str, 't': str, 'timestamps': str}

    local_app_files_root = os.environ.get('LOCAL_APP_FILES_DIR', './resources/local_app_files')
    with open(os.path.join(local_app_files_root, 'provided-app-files/kepler_config.json'), 'r') as kepler_config_json:
        kepler_config = json.load(kepler_config_json)

    logging.info('---- Creating Map ----')
    m = KeplerGl(
        data = {
            'Tracks': extract_line_coordinates(collection.to_line_gdf().astype(dtype_conversion)),
            'Roads': roads,
            'Crossing_Points': crossings.astype(dtype_conversion).astype({'mid_t': str})
            },
        )

    m.config = kepler_config

    return m



def insert_crossings(track_points: GeoDataFrame, crossings: GeoDataFrame, track: Trajectory) -> Trajectory:

    common_crs = 4326

    logging.info('---- Inserting Crossing Points to result ----')

    track_points['crossing_point'] = False

    track_points = track_points.to_crs(common_crs)
    crossings = crossings.to_crs(common_crs)

    new_points = pd.concat([track_points, crossings])

    new_points['merged_t'] = new_points['mid_t']

    new_points['merged_t'] = new_points['merged_t'].fillna(new_points.index.to_series()).astype('datetime64[ns]')

    new_points = new_points.sort_values(by=['trackId', 'merged_t'])

    new_points.merge(track.to_point_gdf(), how='left', left_on=['trackId', 'merged_t'], right_on=['trackId', 'timestamps'])

    trajectory_with_crossings = mpd.Trajectory(df=new_points, traj_id=track.id, t='merged_t')


    logging.info('inserted crossing points')
    return trajectory_with_crossings

def memory_check(checkpoint: str):

    size, peak = tracemalloc.get_traced_memory()
    logging.debug('%s Checkpoint ---- Memory Stats:', checkpoint)
    logging.debug('\t %s size: %s Mb', checkpoint, size / 1000000)
    logging.debug('\t %s peak: %s Mb', checkpoint, peak / 1000000)
