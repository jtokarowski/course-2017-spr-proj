import dml
import prov.model
import datetime
import networkx as nx
import uuid
import math
import sys

class shortestMbtaPath(dml.Algorithm):
    contributor = 'asafer_asambors_maxzm_vivyee'
    reads = ['asafer_asambors_maxzm_vivyee.health_obesity', 'asafer_asambors_maxzm_vivyee.mbta_routes']
    writes = ['asafer_asambors_maxzm_vivyee.health_obesity']

    @staticmethod
    def project(R, p, G):
        return [p(t, G) for t in R]

    @staticmethod
    def get_closest_path(info, G):
        obesity_stops = [ stop['stop_id'] for stop in info['obesity_locations']['stops'] if stop['mode'] == 'Subway' ]
        healthy_stops = [ stop['stop_id'] for stop in info['healthy_locations']['stops'] if stop['mode'] == 'Subway' ]
        
        # print('obesity stops length:', len(obesity_stops), 'healthy stops length:', len(obesity_stops))

        min_times = []
        for o_stop in obesity_stops:
            for h_stop in healthy_stops:
                try:
                    time = nx.dijkstra_path_length(G, o_stop, h_stop)
                    min_times.append(time)
                except nx.NetworkXNoPath:
                    # print('no path found')
                    pass

        if len(min_times) == 0:
            info['min_travel_time'] = sys.maxsize
        else:
            info['min_travel_time'] = min(min_times)
            # print(info)
        # print(min_times)
        # print('info is\n' + str(info))
        return info


    @staticmethod
    def calculate_distance(lat_1, lon_1, lat_2, lon_2):
        # formula from: http://andrew.hedges.name/experiments/haversine/
        # used R = 3961 miles
        lat_2 = math.radians(lat_2)
        lat_1 = math.radians(lat_1)
        lon_1 = math.radians(lon_1)
        lon_2 = math.radians(lon_2)

        R = 3961.0
        dlon = lon_1 - lon_2
        dlat = lat_1 - lat_2
        a = math.sin(dlat/2)**2 + (math.cos(lat_2) * math.cos(lat_1) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c
        return d

    @staticmethod
    def execute(trial = False):
        startTime = datetime.datetime.now()

        #set up the datebase connection
        client = dml.pymongo.MongoClient()
        repo = client.repo
        repo.authenticate('asafer_asambors_maxzm_vivyee','asafer_asambors_maxzm_vivyee')
        
        mbta_routes = repo['asafer_asambors_maxzm_vivyee.mbta_routes'].find()
        health_obesity = repo['asafer_asambors_maxzm_vivyee.health_obesity'].find()

        G = nx.DiGraph()

        transfers = {
            'Park Street': [],
            'Boyleston': [],
            'Government Center': [],
            'Haymarket': [],
            'North Station': [],
            'State Street': [],
            'Downtown Crossing': [],
            'Chinatown': [],
            'Tufts Medical Center': [],
            'South Station': []
        }

        # Add edges, will create nodes u and v if not already in the graph
        # weight = distance / mpm = total time it takes from point 1 to 2
        for route in mbta_routes:
            if route['mode'] == 'Subway':
                mpm = 30.0 / 60.0          # miles per minute

                for direction in route['path']['direction']:
                    prev_lat = 0
                    prev_lon = 0
                    prev_stop = ''
                    # print(direction['stop'])

                    for i in range(len(direction['stop'])):
                        stop = direction['stop'][i]

                        # find all transfer stations
                        for key in transfers.keys():
                            if key == stop['stop_name'][:len(key)]:
                                # add edge for transfer
                                for t in transfers[key]:
                                    G.add_edge(t, stop['stop_id'], weight=10)
                                    G.add_edge(stop['stop_id'], t, weight=10)

                                transfers[key].append(stop['stop_id'])

                        if i > 0:
                            d = shortestMbtaPath.calculate_distance(prev_lat, prev_lon, eval(stop['stop_lat']), eval(stop['stop_lon']))
                            w = d / mpm
                            G.add_edge(prev_stop, stop['stop_id'], weight=w)
                            G.add_edge(stop['stop_id'], prev_stop, weight=w)

                            # if w == 0:
                            #     print(stop['stop_id'], 'to', prev_stop)
                            # print('current stop:', stop['stop_id'], '; last_stop:', prev_stop, '; weight:', w)
                        prev_lon = eval(stop['stop_lon'])
                        prev_lat = eval(stop['stop_lat'])
                        prev_stop = stop['stop_id']
        
        # project

        health_obesity_times = shortestMbtaPath.project(health_obesity, shortestMbtaPath.get_closest_path, G)
        # nx.dijkstra_path_length(G, source, target)
        repo.dropCollection('asafer_asambors_maxzm_vivyee.health_obesity')
        repo.createCollection('asafer_asambors_maxzm_vivyee.health_obesity')

        repo['asafer_asambors_maxzm_vivyee.health_obesity'].insert_many(health_obesity_times)
        repo['asafer_asambors_maxzm_vivyee.health_obesity'].metadata({'complete': True})

        print('all uploaded')

        endTime = datetime.datetime.now

        return {"start":startTime, "end":endTime}

    @staticmethod
    def provenance(doc = prov.model.ProvDocument(), startTime = None, endTime = None):
        # Set up the database connection.
        client = dml.pymongo.MongoClient()
        repo = client.repo
        repo.authenticate('asafer_asambors_maxzm_vivyee', 'asafer_asambors_maxzm_vivyee')
        doc.add_namespace('alg', 'http://datamechanics.io/algorithm/') # The scripts are in <folder>#<filename> format.
        doc.add_namespace('dat', 'http://datamechanics.io/data/') # The data sets are in <user>#<collection> format.
        doc.add_namespace('ont', 'http://datamechanics.io/ontology#') # 'Extension', 'DataResource', 'DataSet', 'Retrieval', 'Query', or 'Computation'.
        doc.add_namespace('log', 'http://datamechanics.io/log/') # The event log.

        repo.logout()

        return doc


shortestMbtaPath.execute()

