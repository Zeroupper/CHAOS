# CHAOS Run Export

**Date:** 2026-03-14 11:25:49

## Query

> What is the maximum number of screen unlock episodes in any 14-day period across all participants?


## Data Context (Explorer → Planner)

```
DATASET SCHEMAS (use these exact column names):

=== sleep ===
Shape: (14260, 921)
  Unnamed: 0 (int64): nulls=0, sample=['0', '1', '2']
  date (str): nulls=0, sample=['2018-04-03', '2018-04-04', '2018-04-05']
  f_slp:fitbit_sleep_summary_rapids_sumdurationafterwakeupmain:14dhist (float64): nulls=3725, sample=['0.0', '0.0', '5.0']
  f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist (float64): nulls=3725, sample=['347.0', '742.0', '1313.0']
  f_slp:fitbit_sleep_summary_rapids_sumdurationawakemain:14dhist (float64): nulls=3725, sample=['17.0', '56.0', '85.0']
  ... +915 more 'f_slp:*' columns (see examples above): nulls=0, sample=['f_slp:fitbit_sleep_summary_rapids_sumdurationtofallasleepmain:14dhist', 'f_slp:fitbit_sleep_summary_rapids_sumdurationinbedmain:14dhist', 'f_slp:fitbit_sleep_summary_rapids_avgefficiencymain:14dhist', 'f_slp:fitbit_sleep_summary_rapids_avgdurationafterwakeupmain:14dhist', 'f_slp:fitbit_sleep_summary_rapids_avgdurationasleepmain:14dhist']
  pid (str): nulls=0, sample=['INS-W_001', 'INS-W_001', 'INS-W_001']

=== screen ===
Shape: (14260, 1137)
  Unnamed: 0 (int64): nulls=0, sample=['0', '1', '2']
  date (str): nulls=0, sample=['2018-04-03', '2018-04-04', '2018-04-05']
  f_screen:phone_screen_rapids_countepisodeunlock:14dhist (float64): nulls=3039, sample=['434.0', '433.0', '421.0']
  f_screen:phone_screen_rapids_sumdurationunlock:14dhist (float64): nulls=3039, sample=['3688.2942', '3627.27323333333', '3278.20403333333']
  f_screen:phone_screen_rapids_maxdurationunlock:14dhist (float64): nulls=3039, sample=['315.286816666667', '313.854233333334', '313.854233333334']
  ... +1131 more 'f_screen:*' columns (see examples above): nulls=0, sample=['f_screen:phone_screen_rapids_mindurationunlock:14dhist', 'f_screen:phone_screen_rapids_avgdurationunlock:14dhist', 'f_screen:phone_screen_rapids_stddurationunlock:14dhist', 'f_screen:phone_screen_rapids_firstuseafter00unlock:14dhist', 'f_screen:phone_screen_rapids_countepisodeunlock_locmap_exercise:14dhist']
  pid (str): nulls=0, sample=['INS-W_001', 'INS-W_001', 'INS-W_001']

=== call ===
Shape: (14260, 786)
  Unnamed: 0 (int64): nulls=0, sample=['0', '1', '2']
  date (str): nulls=0, sample=['2018-04-03', '2018-04-04', '2018-04-05']
  f_call:phone_calls_rapids_missed_count:14dhist (float64): nulls=2805, sample=['0.0', '0.0', '0.0']
  f_call:phone_calls_rapids_missed_distinctcontacts:14dhist (float64): nulls=2805, sample=['0.0', '0.0', '0.0']
  f_call:phone_calls_rapids_missed_timefirstcall:14dhist (float64): nulls=4992, sample=['1422.0', '1422.0', '1422.0']
  ... +780 more 'f_call:*' columns (see examples above): nulls=0, sample=['f_call:phone_calls_rapids_missed_timelastcall:14dhist', 'f_call:phone_calls_rapids_missed_countmostfrequentcontact:14dhist', 'f_call:phone_calls_rapids_incoming_count:14dhist', 'f_call:phone_calls_rapids_incoming_distinctcontacts:14dhist', 'f_call:phone_calls_rapids_incoming_meanduration:14dhist']
  pid (str): nulls=0, sample=['INS-W_001', 'INS-W_001', 'INS-W_001']

=== bluetooth ===
Shape: (14260, 894)
  Unnamed: 0 (int64): nulls=0, sample=['0', '1', '2']
  date (str): nulls=0, sample=['2018-04-03', '2018-04-04', '2018-04-05']
  f_blue:phone_bluetooth_rapids_countscans:14dhist (float64): nulls=1083, sample=['152.0', '563.0', '750.0']
  f_blue:phone_bluetooth_rapids_uniquedevices:14dhist (float64): nulls=1083, sample=['95.0', '291.0', '398.0']
  f_blue:phone_bluetooth_rapids_countscansmostuniquedevice:14dhist (float64): nulls=1083, sample=['6.0', '11.0', '27.0']
  ... +888 more 'f_blue:*' columns (see examples above): nulls=0, sample=['f_blue:phone_bluetooth_doryab_countscansall:14dhist', 'f_blue:phone_bluetooth_doryab_uniquedevicesall:14dhist', 'f_blue:phone_bluetooth_doryab_meanscansall:14dhist', 'f_blue:phone_bluetooth_doryab_stdscansall:14dhist', 'f_blue:phone_bluetooth_doryab_countscansmostfrequentdevicewithinsegmentsall:14dhist']
  pid (str): nulls=0, sample=['INS-W_001', 'INS-W_001', 'INS-W_001']

=== wifi ===
Shape: (14260, 84)
  Unnamed: 0 (int64): nulls=0, sample=['0', '1', '2']
  date (str): nulls=0, sample=['2018-04-03', '2018-04-04', '2018-04-05']
  f_wifi:phone_wifi_connected_rapids_countscans:14dhist (float64): nulls=13505, sample=['21.0', '45.0', '98.0']
  f_wifi:phone_wifi_connected_rapids_uniquedevices:14dhist (float64): nulls=13505, sample=['5.0', '6.0', '11.0']
  f_wifi:phone_wifi_connected_rapids_countscansmostuniquedevice:14dhist (float64): nulls=13512, sample=['24.0', '58.0', '58.0']
  ... +78 more 'f_wifi:*' columns (see examples above): nulls=0, sample=['f_wifi:phone_wifi_connected_rapids_countscans_dis:14dhist', 'f_wifi:phone_wifi_connected_rapids_uniquedevices_dis:14dhist', 'f_wifi:phone_wifi_connected_rapids_countscansmostuniquedevice_dis:14dhist', 'f_wifi:phone_wifi_connected_rapids_countscans_norm:14dhist', 'f_wifi:phone_wifi_connected_rapids_uniquedevices_norm:14dhist']
  pid (str): nulls=0, sample=['INS-W_001', 'INS-W_001', 'INS-W_001']

=== steps ===
Shape: (14260, 597)
  
... (truncated)
```

