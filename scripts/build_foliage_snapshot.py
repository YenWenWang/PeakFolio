#!/usr/bin/env python3
"""
peakfolio. — Seasonal & Historical (1950–2025) Weather & Phenology Snapshot Builder
===================================================================================
Supports two modes for your GitHub repository:

1. DAILY SEASONAL MODE (Default · July 1 – November 30):
   Fetches real-time 14-day trailing chilling observations + 16-day GFS/HRRR forecasts
   across all 106 USFS FIA forestry stations and writes:
     - ./foliage-forecast-snapshot.json (loaded by index.html for the current season)
     - ./data/archive/YYYY/foliage-snapshot-YYYY-MM-DD.json (daily seasonal archive)

2. HISTORICAL ARCHIVE BACKFILL MODE (--backfill-history START_YEAR END_YEAR):
   Pulls 1950–2025 historical autumn (Sep 1 – Nov 30) daily ERA5 reanalysis data
   across all 106 stations and stores static JSON copies directly in your GitHub repo:
     - ./data/historical/foliage-history-YYYY.json (for each year 1950..2025)
   Once committed to GitHub, index.html loads historical years directly from your own
   repository (`./data/historical/foliage-history-YYYY.json`) instead of calling
   external APIs from the visitor's browser.
"""

import argparse
import datetime
import json
import os
import sys
import time
import urllib.request
from typing import Any, Dict, List

