"""Real boba shop data scraped from Google Maps for the Bay Area.

421 verified boba / tea shops across 47 cities, scraped from
all 62 neighbourhood centroids with the boba-relevance filter active.
Used to seed the persistent shop store on first startup so that index
lookups and the price-correlation chart are instant.
"""

from __future__ import annotations

import hashlib
import math
from typing import TypedDict

from models import ShopData


class _RawShop(TypedDict):
    name: str
    lat: float
    lng: float
    rating: float
    reviews: int
    addr: str


DEMO_SHOPS_DB: list[_RawShop] = [
    # -- Los Gatos --
    {"name": "Mandala Tea House", "lat": 37.2628075, "lng": -121.9625422, "rating": 4.3, "reviews": 35, "addr": "14107 Winchester Blvd H, Los Gatos, CA 95032"},
    {"name": "UMe | Tea & Snacks", "lat": 37.2239579, "lng": -121.9834074, "rating": 4.8, "reviews": 193, "addr": "47 N Santa Cruz Ave, Los Gatos, CA 95030"},
    # -- Saratoga --
    {"name": "Ceré Tea", "lat": 37.2918403, "lng": -121.9961235, "rating": 4.8, "reviews": 360, "addr": "18568 Prospect Rd, Saratoga, CA 95070"},
    {"name": "TEAZENTEA", "lat": 37.258709, "lng": -122.0323133, "rating": 4.4, "reviews": 227, "addr": "14410 Big Basin Wy d, Saratoga, CA 95070"},
    {"name": "TaoTaoTea", "lat": 37.2917354, "lng": -121.9941045, "rating": 4.5, "reviews": 440, "addr": "18472 Prospect Rd, Saratoga, CA 95070"},
    # -- Campbell --
    {"name": "Breaktime Tea - Campbell", "lat": 37.287189, "lng": -121.9464941, "rating": 4.4, "reviews": 266, "addr": "199 E Campbell Ave, Campbell, CA 95008"},
    {"name": "Ice Splash", "lat": 37.2787292, "lng": -121.9507527, "rating": 4.8, "reviews": 131, "addr": "2475 Winchester Blvd, Campbell, CA 95008"},
    {"name": "Steepers", "lat": 37.2868828, "lng": -121.9439891, "rating": 4.6, "reviews": 51, "addr": "346 E Campbell Ave, Campbell, CA 95008"},
    {"name": "Teaspoon Campbell", "lat": 37.2884456, "lng": -121.934054, "rating": 4.7, "reviews": 374, "addr": "1875 S Bascom Ave #160, Campbell, CA 95008"},
    # -- San Jose --
    {"name": "4Kids Tea House", "lat": 37.2493105, "lng": -121.8310603, "rating": 4.2, "reviews": 110, "addr": "5681 Snell Ave #1, San Jose, CA 95123"},
    {"name": "A.M. Craft", "lat": 37.3364169, "lng": -121.8770154, "rating": 4.8, "reviews": 268, "addr": "481 E San Carlos St, San Jose, CA 95112"},
    {"name": "Acha Coffee and Tea", "lat": 37.399416, "lng": -121.8482995, "rating": 4.7, "reviews": 171, "addr": "3245 Sierra Rd, San Jose, CA 95132"},
    {"name": "Amor Cafe and Tea", "lat": 37.2519407, "lng": -121.8612639, "rating": 4.0, "reviews": 98, "addr": "925 Blossom Hill Rd, San Jose, CA 95123"},
    {"name": "Arisan Tea & Coffee House", "lat": 37.3311167, "lng": -121.8573369, "rating": 4.0, "reviews": 422, "addr": "979 Story Rd Unit 7012, San Jose, CA 95122"},
    {"name": "Aroma Chè, Coffee & Tea", "lat": 37.3085631, "lng": -121.8140033, "rating": 4.3, "reviews": 149, "addr": "3005 Silver Creek Rd STE 150, San Jose, CA 95121"},
    {"name": "Arome Cafe", "lat": 37.3001432, "lng": -121.7705072, "rating": 4.1, "reviews": 113, "addr": "4878 San Felipe Rd #110, San Jose, CA 95135"},
    {"name": "B Cafe (Berryessa coffee X tea Cafe)", "lat": 37.3727628, "lng": -121.8738208, "rating": 4.1, "reviews": 245, "addr": "1694 Berryessa Rd, San Jose, CA 95133"},
    {"name": "BAMBŪ Desserts & Drinks", "lat": 37.3864483, "lng": -121.8846443, "rating": 3.9, "reviews": 395, "addr": "1688 Hostetter Rd D, San Jose, CA 95131"},
    {"name": "BAMBŪ Desserts and Drinks", "lat": 37.3344457, "lng": -121.8558755, "rating": 4.2, "reviews": 382, "addr": "949 McLaughlin Ave, San Jose, CA 95122"},
    {"name": "Bloom Tea House", "lat": 37.3247667, "lng": -121.7985129, "rating": 4.2, "reviews": 3, "addr": "2850 Quimby Rd #125, San Jose, CA 95148"},
    {"name": "Boba Bar", "lat": 37.332404, "lng": -121.8845785, "rating": 4.3, "reviews": 602, "addr": "310 S Third St, San Jose, CA 95112"},
    {"name": "Boba Bliss", "lat": 37.3974483, "lng": -121.8736499, "rating": 4.8, "reviews": 114, "addr": "1671 N Capitol Ave, San Jose, CA 95132"},
    {"name": "Boba Guys", "lat": 37.3195237, "lng": -121.9475666, "rating": 3.8, "reviews": 417, "addr": "378 Santana Row Suite 1115, San Jose, CA 95128"},
    {"name": "Boba Love", "lat": 37.3220585, "lng": -121.8274478, "rating": 4.1, "reviews": 129, "addr": "1661 Tully Rd, San Jose, CA 95122"},
    {"name": "Boba Nation Grand - San Jose", "lat": 37.3246607, "lng": -121.8144978, "rating": 4.7, "reviews": 1040, "addr": "2200 Eastridge Loop #11056, San Jose, CA 95122"},
    {"name": "Boba Passion", "lat": 37.366068, "lng": -121.8618776, "rating": 5.0, "reviews": 6, "addr": "1901 Las Plumas Ave STE 30, San Jose, CA 95133"},
    {"name": "Boba Pub San Jose", "lat": 37.2490945, "lng": -121.8045391, "rating": 4.6, "reviews": 287, "addr": "5711 Cottle Rd, San Jose, CA 95123"},
    {"name": "Bobaholics", "lat": 37.3843122, "lng": -121.897394, "rating": 4.2, "reviews": 549, "addr": "1055 E Brokaw Rd #40, San Jose, CA 95131"},
    {"name": "Bobaholics", "lat": 37.3665861, "lng": -121.8505441, "rating": 4.2, "reviews": 366, "addr": "2323 McKee Rd #8, San Jose, CA 95116"},
    {"name": "Bobo Drinks", "lat": 37.329658, "lng": -121.859104, "rating": 3.7, "reviews": 352, "addr": "779 Story Rd #80, San Jose, CA 95122"},
    {"name": "Breaktime Tea - San Jose", "lat": 37.3353736, "lng": -121.8865192, "rating": 4.3, "reviews": 259, "addr": "110 E San Fernando St, San Jose, CA 95112"},
    {"name": "Co Ba Dessert, Tea & Coffee", "lat": 37.4109019, "lng": -121.9461343, "rating": 4.5, "reviews": 594, "addr": "3730 N First St Ste. 110, San Jose, CA 95134"},
    {"name": "CoCo Bubble Tea - San Jose", "lat": 37.3695315, "lng": -121.8801382, "rating": 4.2, "reviews": 287, "addr": "1477 Berryessa Rd Suite 40, San Jose, CA 95133"},
    {"name": "Coffee & Water Lab", "lat": 37.3155753, "lng": -121.9765562, "rating": 4.5, "reviews": 816, "addr": "603 Saratoga Ave #40, San Jose, CA 95129"},
    {"name": "Cool Tea Bar", "lat": 37.3194758, "lng": -121.8236945, "rating": 4.6, "reviews": 73, "addr": "2569 S King Rd #8C, San Jose, CA 95122"},
    {"name": "Cozy Tea Loft", "lat": 37.3089354, "lng": -121.9940657, "rating": 4.3, "reviews": 361, "addr": "5152 Moorpark Ave #50, San Jose, CA 95129"},
    {"name": "Ding Tea House", "lat": 37.2930222, "lng": -121.8331657, "rating": 4.2, "reviews": 144, "addr": "3151 Senter Rd Suite# 120, San Jose, CA 95111"},
    {"name": "Dr.ink", "lat": 37.3363155, "lng": -121.8953785, "rating": 4.6, "reviews": 753, "addr": "77 N Almaden Ave #70, San Jose, CA 95110"},
    {"name": "Dumont Creamery & Café", "lat": 37.3355848, "lng": -121.8937742, "rating": 4.7, "reviews": 445, "addr": "28 N Almaden Ave Suite 40, San Jose, CA 95110"},
    {"name": "Egghead/ Sando Cafe", "lat": 37.235936, "lng": -121.803366, "rating": 4.1, "reviews": 229, "addr": "6201 Santa Teresa Blvd, San Jose, CA 95123"},
    {"name": "Feng Cha Teahouse - Almaden", "lat": 37.2511282, "lng": -121.8792452, "rating": 4.4, "reviews": 176, "addr": "5353 Almaden Expy m26, San Jose, CA 95118"},
    {"name": "Formosa Aroma 島嶼茶鄉 - San Jose, CA", "lat": 37.2927979, "lng": -121.991952, "rating": 4.7, "reviews": 304, "addr": "5205 Prospect Rd #135, San Jose, CA 95129"},
    {"name": "Fruitea Refreshers", "lat": 37.248622, "lng": -121.8579239, "rating": 4.8, "reviews": 96, "addr": "860 Blossom Hill Rd, San Jose, CA 95123"},
    {"name": "Gong Cha", "lat": 37.2924814, "lng": -121.9888133, "rating": 3.7, "reviews": 251, "addr": "1600 Saratoga Ave #115, San Jose, CA 95129"},
    {"name": "Gong Cha Willow Glen", "lat": 37.3046517, "lng": -121.9141158, "rating": 4.4, "reviews": 429, "addr": "1087 Meridian Ave #10, San Jose, CA 95125"},
    {"name": "Haiku Teahouse", "lat": 37.3699681, "lng": -121.8791696, "rating": 4.6, "reviews": 380, "addr": "1501 Berryessa Rd Suite 35, San Jose, CA 95133"},
    {"name": "Happy Lemon", "lat": 37.2931055, "lng": -121.9970156, "rating": 4.3, "reviews": 223, "addr": "5379 Prospect Rd, San Jose, CA 95129"},
    {"name": "Happy Lemon", "lat": 37.3405216, "lng": -121.9064138, "rating": 4.4, "reviews": 341, "addr": "567 Coleman Ave #10, San Jose, CA 95110"},
    {"name": "Happy Lemon", "lat": 37.3314514, "lng": -121.8580673, "rating": 4.0, "reviews": 155, "addr": "919 Story Rd, San Jose, CA 95122"},
    {"name": "Happy Lemon", "lat": 37.369576, "lng": -121.8450847, "rating": 4.2, "reviews": 204, "addr": "311 N Capitol Ave suite C, San Jose, CA 95133"},
    {"name": "Happy Lemon", "lat": 37.3088348, "lng": -121.8130053, "rating": 4.4, "reviews": 279, "addr": "3005 Silver Creek Rd STE 112, San Jose, CA 95121"},
    {"name": "Happy Lemon", "lat": 37.2502038, "lng": -121.8442963, "rating": 4.3, "reviews": 272, "addr": "630 Blossom Hill Rd #30, San Jose, CA 95123"},
    {"name": "Hello Tea", "lat": 37.3012981, "lng": -121.8228181, "rating": 4.1, "reviews": 272, "addr": "1051 E Capitol Expy, San Jose, CA 95121"},
    {"name": "Insomnibar", "lat": 37.2582771, "lng": -121.7849461, "rating": 4.8, "reviews": 217, "addr": "5978 Silver Creek Valley Rd #25, San Jose, CA 95138"},
    {"name": "Izumi Matcha", "lat": 37.3084445, "lng": -121.8139182, "rating": 4.3, "reviews": 379, "addr": "3005 Silver Creek Rd STE 142, San Jose, CA 95121"},
    {"name": "J&K Boba", "lat": 37.3461498, "lng": -121.8664706, "rating": 0.0, "reviews": 1, "addr": "68 S 24th St, San Jose, CA 95116"},
    {"name": "Jasmine Kocha", "lat": 37.2688565, "lng": -121.9064685, "rating": 4.6, "reviews": 264, "addr": "3129 Meridian Ave #20, San Jose, CA 95124"},
    {"name": "Kung Fu Tea", "lat": 37.3197573, "lng": -121.9748742, "rating": 4.3, "reviews": 558, "addr": "457 Saratoga Ave, San Jose, CA 95129"},
    {"name": "MACU TEA - Berryessa", "lat": 37.3886286, "lng": -121.8613201, "rating": 4.1, "reviews": 178, "addr": "1196 N Capitol Ave, San Jose, CA 95132"},
    {"name": "MACU TEA - Paloma", "lat": 37.3087487, "lng": -121.8141294, "rating": 4.3, "reviews": 225, "addr": "3005 Silver Creek Rd STE 158, San Jose, CA 95121"},
    {"name": "MTeaShop", "lat": 37.2641019, "lng": -121.9166965, "rating": 4.6, "reviews": 173, "addr": "1795 Hillsdale Ave #40, San Jose, CA 95124"},
    {"name": "Maruwu Seicha", "lat": 37.3363189, "lng": -121.894835, "rating": 4.1, "reviews": 151, "addr": "100 N Almaden Ave #184, San Jose, CA 95110"},
    {"name": "Meow Tea", "lat": 37.2996001, "lng": -121.8403516, "rating": 4.5, "reviews": 70, "addr": "2857 Senter Rd G, San Jose, CA 95111"},
    {"name": "Milk Tea Lab", "lat": 37.2533702, "lng": -121.9031693, "rating": 4.0, "reviews": 384, "addr": "1601 Branham Ln #40, San Jose, CA 95118"},
    {"name": "Milktea Way", "lat": 37.3302777, "lng": -121.8559379, "rating": 4.6, "reviews": 246, "addr": "956 Story Rd, San Jose, CA 95122"},
    {"name": "My Bottle", "lat": 37.3089037, "lng": -121.813364, "rating": 4.5, "reviews": 417, "addr": "3005 Silver Creek Rd STE 120, San Jose, CA 95121"},
    {"name": "N7 Draft Tea + Coffee", "lat": 37.3156118, "lng": -121.9772148, "rating": 4.5, "reviews": 224, "addr": "4306 Moorpark Ave, San Jose, CA 95129"},
    {"name": "N7 Draft Tea + Coffee", "lat": 37.3094951, "lng": -121.8137727, "rating": 4.3, "reviews": 201, "addr": "3005 Silver Creek Rd STE 184, San Jose, CA 95121"},
    {"name": "NCM Cafe", "lat": 37.3966834, "lng": -121.8892291, "rating": 4.6, "reviews": 227, "addr": "2092 Concourse Dr STE 9, San Jose, CA 95131"},
    {"name": "Noveltea Catering", "lat": 37.2710913, "lng": -121.936445, "rating": 5.0, "reviews": 12, "addr": "2784 S Bascom Ave Unit A, San Jose, CA 95124"},
    {"name": "Passion-T Snacks & Desserts", "lat": 37.3106914, "lng": -121.8497072, "rating": 4.2, "reviews": 311, "addr": "2266 Senter Rd STE 128, San Jose, CA 95112"},
    {"name": "Pekoe", "lat": 37.3738171, "lng": -121.8722391, "rating": 4.4, "reviews": 302, "addr": "996 Lundy Ave, San Jose, CA 95133"},
    {"name": "Pekoe", "lat": 37.3146179, "lng": -121.7901318, "rating": 4.3, "reviews": 480, "addr": "3276 S White Rd, San Jose, CA 95148"},
    {"name": "Phin Cafe - Blossom Hill Road | San Jose", "lat": 37.2520913, "lng": -121.8321109, "rating": 4.4, "reviews": 510, "addr": "461 Blossom Hill Rd g, San Jose, CA 95123"},
    {"name": "Pop Up Tea", "lat": 37.2670825, "lng": -121.8337216, "rating": 4.4, "reviews": 559, "addr": "185 Branham Ln, San Jose, CA 95136"},
    {"name": "Pure Tea Bar", "lat": 37.2363188, "lng": -121.8041781, "rating": 4.4, "reviews": 288, "addr": "6195 Santa Teresa Blvd, San Jose, CA 95123"},
    {"name": "Quickly", "lat": 37.3249644, "lng": -121.8138357, "rating": 4.0, "reviews": 191, "addr": "2200 Eastridge Loop #1091, San Jose, CA 95122"},
    {"name": "R&B TEA SAN JOSE", "lat": 37.3322693, "lng": -121.8588498, "rating": 3.9, "reviews": 546, "addr": "929 Story Rd Suite 2039, San Jose, CA 95122"},
    {"name": "R&B Tea Silver Creek", "lat": 37.3092122, "lng": -121.8114512, "rating": 4.2, "reviews": 328, "addr": "1757 E Capitol Expy, San Jose, CA 95121"},
    {"name": "Rose Tea Lounge - San Jose", "lat": 37.3330524, "lng": -121.8522359, "rating": 4.4, "reviews": 279, "addr": "1210 Story Rd, San Jose, CA 95122"},
    {"name": "Shake Tea", "lat": 37.2523674, "lng": -121.8647755, "rating": 3.9, "reviews": 181, "addr": "925 Blossom Hill Rd #1378, San Jose, CA 95123"},
    {"name": "Sharetea", "lat": 37.3875213, "lng": -121.8828791, "rating": 4.4, "reviews": 313, "addr": "1728 Hostetter Rd STE 30, San Jose, CA 95131"},
    {"name": "Sharetea", "lat": 37.3249785, "lng": -121.9472853, "rating": 4.0, "reviews": 617, "addr": "2855 Stevens Creek Blvd, San Jose, CA 95128"},
    {"name": "SimpleTea", "lat": 37.3875255, "lng": -121.8579659, "rating": 3.3, "reviews": 149, "addr": "2520 Berryessa Rd, San Jose, CA 95132"},
    {"name": "Sinceretea", "lat": 37.3527714, "lng": -121.8921082, "rating": 4.5, "reviews": 506, "addr": "392 E Taylor St, San Jose, CA 95112"},
    {"name": "Snow Boba", "lat": 37.2381653, "lng": -121.8317348, "rating": 4.7, "reviews": 43, "addr": "6029 Snell Ave, San Jose, CA 95123"},
    {"name": "Soyful Desserts", "lat": 37.3321611, "lng": -121.8569111, "rating": 4.1, "reviews": 67, "addr": "999 Story Rd, San Jose, CA 95122"},
    {"name": "Sunright Tea Studio - San Jose", "lat": 37.3236552, "lng": -121.9139121, "rating": 4.4, "reviews": 258, "addr": "1401 W San Carlos St, San Jose, CA 95126"},
    {"name": "Sweet Gelato | Tea Lounge", "lat": 37.3313165, "lng": -121.8571634, "rating": 4.2, "reviews": 649, "addr": "979 Story Rd Unit 7084, San Jose, CA 95122"},
    {"name": "T-Square Coffee & Tea", "lat": 37.311126, "lng": -121.8951488, "rating": 4.7, "reviews": 293, "addr": "1102 Bird Ave. # 20, San Jose, CA 95125"},
    {"name": "T4 Almaden Valley", "lat": 37.2102465, "lng": -121.8453115, "rating": 3.9, "reviews": 142, "addr": "6950 Almaden Expy, San Jose, CA 95120"},
    {"name": "TEAZENTEA", "lat": 37.2739288, "lng": -121.8506569, "rating": 4.2, "reviews": 502, "addr": "422 W Capitol Expy, San Jose, CA 95136"},
    {"name": "TP TEA - Berryessa", "lat": 37.3878549, "lng": -121.8599462, "rating": 4.4, "reviews": 183, "addr": "1152 N Capitol Ave, San Jose, CA 95132"},
    {"name": "TP TEA - San Jose Oakridge", "lat": 37.2520873, "lng": -121.8630227, "rating": 4.3, "reviews": 292, "addr": "925 Blossom Hill Rd #1228, San Jose, CA 95123"},
    {"name": "Tapioca Express", "lat": 37.3652831, "lng": -121.850699, "rating": 4.1, "reviews": 586, "addr": "2285 McKee Rd, San Jose, CA 95116"},
    {"name": "Tapioca Express", "lat": 37.3030209, "lng": -121.8647407, "rating": 4.0, "reviews": 430, "addr": "81 Curtner Ave #40, San Jose, CA 95125"},
    {"name": "Tastea Berryessa", "lat": 37.3876548, "lng": -121.860188, "rating": 4.3, "reviews": 509, "addr": "1160 N Capitol Ave, San Jose, CA 95132"},
    {"name": "Tastea Communications Hill", "lat": 37.2751846, "lng": -121.8516099, "rating": 4.2, "reviews": 370, "addr": "509 W Capitol Expy, San Jose, CA 95136"},
    {"name": "Tastea Evergreen", "lat": 37.315323, "lng": -121.793377, "rating": 4.2, "reviews": 311, "addr": "3247 S White Rd, San Jose, CA 95148"},
    {"name": "Tastea Vietnam Town", "lat": 37.3315002, "lng": -121.8571809, "rating": 4.0, "reviews": 332, "addr": "979 Story Rd Unit 7075, San Jose, CA 95122"},
    {"name": "Tea Alley", "lat": 37.3354416, "lng": -121.8898505, "rating": 4.1, "reviews": 172, "addr": "40 S 1st St, San Jose, CA 95113"},
    {"name": "Tea Degree", "lat": 37.336421, "lng": -121.8810451, "rating": 2.8, "reviews": 7, "addr": "211 S 9th St, San Jose, CA 95112"},
    {"name": "Tea Era", "lat": 37.2359784, "lng": -121.8031887, "rating": 4.5, "reviews": 374, "addr": "6205 Santa Teresa Blvd, San Jose, CA 95119"},
    {"name": "Tea Top 台灣第一味", "lat": 37.308664, "lng": -122.01267, "rating": 4.5, "reviews": 309, "addr": "6158 Bollinger Rd, San Jose, CA 95129"},
    {"name": "Teaqueria", "lat": 37.3407623, "lng": -121.9177478, "rating": 4.5, "reviews": 189, "addr": "894 Emory St, San Jose, CA 95126"},
    {"name": "Teasociety San Jose", "lat": 37.306078, "lng": -121.8105455, "rating": 4.2, "reviews": 287, "addr": "1658 E Capitol Expy, San Jose, CA 95121"},
    {"name": "Teaspoon Almaden", "lat": 37.2613878, "lng": -121.8758303, "rating": 4.8, "reviews": 288, "addr": "4750 Almaden Expy UNIT 116, San Jose, CA 95118"},
    {"name": "Teaspoon Hostetter", "lat": 37.3870354, "lng": -121.8835637, "rating": 4.5, "reviews": 419, "addr": "1698 Hostetter Rd, San Jose, CA 95131"},
    {"name": "Teaspoon Saratoga", "lat": 37.315275, "lng": -121.978109, "rating": 4.6, "reviews": 581, "addr": "4328 Moorpark Ave, San Jose, CA 95129"},
    {"name": "The Orange Tabby", "lat": 37.3877058, "lng": -121.8999924, "rating": 4.8, "reviews": 64, "addr": "1344 Ridder Park Dr, San Jose, CA 95131"},
    {"name": "The Sweet Corner", "lat": 37.332775, "lng": -121.8580235, "rating": 4.0, "reviews": 484, "addr": "989 Story Rd, San Jose, CA 95122"},
    {"name": "Tisane", "lat": 37.3308393, "lng": -121.8106657, "rating": 4.3, "reviews": 315, "addr": "2980 E Capitol Expy #50, San Jose, CA 95148"},
    {"name": "Tisane (North Valley)", "lat": 37.4041893, "lng": -121.8820141, "rating": 4.3, "reviews": 239, "addr": "2671 Cropley Ave, San Jose, CA 95132"},
    {"name": "Tpumps", "lat": 37.3121367, "lng": -122.0318249, "rating": 4.4, "reviews": 265, "addr": "7290 Bollinger Rd, San Jose, CA 95129"},
    {"name": "UMe | Tea & Snacks", "lat": 37.2614031, "lng": -121.8754593, "rating": 4.2, "reviews": 259, "addr": "4750 Almaden Expy #136, San Jose, CA 95118"},
    {"name": "UMe | Tea & Snacks", "lat": 37.3831731, "lng": -121.8944946, "rating": 4.9, "reviews": 119, "addr": "1704 Oakland Rd #300, San Jose, CA 95131"},
    {"name": "UMe | Tea & Snacks", "lat": 37.306322, "lng": -121.8993801, "rating": 4.8, "reviews": 258, "addr": "1228 Lincoln Ave, San Jose, CA 95125"},
    {"name": "V KOCHA", "lat": 37.3555191, "lng": -121.8511215, "rating": 3.5, "reviews": 2, "addr": "1915 Alum Rock Ave C, San Jose, CA 95116"},
    {"name": "WUSHILAND BOBA - San Jose", "lat": 37.2525666, "lng": -121.8648164, "rating": 5.0, "reviews": 6, "addr": "925 Blossom Hill Rd #1355, San Jose, CA 95123"},
    {"name": "Yifang Taiwan Fruit Tea", "lat": 37.3046432, "lng": -122.0331824, "rating": 3.8, "reviews": 521, "addr": "1147 S De Anza Blvd, San Jose, CA 95129"},
    {"name": "heytea (Hostetter)", "lat": 37.3871569, "lng": -121.8853509, "rating": 4.7, "reviews": 710, "addr": "1628 Hostetter Rd ste h, San Jose, CA 95131"},
    {"name": "i-Tea San Jose", "lat": 37.3123461, "lng": -121.8097108, "rating": 4.4, "reviews": 323, "addr": "2936 Aborn Sq, San Jose, CA 95121"},
    {"name": "i-tea SR", "lat": 37.3146462, "lng": -121.8712845, "rating": 4.7, "reviews": 293, "addr": "1510 Monterey Rd #30, San Jose, CA 95110"},
    # -- Cupertino --
    {"name": "Boba Guys at Local Kitchens", "lat": 37.322747, "lng": -122.053518, "rating": 3.6, "reviews": 9, "addr": "21666 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Café LaTTea", "lat": 37.3231977, "lng": -122.0123423, "rating": 4.4, "reviews": 451, "addr": "19501 Stevens Creek Blvd STE 101, Cupertino, CA 95014"},
    {"name": "Chicha San Chen 吃茶三千", "lat": 37.3225683, "lng": -122.0348057, "rating": 4.6, "reviews": 1651, "addr": "20688 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Fantasia Coffee & Tea", "lat": 37.3359492, "lng": -122.0158942, "rating": 4.3, "reviews": 320, "addr": "10933 N Wolfe Rd, Cupertino, CA 95014"},
    {"name": "HEYTEA (Cupertino)", "lat": 37.3238225, "lng": -122.0105082, "rating": 4.0, "reviews": 161, "addr": "19469 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Izumi Matcha", "lat": 37.3218001, "lng": -122.0180906, "rating": 4.2, "reviews": 534, "addr": "19740 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Liang's Village", "lat": 37.321987, "lng": -122.0330077, "rating": 4.1, "reviews": 2322, "addr": "20530 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Mia's", "lat": 37.3245956, "lng": -122.0339109, "rating": 3.9, "reviews": 414, "addr": "10118 Bandley Dr ste g, Cupertino, CA 95014"},
    {"name": "Molly Tea (Cupertino)", "lat": 37.3227792, "lng": -122.0068662, "rating": 4.2, "reviews": 549, "addr": "19110 Stevens Creek Blvd ste a, Cupertino, CA 95014"},
    {"name": "MoonTea", "lat": 37.3223447, "lng": -122.0167466, "rating": 4.5, "reviews": 324, "addr": "19620 Stevens Creek Blvd #180, Cupertino, CA 95014"},
    {"name": "O2 Valley", "lat": 37.3226989, "lng": -122.0058359, "rating": 4.5, "reviews": 659, "addr": "19058 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Shang Yu Lin-Cupertino上宇林", "lat": 37.3369331, "lng": -122.040307, "rating": 4.1, "reviews": 611, "addr": "20956 Homestead Rd D, Cupertino, CA 95014"},
    {"name": "Shu Shia 树夏", "lat": 37.3152077, "lng": -122.0329128, "rating": 4.3, "reviews": 360, "addr": "10525 S De Anza Blvd #145, Cupertino, CA 95014"},
    {"name": "Shuyi Grass Jelly & Tea 书亦烧仙草 (Cupertino)", "lat": 37.3362519, "lng": -122.0152063, "rating": 4.8, "reviews": 336, "addr": "10963 N Wolfe Rd, Cupertino, CA 95014"},
    {"name": "TP TEA - Cupertino", "lat": 37.311288, "lng": -122.023624, "rating": 4.4, "reviews": 1100, "addr": "10787 S Blaney Ave, Cupertino, CA 95014"},
    {"name": "Tea Era", "lat": 37.3371864, "lng": -122.040362, "rating": 4.2, "reviews": 819, "addr": "20916 Homestead Rd, Cupertino, CA 95014"},
    {"name": "Ten Ren Tea", "lat": 37.335669, "lng": -122.0149175, "rating": 4.5, "reviews": 291, "addr": "10881 N Wolfe Rd, Cupertino, CA 95014"},
    {"name": "UMe | Tea & Snacks", "lat": 37.3358039, "lng": -122.0156374, "rating": 4.5, "reviews": 666, "addr": "10887 N Wolfe Rd, Cupertino, CA 95014"},
    {"name": "Wanpo Tea Shop", "lat": 37.3233775, "lng": -122.0072072, "rating": 4.4, "reviews": 338, "addr": "19319 Stevens Creek Blvd, Cupertino, CA 95014"},
    {"name": "Wow Tea Drink - Cupertino", "lat": 37.3232882, "lng": -122.0127315, "rating": 4.5, "reviews": 177, "addr": "19505 Stevens Creek Blvd #102, Cupertino, CA 95014"},
    # -- Santa Clara --
    {"name": "Bambu Dessert Drinks", "lat": 37.3862861, "lng": -121.9607754, "rating": 4.6, "reviews": 263, "addr": "3700 Thomas Rd #101, Santa Clara, CA 95054"},
    {"name": "Beastea", "lat": 37.353083, "lng": -121.9770847, "rating": 4.1, "reviews": 797, "addr": "2785 El Camino Real, Santa Clara, CA 95051"},
    {"name": "Boba Pup", "lat": 37.3459399, "lng": -121.9791525, "rating": 4.1, "reviews": 1032, "addr": "1080 Kiely Blvd, Santa Clara, CA 95051"},
    {"name": "CAFFE:iN - Santa Clara", "lat": 37.3449794, "lng": -121.9343894, "rating": 4.3, "reviews": 413, "addr": "2421 The Alameda #101, Santa Clara, CA 95050"},
    {"name": "CoCo Bubble Tea - Valley Fair", "lat": 37.325075, "lng": -121.944007, "rating": 3.7, "reviews": 401, "addr": "2855 Stevens Creek Blvd Ste 1089, Santa Clara, CA 95050"},
    {"name": "Gong Cha", "lat": 37.3816968, "lng": -121.9748852, "rating": 3.9, "reviews": 424, "addr": "2712 Augustine Dr #110, Santa Clara, CA 95054"},
    {"name": "Honeyberry", "lat": 37.3516214, "lng": -121.9929164, "rating": 4.3, "reviews": 507, "addr": "3488 El Camino Real, Santa Clara, CA 95051"},
    {"name": "Jiaren Cafe: Coffee, Boba & Events", "lat": 37.3485601, "lng": -121.9457339, "rating": 4.6, "reviews": 3441, "addr": "1171 Homestead Rd #140b, Santa Clara, CA 95050"},
    {"name": "Matsu Matcha", "lat": 37.3517364, "lng": -121.9814778, "rating": 4.0, "reviews": 597, "addr": "3030 El Camino Real, Santa Clara, CA 95051"},
    {"name": "Meet Fresh Santa Clara", "lat": 37.3950218, "lng": -121.9467505, "rating": 3.1, "reviews": 1016, "addr": "3958 Rivermark Plaza, Santa Clara, CA 95054"},
    {"name": "OMG Tea", "lat": 37.3483367, "lng": -121.9459311, "rating": 4.2, "reviews": 418, "addr": "1171 Homestead Rd #115, Santa Clara, CA 95050"},
    {"name": "Pink Pink Tea Shoppe", "lat": 37.325255, "lng": -121.9455334, "rating": 4.3, "reviews": 276, "addr": "2855 Stevens Creek Blvd ste 2299 floor 2, Santa Clara, CA 95050"},
    {"name": "R&B Tea", "lat": 37.3260456, "lng": -121.9441224, "rating": 2.7, "reviews": 194, "addr": "2855 Stevens Creek Blvd Suite 2456, Santa Clara, CA 95050"},
    {"name": "Rabbit Rabbit Tea", "lat": 37.3254815, "lng": -121.946401, "rating": 3.7, "reviews": 425, "addr": "2855 Stevens Creek Blvd, Santa Clara, CA 95050"},
    {"name": "Teaspoon El Camino", "lat": 37.3519792, "lng": -121.9910948, "rating": 4.4, "reviews": 423, "addr": "3450 El Camino Real #103, Santa Clara, CA 95051"},
    {"name": "UMe | Tea & Snacks", "lat": 37.3444187, "lng": -121.9324703, "rating": 4.6, "reviews": 381, "addr": "2215 The Alameda, Santa Clara, CA 95050"},
    {"name": "frozo's", "lat": 37.3504638, "lng": -121.9438781, "rating": 4.6, "reviews": 253, "addr": "1000 Lafayette St D, Santa Clara, CA 95050"},
    # -- Sunnyvale --
    {"name": "408 Boba", "lat": 37.353016, "lng": -122.004481, "rating": 4.9, "reviews": 57, "addr": "1053 E El Camino Real #1, Sunnyvale, CA 94087"},
    {"name": "Alma Dessert", "lat": 37.376624, "lng": -122.030356, "rating": 4.3, "reviews": 230, "addr": "165 S Murphy Ave Suite D, Sunnyvale, CA 94086"},
    {"name": "Bambu Dessert Drinks", "lat": 37.3762866, "lng": -122.0312401, "rating": 4.1, "reviews": 887, "addr": "189 W Washington Ave, Sunnyvale, CA 94086"},
    {"name": "Blossom Chai Cafe", "lat": 37.37615, "lng": -122.0306344, "rating": 4.1, "reviews": 513, "addr": "199 S Murphy Ave, Sunnyvale, CA 94086"},
    {"name": "Cha La One", "lat": 37.3831224, "lng": -122.0460903, "rating": 4.4, "reviews": 144, "addr": "1026 W Evelyn Ave K224, Sunnyvale, CA 94086"},
    {"name": "Chun Yang Tea", "lat": 37.3735957, "lng": -121.9994804, "rating": 4.1, "reviews": 407, "addr": "1120 Kifer Rd Suite C, Sunnyvale, CA 94086"},
    {"name": "Gong Cha", "lat": 37.3397518, "lng": -122.0425399, "rating": 4.2, "reviews": 338, "addr": "1641 Hollenbeck Ave, Sunnyvale, CA 94087"},
    {"name": "HEYTEA (Sunnyvale)", "lat": 37.3682254, "lng": -122.0355835, "rating": 4.5, "reviews": 650, "addr": "302 W El Camino Real, Sunnyvale, CA 94087"},
    {"name": "Happy Flower Eatery & Boba", "lat": 37.406605, "lng": -121.9977575, "rating": 4.7, "reviews": 529, "addr": "1274 Persian Dr, Sunnyvale, CA 94089"},
    {"name": "Happy Lemon", "lat": 37.382667, "lng": -121.9952452, "rating": 4.4, "reviews": 275, "addr": "520 Lawrence Expy #301, Sunnyvale, CA 94085"},
    {"name": "K Tea Cafe", "lat": 37.3770903, "lng": -122.0305967, "rating": 4.1, "reviews": 693, "addr": "139 S Murphy Ave B, Sunnyvale, CA 94086"},
    {"name": "Molly Tea(Sunnyvale)", "lat": 37.3619851, "lng": -122.0244755, "rating": 4.6, "reviews": 1372, "addr": "605 E El Camino Real Suite 1, Sunnyvale, CA 94087"},
    {"name": "MoonTea", "lat": 37.3704248, "lng": -122.0410635, "rating": 4.2, "reviews": 613, "addr": "513 S Pastoria Ave, Sunnyvale, CA 94086"},
    {"name": "Pekoe", "lat": 37.3717231, "lng": -122.0460436, "rating": 3.8, "reviews": 216, "addr": "939 W El Camino Real Suite 117, Sunnyvale, CA 94087"},
    {"name": "Sips & Scoops", "lat": 37.3516561, "lng": -122.0318704, "rating": 5.0, "reviews": 289, "addr": "1300 Sunnyvale Saratoga Rd, Sunnyvale, CA 94087"},
    {"name": "Sunright Tea Studio - Sunnyvale", "lat": 37.3566016, "lng": -122.0172865, "rating": 4.4, "reviews": 650, "addr": "795 E El Camino Real, Sunnyvale, CA 94087"},
    {"name": "TANING - Sunnyvale", "lat": 37.3672574, "lng": -122.033443, "rating": 4.7, "reviews": 282, "addr": "715 Sunnyvale Saratoga Rd, Sunnyvale, CA 94087"},
    {"name": "TP TEA - Sunnyvale", "lat": 37.363467, "lng": -122.0261262, "rating": 4.5, "reviews": 271, "addr": "567b E El Camino Real, Sunnyvale, CA 94087"},
    {"name": "Tastea Sunnyvale", "lat": 37.3667646, "lng": -122.0320163, "rating": 4.2, "reviews": 394, "addr": "114 E El Camino Real, Sunnyvale, CA 94087"},
    {"name": "Teazzi Tea Shop", "lat": 37.3744394, "lng": -122.0325276, "rating": 4.1, "reviews": 346, "addr": "200 W McKinley Ave #105, Sunnyvale, CA 94086"},
    # -- Milpitas --
    {"name": "3catea", "lat": 37.4559033, "lng": -121.9118064, "rating": 3.6, "reviews": 402, "addr": "1777 N Milpitas Blvd, Milpitas, CA 95035"},
    {"name": "Chick & Tea Milpitas", "lat": 37.4552528, "lng": -121.9116639, "rating": 4.2, "reviews": 718, "addr": "1723 N Milpitas Blvd, Milpitas, CA 95035"},
    {"name": "CoCo Bubble Tea - Milpitas", "lat": 37.4560294, "lng": -121.9102279, "rating": 3.4, "reviews": 312, "addr": "1766 N Milpitas Blvd, Milpitas, CA 95035"},
    {"name": "FENG CHA TEA HOUSE", "lat": 37.4337027, "lng": -121.8976817, "rating": 4.3, "reviews": 431, "addr": "489 E Calaveras Blvd, Milpitas, CA 95035"},
    {"name": "Fantasia Coffee & Tea", "lat": 37.420841, "lng": -121.916504, "rating": 3.9, "reviews": 358, "addr": "528 Barber Ln, Milpitas, CA 95035"},
    {"name": "Honey Express Bento & Tea 甜心便當奶茶", "lat": 37.4474127, "lng": -121.9041642, "rating": 4.6, "reviews": 541, "addr": "279 Jacklin Rd, Milpitas, CA 95035"},
    {"name": "K On the Go", "lat": 37.4279089, "lng": -121.9113095, "rating": 4.5, "reviews": 514, "addr": "261 W Calaveras Blvd, Milpitas, CA 95035"},
    {"name": "Milksha Great Mall", "lat": 37.4163596, "lng": -121.898994, "rating": 4.0, "reviews": 152, "addr": "447 Great Mall Dr Entrance 1, Milpitas, CA 95035"},
    {"name": "Pekoe", "lat": 37.4167884, "lng": -121.8738939, "rating": 3.4, "reviews": 156, "addr": "1404 S Park Victoria Dr, Milpitas, CA 95035"},
    {"name": "Quickly", "lat": 37.417615, "lng": -121.8744037, "rating": 3.5, "reviews": 252, "addr": "1350 S Park Victoria Dr # 30, Milpitas, CA 95035"},
    {"name": "R&B Tea - Nitro", "lat": 37.4296087, "lng": -121.9075945, "rating": 3.7, "reviews": 676, "addr": "60 S Abel St, Milpitas, CA 95035"},
    {"name": "Sunright Tea Studio - Milpitas", "lat": 37.4549753, "lng": -121.9115788, "rating": 4.4, "reviews": 467, "addr": "1693 N Milpitas Blvd, Milpitas, CA 95035"},
    {"name": "TP TEA - Milpitas", "lat": 37.4575549, "lng": -121.9102095, "rating": 4.3, "reviews": 169, "addr": "108 Dixon Rd, Milpitas, CA 95035"},
    {"name": "Tea Top Milpitas", "lat": 37.42642, "lng": -121.9214078, "rating": 4.5, "reviews": 440, "addr": "82 Ranch Dr, Milpitas, CA 95035"},
    {"name": "Tea number one", "lat": 37.4192284, "lng": -121.9157526, "rating": 5.0, "reviews": 3, "addr": "686 Barber Ln, Milpitas, CA 95035"},
    {"name": "Teaspoon Milpitas", "lat": 37.4288537, "lng": -121.9111729, "rating": 4.5, "reviews": 644, "addr": "201 W Calaveras Blvd, Milpitas, CA 95035"},
    {"name": "Ten Ren Tea Co of Milpitas", "lat": 37.4555604, "lng": -121.9099429, "rating": 4.2, "reviews": 91, "addr": "1732 N Milpitas Blvd, Milpitas, CA 95035"},
    {"name": "UMe | Tea & Snacks", "lat": 37.4237524, "lng": -121.9178675, "rating": 4.6, "reviews": 705, "addr": "272 Barber Ct, Milpitas, CA 95035"},
    {"name": "UMe | Tea & Snacks", "lat": 37.41697, "lng": -121.8977643, "rating": 4.5, "reviews": 229, "addr": "450 Great Mall Dr #5, Milpitas, CA 95035"},
    {"name": "Xing Fu Tang", "lat": 37.4554225, "lng": -121.9116783, "rating": 4.1, "reviews": 838, "addr": "1735 N Milpitas Blvd, Milpitas, CA 95035"},
    {"name": "heytea (Milpitas)", "lat": 37.4224675, "lng": -121.9168824, "rating": 4.6, "reviews": 596, "addr": "372 Barber Ln, Milpitas, CA 95035"},
    {"name": "i-Tea Milpitas", "lat": 37.4331861, "lng": -121.8928667, "rating": 4.3, "reviews": 435, "addr": "760 E Calaveras Blvd, Milpitas, CA 95035"},
    # -- Mountain View --
    {"name": "Boba Bliss", "lat": 37.401487, "lng": -122.1131052, "rating": 4.6, "reviews": 601, "addr": "685 San Antonio Rd Suite 15, Mountain View, CA 94040"},
    {"name": "Happy Lemon", "lat": 37.3937018, "lng": -122.0784145, "rating": 4.0, "reviews": 201, "addr": "742 Villa St, Mountain View, CA 94041"},
    {"name": "Junbi Matcha & Tea - Mountain View", "lat": 37.4041613, "lng": -122.1121597, "rating": 4.4, "reviews": 394, "addr": "450 San Antonio Rd Ste K, Mountain View, CA 94040"},
    {"name": "Mochi Waffle Corner", "lat": 37.3756145, "lng": -122.0621831, "rating": 4.3, "reviews": 300, "addr": "805 E El Camino Real Suite F, Mountain View, CA 94040"},
    {"name": "Mr. Sun Tea Mountain View", "lat": 37.3856394, "lng": -122.0842281, "rating": 4.1, "reviews": 420, "addr": "801 W El Camino Real A, Mountain View, CA 94040"},
    {"name": "T. Castle", "lat": 37.393634, "lng": -122.0782408, "rating": 4.6, "reviews": 412, "addr": "738 Villa St, Mountain View, CA 94041"},
    {"name": "Tea Era", "lat": 37.3929293, "lng": -122.0792228, "rating": 4.3, "reviews": 631, "addr": "271 Castro St, Mountain View, CA 94041"},
    {"name": "UMe | Tea & Snacks", "lat": 37.3936622, "lng": -122.0794502, "rating": 4.5, "reviews": 854, "addr": "220 Castro St, Mountain View, CA 94041"},
    {"name": "Verde Tea Cafe", "lat": 37.3941637, "lng": -122.0794885, "rating": 4.2, "reviews": 159, "addr": "852 Villa St, Mountain View, CA 94041"},
    {"name": "Yi Fang Taiwan Fruit Tea", "lat": 37.394429, "lng": -122.0782705, "rating": 4.1, "reviews": 376, "addr": "143 Castro St, Mountain View, CA 94041"},
    {"name": "四季茶馆火锅 Four Seasons Tea House Hot Pot", "lat": 37.3947376, "lng": -122.0788399, "rating": 4.7, "reviews": 430, "addr": "134 Castro St, Mountain View, CA 94041"},
    # -- Los Altos --
    {"name": "Boba Guys Los Altos", "lat": 37.3786262, "lng": -122.1182382, "rating": 4.1, "reviews": 112, "addr": "201 1st St, Los Altos, CA 94022"},
    {"name": "Sweet Diplomacy® Gluten-Free", "lat": 37.3785696, "lng": -122.11819, "rating": 4.7, "reviews": 342, "addr": "209 1st St, Los Altos, CA 94022"},
    {"name": "Teaspoon Los Altos", "lat": 37.4012135, "lng": -122.1144238, "rating": 4.3, "reviews": 675, "addr": "4546 El Camino Real a11, Los Altos, CA 94022"},
    # -- Palo Alto --
    {"name": "Boba Guys Palo Alto", "lat": 37.4386007, "lng": -122.1589247, "rating": 4.3, "reviews": 588, "addr": "855 El Camino Real #120, Palo Alto, CA 94301"},
    {"name": "HE&C Tea + Pot", "lat": 37.4439995, "lng": -122.1620763, "rating": 4.6, "reviews": 716, "addr": "544 Emerson St, Palo Alto, CA 94301"},
    {"name": "Maruwu Seicha - Palo Alto", "lat": 37.4453204, "lng": -122.161961, "rating": 4.0, "reviews": 876, "addr": "250 University Ave STE 101, Palo Alto, CA 94301"},
    {"name": "Molly Tea (Palo Alto)", "lat": 37.4461192, "lng": -122.1610784, "rating": 4.7, "reviews": 637, "addr": "318 University Ave, Palo Alto, CA 94301"},
    {"name": "Mr. Sun Tea Palo Alto", "lat": 37.4474688, "lng": -122.1597402, "rating": 4.1, "reviews": 302, "addr": "436 University Ave, Palo Alto, CA 94301"},
    {"name": "O2 Valley", "lat": 37.4476055, "lng": -122.1595835, "rating": 4.3, "reviews": 560, "addr": "452 University Ave, Palo Alto, CA 94301"},
    {"name": "Pop Tea Bar", "lat": 37.4265169, "lng": -122.1462117, "rating": 4.4, "reviews": 268, "addr": "456 Cambridge Ave, Palo Alto, CA 94306"},
    {"name": "Rabbit Rabbit Cream", "lat": 37.4435822, "lng": -122.1718406, "rating": 3.8, "reviews": 451, "addr": "78 Stanford Shopping Center, Palo Alto, CA 94304"},
    {"name": "Ryokucha Cafe", "lat": 37.4131249, "lng": -122.1250582, "rating": 4.4, "reviews": 164, "addr": "4131 El Camino Real, Palo Alto, CA 94306"},
    {"name": "T4", "lat": 37.4445201, "lng": -122.1633847, "rating": 4.1, "reviews": 373, "addr": "165 University Ave #D, Palo Alto, CA 94301"},
    {"name": "Tea Time in Palo Alto", "lat": 37.444642, "lng": -122.161476, "rating": 4.2, "reviews": 250, "addr": "542 Ramona St, Palo Alto, CA 94301"},
    {"name": "Teaspoon Palo Alto", "lat": 37.4340874, "lng": -122.1294149, "rating": 4.5, "reviews": 408, "addr": "2675 Middlefield Rd C, Palo Alto, CA 94306"},
    {"name": "UMe | Tea & Snacks", "lat": 37.4261194, "lng": -122.1447222, "rating": 4.2, "reviews": 530, "addr": "421 California Ave, Palo Alto, CA 94306"},
    {"name": "Wanpo Tea Shop", "lat": 37.4427023, "lng": -122.1726089, "rating": 3.8, "reviews": 335, "addr": "660 Stanford Shopping Center #721, Palo Alto, CA 94304"},
    {"name": "Wow Tea Drink - Palo Alto", "lat": 37.4246793, "lng": -122.1443119, "rating": 4.9, "reviews": 39, "addr": "2515 El Camino Real Suite 110, Palo Alto, CA 94306"},
    # -- Menlo Park --
    {"name": "Mr. Green Bubble | Menlo Park", "lat": 37.453325, "lng": -122.1835405, "rating": 4.1, "reviews": 424, "addr": "604 Santa Cruz Ave, Menlo Park, CA 94025"},
    {"name": "Tea Friends", "lat": 37.4525008, "lng": -122.1816423, "rating": 4.2, "reviews": 201, "addr": "993 El Camino Real, Menlo Park, CA 94025"},
    # -- Redwood City --
    {"name": "Bobalicious", "lat": 37.4866597, "lng": -122.2293724, "rating": 4.7, "reviews": 66, "addr": "2202 Broadway, Redwood City, CA 94063"},
    {"name": "Happy Lemon", "lat": 37.4859465, "lng": -122.2288828, "rating": 4.3, "reviews": 269, "addr": "851 Middlefield Rd, Redwood City, CA 94063"},
    {"name": "Kung Fu Tea | Woodside Road", "lat": 37.469409, "lng": -122.2230916, "rating": 4.7, "reviews": 382, "addr": "593 Woodside Rd ste d, Redwood City, CA 94061"},
    {"name": "Quickly", "lat": 37.4917634, "lng": -122.2243167, "rating": 4.0, "reviews": 628, "addr": "300 Walnut St, Redwood City, CA 94063"},
    {"name": "Teaspoon Redwood City", "lat": 37.4862578, "lng": -122.2307483, "rating": 4.4, "reviews": 453, "addr": "2361 Broadway, Redwood City, CA 94063"},
    {"name": "Teatime", "lat": 37.4845396, "lng": -122.2325183, "rating": 4.4, "reviews": 91, "addr": "1003 El Camino Real, Redwood City, CA 94063"},
    # -- San Carlos --
    {"name": "Boba Guys", "lat": 37.5027989, "lng": -122.2569245, "rating": 4.5, "reviews": 659, "addr": "872 Laurel St, San Carlos, CA 94070"},
    {"name": "Bober Tea & Coffee", "lat": 37.4991579, "lng": -122.2521173, "rating": 4.4, "reviews": 159, "addr": "1189 Laurel St, San Carlos, CA 94070"},
    {"name": "Mints & Honey", "lat": 37.4961776, "lng": -122.2476941, "rating": 4.4, "reviews": 1545, "addr": "1524 El Camino Real, San Carlos, CA 94070"},
    {"name": "Tea Hut", "lat": 37.5051418, "lng": -122.259372, "rating": 4.2, "reviews": 291, "addr": "711 Laurel St, San Carlos, CA 94070"},
    {"name": "Tea Juice", "lat": 37.499325, "lng": -122.252766, "rating": 4.2, "reviews": 84, "addr": "1156 Laurel St, San Carlos, CA 94070"},
    {"name": "The Crepe Stop", "lat": 37.5030194, "lng": -122.2572166, "rating": 4.4, "reviews": 630, "addr": "852 Laurel St, San Carlos, CA 94070"},
    # -- San Mateo --
    {"name": "Boba Bless", "lat": 37.5631447, "lng": -122.32535, "rating": 4.7, "reviews": 120, "addr": "16 E 3rd Ave, San Mateo, CA 94401"},
    {"name": "Fat's boba and snacks", "lat": 37.5676564, "lng": -122.3196758, "rating": 0.0, "reviews": 1, "addr": "615 E 3rd Ave Suite G, San Mateo, CA 94401"},
    {"name": "Izumi Matcha", "lat": 37.564654, "lng": -122.323096, "rating": 3.9, "reviews": 33, "addr": "180 E 3rd Ave unit 100A, San Mateo, CA 94401"},
    {"name": "Little Late Bird", "lat": 37.5621565, "lng": -122.2861219, "rating": 4.7, "reviews": 537, "addr": "777 Mariners Island Blvd STE 170, San Mateo, CA 94404"},
    {"name": "Meet Fresh | San Mateo", "lat": 37.5656637, "lng": -122.3224362, "rating": 3.6, "reviews": 1064, "addr": "277 S B St, San Mateo, CA 94401"},
    {"name": "Molly Tea (San Mateo)", "lat": 37.5665861, "lng": -122.3232866, "rating": 4.6, "reviews": 503, "addr": "153 S B St, San Mateo, CA 94401"},
    {"name": "Mr. Green Bubble | San Mateo", "lat": 37.5445029, "lng": -122.2850797, "rating": 3.7, "reviews": 498, "addr": "2986 S Norfolk St, San Mateo, CA 94403"},
    {"name": "Palette Tea Garden & Dim Sum 彩苑", "lat": 37.5386697, "lng": -122.3018257, "rating": 4.1, "reviews": 4637, "addr": "48 Hillsdale Mall, San Mateo, CA 94403"},
    {"name": "Rare Tea | San Mateo / Half Moon Bay", "lat": 37.5337594, "lng": -122.3272373, "rating": 4.5, "reviews": 76, "addr": "1330 W Hillsdale Blvd, San Mateo, CA 94403"},
    {"name": "Sharetea San Mateo", "lat": 37.5663029, "lng": -122.3226355, "rating": 4.4, "reviews": 225, "addr": "220 Main St, San Mateo, CA 94401"},
    {"name": "Shuyi Grass Jelly & Tea 书亦烧仙草 (San Mateo)", "lat": 37.5641299, "lng": -122.3229547, "rating": 4.1, "reviews": 304, "addr": "165 E 4th Ave, San Mateo, CA 94401"},
    {"name": "TP TEA - San Mateo", "lat": 37.5634216, "lng": -122.3238095, "rating": 4.2, "reviews": 311, "addr": "65 E 4th Ave, San Mateo, CA 94401"},
    {"name": "Teaspoon San Mateo", "lat": 37.5643177, "lng": -122.3238878, "rating": 4.3, "reviews": 725, "addr": "128 E 3rd Ave, San Mateo, CA 94401"},
    {"name": "Tiger Tea & Juice San Mateo", "lat": 37.5651088, "lng": -122.3228227, "rating": 4.4, "reviews": 135, "addr": "212 E 3rd Ave, San Mateo, CA 94401"},
    {"name": "Urban Ritual", "lat": 37.5665398, "lng": -122.3237254, "rating": 4.3, "reviews": 374, "addr": "140 S B St, San Mateo, CA 94401"},
    {"name": "Yifang Taiwan Fruit Tea", "lat": 37.5668318, "lng": -122.324049, "rating": 4.2, "reviews": 336, "addr": "110 S B St, San Mateo, CA 94401"},
    # -- Burlingame --
    {"name": "Ceré Tea", "lat": 37.5792628, "lng": -122.3457131, "rating": 4.3, "reviews": 104, "addr": "1115 Burlingame Ave, Burlingame, CA 94010"},
    {"name": "Happy Lemon Burlingame", "lat": 37.5774235, "lng": -122.3485017, "rating": 4.3, "reviews": 322, "addr": "1419 Burlingame Ave ste a, Burlingame, CA 94010"},
    {"name": "La Matcha Cafe", "lat": 37.5955346, "lng": -122.3838125, "rating": 4.7, "reviews": 662, "addr": "1828 El Camino Real UNIT 102, Burlingame, CA 94010"},
    {"name": "Leland Tea Company", "lat": 37.5790297, "lng": -122.3474149, "rating": 4.6, "reviews": 137, "addr": "1223 Donnelly Ave, Burlingame, CA 94010"},
    {"name": "Lilikoi on Broadway", "lat": 37.5851422, "lng": -122.3654097, "rating": 4.4, "reviews": 252, "addr": "1355 Broadway, Burlingame, CA 94010"},
    {"name": "Sunright Tea Studio - Burlingame", "lat": 37.5800737, "lng": -122.346656, "rating": 4.6, "reviews": 437, "addr": "346 Lorton Ave, Burlingame, CA 94010"},
    {"name": "Tiger Tea & Juice", "lat": 37.5939818, "lng": -122.3843043, "rating": 4.4, "reviews": 524, "addr": "1803 El Camino Real, Burlingame, CA 94010"},
    {"name": "Tpumps", "lat": 37.5795451, "lng": -122.3460036, "rating": 4.4, "reviews": 130, "addr": "1118 Burlingame Ave, Burlingame, CA 94010"},
    {"name": "UMe | Tea & Snacks", "lat": 37.5789081, "lng": -122.3460332, "rating": 4.6, "reviews": 267, "addr": "283 Lorton Ave, Burlingame, CA 94010"},
    # -- Millbrae --
    {"name": "Bambu Dessert Drinks", "lat": 37.6003794, "lng": -122.3901122, "rating": 4.2, "reviews": 424, "addr": "203 El Camino Real, Millbrae, CA 94030"},
    {"name": "Grapeholic", "lat": 37.5979912, "lng": -122.3865025, "rating": 4.3, "reviews": 236, "addr": "102 S El Camino Real, Millbrae, CA 94030"},
    {"name": "T4", "lat": 37.600989, "lng": -122.392115, "rating": 4.0, "reviews": 231, "addr": "315 Broadway, Millbrae, CA 94032"},
    {"name": "TP TEA - Millbrae", "lat": 37.6017315, "lng": -122.3926076, "rating": 4.0, "reviews": 173, "addr": "400 Broadway, Millbrae, CA 94030"},
    {"name": "Tea Hut", "lat": 37.6015989, "lng": -122.3913904, "rating": 4.4, "reviews": 201, "addr": "325 El Camino Real, Millbrae, CA 94030"},
    {"name": "TeaEver", "lat": 37.59989, "lng": -122.3894478, "rating": 3.9, "reviews": 311, "addr": "153 El Camino Real, Millbrae, CA 94030"},
    {"name": "UMe | Tea & Snacks", "lat": 37.6016588, "lng": -122.3929324, "rating": 4.3, "reviews": 296, "addr": "405 Broadway, Millbrae, CA 94030"},
    {"name": "WanPo Tea Shop", "lat": 37.6061583, "lng": -122.3978959, "rating": 4.4, "reviews": 280, "addr": "1069 El Camino Real, Millbrae, CA 94030"},
    {"name": "ha tea handmade", "lat": 37.59989, "lng": -122.3894478, "rating": 4.2, "reviews": 79, "addr": "153 El Camino Real, Millbrae, CA 94030"},
    # -- San Bruno --
    {"name": "Local Kitchens", "lat": 37.6267993, "lng": -122.425534, "rating": 4.3, "reviews": 13, "addr": "851 Cherry Ave Suite 2, San Bruno, CA 94066"},
    {"name": "Quickly", "lat": 37.6389453, "lng": -122.421122, "rating": 3.9, "reviews": 219, "addr": "1212 El Camino Real A, San Bruno, CA 94066"},
    {"name": "Societea Tea House & Eatery", "lat": 37.6228316, "lng": -122.4111046, "rating": 4.5, "reviews": 480, "addr": "446 San Mateo Ave, San Bruno, CA 94066"},
    # -- South San Francisco --
    {"name": "Brew Cha & Matcha - South San Francisco", "lat": 37.6548175, "lng": -122.4333511, "rating": 4.1, "reviews": 168, "addr": "988 El Camino Real suite 4, South San Francisco, CA 94080"},
    {"name": "Milk Tea Lab", "lat": 37.6492149, "lng": -122.4295312, "rating": 4.4, "reviews": 241, "addr": "630 El Camino Real, South San Francisco, CA 94080"},
    {"name": "Pit Stop Boba Shop", "lat": 37.6435367, "lng": -122.4534993, "rating": 4.4, "reviews": 161, "addr": "2300 Westborough Blvd, South San Francisco, CA 94080"},
    {"name": "Tea World", "lat": 37.6434269, "lng": -122.4637298, "rating": 4.1, "reviews": 27, "addr": "3573 Callan Blvd, South San Francisco, CA 94080"},
    # -- Fremont --
    {"name": "101 Tea Plantation", "lat": 37.4882323, "lng": -121.9300392, "rating": 4.0, "reviews": 43, "addr": "46859 Warm Springs Blvd, Fremont, CA 94539"},
    {"name": "A Sack of Potatoes 一袋馬鈴薯", "lat": 37.5603146, "lng": -122.0105304, "rating": 4.2, "reviews": 706, "addr": "37100 Fremont Blvd Suite #3C, Fremont, CA 94536"},
    {"name": "BingBing", "lat": 37.5630945, "lng": -122.0153528, "rating": 4.3, "reviews": 172, "addr": "36400 Fremont Blvd, Fremont, CA 94536"},
    {"name": "Boba Queen", "lat": 37.5757945, "lng": -122.0398366, "rating": 4.1, "reviews": 399, "addr": "34420 Fremont Blvd, Fremont, CA 94555"},
    {"name": "Boiling Point", "lat": 37.4890936, "lng": -121.9294927, "rating": 4.0, "reviews": 964, "addr": "46807 Warm Springs Blvd, Fremont, CA 94539"},
    {"name": "Brian Black Tea", "lat": 37.5009418, "lng": -121.9690679, "rating": 4.2, "reviews": 327, "addr": "43982 Pacific Commons Blvd, Fremont, CA 94538"},
    {"name": "ChaChaCha", "lat": 37.5631579, "lng": -122.0100983, "rating": 4.2, "reviews": 383, "addr": "3623 Thornton Ave, Fremont, CA 94536"},
    {"name": "ChaChaGo", "lat": 37.550363, "lng": -121.9857287, "rating": 4.2, "reviews": 489, "addr": "39025 State St, Fremont, CA 94538"},
    {"name": "Chai Shai", "lat": 37.5461053, "lng": -121.9872428, "rating": 3.6, "reviews": 365, "addr": "39133 Fremont Hub Courtyard unit 181, Fremont, CA 94538"},
    {"name": "Chicha San Chen 吃茶三千", "lat": 37.5002806, "lng": -121.9740219, "rating": 4.3, "reviews": 160, "addr": "43731 Boscell Rd, Fremont, CA 94538"},
    {"name": "Duet Tea", "lat": 37.5437592, "lng": -121.9868351, "rating": 4.4, "reviews": 350, "addr": "39230 Argonaut Way, Fremont, CA 94538"},
    {"name": "Happy Lemon", "lat": 37.4881292, "lng": -121.9302822, "rating": 4.1, "reviews": 255, "addr": "46873 Warm Springs Blvd, Fremont, CA 94539"},
    {"name": "Meet Fresh | Fremont", "lat": 37.5032152, "lng": -121.976251, "rating": 3.8, "reviews": 1365, "addr": "43337 Boscell Rd suite p9-c, Fremont, CA 94538"},
    {"name": "Milk & Honey Cafe", "lat": 37.5754299, "lng": -122.0425774, "rating": 4.4, "reviews": 2057, "addr": "34265 Fremont Blvd, Fremont, CA 94555"},
    {"name": "Mission Tasty Hut", "lat": 37.530523, "lng": -121.9198865, "rating": 4.7, "reviews": 160, "addr": "135 Anza St, Fremont, CA 94539"},
    {"name": "Mr. Sun Tea Fremont", "lat": 37.5197119, "lng": -121.9876626, "rating": 4.3, "reviews": 450, "addr": "40526 Albrae St, Fremont, CA 94538"},
    {"name": "R&B Tea - Fremont", "lat": 37.5598967, "lng": -122.0096665, "rating": 3.9, "reviews": 924, "addr": "37120 Fremont Blvd unit i, Fremont, CA 94536"},
    {"name": "Royal Tea USA", "lat": 37.5510474, "lng": -121.9936491, "rating": 4.4, "reviews": 412, "addr": "38509 Fremont Blvd, Fremont, CA 94536"},
    {"name": "Sharetea Fremont", "lat": 37.5319259, "lng": -121.9579538, "rating": 4.1, "reviews": 122, "addr": "3948 Washington Blvd, Fremont, CA 94538"},
    {"name": "Tapioca Express", "lat": 37.5232051, "lng": -121.9706882, "rating": 4.3, "reviews": 361, "addr": "41200 Blacow Rd # G, Fremont, CA 94538"},
    {"name": "Tea Moment", "lat": 37.5184773, "lng": -121.9900579, "rating": 4.2, "reviews": 352, "addr": "6088 Stevenson Blvd, Fremont, CA 94538"},
    {"name": "Tea-Rek'z", "lat": 37.5773125, "lng": -121.9802585, "rating": 4.6, "reviews": 223, "addr": "37390 Niles Blvd, Fremont, CA 94536"},
    {"name": "Teaspoon Fremont", "lat": 37.4890277, "lng": -121.9294567, "rating": 4.4, "reviews": 379, "addr": "46809 Warm Springs Blvd, Fremont, CA 94539"},
    {"name": "Tpumps", "lat": 37.5242846, "lng": -121.9572597, "rating": 4.4, "reviews": 150, "addr": "42130 Blacow Rd, Fremont, CA 94538"},
    {"name": "Tyme For Tea & Co", "lat": 37.5768672, "lng": -121.9792643, "rating": 4.3, "reviews": 917, "addr": "37501 Niles Blvd, Fremont, CA 94536"},
    {"name": "UMe | Tea & Snacks", "lat": 37.5002936, "lng": -121.9740632, "rating": 4.8, "reviews": 430, "addr": "43743 Boscell Rd, Fremont, CA 94538"},
    {"name": "Wushiland Boba - Fremont (Inside 99 Ranch) - COMING SOON", "lat": 37.4920422, "lng": -121.9294998, "rating": 3.0, "reviews": 4, "addr": "46551 Mission Blvd Unit 109, Fremont, CA 94539"},
    {"name": "Yifang Taiwan Fruit Tea", "lat": 37.5754531, "lng": -122.0445161, "rating": 4.2, "reviews": 355, "addr": "34133 Fremont Blvd, Fremont, CA 94555"},
    {"name": "Yokee Milk Tea", "lat": 37.4937273, "lng": -121.9301279, "rating": 4.4, "reviews": 573, "addr": "46164 Warm Springs Blvd UNIT 234, Fremont, CA 94539"},
    {"name": "iTea Fremont", "lat": 37.5050633, "lng": -121.9710475, "rating": 3.8, "reviews": 642, "addr": "43421 Christy St, Fremont, CA 94538"},
    {"name": "oh Chai! (High Tea Catering)", "lat": 37.4993362, "lng": -121.9140748, "rating": 5.0, "reviews": 74, "addr": "46200 Paseo Padre Pkwy, Fremont, CA 94539"},
    # -- Newark --
    {"name": "Boba Nation Grand - Newark", "lat": 37.5263757, "lng": -122.0018074, "rating": 4.7, "reviews": 982, "addr": "2086 Newpark Mall # 1036, Newark, CA 94560"},
    {"name": "Feng Cha Teahouse - Newark", "lat": 37.5486107, "lng": -122.0488746, "rating": 4.5, "reviews": 753, "addr": "6180 Jarvis Ave ste w, Newark, CA 94560"},
    {"name": "Happy Lemon | Newark", "lat": 37.5231789, "lng": -122.0061229, "rating": 4.3, "reviews": 175, "addr": "39151 Cedar Blvd, Newark, CA 94560"},
    {"name": "MandRo Teahouse", "lat": 37.5515343, "lng": -122.0501746, "rating": 4.2, "reviews": 539, "addr": "34956 Newark Blvd, Newark, CA 94560"},
    {"name": "TP TEA - Newark (SOFT OPEN)", "lat": 37.5230369, "lng": -122.0056814, "rating": 5.0, "reviews": 10, "addr": "39181 Cedar Blvd, Newark, CA 94560"},
    {"name": "Tao's Fresh", "lat": 37.5496335, "lng": -122.0503804, "rating": 4.5, "reviews": 673, "addr": "6185 Jarvis Ave, Newark, CA 94560"},
    {"name": "Tastea Newark", "lat": 37.5253355, "lng": -122.0063646, "rating": 4.3, "reviews": 343, "addr": "5970 Mowry Ave Unit N, Newark, CA 94560"},
    {"name": "Tasty Pot - Newark", "lat": 37.5508998, "lng": -122.0509961, "rating": 4.3, "reviews": 958, "addr": "34909 Newark Blvd, Newark, CA 94560"},
    {"name": "Tea Top 台灣第一味", "lat": 37.5224201, "lng": -122.0040057, "rating": 4.5, "reviews": 159, "addr": "39269 Cedar Blvd #5007, Newark, CA 94560"},
    {"name": "Teaspoon Newark", "lat": 37.5213375, "lng": -121.996354, "rating": 4.6, "reviews": 285, "addr": "39730 Cedar Blvd, Newark, CA 94560"},
    {"name": "Truewin Tea Shoppe 初韻 新中式奶茶", "lat": 37.5508422, "lng": -122.0510285, "rating": 4.1, "reviews": 597, "addr": "34925 Newark Blvd, Newark, CA 94560"},
    # -- Union City --
    {"name": "CAFFE:iN-Union City", "lat": 37.5880449, "lng": -122.0195674, "rating": 4.0, "reviews": 686, "addr": "1788 Decoto Rd, Union City, CA 94587"},
    {"name": "Gong Cha", "lat": 37.5916647, "lng": -122.0711135, "rating": 3.8, "reviews": 149, "addr": "31812 Alvarado Blvd, Union City, CA 94587"},
    {"name": "Happy Lemon", "lat": 37.5882175, "lng": -122.0195135, "rating": 4.2, "reviews": 203, "addr": "1780 Decoto Rd, Union City, CA 94587"},
    {"name": "K On the Go", "lat": 37.5896075, "lng": -122.0711882, "rating": 4.5, "reviews": 305, "addr": "31877 Alvarado Blvd, Union City, CA 94587"},
    {"name": "Milk Tea Factory", "lat": 37.59994, "lng": -122.0410595, "rating": 4.3, "reviews": 81, "addr": "33155 Transit Ave, Union City, CA 94587"},
    {"name": "Mr. Green Bubble | Union City", "lat": 37.5895461, "lng": -122.019881, "rating": 4.0, "reviews": 533, "addr": "1644 Decoto Rd, Union City, CA 94587"},
    {"name": "Sunright Tea Studio", "lat": 37.5864248, "lng": -122.0200329, "rating": 4.4, "reviews": 478, "addr": "34563 Alvarado-Niles Rd, Union City, CA 94587"},
    {"name": "TOCOTEA.UNION CITY", "lat": 37.5979286, "lng": -122.069454, "rating": 3.9, "reviews": 174, "addr": "32360 Dyer St, Union City, CA 94587"},
    {"name": "Tapioca Express", "lat": 37.589401, "lng": -122.0217677, "rating": 3.9, "reviews": 370, "addr": "1707 Decoto Rd, Union City, CA 94587"},
    # -- Hayward --
    {"name": "Fanale Drinks", "lat": 37.6211571, "lng": -122.0553744, "rating": 4.6, "reviews": 36, "addr": "790 Sandoval Way, Hayward, CA 94544"},
    {"name": "Kingtea Corporation", "lat": 37.618414, "lng": -122.0761673, "rating": 0.0, "reviews": 1, "addr": "28976 Hopkins St # D, Hayward, CA 94545"},
    {"name": "Sip & Savor", "lat": 37.6443406, "lng": -122.0624824, "rating": 4.5, "reviews": 156, "addr": "26953 Mission Blvd Ste M, Hayward, CA 94544"},
    {"name": "Teaspoon Hayward", "lat": 37.6443947, "lng": -122.1045516, "rating": 4.8, "reviews": 272, "addr": "25034 Hesperian Blvd, Hayward, CA 94545"},
    # -- Alameda --
    {"name": "Boba Me", "lat": 37.7635154, "lng": -122.2431941, "rating": 4.2, "reviews": 240, "addr": "1342 Park St, Alameda, CA 94501"},
    {"name": "Gong Cha", "lat": 37.7655178, "lng": -122.2419304, "rating": 4.0, "reviews": 205, "addr": "1501 Park St, Alameda, CA 94501"},
    {"name": "Happy Lemon", "lat": 37.7657671, "lng": -122.242253, "rating": 4.1, "reviews": 275, "addr": "2321 Santa Clara Ave, Alameda, CA 94501"},
    {"name": "Malaya Tea Room", "lat": 37.771021, "lng": -122.2695759, "rating": 4.6, "reviews": 449, "addr": "920 Central Ave, Alameda, CA 94501"},
    {"name": "MandRo Teahouse", "lat": 37.76313, "lng": -122.2439707, "rating": 4.4, "reviews": 175, "addr": "1321 Park St, Alameda, CA 94501"},
    {"name": "Raretea Alameda", "lat": 37.787157, "lng": -122.2800197, "rating": 4.0, "reviews": 250, "addr": "2670 5th St Suite C, Alameda, CA 94501"},
    {"name": "T4 Alameda", "lat": 37.7651221, "lng": -122.2418879, "rating": 4.1, "reviews": 500, "addr": "1434 Park St, Alameda, CA 94501"},
    {"name": "TOMO Tea House", "lat": 37.7838765, "lng": -122.2734748, "rating": 4.4, "reviews": 570, "addr": "825 Marina Village Pkwy, Alameda, CA 94501"},
    {"name": "Top Up Tea", "lat": 37.7707636, "lng": -122.2774573, "rating": 4.3, "reviews": 223, "addr": "650 Central Ave ste.g, Alameda, CA 94501"},
    {"name": "Yifang Taiwan Fruit Tea", "lat": 37.7563475, "lng": -122.2513024, "rating": 4.2, "reviews": 442, "addr": "409 S Shore Center, Alameda, CA 94501"},
    {"name": "iTea Alameda", "lat": 37.7673267, "lng": -122.2399403, "rating": 4.2, "reviews": 204, "addr": "1626 Park St, Alameda, CA 94501"},
    # -- Oakland --
    {"name": "Boba Binge Uptown", "lat": 37.811078, "lng": -122.2666285, "rating": 4.6, "reviews": 362, "addr": "2212 Broadway, Oakland, CA 94612"},
    {"name": "Boba Guys Rockridge", "lat": 37.8475845, "lng": -122.2522548, "rating": 4.1, "reviews": 164, "addr": "5925 College Ave, Oakland, CA 94618"},
    {"name": "Golden Tea Shop", "lat": 37.8006377, "lng": -122.2724032, "rating": 4.7, "reviews": 395, "addr": "901 Franklin St # 128, Oakland, CA 94607"},
    {"name": "Great Tea", "lat": 37.800247, "lng": -122.2710037, "rating": 4.9, "reviews": 51, "addr": "101 Webster St, Oakland, CA 94607"},
    {"name": "Happy Lemon", "lat": 37.8276855, "lng": -122.2505114, "rating": 4.4, "reviews": 178, "addr": "4214 Piedmont Ave, Oakland, CA 94611"},
    {"name": "Mr. Green Bubble | Oakland", "lat": 37.828967, "lng": -122.249412, "rating": 4.1, "reviews": 398, "addr": "4299 Piedmont Ave # D, Oakland, CA 94611"},
    {"name": "QTea Bar", "lat": 37.8110842, "lng": -122.2472538, "rating": 4.6, "reviews": 40, "addr": "478 Lake Park Ave, Oakland, CA 94610"},
    {"name": "RareTea Oakland", "lat": 37.8464671, "lng": -122.2522065, "rating": 4.2, "reviews": 435, "addr": "5817 College Ave, Oakland, CA 94618"},
    {"name": "SUPTEA LAB", "lat": 37.8135188, "lng": -122.2469467, "rating": 4.8, "reviews": 270, "addr": "3349 Grand Ave, Oakland, CA 94610"},
    {"name": "Sophie's Cuppa Tea", "lat": 37.8261444, "lng": -122.2089694, "rating": 4.8, "reviews": 87, "addr": "2078 Antioch Ct, Oakland, CA 94611"},
    {"name": "Sweetheart Café & Tea", "lat": 37.7994619, "lng": -122.270047, "rating": 4.4, "reviews": 181, "addr": "315 9th St, Oakland, CA 94607"},
    {"name": "T4 Oakland", "lat": 37.8011133, "lng": -122.2700411, "rating": 4.2, "reviews": 500, "addr": "1068 Webster St, Oakland, CA 94607"},
    {"name": "TF Montclair", "lat": 37.8261581, "lng": -122.2092287, "rating": 3.6, "reviews": 12, "addr": "2066 Mountain Blvd, Oakland, CA 94611"},
    {"name": "Tea On Piedmont", "lat": 37.8264535, "lng": -122.2520287, "rating": 4.7, "reviews": 219, "addr": "4098 Piedmont Ave, Oakland, CA 94611"},
    {"name": "The Mix", "lat": 37.8133417, "lng": -122.2464083, "rating": 4.6, "reviews": 298, "addr": "3340 Grand Ave, Oakland, CA 94610"},
    {"name": "YOKEE MILK TEA", "lat": 37.806607, "lng": -122.26807, "rating": 4.6, "reviews": 591, "addr": "1728 Franklin St, Oakland, CA 94612"},
    {"name": "i-Tea Oakland", "lat": 37.8005139, "lng": -122.2707728, "rating": 4.3, "reviews": 283, "addr": "388 9th St #125a, Oakland, CA 94607"},
    # -- Berkeley --
    {"name": "8 Grams Matcha", "lat": 37.8683181, "lng": -122.2604369, "rating": 4.0, "reviews": 62, "addr": "2440 Bancroft Way, Berkeley, CA 94704"},
    {"name": "Asha Tea House", "lat": 37.871952, "lng": -122.268853, "rating": 4.5, "reviews": 891, "addr": "2086 University Ave, Berkeley, CA 94704"},
    {"name": "Bee Boba and Deli", "lat": 37.8543956, "lng": -122.2712878, "rating": 4.6, "reviews": 30, "addr": "2948 Martin Luther King Jr Way, Berkeley, CA 94703"},
    {"name": "Blue Willow Teaspot", "lat": 37.8819243, "lng": -122.2976412, "rating": 4.6, "reviews": 273, "addr": "1200 Tenth St, Berkeley, CA 94710"},
    {"name": "Boba Ninja", "lat": 37.8680755, "lng": -122.2581506, "rating": 4.2, "reviews": 389, "addr": "2519 Durant Ave, Berkeley, CA 94704"},
    {"name": "Cha Thai Tea", "lat": 37.8749091, "lng": -122.2689538, "rating": 4.8, "reviews": 164, "addr": "1796 Shattuck Ave., Berkeley, CA 94709"},
    {"name": "Chicha San Chen 吃茶三千", "lat": 37.8683082, "lng": -122.2612332, "rating": 4.7, "reviews": 257, "addr": "2400A Bancroft Way, Berkeley, CA 94704"},
    {"name": "De Matcha", "lat": 37.8683282, "lng": -122.258951, "rating": 4.1, "reviews": 96, "addr": "2315 Telegraph Ave, Berkeley, CA 94704"},
    {"name": "Far Leaves Tea", "lat": 37.8582265, "lng": -122.2890771, "rating": 4.8, "reviews": 178, "addr": "2626 San Pablo Ave, Berkeley, CA 94702"},
    {"name": "Forest Tea Bar", "lat": 37.8610702, "lng": -122.2673136, "rating": 4.8, "reviews": 125, "addr": "2628 Shattuck Ave., Berkeley, CA 94704"},
    {"name": "Happy Lemon | Berkeley", "lat": 37.8709291, "lng": -122.2685587, "rating": 4.2, "reviews": 239, "addr": "2106 Shattuck Ave., Berkeley, CA 94704"},
    {"name": "J's Snacks and Tea", "lat": 37.8754951, "lng": -122.2598101, "rating": 4.7, "reviews": 150, "addr": "2505 Hearst Ave Ste G, Berkeley, CA 94709"},
    {"name": "Kuboba Spot", "lat": 37.8625925, "lng": -122.2590371, "rating": 4.9, "reviews": 211, "addr": "2618 Telegraph Ave, Berkeley, CA 94704"},
    {"name": "Plentea", "lat": 37.8675441, "lng": -122.259572, "rating": 4.4, "reviews": 378, "addr": "2430 Durant Ave, Berkeley, CA 94704"},
    {"name": "Presotea Berkeley", "lat": 37.8710129, "lng": -122.2746711, "rating": 4.5, "reviews": 227, "addr": "1812-B University Ave, Berkeley, CA 94703"},
    {"name": "Purple Kow", "lat": 37.8668785, "lng": -122.2584038, "rating": 4.4, "reviews": 71, "addr": "2508 Channing Way, Berkeley, CA 94704"},
    {"name": "Sweetheart Café", "lat": 37.868076, "lng": -122.2579151, "rating": 4.2, "reviews": 223, "addr": "2523 Durant Ave, Berkeley, CA 94704"},
    {"name": "TP TEA - Berkeley", "lat": 37.8672047, "lng": -122.2586518, "rating": 4.3, "reviews": 416, "addr": "2383 Telegraph Ave, Berkeley, CA 94704"},
    {"name": "Tea Hut", "lat": 37.8745636, "lng": -122.268357, "rating": 4.8, "reviews": 116, "addr": "1801 Shattuck Ave., Berkeley, CA 94709"},
    {"name": "Teaspoon Berkeley", "lat": 37.8725267, "lng": -122.2674603, "rating": 4.2, "reviews": 295, "addr": "2129 University Ave, Berkeley, CA 94704"},
    {"name": "U :Dessert Story", "lat": 37.8740203, "lng": -122.2684191, "rating": 4.3, "reviews": 1420, "addr": "1849 Shattuck Ave., Berkeley, CA 94709"},
    {"name": "Yifang Taiwan Fruit Tea", "lat": 37.8686583, "lng": -122.2586494, "rating": 4.2, "reviews": 622, "addr": "2516 Bancroft Way, Berkeley, CA 94704"},
    {"name": "heytea (Berkeley)", "lat": 37.8709151, "lng": -122.2679513, "rating": 4.4, "reviews": 182, "addr": "2125 Shattuck Ave., Berkeley, CA 94704"},
    # -- Albany --
    {"name": "Nomi Tea", "lat": 37.8910141, "lng": -122.2884962, "rating": 4.2, "reviews": 87, "addr": "1475 Solano Ave, Albany, CA 94706"},
    # -- El Cerrito --
    {"name": "Tala Coffee & Tea", "lat": 37.913807, "lng": -122.3092489, "rating": 4.0, "reviews": 309, "addr": "10734 San Pablo Ave, El Cerrito, CA 94530"},
    # -- Richmond --
    {"name": "Happy Lemon", "lat": 37.8990841, "lng": -122.3076357, "rating": 3.9, "reviews": 339, "addr": "3288 Pierce St D103, Richmond, CA 94804"},
    # -- Orinda --
    {"name": "Nine Tailed Fox - Orinda", "lat": 37.8788694, "lng": -122.1814123, "rating": 4.8, "reviews": 205, "addr": "41 Moraga Way, Orinda, CA 94563"},
    # -- 15545 Union Ave --
    {"name": "T4 Los Gatos", "lat": 37.24277, "lng": -121.932346, "rating": 4.2, "reviews": 148, "addr": "Downing Center, 15545 Union Ave, Los Gatos, CA 95032"},
    # -- 285 Hillsdale Mall --
    {"name": "Pink Pink Tea Shoppe", "lat": 37.5375337, "lng": -122.3004025, "rating": 4.3, "reviews": 163, "addr": "60 31st Avenue, 285 Hillsdale Mall, San Mateo, CA 94403"},
    # -- 2855 Stevens Creek Blvd #2170 --
    {"name": "Lucky Tea", "lat": 37.3252844, "lng": -121.9472239, "rating": 3.4, "reviews": 288, "addr": "Second floor adjacent to ICON theater, 2855 Stevens Creek Blvd #2170, Santa Clara, CA 95050"},
    # -- 3005 Silver Creek Rd STE 170 --
    {"name": "Soyful Desserts", "lat": 37.3088703, "lng": -121.8144539, "rating": 4.3, "reviews": 113, "addr": "Parking lot, 3005 Silver Creek Rd STE 170, San Jose, CA 95121"},
    # -- 31st Ave --
    {"name": "Sharetea | Hillsdale", "lat": 37.5381285, "lng": -122.3012975, "rating": 3.0, "reviews": 96, "addr": "Hillsdale Shopping Center Dining Terrace (Upper Level 60 East, 31st Ave, San Mateo, CA 94403"},
    # -- 447 Blossom Hill Rd B --
    {"name": "7 Leaves Cafe - Blossom Hill", "lat": 37.2517545, "lng": -121.8298646, "rating": 4.3, "reviews": 292, "addr": "B, 447 Blossom Hill Rd B, San Jose, CA 95123"},
    # -- 46551 Mission Blvd Unit 102 --
    {"name": "Shuyi Grass Jelly & Tea 书亦烧仙草 (Fremont)", "lat": 37.4920694, "lng": -121.9295516, "rating": 4.4, "reviews": 270, "addr": "Inside 99 Ranch Market, 46551 Mission Blvd Unit 102, Fremont, CA 94539"},
    # -- 520 Lasuen Mall --
    {"name": "Chun Yang 春陽茶室", "lat": 37.4251734, "lng": -122.1704029, "rating": 4.3, "reviews": 160, "addr": "TAP(The Axe and Palm, 520 Lasuen Mall, Stanford, CA 94305"},
    # -- Beaverton --
    {"name": "Bubble Bubble Tea", "lat": 45.4884459, "lng": -122.7971988, "rating": 4.5, "reviews": 147, "addr": "11723 SW Beaverton Hillsdale Hwy, Beaverton, OR 97005"},
    {"name": "Bubble N Tea", "lat": 45.4944397, "lng": -122.8089409, "rating": 4.7, "reviews": 610, "addr": "3496 SW Cedar Hills Blvd, Beaverton, OR 97005"},
    {"name": "FANTASTEA HOUSE", "lat": 45.4752896, "lng": -122.8269776, "rating": 4.6, "reviews": 568, "addr": "6115 SW Murray Blvd, Beaverton, OR 97008"},
    # -- Belmont --
    {"name": "Happy Lemon Belmont", "lat": 37.5194716, "lng": -122.2757123, "rating": 4.4, "reviews": 235, "addr": "850 Emmett Ave Suite A, Belmont, CA 94002"},
    {"name": "Taco Catering And Bubble Milk Tea Boba Bar Catering", "lat": 37.5180837, "lng": -122.2747101, "rating": 5.0, "reviews": 88, "addr": "900 Oneill Ave #3840, Belmont, CA 94002"},
    {"name": "Ya-Ua Boba Tea", "lat": 37.5102583, "lng": -122.2937, "rating": 4.5, "reviews": 39, "addr": "1090 Alameda de las Pulgas, Belmont, CA 94002"},
    # -- Foster City --
    {"name": "Happy Lemon Foster City", "lat": 37.5591066, "lng": -122.267132, "rating": 4.2, "reviews": 361, "addr": "780 Alma Ln STE 170, Foster City, CA 94404"},
    {"name": "Quickly", "lat": 37.5444133, "lng": -122.2706263, "rating": 4.2, "reviews": 229, "addr": "969K Edgewater Blvd, Foster City, CA 94404"},
    # -- Hillsboro --
    {"name": "Chen Fu Bubble Tea", "lat": 45.5179186, "lng": -122.975441, "rating": 4.9, "reviews": 181, "addr": "424 SE 9th Ave, Hillsboro, OR 97123"},
    {"name": "Sharetea Hillsboro", "lat": 45.5307737, "lng": -122.9157475, "rating": 4.0, "reviews": 310, "addr": "933 NE Orenco Station Loop, Hillsboro, OR 97124"},
    {"name": "Zero Degrees Beaverton", "lat": 45.5295711, "lng": -122.8688265, "rating": 4.1, "reviews": 1160, "addr": "1315 NW 185th Ave, Hillsboro, OR 97006"},
    # -- Kensington --
    {"name": "Raxakoul Coffee & Cheese", "lat": 37.9036535, "lng": -122.2779627, "rating": 4.7, "reviews": 34, "addr": "299 Arlington Ave, Kensington, CA 94707"},
    # -- Metro Center Blvd --
    {"name": "Tpumps", "lat": 37.5573764, "lng": -122.274683, "rating": 4.4, "reviews": 162, "addr": "985 E Hillsdale Boulevard, Metro Center Blvd, Foster City, CA 94404"},
    # -- Portland --
    {"name": "Bubble Crunch", "lat": 45.5434053, "lng": -122.8663844, "rating": 4.5, "reviews": 84, "addr": "3288 NW 185th Ave, Portland, OR 97229"},
    {"name": "T4.Tea For", "lat": 45.5583842, "lng": -122.8657234, "rating": 4.3, "reviews": 151, "addr": "18365 NW West Union Rd, Portland, OR 97229"},
    # -- Portola Valley --
    {"name": "Konditorei", "lat": 37.4018676, "lng": -122.1933674, "rating": 4.3, "reviews": 139, "addr": "3130 Alpine Rd, Portola Valley, CA 94028"},
    # -- San Francisco International Airport-T1 Harvey Milk Terminal Gate B18 --
]