## Plan

**Understanding:** Find the maximum value from the screen unlock episode count column (f_screen:phone_screen_rapids_countepisodeunlock:14dhist) across all participants in the screen dataset. This column tracks the number of screen unlock episodes in a 14-day history window.

| Step | Action | Source |
|------|--------|--------|
| 1 | Filter screen dataset to get records with f_screen:phone_screen_rapids_countepisodeunlock:14dhist values | screen |
| 2 | Extract values from f_screen:phone_screen_rapids_countepisodeunlock:14dhist column across all participants | screen |
| 3 | Calculate maximum value from the extracted values | screen |

## Execution Log


**Sensemaker Request:** Filter the screen dataset to extract records containing the f_screen:phone_screen_rapids_countepisodeunlock:14dhist column values. This column tracks the number of screen unlock episodes in a 14-day history window for each participant.

*Reasoning:* Starting with step 1 to filter and prepare the screen dataset records that contain the target column for maximum value calculation.

**Info Seeker Response:**

- **Source:** screen
- **Success:** Yes

```python
result = screen[screen['f_screen:phone_screen_rapids_countepisodeunlock:14dhist'].notnull()]
```

**Result:**
```
{"Unnamed: 0":{"27":27,"28":28,"29":29,"30":30,"31":31,"32":32,"33":33,"34":34,"35":35,"36":36,"37":37,"38":38,"39":39,"40":40,"41":41,"42":42,"43":43,"44":44,"45":45,"46":46,"47":47,"48":48,"49":49,"50":50,"51":51,"52":52,"53":53,"54":54,"55":55,"56":56,"57":57,"58":58,"59":59,"60":60,"61":61,"62":62,"63":63,"64":64,"65":65,"66":66,"67":67,"68":68,"69":69,"70":70,"71":71,"72":72,"73":73,"74":74,"75":75,"105":105,"106":106,"107":107,"108":108,"109":109,"110":110,"111":111,"112":112,"113":113,"114":114,"115":115,"116":116,"117":117,"118":118,"119":119,"120":120,"121":121,"122":122,"123":123,"124":124,"125":125,"126":126,"127":127,"128":128,"129":129,"130":130,"131":131,"132":132,"133":133,"134":134,"135":135,"136":136,"137":137,"138":138,"139":139,"140":140,"141":141,"142":142,"143":143,"144":144,"145":145,"146":146,"147":147,"148":148,"149":149,"150":150,"151":151,"152":152,"153":153,"154":154,"155":155,"156":156,"157":157,"158":158,"159":159,"160":160,"161":161,"162":162,"163":163,"164":164,"165":165,"166":166,"167":167,"168":168,"169":169,"170":170,"171":171,"172":172,"173":173,"174":174,"175":175,"176":176,"197":197,"198":198,"199":199,"200":200,"201":201,"202":202,"203":203,"204":204,"205":205,"206":206,"207":207,"208":208,"209":209,"210":210,"211":211,"212":212,"213":213,"214":214,"215":215,"216":216,"217":217,"218":218,"219":219,"220":220,"221":221,"222":222,"223":223,"224":224,"225":225,"226":226,"227":227,"228":228,"229":229,"230":230,"231":231,"232":232,"233":233,"234":234,"235":235,"236":236,"237":237,"238":238,"239":239,"240":240,"241":241,"242":242,"243":243,"244":244,"245":245,"246":246,"247":247,"248":248,"249":249,"250":250,"251":251,"252":252,"253":253,"254":254,"255":255,"256":256,"257":257,"258":258,"259":259,"260":260,"261":261,"262":262,"263":263,"264":264,"265":265,"266":266,"267":267,"268":268,"269":269,"270":270,"271":271,"272":272,"273":273,"274":274,"275":275,"289":289,"290":290,"291":291,"292":292,"293":293,"294":294,"295":295,"296":296,"29
... (truncated)
```


