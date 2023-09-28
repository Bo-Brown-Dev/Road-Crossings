import time

from movingpandas import TrajectoryCollection
from geopandas import GeoDataFrame
import pandas as pd


def to_kepler_trip(data: TrajectoryCollection):
    # Still in development
    feature_list = []
    for traj in data.trajectories:
        df = traj.df

        coordinate_list = []
        animal = df['animalName'][0]
        for index, row in df.iterrows():
            coords = [row['geometry'].x, row['geometry'].y, 0, time.mktime(row['timestamps'].timetuple())]
            coordinate_list.append(coords)

        geometryString = {
            'type': 'LineString',
            'coordinates': coordinate_list,
        }
        feat = {
                'type': 'Fureate',
                'properties': {'animalName': animal},
                'geometry': {
                    'type': 'LineString',
                    'coordinates': coordinate_list,
                    }
                }
        feature_list.append(feat)
        feature_collection = {
            'type': 'FeatureCollection',
            'features':
                feature_list

        }
        return feature_collection

def extract_line_coordinates(data: GeoDataFrame):
    """

    :param data: Accepts the GeoDataFrame result of movingpandas.to_line_gdf()
    :return: Returns the GeoDataFrame concatenated to include the starting x, y, and z as well as the destination x, y, z

    """
    coordinate_columns = data.geometry.get_coordinates(include_z=True, index_parts=True).unstack(sort=False)
    coordinate_columns.columns = ['source_x', 'target_x', 'source_y', 'target_y', 'source_z', 'target_z']

    #coordinate_columns = coordinate_columns

    return pd.concat([
        data,
        coordinate_columns[['source_x', 'source_y', 'source_z', 'target_x', 'target_y', 'target_z']]
    ], axis='columns')