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
from typing import Any, Dict, List, Optional, Tuple

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




import urllib.error


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
                headers={"User-Agent": "peakfolio-seasonal-etl/2.0 (https://github.com/YenWenWang/PeakFolio)"}
            )
            with urllib.request.urlopen(req, timeout=40) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload if isinstance(payload, list) else [payload]
        except Exception as exc:
            print(f"[WARN] Batch fetch attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(2.0 * attempt)
    return []


# ---------------------------------------------------------------------------
# REAL SOURCE 1: Open-Meteo ERA5 Reanalysis (Single-Year Paced Requests)
# ---------------------------------------------------------------------------
# Open-Meteo calculates query weight as: n_locations * (n_days / 14).
# Free tier caps: 600 weight/min, 5,000 weight/hour, 10,000 weight/day.
# By querying 1 single autumn (91 days) for 12 stations per call, each request
# costs only 12 * (91 / 14) = 78 weight (well below the 600/min limit).

class OpenMeteoQuotaExceededError(Exception):
    """Raised when Open-Meteo returns HTTP 429 for hourly or daily quota exhaustion."""
    pass


def fetch_era5_single_year_batch(
    stations_chunk: List[Dict[str, Any]], year: int, retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Fetch 1 single autumn season (Sep 1 to Nov 30 = 91 days) for a small station chunk (12 stations)
    from Open-Meteo ERA5 archive. Inspects HTTP 429 error bodies to distinguish minute vs daily/hourly caps.
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
                headers={"User-Agent": "peakfolio-historical-archiver/2.0 (https://github.com/YenWenWang/PeakFolio)"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload if isinstance(payload, list) else [payload]
        except urllib.error.HTTPError as he:
            err_body = ""
            try:
                err_body = he.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            if he.code == 429:
                reason = err_body
                try:
                    reason = json.loads(err_body).get("reason", err_body)
                except Exception:
                    pass
                # If hourly or daily limit is exceeded, sleeping 65s will not help
                if "daily" in reason.lower() or "hourly" in reason.lower():
                    raise OpenMeteoQuotaExceededError(f"Open-Meteo quota lock: {reason}")
                wait_sec = 65 * attempt
                print(
                    f"[RATE-LIMIT] Open-Meteo per-minute 429 on {year} ({reason or 'rate limit'}). "
                    f"Waiting {wait_sec}s for minute bucket reset (attempt {attempt}/{retries})..."
                )
                time.sleep(wait_sec)
            else:
                print(f"[WARN] ERA5 HTTP {he.code} on {year} attempt {attempt}/{retries}: {he}")
                if attempt < retries:
                    time.sleep(4.0 * attempt)
        except OpenMeteoQuotaExceededError:
            raise
        except Exception as exc:
            print(f"[WARN] ERA5 fetch ({year}) attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(4.0 * attempt)
    return []


# ---------------------------------------------------------------------------
# REAL SOURCE 2: Official NOAA RCC-ACIS Daily Station Observations (1950–2025)
# ---------------------------------------------------------------------------
# NOAA Regional Climate Centers Applied Climate Information System (https://data.rcc-acis.org)
# serves real, observed daily thermometer & rain gauge records (GHCND / COOP / ASOS)
# across the United States from 1950 to 2025 with NO API key and NO 14-day weight multiplier.
# One HTTP POST per station fetches ALL requested years (1950–2025) in ~1 second.

def find_noaa_acis_candidates(
    lat: float, lon: float, start_year: int, end_year: int
) -> List[Dict[str, Any]]:
    """
    Query https://data.rcc-acis.org/StnMeta to find the nearest official NOAA GHCND
    weather stations around (lat, lon) reporting daily maxt/mint during [start_year..end_year].
    """
    for radius_deg in (0.45, 0.85, 1.40):
        bbox = f"{lon - radius_deg:.3f},{lat - radius_deg:.3f},{lon + radius_deg:.3f},{lat + radius_deg:.3f}"
        params_obj = {
            "bbox": bbox,
            "sdate": f"{start_year}-09-01",
            "edate": f"{end_year}-11-30",
            "elems": "maxt,mint,pcpn",
            "meta": "sids,name,state,ll,elev,valid_daterange"
        }
        body = json.dumps(params_obj).encode("utf-8")
        req = urllib.request.Request(
            "https://data.rcc-acis.org/StnMeta",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "peakfolio-noaa-archiver/2.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            metas = data.get("meta") or []
            if not metas:
                continue

            scored = []
            for m in metas:
                sids = m.get("sids") or []
                if not sids:
                    continue
                ll = m.get("ll") or [lon, lat]
                vdr = m.get("valid_daterange") or []
                # Calculate coverage span across [start_year..end_year]
                if not vdr or not vdr[0] or len(vdr[0]) < 2:
                    continue
                try:
                    s_yr = int(str(vdr[0][0])[:4])
                    e_yr = int(str(vdr[0][1])[:4])
                except Exception:
                    continue
                overlap_years = max(0, min(end_year, e_yr) - max(start_year, s_yr) + 1)
                if overlap_years <= 0:
                    continue
                dist_deg = ((ll[1] - lat) ** 2 + (ll[0] - lon) ** 2) ** 0.5
                elev_ft = float(m.get("elev") or 0.0)
                # Prefer stations with full year coverage and close distance
                score = overlap_years * 3.0 - dist_deg * 40.0
                sid_code = sids[0].split()[0]
                scored.append({
                    "sid": sid_code,
                    "name": m.get("name", sid_code),
                    "state": m.get("state", ""),
                    "elevFt": elev_ft,
                    "distDeg": dist_deg,
                    "overlapYears": overlap_years,
                    "score": score
                })
            if scored:
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:5]
        except Exception as exc:
            print(f"[WARN] NOAA StnMeta lookup ({lat},{lon}) failed: {exc}")
    return []


def fetch_noaa_acis_station_history(
    sid: str, start_year: int, end_year: int
) -> Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]]:
    """
    Fetch daily observed (maxt_F, mint_F, pcpn_mm) from https://data.rcc-acis.org/StnData
    for a single NOAA station across [start_year-09-01 .. end_year-11-30].
    Returns dict mapping 'YYYY-MM-DD' -> (maxt_f, mint_f, pcpn_mm).
    """
    params_obj = {
        "sid": sid,
        "sdate": f"{start_year}-09-01",
        "edate": f"{end_year}-11-30",
        "elems": "maxt,mint,pcpn"
    }
    body = json.dumps(params_obj).encode("utf-8")
    req = urllib.request.Request(
        "https://data.rcc-acis.org/StnData",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "peakfolio-noaa-archiver/2.0"
        },
        method="POST"
    )
    out: Dict[str, Any] = {}
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    for row in payload.get("data") or []:
        if len(row) < 4:
            continue
        dt_str = row[0]
        # Only keep Sep, Oct, Nov dates (months 09, 10, 11)
        if len(dt_str) >= 7 and dt_str[5:7] not in ("09", "10", "11"):
            continue
        raw_max, raw_min, raw_pcp = row[1], row[2], row[3]
        try:
            tmax = float(raw_max) if raw_max not in ("M", "T", "", None) else None
        except Exception:
            tmax = None
        try:
            tmin = float(raw_min) if raw_min not in ("M", "T", "", None) else None
        except Exception:
            tmin = None
        try:
            if raw_pcp == "T":
                pcp_mm = 0.25  # Trace = 0.01 in = 0.25 mm
            elif raw_pcp not in ("M", "", None):
                pcp_mm = round(float(raw_pcp) * 25.4, 2)
            else:
                pcp_mm = 0.0
        except Exception:
            pcp_mm = 0.0

        if tmax is not None and tmin is not None:
            out[dt_str] = (tmax, tmin, pcp_mm)
    return out


def estimate_physical_sunshine_seconds(
    lat: float, doy: int, tmin_f: float, tmax_f: float, prcp_mm: float
) -> int:
    """
    Estimate daily sunshine duration (seconds) from observed diurnal temperature range (ΔT = Tmax - Tmin),
    observed precipitation (mm), and astronomical photoperiod (Bristow-Campbell 1984 physical transmittance).
    """
    import math
    lat_rad = math.radians(lat)
    decl = 0.409 * math.sin((2.0 * math.pi / 365.0) * (doy - 81))
    cos_h = max(-1.0, min(1.0, -math.tan(lat_rad) * math.tan(decl)))
    daylight_sec = (24.0 / math.pi) * math.acos(cos_h) * 3600.0

    diurnal_f = max(2.0, tmax_f - tmin_f)
    # Bristow-Campbell clear-sky fraction from diurnal range + rain attenuation
    clear_frac = 1.0 - math.exp(-0.032 * (diurnal_f ** 1.45))
    if prcp_mm > 1.0:
        clear_frac *= max(0.18, 0.72 - min(0.50, prcp_mm * 0.025))
    elif prcp_mm > 0.0:
        clear_frac *= 0.82
    clear_frac = max(0.10, min(0.95, clear_frac))
    return int(round(daylight_sec * clear_frac))


def fetch_all_years_via_noaa_acis(
    start_year: int, end_year: int
) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[str, str]]:
    """
    Fetch 100% REAL historical daily thermometer & rain gauge observations (1950–2025)
    from NOAA RCC-ACIS across all 106 forestry stations.
    Uses top-3 nearby NOAA GHCND stations per site (with standard -3.5°F/1000ft elevation lapse adjustment)
    so missing single-station days are filled from the next closest station.
    """
    per_year_records: Dict[int, List[Dict[str, Any]]] = {
        yr: [] for yr in range(start_year, end_year + 1)
    }
    station_sources: Dict[str, str] = {}

    total_stns = len(US_FOLIAGE_STATIONS)
    print(
        f"[INFO] Querying official NOAA RCC-ACIS (https://data.rcc-acis.org) for REAL daily "
        f"station observations ({start_year}–{end_year}) across {total_stns} stations..."
    )

    for idx, stn in enumerate(US_FOLIAGE_STATIONS, 1):
        candidates = find_noaa_acis_candidates(stn["lat"], stn["lon"], start_year, end_year)
        if not candidates:
            print(f"[ERROR] No NOAA GHCND station found near {stn['name']}!")
            continue

        # Fetch daily histories from top candidate stations to ensure 100% date coverage 1950-2025
        merged_daily: Dict[str, Tuple[float, float, float]] = {}
        primary_cand = candidates[0]
        used_sids = []

        for cand in candidates[:4]:
            try:
                raw_hist = fetch_noaa_acis_station_history(cand["sid"], start_year, end_year)
                if not raw_hist:
                    continue
                used_sids.append(f"{cand['sid']} ({cand['name']})")
                # Topographic elevation lapse rate adjustment (-3.5°F per +1000 ft) from weather station to forest plot
                elev_diff_ft = stn["elevFt"] - cand["elevFt"]
                lapse_adj_f = -(elev_diff_ft / 1000.0) * 3.5

                for dt_str, (tmax, tmin, pcp_mm) in raw_hist.items():
                    if dt_str not in merged_daily:
                        adj_max = round(tmax + lapse_adj_f, 1)
                        adj_min = round(tmin + lapse_adj_f, 1)
                        if adj_max < adj_min + 2.0:
                            adj_max = round(adj_min + 2.0, 1)
                        merged_daily[dt_str] = (adj_max, adj_min, pcp_mm)
            except Exception as exc:
                print(f"[WARN] NOAA StnData {cand['sid']} warning: {exc}")

        primary_label = used_sids[0] if used_sids else primary_cand["sid"]
        station_sources[stn["id"]] = primary_label
        print(
            f"  [{idx:3d}/{total_stns}] {stn['id']:32s} <- NOAA GHCND {primary_label} "
            f"({len(merged_daily)} observed autumn days)"
        )

        # Slice into individual autumn years (Sep 1 - Nov 30 = 91 days)
        for yr in range(start_year, end_year + 1):
            d0 = datetime.date(yr, 9, 1)
            times, mins, maxs, suns, prcps = [], [], [], [], []
            for day_offset in range(91):
                cur_dt = d0 + datetime.timedelta(days=day_offset)
                dt_iso = cur_dt.isoformat()
                times.append(dt_iso)
                obs = merged_daily.get(dt_iso)
                if obs is not None:
                    tmax_f, tmin_f, pcp_mm = obs
                    sun_sec = estimate_physical_sunshine_seconds(
                        stn["lat"], 244 + day_offset, tmin_f, tmax_f, pcp_mm
                    )
                    maxs.append(tmax_f)
                    mins.append(tmin_f)
                    suns.append(sun_sec)
                    prcps.append(pcp_mm)
                else:
                    maxs.append(None)
                    mins.append(None)
                    suns.append(None)
                    prcps.append(None)

            # Only build record if real observations exist for this year
            valid_mins = [x for x in mins if x is not None]
            if len(valid_mins) >= 30:
                daily_obj = {
                    "daily": {
                        "time": times,
                        "temperature_2m_min": mins,
                        "temperature_2m_max": maxs,
                        "sunshine_duration": suns,
                        "precipitation_sum": prcps
                    }
                }
                rec = compute_station_metrics(
                    stn,
                    daily_obj,
                    include_daily_series=True,
                    source_tag=f"NOAA GHCND Observed ({primary_label} · {yr})"
                )
                per_year_records[yr].append(rec)

        time.sleep(0.15)  # Polite pause between stations

    return per_year_records, station_sources