**Sensemaker Request:** Extract all numeric values from the f_screen:phone_screen_rapids_countepisodeunlock:14dhist column from the filtered screen dataset

*Reasoning:* Step 1 completed filtering the dataset to include only records with non-null values in the target column. Now need to extract the actual values from this column to prepare for calculating the maximum.

**Info Seeker Response:**

- **Source:** screen
- **Success:** Yes

```python
result = screen['f_screen:phone_screen_rapids_countepisodeunlock:14dhist'].astype(float).dropna().tolist()
```

**Result:**
```
[434.0, 433.0, 421.0, 405.0, 408.0, 407.0, 336.0, 311.0, 330.0, 312.0, 303.0, 283.0, 267.0, 271.0, 265.0, 262.0, 262.0, 287.0, 344.0, 341.0, 336.0, 289.0, 239.0, 214.0, 166.0, 129.0, 112.0, 98.0, 98.0, 98.0, 100.0, 80.0, 27.0, 32.0, 33.0, 36.0, 36.0, 36.0, 36.0, 29.0, 22.0, 22.0, 21.0, 22.0, 20.0, 14.0, 9.0, 4.0, 4.0, 311.0, 364.0, 350.0, 364.0, 441.0, 541.0, 710.0, 803.0, 872.0, 956.0, 1113.0, 1189.0, 1306.0, 1365.0, 1394.0, 1316.0, 1274.0, 1225.0, 1232.0, 1214.0, 1121.0, 1107.0, 1168.0, 1171.0, 1097.0, 1083.0, 1030.0, 1017.0, 1007.0, 1085.0, 1102.0, 1152.0, 1152.0, 1121.0, 1084.0, 1033.0, 998.0, 977.0, 1000.0, 1028.0, 1032.0, 1061.0, 1109.0, 1093.0, 1119.0, 1102.0, 1037.0, 1029.0, 1012.0, 1007.0, 938.0, 919.0, 873.0, 862.0, 904.0, 894.0, 876.0, 825.0, 733.0, 652.0, 629.0, 587.0, 563.0, 541.0, 517.0, 470.0, 411.0, 328.0, 218.0, 153.0, 56.0, 4.0, 2081.0, 2199.0, 2220.0, 2285.0, 2253.0, 2170.0, 2364.0, 2672.0, 2980.0, 3164.0, 3203.0, 3310.0, 3275.0, 3423.0, 3454.0, 3530.0, 3564.0, 3401.0, 3422.0, 3508.0, 3539.0, 3469.0, 3375.0, 3352.0, 3345.0, 3306.0, 3391.0, 3277.0, 3015.0, 2741.0, 2866.0, 2988.0, 2830.0, 2726.0, 2662.0, 2618.0, 2571.0, 2533.0, 2539.0, 2528.0, 2510.0, 2550.0, 2735.0, 2931.0, 2741.0, 2673.0, 2741.0, 2801.0, 2792.0, 2854.0, 2961.0, 3041.0, 3079.0, 3111.0, 3115.0, 3107.0, 3076.0, 3085.0, 3070.0, 2917.0, 2959.0, 2936.0, 2985.0, 2868.0, 2690.0, 2436.0, 2107.0, 1849.0, 1643.0, 1475.0, 1310.0, 1078.0, 900.0, 807.0, 624.0, 486.0, 269.0, 129.0, 33.0, 1733.0, 1868.0, 1990.0, 2015.0, 2077.0, 2013.0, 2031.0, 1946.0, 1953.0, 1949.0, 2070.0, 2198.0, 2070.0, 2062.0, 2098.0, 2144.0, 2078.0, 1913.0, 1862.0, 1880.0, 1856.0, 1915.0, 1863.0, 1906.0, 1937.0, 1942.0, 1968.0, 1932.0, 1860.0, 1787.0, 1815.0, 1949.0, 1947.0, 1954.0, 2023.0, 2006.0, 1993.0, 1963.0, 1894.0, 1826.0, 1910.0, 1960.0, 1964.0, 2049.0, 2072.0, 2111.0, 2129.0, 2114.0, 2126.0, 2149.0, 2233.0, 2242.0, 2337.0, 2349.0, 2250.0, 2119.0, 1959.0, 1788.0, 1765.0, 1635.0, 1477.0, 1348.0, 1163.0, 983.0, 800.0,
... (truncated)
```


**Sensemaker Request:** Calculate the maximum value from screen['f_screen:phone_screen_rapids_countepisodeunlock:14dhist'].astype(float).dropna() and return the result

*Reasoning:* Step 3 is pending. I need to calculate the maximum value from the extracted values to complete the query. The step_2_result contains the extracted list of values, and I need to find the max.

**Info Seeker Response:**

- **Source:** screen
- **Success:** Yes

```python
result = screen['f_screen:phone_screen_rapids_countepisodeunlock:14dhist'].astype(float).dropna().max()
```

**Result:**
```
3955.0
```

### Sensemaker Complete

## Final Answer

```
3955.0 (maximum screen unlock episode count in 14-day history window across all participants)
```

## Verification

| Metric | Value |
|--------|-------|
| Complete | Yes |
| Accurate | Yes |
| Confidence | 100% |
| Recommendation | APPROVE |

**Summary:** The verification confirms the answer (3955.0) matches the output of Step 3 in the evidence, which was `screen['f_screen:phone_screen_rapids_countepisodeunlock:14dhist'].astype(float).dropna().max()`. This execution directly aligns with the plan's instruction to find the maximum value from the specified column.
