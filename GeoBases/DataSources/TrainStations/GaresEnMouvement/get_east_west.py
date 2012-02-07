#!/usr/bin/python

import sys, math
import Levenshtein as L

def parse_city_file(input_file):
  f = open(input_file, 'r')
  cities, lat_by_city, lon_by_city = set(), {}, {}
  for line in f:
    fields = line.rstrip('\n').split('\t')
    if len(fields) < 10: continue
    country = fields[8]
    if country != "FR": continue
    city_name = fields[2]
    lat = float(fields[4])
    lon = float(fields[5])
    cities.add(city_name)
    lat_by_city[city_name] = lat
    lon_by_city[city_name] = lon
  f.close()
  return cities, lat_by_city, lon_by_city

def parse_station_file(input_file):
  f = open(input_file, 'r')
  stations, name_by_station, lat_by_station, lon_by_station = set(), {}, {}, {}
  for line in f:
    fields = line.rstrip('\n').split('^')
    if len(fields) < 4: continue
    station = fields[0]
    stations.add(station)
    name_by_station[station] = fields[1]
    lat_by_station[station] = float(fields[2])
    lon_by_station[station] = float(fields[3])
  f.close()
  return stations, name_by_station, lat_by_station, lon_by_station

def great_circle_distance(lat1, lon1, lat2, lon2, degrees=True):
  if degrees:
    lat1, lon1, lat2, lon2 = lat1/180.0*math.pi, lon1/180.0*math.pi, lat2/180.0*math.pi, lon2/180.0*math.pi
  return 12756.0*math.asin(math.sqrt((math.sin((lat2-lat1)/2.0))**2.0+math.cos(lat1)*math.cos(lat2)*(math.sin((lon2-lon1)/2.0))**2.0))

def match_city_station(station_name, station_lat, station_lon, cities, lat_by_city, lon_by_city):
  flag_match_name = False
  for city in cities:
    if L.ratio(city, station_name) > 0.8:
      flag_match_name = True
      city_lon = lon_by_city[city]
      city_lat = lat_by_city[city]
      if great_circle_distance(city_lat, city_lon, station_lat, station_lon, degrees=True) < 50: return city, flag_match_name, 1
      if great_circle_distance(city_lat, city_lon, station_lat, -station_lon, degrees=True) < 50: return city, flag_match_name, -1
  return '', flag_match_name, 0

def main():
  city_file = 'cities1000.txt'
  station_file = 'station_code_name_lat_lon.txt'
  cities, lat_by_city, lon_by_city = parse_city_file(city_file)
  stations, name_by_station, lat_by_station, lon_by_station = parse_station_file(station_file)
  city_by_station = {}

  for station in stations:
    city, flag_match, lon_mult = match_city_station(name_by_station[station], lat_by_station[station], lon_by_station[station], cities, lat_by_city, lon_by_city)
    city_by_station[station] = city
    print '^'.join([station, name_by_station[station], city, str(flag_match), str(lon_mult), str(lon_mult*abs(lon_by_station[station]))])

if __name__ == "__main__":
  main()