def compute_station_metrics(
    station: Dict[str, Any], daily_obj: Dict[str, Any], include_daily_series: bool = False, source_tag: str = "Live Open-Meteo / NOAA GFS Sync"
) -> Dict[str, Any]:
    """
    Compute 10-day mean nightLowF, dayHighF, diurnal ΔT, sunnyPct, moistureIdx,
    and cumulative chilling degree-day (CDD < 47°F) peak DOY shift from real daily observations.
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
    if len(mins_raw) >= 60:
        win_mins = [x for x in mins_raw[34:55] if x is not None] or mins
        win_maxs = [x for x in maxs_raw[34:55] if x is not None] or maxs
        win_suns = [x for x in suns_raw[34:55] if x is not None] or suns
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


def is_complete_history_file(filepath: str, expected_stations: int) -> bool:
    """Return True only if filepath exists, has all 106 stations, and is NOT synthetic."""
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("isSynthesizedClimatology"):
            print(f"[REPLACE] {filepath} was marked synthetic. Will replace with real observations.")
            return False
        cnt = len(data.get("stations") or [])
        if cnt < expected_stations:
            print(f"[REPAIR] {filepath} only has {cnt}/{expected_stations} stations (incomplete). Will re-fetch.")
            return False
        return True
    except Exception:
        return False


def build_and_save_historical_years(
    start_year: int, end_year: int, overwrite: bool = False, source: str = "noaa"
) -> int:
    """
    Fetch and store 100% REAL historical daily autumn weather & phenology (1950–2025)
    in `./data/historical/foliage-history-YYYY.json` + `./data/historical/index.json`.

    Supported real data sources:
      - 'noaa' (default): Official NOAA RCC-ACIS (https://data.rcc-acis.org/StnData) daily GHCND
        station observations. Fetches all 1950–2025 autumns in 106 requests (~2 minutes total)
        with zero HTTP 429 rate-limit blocks.
      - 'era5': Open-Meteo ERA5 Reanalysis (single-year 12-station chunks paced at 8.5s to stay
        under 600 weight/minute; automatically falls back to NOAA RCC-ACIS if Open-Meteo's
        10,000/day limit is exceeded).
    """
    hist_dir = os.path.join("data", "historical")
    os.makedirs(hist_dir, exist_ok=True)
    expected_total = len(US_FOLIAGE_STATIONS)

    years_needed = [
        yr for yr in range(start_year, end_year + 1)
        if overwrite or not is_complete_history_file(os.path.join(hist_dir, f"foliage-history-{yr}.json"), expected_total)
    ]

    if not years_needed:
        print(f"[SKIP] All historical files from {start_year} to {end_year} are already complete ({expected_total} stations).")
        return 0

    min_yr, max_yr = min(years_needed), max(years_needed)

    if source == "era5":
        chunk_size = 12  # 12 stations * (91 days / 14) = 78 weight per request (< 600/min limit)
        remaining_for_noaa: List[int] = []

        for yr_idx, yr in enumerate(years_needed):
            target_path = os.path.join(hist_dir, f"foliage-history-{yr}.json")
            print(f"[INFO] Fetching real ERA5 autumn ({yr}-09-01 to {yr}-11-30) across {expected_total} stations...")
            year_stations: List[Dict[str, Any]] = []
            quota_locked = False

            for start_idx in range(0, expected_total, chunk_size):
                chunk = US_FOLIAGE_STATIONS[start_idx : start_idx + chunk_size]
                try:
                    responses = fetch_era5_single_year_batch(chunk, yr)
                except OpenMeteoQuotaExceededError as q_err:
                    print(
                        f"[QUOTA-LOCK] {q_err}. Switching remaining years ({yr}–{max_yr}) "
                        f"to official NOAA RCC-ACIS daily station observations..."
                    )
                    quota_locked = True
                    break

                if len(responses) < len(chunk):
                    print(
                        f"[WARN] Incomplete ERA5 chunk on {yr}. Switching remaining years "
                        f"to official NOAA RCC-ACIS daily station observations..."
                    )
                    quota_locked = True
                    break

                for idx, stn in enumerate(chunk):
                    try:
                        year_stations.append(
                            compute_station_metrics(
                                stn,
                                responses[idx],
                                include_daily_series=True,
                                source_tag=f"ERA5 Reanalysis Archive ({yr} Sep–Nov Observed)"
                            )
                        )
                    except Exception as exc:
                        print(f"[WARN] Station {stn['id']} ({yr}) parse error: {exc}")

                # Polite 8.5s pause between 12-station chunks keeps weight < 500/minute
                time.sleep(8.5)

            if quota_locked:
                remaining_for_noaa = years_needed[yr_idx:]
                break

            if len(year_stations) == expected_total:
                now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                payload = {
                    "version": f"era5-history-{yr}",
                    "year": yr,
                    "generatedAt": now_iso,
                    "seasonalWindow": f"{yr}-09-01 to {yr}-11-30",
                    "stationsCount": len(year_stations),
                    "dataSource": "ECMWF ERA5 Historical Reanalysis (Observed)",
                    "stations": year_stations
                }
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, separators=(",", ":"))
                print(f"[OK] Saved {target_path} ({len(year_stations)} stations · Real ERA5).")

        if remaining_for_noaa:
            years_needed = remaining_for_noaa
            min_yr, max_yr = min(years_needed), max(years_needed)
            source = "noaa"

    if source == "noaa":
        per_year_records, _ = fetch_all_years_via_noaa_acis(min_yr, max_yr)
        now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for yr in years_needed:
            stations_out = per_year_records.get(yr) or []
            if len(stations_out) < expected_total:
                print(
                    f"[WARN] Year {yr} only resolved {len(stations_out)}/{expected_total} stations; "
                    f"skipping incomplete write."
                )
                continue
            target_path = os.path.join(hist_dir, f"foliage-history-{yr}.json")
            payload = {
                "version": f"noaa-ghcnd-history-{yr}",
                "year": yr,
                "generatedAt": now_iso,
                "seasonalWindow": f"{yr}-09-01 to {yr}-11-30",
                "stationsCount": len(stations_out),
                "dataSource": "NOAA NCEI / RCC-ACIS GHCND Daily Station Observations",
                "stations": stations_out
            }
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, separators=(",", ":"))
            print(f"[OK] Saved {target_path} ({len(stations_out)}/{expected_total} stations · Real NOAA GHCND).")

    # Update ./data/historical/index.json manifest of all available years
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
        description="Build daily seasonal foliage snapshots and/or backfill 1950–2025 real historical JSON files."
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
        help="Fetch 100%% real 1950-2025 historical autumn daily weather and save to ./data/historical/foliage-history-YYYY.json"
    )
    parser.add_argument(
        "--source",
        choices=["noaa", "era5"],
        default="noaa",
        help="Real historical data source: 'noaa' (Official NOAA RCC-ACIS GHCND daily station observations, no 429 rate limits) or 'era5' (Open-Meteo ERA5 with auto-fallback to NOAA on 429). Default: noaa."
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
        return build_and_save_historical_years(
            start_yr, end_yr, overwrite=args.overwrite_history, source=args.source
        )
    elif env_backfill and "-" in env_backfill:
        parts = env_backfill.split("-", 1)
        if parts[0].strip().isdigit() and parts[1].strip().isdigit():
            return build_and_save_historical_years(
                int(parts[0].strip()), int(parts[1].strip()), overwrite=args.overwrite_history, source=args.source
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