_EARTH_RADIUS_MI = 3958.8


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return _EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(a))


def _stable_id(name: str, lat: float, lng: float) -> str:
    raw = f"{name}:{lat:.6f}:{lng:.6f}"
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:16]


def search_boba_shops(
    lat: float,
    lng: float,
    radius_miles: float = 3.0,
) -> list[ShopData]:
    """Return demo shops within *radius_miles* of the given coordinate.

    Args:
        lat: Centre latitude for the search.
        lng: Centre longitude for the search.
        radius_miles: Search radius in miles.

    Returns:
        List of ``ShopData`` dicts sorted by distance, nearest first.
    """
    results: list[ShopData] = []
    for shop in DEMO_SHOPS_DB:
        dist = _haversine_miles(lat, lng, shop["lat"], shop["lng"])
        if dist <= radius_miles:
            results.append(
                {
                    "source": "demo",
                    "id": _stable_id(shop["name"], shop["lat"], shop["lng"]),
                    "name": shop["name"],
                    "lat": shop["lat"],
                    "lng": shop["lng"],
                    "rating": shop["rating"],
                    "review_count": shop["reviews"],
                    "address": shop["addr"],
                    "categories": ["Bubble Tea", "Tea"],
                    "distance_miles": round(dist, 2),
                }
            )
    results.sort(key=lambda s: s.get("distance_miles", 0.0))
    return results