# All 106 Primary USFS FIA Forestry & NOAA GHCND Co-Located Stations
US_FOLIAGE_STATIONS: List[Dict[str, Any]] = [
  {
    "id": "stowe-vt",
    "name": "Stowe & Green Mountains, VT",
    "state": "VT",
    "ecoregion": "Northern Hardwoods",
    "lat": 44.47,
    "lon": -72.68,
    "elevFt": 1550,
    "peakDoyBase": 284
  },
  {
    "id": "white-mtns-nh",
    "name": "Kancamagus Hwy (White Mtns), NH",
    "state": "NH",
    "ecoregion": "New England Montane",
    "lat": 44.03,
    "lon": -71.38,
    "elevFt": 2100,
    "peakDoyBase": 282
  },
  {
    "id": "acadia-me",
    "name": "Acadia & Penobscot Bay, ME",
    "state": "ME",
    "ecoregion": "Acadian Coastal Forest",
    "lat": 44.34,
    "lon": -68.27,
    "elevFt": 650,
    "peakDoyBase": 287
  },
  {
    "id": "adirondacks-ny",
    "name": "Lake Placid & Adirondacks, NY",
    "state": "NY",
    "ecoregion": "Adirondack High Peaks",
    "lat": 44.28,
    "lon": -73.98,
    "elevFt": 1950,
    "peakDoyBase": 280
  },
  {
    "id": "berkshires-ma",
    "name": "The Berkshires & Litchfield Hills, MA/CT",
    "state": "MA",
    "ecoregion": "Southern New England Transition",
    "lat": 42.31,
    "lon": -73.25,
    "elevFt": 1200,
    "peakDoyBase": 291
  },
  {
    "id": "poconos-pa",
    "name": "Pocono Mountains & Alleghenies, PA",
    "state": "PA",
    "ecoregion": "Allegheny Plateau",
    "lat": 41.12,
    "lon": -75.35,
    "elevFt": 1650,
    "peakDoyBase": 293
  },
  {
    "id": "shenandoah-va",
    "name": "Shenandoah & Blue Ridge Pkwy, VA",
    "state": "VA",
    "ecoregion": "Central Appalachian Mixed",
    "lat": 38.52,
    "lon": -78.43,
    "elevFt": 2600,
    "peakDoyBase": 297
  },
  {
    "id": "smokies-nc-tn",
    "name": "Great Smoky Mountains & Blue Ridge, NC/TN",
    "state": "NC",
    "ecoregion": "Southern Appalachian Cove Forest",
    "lat": 35.61,
    "lon": -83.48,
    "elevFt": 3200,
    "peakDoyBase": 301
  },
  {
    "id": "up-michigan",
    "name": "Porcupine Mtns & Upper Peninsula, MI",
    "state": "MI",
    "ecoregion": "Laurentian Mixed Forest",
    "lat": 46.75,
    "lon": -89.78,
    "elevFt": 1350,
    "peakDoyBase": 279
  },
  {
    "id": "north-shore-mn",
    "name": "North Shore Superior & Boundary Waters, MN",
    "state": "MN",
    "ecoregion": "Boreal Hardwood Transition",
    "lat": 47.62,
    "lon": -90.85,
    "elevFt": 1400,
    "peakDoyBase": 274
  },
  {
    "id": "door-county-wi",
    "name": "Door County & Driftless Area, WI",
    "state": "WI",
    "ecoregion": "Great Lakes Hardwood",
    "lat": 45.05,
    "lon": -87.15,
    "elevFt": 780,
    "peakDoyBase": 288
  },
  {
    "id": "hocking-hills-oh",
    "name": "Hocking Hills & Brown County, OH/IN",
    "state": "OH",
    "ecoregion": "Central Hardwood Region",
    "lat": 39.43,
    "lon": -82.53,
    "elevFt": 980,
    "peakDoyBase": 296
  },
  {
    "id": "ozarks-ar",
    "name": "Ozark Highlands & Buffalo River, AR/MO",
    "state": "AR",
    "ecoregion": "Ozark Oak-Hickory-Gum",
    "lat": 36.04,
    "lon": -93.18,
    "elevFt": 1450,
    "peakDoyBase": 306
  },
  {
    "id": "caddo-lake-tx-la",
    "name": "Caddo Lake & Atchafalaya Basin, TX/LA",
    "state": "LA",
    "ecoregion": "Southern Bottomland Cypress-Gum",
    "lat": 32.68,
    "lon": -94.12,
    "elevFt": 180,
    "peakDoyBase": 320
  },
  {
    "id": "lost-maples-tx",
    "name": "Lost Maples & Hill Country, TX",
    "state": "TX",
    "ecoregion": "Edwards Plateau Canyons",
    "lat": 29.81,
    "lon": -99.57,
    "elevFt": 1900,
    "peakDoyBase": 318
  },
  {
    "id": "maroon-bells-co",
    "name": "Maroon Bells & Kebler Pass (Aspen), CO",
    "state": "CO",
    "ecoregion": "Southern Rocky Mountain Subalpine",
    "lat": 39.07,
    "lon": -106.94,
    "elevFt": 9500,
    "peakDoyBase": 273
  },
  {
    "id": "wasatch-ut",
    "name": "Wasatch Back & Logan Canyon, UT",
    "state": "UT",
    "ecoregion": "Wasatch Montane Maple-Aspen",
    "lat": 40.65,
    "lon": -111.58,
    "elevFt": 7400,
    "peakDoyBase": 277
  },
  {
    "id": "glacier-mt",
    "name": "Glacier NP & Seeley-Swan Valley, MT",
    "state": "MT",
    "ecoregion": "Northern Rockies Larch-Conifer",
    "lat": 48.51,
    "lon": -113.99,
    "elevFt": 4200,
    "peakDoyBase": 286
  },
  {
    "id": "enchantments-wa",
    "name": "The Enchantments & North Cascades, WA",
    "state": "WA",
    "ecoregion": "North Cascades Alpine & Valley",
    "lat": 47.52,
    "lon": -120.82,
    "elevFt": 5400,
    "peakDoyBase": 285
  },
  {
    "id": "columbia-gorge-or",
    "name": "Columbia River Gorge & Willamette, OR",
    "state": "OR",
    "ecoregion": "Pacific Northwest Mixed Forest",
    "lat": 45.57,
    "lon": -122.12,
    "elevFt": 950,
    "peakDoyBase": 298
  },
  {
    "id": "eastern-sierra-ca",
    "name": "Eastern Sierra (Bishop Creek & June Lake), CA",
    "state": "CA",
    "ecoregion": "Sierra Nevada East Slope",
    "lat": 37.24,
    "lon": -118.59,
    "elevFt": 8100,
    "peakDoyBase": 289
  },
  {
    "id": "new-haven-ct",
    "name": "New Haven & East Rock / Sleeping Giant, CT",
    "state": "CT",
    "ecoregion": "Coastal New England Oak-Hickory-Maple",
    "lat": 41.31,
    "lon": -72.92,
    "elevFt": 380,
    "peakDoyBase": 296
  },
  {
    "id": "hudson-valley-catskills-ny",
    "name": "Catskills & Hudson Highlands, NY",
    "state": "NY",
    "ecoregion": "Catskill Montane Hardwood",
    "lat": 42.12,
    "lon": -74.24,
    "elevFt": 2150,
    "peakDoyBase": 289
  },
  {
    "id": "monongahela-wv",
    "name": "Dolly Sods & Blackwater Falls, WV",
    "state": "WV",
    "ecoregion": "Allegheny Highland Red Spruce-Maple",
    "lat": 39.04,
    "lon": -79.32,
    "elevFt": 3700,
    "peakDoyBase": 286
  },
  {
    "id": "traverse-city-mi",
    "name": "Sleeping Bear Dunes & Traverse City, MI",
    "state": "MI",
    "ecoregion": "Great Lakes Coastal Beech-Maple",
    "lat": 44.76,
    "lon": -85.62,
    "elevFt": 820,
    "peakDoyBase": 289
  },
  {
    "id": "brown-county-in",
    "name": "Brown County & Shawnee National Forest, IN/IL",
    "state": "IN",
    "ecoregion": "Interior Low Plateau Oak-Hickory",
    "lat": 39.15,
    "lon": -86.24,
    "elevFt": 890,
    "peakDoyBase": 298
  },
  {
    "id": "chattahoochee-ga",
    "name": "Chattahoochee NF & Amicalola Falls, GA",
    "state": "GA",
    "ecoregion": "Southern Blue Ridge Foothills",
    "lat": 34.62,
    "lon": -84.19,
    "elevFt": 2400,
    "peakDoyBase": 307
  },
  {
    "id": "black-hills-sd",
    "name": "Spearfish Canyon & Black Hills, SD/WY",
    "state": "SD",
    "ecoregion": "Black Hills Montane Aspen-Birch-Pine",
    "lat": 44.35,
    "lon": -103.92,
    "elevFt": 5200,
    "peakDoyBase": 276
  },
  {
    "id": "flagstaff-az",
    "name": "San Francisco Peaks & Oak Creek Canyon, AZ",
    "state": "AZ",
    "ecoregion": "Colorado Plateau Ponderosa-Aspen-Maple",
    "lat": 35.19,
    "lon": -111.65,
    "elevFt": 7100,
    "peakDoyBase": 288
  },
  {
    "id": "yosemite-napa-ca",
    "name": "Yosemite Valley & Sierra Foothills, CA",
    "state": "CA",
    "ecoregion": "Western Sierra Mixed Conifer-Oak-Maple",
    "lat": 37.74,
    "lon": -119.59,
    "elevFt": 4200,
    "peakDoyBase": 300
  },
  {
    "id": "tetons-wy-id",
    "name": "Grand Teton & Snake River Valley, WY/ID",
    "state": "WY",
    "ecoregion": "Greater Yellowstone Aspen-Cottonwood-Conifer",
    "lat": 43.79,
    "lon": -110.68,
    "elevFt": 6800,
    "peakDoyBase": 274
  },
  {
    "id": "baxter-katahdin-me",
    "name": "Baxter State Park & North Maine Woods, ME",
    "state": "ME",
    "ecoregion": "Northern Boreal-Hardwood Transition",
    "lat": 45.92,
    "lon": -68.92,
    "elevFt": 2450,
    "peakDoyBase": 275
  },
  {
    "id": "finger-lakes-ithaca-ny",
    "name": "Finger Lakes & Letchworth Gorge, NY",
    "state": "NY",
    "ecoregion": "Glaciated Allegheny & Gorges",
    "lat": 42.45,
    "lon": -76.5,
    "elevFt": 1120,
    "peakDoyBase": 290
  },
  {
    "id": "pine-barrens-nj",
    "name": "Wharton State Forest & Pine Barrens, NJ",
    "state": "NJ",
    "ecoregion": "Atlantic Coastal Pine-Oak-Tupelo",
    "lat": 39.72,
    "lon": -74.68,
    "elevFt": 140,
    "peakDoyBase": 302
  },
  {
    "id": "allegheny-nf-pa",
    "name": "Allegheny National Forest & Kinzua, PA",
    "state": "PA",
    "ecoregion": "Northern Allegheny Plateau Hardwood",
    "lat": 41.75,
    "lon": -78.95,
    "elevFt": 1920,
    "peakDoyBase": 286
  },
  {
    "id": "pisgah-grandfather-nc",
    "name": "Pisgah NF & Grandfather Mountain, NC",
    "state": "NC",
    "ecoregion": "High-Elevation Blue Ridge Escarpment",
    "lat": 36.09,
    "lon": -81.83,
    "elevFt": 4100,
    "peakDoyBase": 291
  },
  {
    "id": "congaree-np-sc",
    "name": "Congaree National Park & Santee Bottoms, SC",
    "state": "SC",
    "ecoregion": "Southeastern Floodplain Old-Growth",
    "lat": 33.79,
    "lon": -80.78,
    "elevFt": 110,
    "peakDoyBase": 314
  },
  {
    "id": "bankhead-talladega-al",
    "name": "Bankhead & Talladega National Forests, AL",
    "state": "AL",
    "ecoregion": "Cumberland Plateau & Sipsey Wilderness",
    "lat": 34.25,
    "lon": -87.35,
    "elevFt": 1150,
    "peakDoyBase": 311
  },
  {
    "id": "daniel-boone-ky",
    "name": "Daniel Boone NF & Red River Gorge, KY",
    "state": "KY",
    "ecoregion": "Cumberland Escarpment Mixed Mesophytic",
    "lat": 37.8,
    "lon": -83.62,
    "elevFt": 1320,
    "peakDoyBase": 299
  },
  {
    "id": "cuyahoga-np-oh",
    "name": "Cuyahoga Valley National Park, OH",
    "state": "OH",
    "ecoregion": "Erie Drift Plain Beech-Maple-Oak",
    "lat": 41.24,
    "lon": -81.55,
    "elevFt": 850,
    "peakDoyBase": 292
  },
  {
    "id": "shawnee-nf-il",
    "name": "Shawnee National Forest (Garden of the Gods), IL",
    "state": "IL",
    "ecoregion": "Illinois Ozarks Oak-Hickory-Cypress",
    "lat": 37.6,
    "lon": -88.38,
    "elevFt": 820,
    "peakDoyBase": 302
  },
  {
    "id": "chequamegon-nicolet-wi",
    "name": "Chequamegon-Nicolet National Forest, WI",
    "state": "WI",
    "ecoregion": "Northwoods Maple-Birch-Hemlock",
    "lat": 45.88,
    "lon": -89.62,
    "elevFt": 1620,
    "peakDoyBase": 278
  },
  {
    "id": "driftless-effigy-ia",
    "name": "Effigy Mounds & Upper Iowa River (Driftless), IA",
    "state": "IA",
    "ecoregion": "Paleozoic Plateau Bluff Hardwood",
    "lat": 43.09,
    "lon": -91.18,
    "elevFt": 1080,
    "peakDoyBase": 289
  },
  {
    "id": "mark-twain-nf-mo",
    "name": "Mark Twain National Forest & Current River, MO",
    "state": "MO",
    "ecoregion": "Ozark Highlands Oak-Pine",
    "lat": 37.18,
    "lon": -91.25,
    "elevFt": 1280,
    "peakDoyBase": 301
  },
  {
    "id": "ouachita-talimena-ok",
    "name": "Ouachita NF & Talimena Scenic Drive, OK/AR",
    "state": "OK",
    "ecoregion": "Ouachita Mountain Ridge Forest",
    "lat": 34.69,
    "lon": -94.62,
    "elevFt": 2150,
    "peakDoyBase": 308
  },
  {
    "id": "flint-hills-ks",
    "name": "Konza Prairie & Kansas River Gallery Forest, KS",
    "state": "KS",
    "ecoregion": "Central Riparian Cottonwood-Oak-Hickory",
    "lat": 39.1,
    "lon": -96.56,
    "elevFt": 1180,
    "peakDoyBase": 299
  },
  {
    "id": "pine-ridge-niobrara-ne",
    "name": "Niobrara Valley & Pine Ridge, NE",
    "state": "NE",
    "ecoregion": "Niobrara Boreal-Prairie Ecotone",
    "lat": 42.78,
    "lon": -100.02,
    "elevFt": 2650,
    "peakDoyBase": 286
  },
  {
    "id": "turtle-mtns-sheyenne-nd",
    "name": "Turtle Mountains & Sheyenne River Valley, ND",
    "state": "ND",
    "ecoregion": "Northern Prairie Aspen Parkland",
    "lat": 48.85,
    "lon": -100.05,
    "elevFt": 2150,
    "peakDoyBase": 271
  },
  {
    "id": "rocky-mtn-np-co",
    "name": "Rocky Mountain National Park (Bear Lake), CO",
    "state": "CO",
    "ecoregion": "Front Range Subalpine Aspen-Conifer",
    "lat": 40.34,
    "lon": -105.68,
    "elevFt": 9450,
    "peakDoyBase": 271
  },
  {
    "id": "san-juan-telluride-co",
    "name": "San Juan Mountains (Telluride & Million Dollar Hwy), CO",
    "state": "CO",
    "ecoregion": "San Juan Volcanic Montane",
    "lat": 37.93,
    "lon": -107.81,
    "elevFt": 9300,
    "peakDoyBase": 276
  },
  {
    "id": "zion-kolob-ut",
    "name": "Zion National Park & Kolob Canyons, UT",
    "state": "UT",
    "ecoregion": "Colorado Plateau Canyon Riparian & Rim",
    "lat": 37.29,
    "lon": -113.02,
    "elevFt": 6200,
    "peakDoyBase": 294
  },
  {
    "id": "lolo-bitterroot-mt",
    "name": "Bitterroot & Lolo National Forests, MT/ID",
    "state": "MT",
    "ecoregion": "Northern Rocky Larch-Ponderosa-Aspen",
    "lat": 46.62,
    "lon": -114.12,
    "elevFt": 4600,
    "peakDoyBase": 287
  },
  {
    "id": "sawtooth-boise-id",
    "name": "Sawtooth National Forest & Stanley Basin, ID",
    "state": "ID",
    "ecoregion": "Central Idaho Montane Aspen-Conifer",
    "lat": 44.21,
    "lon": -114.93,
    "elevFt": 6450,
    "peakDoyBase": 277
  },
  {
    "id": "olympic-rainier-wa",
    "name": "Mt. Rainier & Olympic National Parks, WA",
    "state": "WA",
    "ecoregion": "Pacific Temperate Rainforest & Subalpine",
    "lat": 46.85,
    "lon": -121.75,
    "elevFt": 3800,
    "peakDoyBase": 290
  },
  {
    "id": "shasta-trinity-ca",
    "name": "Shasta-Trinity & Plumas National Forests, CA",
    "state": "CA",
    "ecoregion": "Klamath-Cascade Mixed Oak-Maple-Conifer",
    "lat": 40.28,
    "lon": -121.15,
    "elevFt": 4500,
    "peakDoyBase": 295
  },
  {
    "id": "sangre-de-cristo-nm",
    "name": "Taos & Santa Fe National Forest, NM",
    "state": "NM",
    "ecoregion": "Southwest Sky Island Montane",
    "lat": 35.78,
    "lon": -105.82,
    "elevFt": 8800,
    "peakDoyBase": 284
  },
  {
    "id": "mt-washington-franconia-nh",
    "name": "Franconia Ridge & Presidential Range, NH",
    "state": "NH",
    "ecoregion": "White Mountain Subalpine Birch-Spruce-Maple",
    "lat": 44.27,
    "lon": -71.3,
    "elevFt": 3650,
    "peakDoyBase": 274
  },
  {
    "id": "northeast-kingdom-jay-vt",
    "name": "Northeast Kingdom & Lake Willoughby, VT",
    "state": "VT",
    "ecoregion": "Boreal-Hardwood Montane Transition",
    "lat": 44.75,
    "lon": -72.06,
    "elevFt": 1880,
    "peakDoyBase": 277
  },
  {
    "id": "moosehead-rangeley-me",
    "name": "Moosehead Lake & Western Mountains, ME",
    "state": "ME",
    "ecoregion": "Western Maine Montane Hardwood-Spruce",
    "lat": 45.48,
    "lon": -69.68,
    "elevFt": 1650,
    "peakDoyBase": 278
  },
  {
    "id": "cape-cod-plymouth-ma",
    "name": "Cape Cod & Plymouth Pine-Oak Woodlands, MA",
    "state": "MA",
    "ecoregion": "Atlantic Coastal Pine Barrens & Scarlet Oak",
    "lat": 41.78,
    "lon": -70.32,
    "elevFt": 110,
    "peakDoyBase": 301
  },
  {
    "id": "quiet-corner-pachaug-ct",
    "name": "Pachaug Forest & Narragansett Uplands, CT/RI",
    "state": "CT",
    "ecoregion": "Southern New England Oak-Hickory-Maple",
    "lat": 41.62,
    "lon": -71.84,
    "elevFt": 540,
    "peakDoyBase": 294
  },
  {
    "id": "tug-hill-thousand-islands-ny",
    "name": "Tug Hill Plateau & St. Lawrence Valley, NY",
    "state": "NY",
    "ecoregion": "Lake Ontario Snowbelt Northern Hardwood",
    "lat": 43.78,
    "lon": -75.62,
    "elevFt": 1780,
    "peakDoyBase": 282
  },
  {
    "id": "shawangunks-minnewaska-ny",
    "name": "Shawangunk Ridge & Hudson Highlands, NY",
    "state": "NY",
    "ecoregion": "Appalachian Ridge Pitch Pine-Oak-Maple",
    "lat": 41.68,
    "lon": -74.22,
    "elevFt": 1620,
    "peakDoyBase": 292
  },
  {
    "id": "laurel-highlands-ohiopyle-pa",
    "name": "Laurel Highlands & Ohiopyle Gorge, PA",
    "state": "PA",
    "ecoregion": "Allegheny Mountains Mixed Mesophytic",
    "lat": 39.88,
    "lon": -79.48,
    "elevFt": 2350,
    "peakDoyBase": 289
  },
  {
    "id": "pine-creek-gorge-pa",
    "name": "Pine Creek Gorge (PA Grand Canyon) & Tioga, PA",
    "state": "PA",
    "ecoregion": "Deep Canyon Northern Hardwood-Hemlock",
    "lat": 41.7,
    "lon": -77.44,
    "elevFt": 1890,
    "peakDoyBase": 287
  },
  {
    "id": "catoctin-deep-creek-md",
    "name": "Deep Creek Lake & Catoctin Mountain, MD",
    "state": "MD",
    "ecoregion": "Blue Ridge & Allegheny Plateau Maryland",
    "lat": 39.58,
    "lon": -78.85,
    "elevFt": 2280,
    "peakDoyBase": 291
  },
  {
    "id": "delmarva-chesapeake-md-de",
    "name": "Chesapeake Bay & Delmarva Sweetgum-Oak, MD/DE",
    "state": "MD",
    "ecoregion": "Mid-Atlantic Coastal Plain Mixed Forest",
    "lat": 38.88,
    "lon": -75.85,
    "elevFt": 65,
    "peakDoyBase": 305
  },
  {
    "id": "new-river-gauley-wv",
    "name": "New River Gorge & Gauley River Canyon, WV",
    "state": "WV",
    "ecoregion": "Central Appalachian Gorge Mixed Hardwood",
    "lat": 38.07,
    "lon": -81.08,
    "elevFt": 1980,
    "peakDoyBase": 294
  },
  {
    "id": "mount-rogers-clinches-va",
    "name": "Mt. Rogers High Country & Clinch Mtns, VA",
    "state": "VA",
    "ecoregion": "Southern Virginian High-Elevation Crest",
    "lat": 36.66,
    "lon": -81.54,
    "elevFt": 4450,
    "peakDoyBase": 288
  },
  {
    "id": "virginia-piedmont-james-va",
    "name": "Virginia Piedmont & James River Valley, VA",
    "state": "VA",
    "ecoregion": "Piedmont Oak-Hickory-Poplar Belt",
    "lat": 37.55,
    "lon": -77.85,
    "elevFt": 420,
    "peakDoyBase": 304
  },
  {
    "id": "nantahala-highlands-nc",
    "name": "Nantahala Gorge & Highlands Plateau, NC",
    "state": "NC",
    "ecoregion": "Southern Escarpment Temperate Rainforest",
    "lat": 35.06,
    "lon": -83.2,
    "elevFt": 3850,
    "peakDoyBase": 296
  },
  {
    "id": "uwharrie-piedmont-nc",
    "name": "Uwharrie Mountains & North Carolina Piedmont, NC",
    "state": "NC",
    "ecoregion": "Southeastern Piedmont Oak-Sweetgum-Hickory",
    "lat": 35.42,
    "lon": -80.05,
    "elevFt": 740,
    "peakDoyBase": 308
  },
  {
    "id": "jocassee-table-rock-sc",
    "name": "Jocassee Gorges & Table Rock Escarpment, SC",
    "state": "SC",
    "ecoregion": "Blue Ridge Foothills Escarpment",
    "lat": 35.02,
    "lon": -82.72,
    "elevFt": 2250,
    "peakDoyBase": 305
  },
  {
    "id": "providence-pine-mtn-ga",
    "name": "F.D. Roosevelt Pine Mountain & Providence Canyon, GA",
    "state": "GA",
    "ecoregion": "Southern Piedmont & Fall Line Hills",
    "lat": 32.84,
    "lon": -84.82,
    "elevFt": 1150,
    "peakDoyBase": 315
  },
  {
    "id": "torreya-apalachicola-fl",
    "name": "Torreya Ravines & Apalachicola Bluffs, FL",
    "state": "FL",
    "ecoregion": "Florida Panhandle Steephead Ravine Relict Hardwoods",
    "lat": 30.57,
    "lon": -84.95,
    "elevFt": 250,
    "peakDoyBase": 322
  },
  {
    "id": "cheaha-little-river-al",
    "name": "Mt. Cheaha & Little River Canyon, AL",
    "state": "AL",
    "ecoregion": "Southernmost Appalachian Ridge & Canyon",
    "lat": 33.49,
    "lon": -85.81,
    "elevFt": 2350,
    "peakDoyBase": 309
  },
  {
    "id": "tishomingo-natchez-ms",
    "name": "Tishomingo Foothills & Natchez Trace, MS",
    "state": "MS",
    "ecoregion": "Tombigbee Hills Oak-Gum-Cypress",
    "lat": 34.6,
    "lon": -88.18,
    "elevFt": 590,
    "peakDoyBase": 312
  },
  {
    "id": "cumberland-plateau-savage-tn",
    "name": "Savage Gulf & Fall Creek Falls (Cumberland), TN",
    "state": "TN",
    "ecoregion": "Cumberland Plateau Gorge Mesophytic",
    "lat": 35.66,
    "lon": -85.35,
    "elevFt": 1920,
    "peakDoyBase": 300
  },
  {
    "id": "reelfoot-west-tn",
    "name": "Reelfoot Lake & Chickasaw Bluffs, TN/KY",
    "state": "TN",
    "ecoregion": "Mississippi Alluvial Cypress-Tupelo-Sweetgum",
    "lat": 36.39,
    "lon": -89.38,
    "elevFt": 320,
    "peakDoyBase": 310
  },
  {
    "id": "land-between-lakes-ky",
    "name": "Land Between the Lakes & Mammoth Cave, KY",
    "state": "KY",
    "ecoregion": "Western Pennyroyal Karst Oak-Hickory",
    "lat": 36.86,
    "lon": -88.06,
    "elevFt": 620,
    "peakDoyBase": 303
  },
  {
    "id": "mohican-malabar-oh",
    "name": "Mohican Gorge & Clear Fork Valley, OH",
    "state": "OH",
    "ecoregion": "Glaciated Allegheny Plateau Beech-Maple",
    "lat": 40.61,
    "lon": -82.26,
    "elevFt": 1180,
    "peakDoyBase": 291
  },
  {
    "id": "turkey-run-shades-in",
    "name": "Turkey Run & Sugar Creek Sandstone Gorges, IN",
    "state": "IN",
    "ecoregion": "Wabash Basin Old-Growth Beech-Maple-Poplar",
    "lat": 39.88,
    "lon": -87.2,
    "elevFt": 690,
    "peakDoyBase": 295
  },
  {
    "id": "starved-rock-illinois-river-il",
    "name": "Starved Rock & Mississippi Palisades, IL",
    "state": "IL",
    "ecoregion": "Upper Illinois Canyon Oak-Maple",
    "lat": 41.32,
    "lon": -88.99,
    "elevFt": 680,
    "peakDoyBase": 292
  },
  {
    "id": "tahquamenon-pictured-rocks-mi",
    "name": "Pictured Rocks & Tahquamenon Falls, MI",
    "state": "MI",
    "ecoregion": "Lake Superior Escarpment Maple-Beech-Birch",
    "lat": 46.56,
    "lon": -86.32,
    "elevFt": 890,
    "peakDoyBase": 281
  },
  {
    "id": "baraboo-devils-lake-wi",
    "name": "Baraboo Hills & Devils Lake Quartzite Bluffs, WI",
    "state": "WI",
    "ecoregion": "Driftless Margin Oak-Maple-Pine Relict",
    "lat": 43.42,
    "lon": -89.73,
    "elevFt": 1250,
    "peakDoyBase": 287
  },
  {
    "id": "itasca-chippewa-mn",
    "name": "Itasca Headwaters & Chippewa National Forest, MN",
    "state": "MN",
    "ecoregion": "Pine Moraines & Tamarack-Aspen Bog",
    "lat": 47.21,
    "lon": -95.21,
    "elevFt": 1475,
    "peakDoyBase": 275
  },
  {
    "id": "st-croix-blufflands-mn-wi",
    "name": "St. Croix River Valley & Southeast Blufflands, MN/WI",
    "state": "MN",
    "ecoregion": "Big Woods Maple-Basswood-Oak Savanna",
    "lat": 44.55,
    "lon": -92.65,
    "elevFt": 980,
    "peakDoyBase": 286
  },
  {
    "id": "loess-hills-des-moines-ia",
    "name": "Loess Hills & Des Moines River Valley, IA",
    "state": "IA",
    "ecoregion": "Western Tallgrass Bur Oak-Hickory Woodland",
    "lat": 41.85,
    "lon": -95.92,
    "elevFt": 1220,
    "peakDoyBase": 292
  },
  {
    "id": "katy-trail-missouri-river-mo",
    "name": "Missouri River Bluffs & Hermann Wine Country, MO",
    "state": "MO",
    "ecoregion": "Ozark Border Sugar Maple-White Oak Bluffs",
    "lat": 38.7,
    "lon": -91.44,
    "elevFt": 860,
    "peakDoyBase": 298
  },
  {
    "id": "magazine-petit-jean-ar",
    "name": "Mount Magazine & Arkansas River Valley, AR",
    "state": "AR",
    "ecoregion": "Arkansas Valley High Mesa Oak-Gum-Maple",
    "lat": 35.17,
    "lon": -93.64,
    "elevFt": 2650,
    "peakDoyBase": 304
  },
  {
    "id": "piney-woods-daingerfield-tx",
    "name": "East Texas Piney Woods (Daingerfield & Davy Crockett), TX",
    "state": "TX",
    "ecoregion": "West Gulf Coastal Plain Sweetgum-Oak-Pine",
    "lat": 33.05,
    "lon": -94.72,
    "elevFt": 460,
    "peakDoyBase": 317
  },
  {
    "id": "mckittrick-guadalupe-tx",
    "name": "McKittrick Canyon (Guadalupe Mountains NP), TX",
    "state": "TX",
    "ecoregion": "Chihuahuan Sky Island Bigtooth Maple Canyon",
    "lat": 31.98,
    "lon": -104.75,
    "elevFt": 5650,
    "peakDoyBase": 305
  },
  {
    "id": "steamboat-routt-co",
    "name": "Steamboat Springs & Medicine Bow-Routt NF, CO/WY",
    "state": "CO",
    "ecoregion": "Park Range High Subalpine Aspen-Spruce",
    "lat": 40.52,
    "lon": -106.78,
    "elevFt": 8850,
    "peakDoyBase": 269
  },
  {
    "id": "sangre-de-cristo-westcliffe-co",
    "name": "Sangre de Cristo Range & Spanish Peaks, CO",
    "state": "CO",
    "ecoregion": "Southern Rockies Alpine Aspen-Cottonwood",
    "lat": 37.65,
    "lon": -105.48,
    "elevFt": 9200,
    "peakDoyBase": 277
  },
  {
    "id": "bighorn-wind-river-wy",
    "name": "Bighorn Mountains & Wind River Range, WY",
    "state": "WY",
    "ecoregion": "Middle Rockies Subalpine Aspen-Conifer",
    "lat": 44.32,
    "lon": -107.25,
    "elevFt": 7600,
    "peakDoyBase": 272
  },
  {
    "id": "jemez-valles-caldera-nm",
    "name": "Valles Caldera & Jemez Mountains, NM",
    "state": "NM",
    "ecoregion": "Jemez Volcanic Plateau Aspen-Ponderosa",
    "lat": 35.86,
    "lon": -106.52,
    "elevFt": 8650,
    "peakDoyBase": 283
  },
  {
    "id": "cloudcroft-ruidoso-nm",
    "name": "Cloudcroft & Sacramento Mountains (Lincoln NF), NM",
    "state": "NM",
    "ecoregion": "Southern New Mexico Sky Island Maple-Aspen",
    "lat": 32.95,
    "lon": -105.74,
    "elevFt": 8650,
    "peakDoyBase": 291
  },
  {
    "id": "mogollon-rim-chiricahua-az",
    "name": "Mogollon Rim & White Mountains (Greer), AZ",
    "state": "AZ",
    "ecoregion": "Arizona Montane Aspen-Bigtooth Maple-Pine",
    "lat": 34.01,
    "lon": -109.46,
    "elevFt": 8350,
    "peakDoyBase": 286
  },
  {
    "id": "fishlake-boulder-mtn-ut",
    "name": "Fishlake (Pando Clone) & Boulder Mountain, UT",
    "state": "UT",
    "ecoregion": "High Plateaus Clonal Aspen Sanctuary",
    "lat": 38.52,
    "lon": -111.75,
    "elevFt": 8850,
    "peakDoyBase": 274
  },
  {
    "id": "ruby-mountains-lamoille-nv",
    "name": "Ruby Mountains (Lamoille Canyon) & Great Basin, NV",
    "state": "NV",
    "ecoregion": "Great Basin Glacial Canyon Aspen-Cottonwood",
    "lat": 40.62,
    "lon": -115.38,
    "elevFt": 8200,
    "peakDoyBase": 279
  },
  {
    "id": "lake-tahoe-hope-valley-ca-nv",
    "name": "Lake Tahoe Basin & Hope Valley (Carson Pass), CA/NV",
    "state": "CA",
    "ecoregion": "High Sierra Alpine Aspen-Pine Meadow",
    "lat": 38.78,
    "lon": -119.93,
    "elevFt": 7150,
    "peakDoyBase": 285
  },
  {
    "id": "napa-sonoma-mendocino-ca",
    "name": "Napa Valley, Sonoma & Russian River Hardwoods, CA",
    "state": "CA",
    "ecoregion": "California Coast Ranges Black Oak-Bigleaf Maple",
    "lat": 38.5,
    "lon": -122.47,
    "elevFt": 850,
    "peakDoyBase": 309
  },
  {
    "id": "mckenzie-deschutes-sisters-or",
    "name": "McKenzie River & Three Sisters Wilderness, OR",
    "state": "OR",
    "ecoregion": "Western & High Cascades Vine Maple-Larch-Fir",
    "lat": 44.18,
    "lon": -122.05,
    "elevFt": 2950,
    "peakDoyBase": 292
  },
  {
    "id": "wallowa-blue-mtns-or",
    "name": "Wallowa Mountains & Hells Canyon Overlook, OR",
    "state": "OR",
    "ecoregion": "Blue Mountains Larch-Aspen-Ponderosa",
    "lat": 45.28,
    "lon": -117.22,
    "elevFt": 4850,
    "peakDoyBase": 286
  },
  {
    "id": "selkirk-priest-lake-id-wa",
    "name": "Selkirk Mountains & Priest Lake (Panhandle), ID/WA",
    "state": "ID",
    "ecoregion": "Inland Maritime Western Larch-Birch-Cedar",
    "lat": 48.35,
    "lon": -116.85,
    "elevFt": 3400,
    "peakDoyBase": 284
  },
  {
    "id": "gallatin-paradise-valley-mt",
    "name": "Gallatin Canyon & Absaroka-Beartooth Range, MT",
    "state": "MT",
    "ecoregion": "Greater Yellowstone Northern Aspen-Cottonwood",
    "lat": 45.45,
    "lon": -111.15,
    "elevFt": 6150,
    "peakDoyBase": 273
  }
]


def is_within_seasonal_window(dt: datetime.date) -> bool:
    """Return True if date is within July 1 (month 7) through November 30 (month 11)."""
    return 7 <= dt.month <= 11


def fetch_open_meteo_batch(stations_chunk: List[Dict[str, Any]], retries: int = 3) -> List[Dict[str, Any]]:
    """
    Batch-fetch past 14 days + 16-day forecast daily temperature, sunshine duration,
    and precipitation for up to 53 coordinates per HTTP request.
    """
    lats = ",".join(f"{s['lat']:.2f}" for s in stations_chunk)
    lons = ",".join(f"{s['lon']:.2f}" for s in stations_chunk)
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lats}&longitude={lons}"
        f"&daily=temperature_2m_max,temperature_2m_min,sunshine_duration,precipitation_sum"
        f"&past_days=14&forecast_days=16&temperature_unit=fahrenheit&timezone=auto"
    )

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "peakfolio-seasonal-etl/1.0 (https://github.com/YenWenWang/PeakFolio)"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload if isinstance(payload, list) else [payload]
        except Exception as exc:
            print(f"[WARN] Forecast batch fetch attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(2.5 * attempt)
    return []


def fetch_era5_historical_year_batch(
    stations_chunk: List[Dict[str, Any]], year: int, retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Batch-fetch historical ERA5 daily autumn observations (Sep 1 - Nov 30) for a given year
    across up to 53 stations per request, so we can commit static JSON copies into GitHub.
    """
    lats = ",".join(f"{s['lat']:.2f}" for s in stations_chunk)
    lons = ",".join(f"{s['lon']:.2f}" for s in stations_chunk)
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lats}&longitude={lons}"
        f"&start_date={year}-09-01&end_date={year}-11-30"
        f"&daily=temperature_2m_max,temperature_2m_min,sunshine_duration,precipitation_sum"
        f"&temperature_unit=fahrenheit&timezone=auto"
    )

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "peakfolio-historical-archiver/1.0 (https://github.com/YenWenWang/PeakFolio)"}
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload if isinstance(payload, list) else [payload]
        except Exception as exc:
            print(f"[WARN] Historical ERA5 batch fetch ({year}) attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(3.0 * attempt)
    return []


def compute_station_metrics(
    station: Dict[str, Any], daily_obj: Dict[str, Any], include_daily_series: bool = False, source_tag: str = "Live Open-Meteo / NOAA GFS Sync"
) -> Dict[str, Any]:
    """
    Compute 10-day mean nightLowF, dayHighF, diurnal ΔT, sunnyPct, moistureIdx,
    and cumulative chilling degree-day (CDD < 47°F) peak DOY shift.
    """
    daily = daily_obj.get("daily", {})
    times = daily.get("time") or []
    mins_raw = daily.get("temperature_2m_min") or []
    maxs_raw = daily.get("temperature_2m_max") or []
    suns_raw = daily.get("sunshine_duration") or []
    prcps_raw = daily.get("precipitation_sum") or []

    mins = [x for x in mins_raw if x is not None]
    maxs = [x for x in maxs_raw if x is not None]
    suns = [x for x in suns_raw if x is not None]
    prcps = [x for x in prcps_raw if x is not None]

    if not mins or not maxs:
        raise ValueError("Empty temperature series")

    # For a 91-day full autumn archive (Sep 1 - Nov 30), use the core Oct 5 - Oct 25 window for summary stats
    if len(mins) >= 60:
        win_mins = mins[34:55]
        win_maxs = maxs[34:55]
        win_suns = suns[34:55] if len(suns) >= 55 else suns
    else:
        win_mins = mins[-14:-4] if len(mins) >= 14 else mins[-10:]
        win_maxs = maxs[-14:-4] if len(maxs) >= 14 else maxs[-10:]
        win_suns = suns[-14:-4] if len(suns) >= 14 else suns[-10:]

    night_low_f = round(sum(win_mins) / max(1, len(win_mins)))
    day_high_f = round(sum(win_maxs) / max(1, len(win_maxs)))
    diurnal_swing_f = max(4, day_high_f - night_low_f)

    sunny_pct = (
        min(96, max(25, round((sum(win_suns) / max(1, len(win_suns))) / 38500.0 * 100)))
        if win_suns else 68
    )
    total_prcp = sum(prcps)
    moisture_idx = round(max(-0.5, min(1.2, (total_prcp / 45.0) - 0.25)), 2)

    cdd_delta = round((38.0 - night_low_f) * 0.35, 1)
    adjusted_peak_doy = int(round(max(250, min(332, station["peakDoyBase"] - cdd_delta))))

    record: Dict[str, Any] = {
        "id": station["id"],
        "name": station["name"],
        "state": station["state"],
        "lat": station["lat"],
        "lon": station["lon"],
        "elevFt": station["elevFt"],
        "peakDoyBase": adjusted_peak_doy,
        "weather": {
            "nightLowF": night_low_f,
            "dayHighF": day_high_f,
            "diurnalSwingF": diurnal_swing_f,
            "sunnyPct": sunny_pct,
            "moistureIdx": moisture_idx,
            "microclimateLabel": (
                f"{source_tag} · Night {night_low_f}°F / "
                f"Day {day_high_f}°F (ΔT {diurnal_swing_f}°F) · {sunny_pct}% Sun"
            )
        }
    }

    if include_daily_series:
        record["dailySeries"] = {
            "time": times,
            "temperature_2m_min": [round(x, 1) if x is not None else None for x in mins_raw],
            "temperature_2m_max": [round(x, 1) if x is not None else None for x in maxs_raw],
            "sunshine_duration": [round(x) if x is not None else None for x in suns_raw],
            "precipitation_sum": [round(x, 2) if x is not None else None for x in prcps_raw],
            "isFullAutumnArchive": len(times) >= 60,
            "sourceLabel": source_tag
        }

    return record


def build_and_save_historical_years(start_year: int, end_year: int, overwrite: bool = False) -> int:
    """
    Fetch and store static GitHub repository copies of 1950–2025 autumn weather & phenology
    in `./data/historical/foliage-history-YYYY.json` + `./data/historical/index.json`.
    """
    hist_dir = os.path.join("data", "historical")
    os.makedirs(hist_dir, exist_ok=True)
    chunk_size = 53
    saved_years: List[int] = []

    for yr in range(start_year, end_year + 1):
        target_path = os.path.join(hist_dir, f"foliage-history-{yr}.json")
        if os.path.exists(target_path) and not overwrite:
            print(f"[SKIP] {target_path} already exists in repository. Skipping {yr}.")
            saved_years.append(yr)
            continue

        print(f"[INFO] Fetching ERA5 historical autumn (Sep 1 - Nov 30, {yr}) across {len(US_FOLIAGE_STATIONS)} stations...")
        stations_out: List[Dict[str, Any]] = []

        for start_idx in range(0, len(US_FOLIAGE_STATIONS), chunk_size):
            chunk = US_FOLIAGE_STATIONS[start_idx : start_idx + chunk_size]
            responses = fetch_era5_historical_year_batch(chunk, yr)
            for idx, stn in enumerate(chunk):
                if idx < len(responses) and responses[idx]:
                    try:
                        stations_out.append(
                            compute_station_metrics(
                                stn,
                                responses[idx],
                                include_daily_series=True,
                                source_tag=f"GitHub Repo ERA5 Archive ({yr} Sep–Nov Observed)"
                            )
                        )
                    except Exception as exc:
                        print(f"[WARN] Station {stn['id']} ({yr}) parse warning: {exc}")
            time.sleep(0.8)

        if not stations_out:
            print(f"[WARN] Could not fetch historical year {yr}; skipping write.")
            continue

        now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "version": f"era5-history-{yr}",
            "year": yr,
            "generatedAt": now_iso,
            "seasonalWindow": f"{yr}-09-01 to {yr}-11-30",
            "stationsCount": len(stations_out),
            "stations": stations_out
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        print(f"[OK] Saved {target_path} ({len(stations_out)} stations).")
        saved_years.append(yr)
        time.sleep(0.6)

    # Update ./data/historical/index.json manifest of all available years in the repo
    existing_files = sorted(
        f for f in os.listdir(hist_dir) if f.startswith("foliage-history-") and f.endswith(".json")
    )
    manifest = {
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "availableYears": [
            int(f.replace("foliage-history-", "").replace(".json", ""))
            for f in existing_files
            if f.replace("foliage-history-", "").replace(".json", "").isdigit()
        ],
        "files": [f"data/historical/{f}" for f in existing_files]
    }
    manifest_path = os.path.join(hist_dir, "index.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[OK] Updated {manifest_path} ({len(manifest['availableYears'])} historical years indexed).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build daily seasonal foliage snapshots and/or backfill 1950–2025 historical JSON files."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run daily snapshot pull even outside the July 1 - November 30 seasonal window."
    )
    parser.add_argument(
        "--backfill-history",
        nargs=2,
        metavar=("START_YEAR", "END_YEAR"),
        type=int,
        help="Fetch 1950-2025 historical ERA5 autumn data and save static JSON copies to ./data/historical/foliage-history-YYYY.json"
    )
    parser.add_argument(
        "--overwrite-history",
        action="store_true",
        help="Re-download and overwrite existing ./data/historical/foliage-history-YYYY.json files."
    )
    args = parser.parse_args()

    # Check environment variable fallback for GitHub Actions workflow_dispatch
    env_backfill = os.environ.get("BACKFILL_HISTORY_RANGE", "").strip()
    if args.backfill_history:
        start_yr, end_yr = args.backfill_history
        return build_and_save_historical_years(start_yr, end_yr, overwrite=args.overwrite_history)
    elif env_backfill and "-" in env_backfill:
        parts = env_backfill.split("-", 1)
        if parts[0].strip().isdigit() and parts[1].strip().isdigit():
            return build_and_save_historical_years(
                int(parts[0].strip()), int(parts[1].strip()), overwrite=args.overwrite_history
            )

    today = datetime.date.today()
    force_flag = args.force or (os.environ.get("FORCE_RUN", "").lower() == "true")

    if not is_within_seasonal_window(today) and not force_flag:
        print(
            f"[SKIP] Current date ({today.isoformat()}) is outside the July 1 - November 30 "
            f"seasonal window. Exiting cleanly without pulling data. (Use --force to override.)"
        )
        return 0

    print(f"[INFO] Starting peakfolio seasonal data sync for {today.isoformat()} across {len(US_FOLIAGE_STATIONS)} stations...")

    chunk_size = 53
    updated_stations: List[Dict[str, Any]] = []

    for start_idx in range(0, len(US_FOLIAGE_STATIONS), chunk_size):
        chunk = US_FOLIAGE_STATIONS[start_idx : start_idx + chunk_size]
        responses = fetch_open_meteo_batch(chunk)
        for idx, stn in enumerate(chunk):
            if idx < len(responses) and responses[idx]:
                try:
                    updated_stations.append(compute_station_metrics(stn, responses[idx]))
                except Exception as exc:
                    print(f"[WARN] Fallback for {stn['id']}: {exc}")
        time.sleep(0.5)

    if not updated_stations:
        print("[ERROR] No stations were updated from Open-Meteo. Aborting write.")
        return 1

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot_payload = {
        "version": f"{today.strftime('%Y.%m.%d')}-seasonal",
        "generatedAt": now_iso,
        "seasonalWindow": "July 1 - November 30",
        "stationsCount": len(updated_stations),
        "stations": updated_stations
    }

    # 1. Write root ./foliage-forecast-snapshot.json (auto-loaded by index.html on GitHub Pages)
    out_file = "foliage-forecast-snapshot.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, indent=2)
    print(f"[OK] Wrote {out_file} ({len(updated_stations)} stations updated at {now_iso}).")

    # 2. Save dated seasonal checkpoint in data/archive/YYYY/
    archive_dir = os.path.join("data", "archive", str(today.year))
    os.makedirs(archive_dir, exist_ok=True)
    archive_file = os.path.join(archive_dir, f"foliage-snapshot-{today.isoformat()}.json")
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, indent=2)
    print(f"[OK] Archived daily snapshot to {archive_file}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())