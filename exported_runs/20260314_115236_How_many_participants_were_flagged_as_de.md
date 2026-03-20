# CHAOS Run Export

**Date:** 2026-03-14 11:46:29

## Query

> How many participants were flagged as depressed at end-of-term AND had an above-median average 14-day rolling screen unlock count? The median is computed across all participants who have both sensor data and an end-of-term assessment.


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

**Understanding:** Need to find participants who (1) have both sensor data and end-of-term assessment, (2) were flagged as depressed at end-of-term (dep=True in dep_endterm), and (3) have screen unlock counts above the median calculated across this group. Then count these participants.

| Step | Action | Source |
|------|--------|--------|
| 1 | Load dep_endterm dataset to identify participants with end-of-term deployment status | dep_endterm |
| 2 | Identify unique participants from all sensor datasets (screen, sleep, steps, location, bluetooth, wifi, call) who have data | sensor_data |
| 3 | Join dep_endterm with sensor_data participants to find participants who have both end-of-term assessment AND sensor data | join_dep_endterm_sensor |
| 4 | Filter participants flagged as depressed at end-of-term (dep=True in dep_endterm) | dep_endterm |
| 5 | Calculate median of average 14-day rolling screen unlock count (f_screen:phone_screen_rapids_countepisodeunlock:14dhist) across depressed participants | screen |
| 6 | Filter depressed participants with screen unlock count above the calculated median | screen |
| 7 | Count the number of participants meeting all criteria | aggregated_count |

## Execution Log


**Sensemaker Request:** Load the dep_endterm dataset and extract unique participant identifiers (snowboots) who have data in the end-of-term assessment.

*Reasoning:* Starting with Step 1 of the 7-step plan. Need to load the dep_endterm dataset first to identify participants with end-of-term assessment data before we can join it with sensor data or perform any filtering operations.

**Info Seeker Response:**

- **Source:** dataset_query
- **Success:** No

```python
import pandas as pd
result = dep_endterm['snowboots'].unique().tolist()
```

**Result:**
```
Code execution failed: 'snowboots'
```


**Sensemaker Request:** Load dep_endterm dataset and extract unique participant identifiers (pid column) who have end-of-term assessment data.

*Reasoning:* Step 1 failed because 'snowboots' column doesn't exist in dep_endterm. The correct column name is 'pid' based on the dataset schema provided. Re-executing Step 1 with the correct column name.

**Info Seeker Response:**

- **Source:** pandas
- **Success:** Yes

```python
result = dep_endterm['pid'].unique().tolist()
```

**Result:**
```
['INS-W_001', 'INS-W_002', 'INS-W_003', 'INS-W_004', 'INS-W_005', 'INS-W_006', 'INS-W_007', 'INS-W_008', 'INS-W_009', 'INS-W_010', 'INS-W_011', 'INS-W_012', 'INS-W_013', 'INS-W_014', 'INS-W_015', 'INS-W_016', 'INS-W_019', 'INS-W_020', 'INS-W_022', 'INS-W_023', 'INS-W_024', 'INS-W_025', 'INS-W_028', 'INS-W_030', 'INS-W_031', 'INS-W_032', 'INS-W_033', 'INS-W_034', 'INS-W_035', 'INS-W_036', 'INS-W_037', 'INS-W_038', 'INS-W_039', 'INS-W_040', 'INS-W_042', 'INS-W_043', 'INS-W_044', 'INS-W_045', 'INS-W_046', 'INS-W_048', 'INS-W_049', 'INS-W_050', 'INS-W_051', 'INS-W_052', 'INS-W_054', 'INS-W_055', 'INS-W_057', 'INS-W_058', 'INS-W_060', 'INS-W_061', 'INS-W_062', 'INS-W_064', 'INS-W_065', 'INS-W_066', 'INS-W_068', 'INS-W_070', 'INS-W_072', 'INS-W_073', 'INS-W_074', 'INS-W_075', 'INS-W_076', 'INS-W_077', 'INS-W_078', 'INS-W_079', 'INS-W_080', 'INS-W_082', 'INS-W_086', 'INS-W_088', 'INS-W_090', 'INS-W_093', 'INS-W_094', 'INS-W_096', 'INS-W_098', 'INS-W_099', 'INS-W_102', 'INS-W_104', 'INS-W_106', 'INS-W_108', 'INS-W_109', 'INS-W_111', 'INS-W_115', 'INS-W_116', 'INS-W_117', 'INS-W_118', 'INS-W_120', 'INS-W_122', 'INS-W_123', 'INS-W_124', 'INS-W_125', 'INS-W_126', 'INS-W_127', 'INS-W_128', 'INS-W_130', 'INS-W_132', 'INS-W_134', 'INS-W_136', 'INS-W_137', 'INS-W_138', 'INS-W_140', 'INS-W_142', 'INS-W_143', 'INS-W_144', 'INS-W_145', 'INS-W_146', 'INS-W_148', 'INS-W_149', 'INS-W_150', 'INS-W_153', 'INS-W_154', 'INS-W_156', 'INS-W_157', 'INS-W_160', 'INS-W_161', 'INS-W_162', 'INS-W_163', 'INS-W_165', 'INS-W_166', 'INS-W_167', 'INS-W_168', 'INS-W_169', 'INS-W_170', 'INS-W_171', 'INS-W_172', 'INS-W_174', 'INS-W_175', 'INS-W_176', 'INS-W_177', 'INS-W_178', 'INS-W_179', 'INS-W_180', 'INS-W_181', 'INS-W_188', 'INS-W_189', 'INS-W_190', 'INS-W_191', 'INS-W_194', 'INS-W_195', 'INS-W_198', 'INS-W_201', 'INS-W_202', 'INS-W_203', 'INS-W_205']
```


**Sensemaker Request:** Load dep_endterm dataset to get participant information and filter for those flagged as depressed (dep=True)

*Reasoning:* Step 1 failed due to incorrect column name 'snowboots'. Need to properly load dep_endterm dataset which has pid and dep columns to identify participants with end-of-term assessment who were flagged as depressed.

**Info Seeker Response:**

- **Source:** dep_endterm
- **Success:** Yes

```python
import pandas as pd

result = dep_endterm[dep_endterm['dep'] == True]
```

**Result:**
```
{"Unnamed: 0":{"2":2,"3":3,"7":7,"8":8,"10":10,"11":11,"13":13,"16":16,"18":18,"20":20,"23":23,"26":26,"27":27,"30":30,"40":40,"41":41,"45":45,"48":48,"50":50,"59":59,"62":62,"63":63,"64":64,"70":70,"72":72,"74":74,"76":76,"79":79,"82":82,"88":88,"94":94,"96":96,"97":97,"101":101,"102":102,"104":104,"105":105,"109":109,"110":110,"111":111,"112":112,"118":118,"122":122,"123":123,"124":124,"127":127,"130":130,"132":132,"134":134,"136":136,"137":137},"pid":{"2":"INS-W_003","3":"INS-W_004","7":"INS-W_008","8":"INS-W_009","10":"INS-W_011","11":"INS-W_012","13":"INS-W_014","16":"INS-W_019","18":"INS-W_022","20":"INS-W_024","23":"INS-W_030","26":"INS-W_033","27":"INS-W_034","30":"INS-W_037","40":"INS-W_049","41":"INS-W_050","45":"INS-W_055","48":"INS-W_060","50":"INS-W_062","59":"INS-W_075","62":"INS-W_078","63":"INS-W_079","64":"INS-W_080","70":"INS-W_094","72":"INS-W_098","74":"INS-W_102","76":"INS-W_106","79":"INS-W_111","82":"INS-W_117","88":"INS-W_125","94":"INS-W_134","96":"INS-W_137","97":"INS-W_138","101":"INS-W_144","102":"INS-W_145","104":"INS-W_148","105":"INS-W_149","109":"INS-W_156","110":"INS-W_157","111":"INS-W_160","112":"INS-W_161","118":"INS-W_168","122":"INS-W_172","123":"INS-W_174","124":"INS-W_175","127":"INS-W_178","130":"INS-W_181","132":"INS-W_189","134":"INS-W_191","136":"INS-W_195","137":"INS-W_198"},"date":{"2":"2018-06-14","3":"2018-06-14","7":"2018-06-12","8":"2018-06-15","10":"2018-06-18","11":"2018-06-15","13":"2018-06-08","16":"2018-06-11","18":"2018-06-13","20":"2018-06-11","23":"2018-06-11","26":"2018-06-14","27":"2018-06-12","30":"2018-06-11","40":"2018-06-14","41":"2018-06-12","45":"2018-06-18","48":"2018-06-13","50":"2018-06-12","59":"2018-06-09","62":"2018-06-12","63":"2018-06-14","64":"2018-06-11","70":"2018-06-14","72":"2018-06-13","74":"2018-06-08","76":"2018-06-15","79":"2018-06-14","82":"2018-06-11","88":"2018-06-11","94":"2018-06-13","96":"2018-06-14","97":"2018-06-12","101":"2018-06-15","102":"2018-06-14","104":"2018-06-12","105
... (truncated)
```


**Sensemaker Request:** Join dep_endterm (filtered for dep=True) with sensor_data participant IDs to find participants who have both end-of-term assessment AND sensor data

*Reasoning:* Step 3 is the next pending step. I need to find the intersection of participants who have both dep_endterm data (with dep=True) and sensor data. I have the depressed participants from the previous step and the sensor participant IDs from step_2_result.

**Info Seeker Response:**

- **Source:** datasets
- **Success:** Yes

```python
import pandas as pd

# Get participants with dep=True from dep_endterm
dep_participants = dep_endterm[dep_endterm['dep'] == True]['pid'].values

# Get participant IDs from sensor data (using sleep as primary sensor dataset)
sensor_participants = sleep['pid'].values

# Find participants who have both end-of-term assessment AND sensor data
result = list(set(dep_participants) & set(sensor_participants))
```

**Result:**
```
['INS-W_102', 'INS-W_149', 'INS-W_050', 'INS-W_075', 'INS-W_134', 'INS-W_195', 'INS-W_024', 'INS-W_178', 'INS-W_175', 'INS-W_019', 'INS-W_011', 'INS-W_160', 'INS-W_037', 'INS-W_014', 'INS-W_094', 'INS-W_049', 'INS-W_145', 'INS-W_148', 'INS-W_181', 'INS-W_003', 'INS-W_098', 'INS-W_157', 'INS-W_012', 'INS-W_111', 'INS-W_079', 'INS-W_198', 'INS-W_034', 'INS-W_055', 'INS-W_168', 'INS-W_125', 'INS-W_191', 'INS-W_106', 'INS-W_080', 'INS-W_144', 'INS-W_174', 'INS-W_009', 'INS-W_138', 'INS-W_060', 'INS-W_161', 'INS-W_078', 'INS-W_022', 'INS-W_033', 'INS-W_117', 'INS-W_030', 'INS-W_062', 'INS-W_172', 'INS-W_156', 'INS-W_137', 'INS-W_008', 'INS-W_189', 'INS-W_004']
```


**Sensemaker Request:** Load dep_endterm dataset and filter for participants with dep=True, then extract their participant IDs for later filtering

*Reasoning:* Step 4 is pending per step states. Need to filter dep_endterm for depressed participants (dep=True) and get their participant IDs to continue the workflow. Previous execution showed the join was done on dep=True participants, but we need to explicitly get the list of depressed participants for Step 6 filtering.

**Info Seeker Response:**

- **Source:** python
- **Success:** Yes

```python
import pandas as pd

# Filter dep_endterm for participants where dep=True and extract participant IDs
result = dep_endterm[dep_endterm['dep'] == True]['pid'].tolist()
```

**Result:**
```
['INS-W_003', 'INS-W_004', 'INS-W_008', 'INS-W_009', 'INS-W_011', 'INS-W_012', 'INS-W_014', 'INS-W_019', 'INS-W_022', 'INS-W_024', 'INS-W_030', 'INS-W_033', 'INS-W_034', 'INS-W_037', 'INS-W_049', 'INS-W_050', 'INS-W_055', 'INS-W_060', 'INS-W_062', 'INS-W_075', 'INS-W_078', 'INS-W_079', 'INS-W_080', 'INS-W_094', 'INS-W_098', 'INS-W_102', 'INS-W_106', 'INS-W_111', 'INS-W_117', 'INS-W_125', 'INS-W_134', 'INS-W_137', 'INS-W_138', 'INS-W_144', 'INS-W_145', 'INS-W_148', 'INS-W_149', 'INS-W_156', 'INS-W_157', 'INS-W_160', 'INS-W_161', 'INS-W_168', 'INS-W_172', 'INS-W_174', 'INS-W_175', 'INS-W_178', 'INS-W_181', 'INS-W_189', 'INS-W_191', 'INS-W_195', 'INS-W_198']
```


**Sensemaker Request:** Calculate median of average 14-day rolling screen unlock count (f_screen:phone_screen_rapids_countepisodeunlock:14dhist) for depressed participants

*Reasoning:* Step 5 is pending. I need to calculate the median of screen unlock counts for the depressed participants identified in Step 4. This will be needed to filter participants with screen unlock counts above the median.

**Info Seeker Response:**

- **Source:** step_4_result
- **Success:** Yes

```python
import pandas as pd

# Get depressed participant IDs from step_4_result
depressed_ids = set(step_4_result)

# Filter screen data for depressed participants
dep_screen = screen[screen.pid.isin(depressed_ids)]

# Calculate 14-day rolling average of screen unlock count
roll_mean = dep_screen['f_screen:phone_screen_rapids_countepisodeunlock:14dhist'].rolling(window=14).mean()

# Calculate and store the median of these averages
result = roll_mean.median()
```

**Result:**
```
1257.9285714285716
```


**Sensemaker Request:** Filter depressed participants (from step_4_result) whose screen unlock count's 14-day rolling average exceeds the Step 5 median (1257.9285714285716). Count the number of unique participants meeting this criteria.

*Reasoning:* Step 6 requires filtering screen data for depressed participants, calculating each participant's 14-day rolling average, then comparing against the Step 5 median. Previous steps provided the median and participant IDs; this step filters and counts qualifying participants.

**Info Seeker Response:**

- **Source:** preprocess
- **Success:** No

```python
import pandas as pd

# Filter depressed participants from step_4_result
depressed_participants = set(step_4_result)

# Filter screen data to only include depressed participants
screen_filtered = screen[screen['pid'].isin(depressed_participants)].copy()

# Sort by date to ensure correct rolling window calculation
screen_filtered = screen_filtered.sort_values('date')

# Calculate the 14-day rolling average of screen_unlocks per participant
rolling_avg = screen_filtered.groupby('pid')['screen_unlocks'].transform(
    lambda x: x.rolling(window=14, min_periods=1).mean()
)

# Count unique participants whose rolling average exceeds the median threshold
result = rolling_avg[rolling_avg > 1257.9285714285716].reset_index().groupby('pid').nunique().values[0]
```

**Result:**
```
Code execution failed: 'Column not found: screen_unlocks'
```


**Sensemaker Request:** Filter depressed participants from step_4_result whose f_screen:phone_screen_rapids_countepisodeunlock:14dhist's 14-day rolling average exceeds the Step 5 median (1257.9285714285716). Count the number of unique participants meeting this criteria using the correct column name from the screen dataset schema.

*Reasoning:* Step 6 failed with error 'Column not found: screen_unlocks'. The schema shows screen data uses column name 'f_screen:phone_screen_rapids_countepisodeunlock:14dhist' (as used correctly in Step 5), not 'screen_unlocks'. Need to re-run Step 6 with correct column name for filtering depressed participants whose screen unlock count's 14-day rolling average exceeds the median threshold from Step 5.

**Info Seeker Response:**

- **Source:** screen
- **Success:** Yes

```python
import pandas as pd
import numpy as np

# Step 4 result contains participant IDs
step_4_pids = set(step_4_result)

# Get depressed participants from dep_weekly
dep_mask = dep_weekly['dep'].notna()
depert_pids = set(dep_weekly[dep_mask]['pid'].unique())

# Find intersection of depressed participants in step_4
filtered_pids = step_4_pids.intersection(depert_pids)

# Get screen data for these participants
screen_whitelisted = screen[screen['pid'].isin(filtered_pids)]

# Calculate the 14-day rolling average of phone screen episode unlocks
target_col = 'phone_screen_rapids_countepisodeunlock_14dhist'
for col in screen.columns:
    if 'phone' in col.lower() and 'screen' in col.lower():
        target_col = col

screen_whitelisted['rolling_avg'] = screen_whitelisted[target_col].rolling(window=14).mean()

# Filter those exceeding the Step 5 threshold (1257.9285714285716)
filtered = screen_whitelisted[screen_whitelisted['rolling_avg'] > 1257.9285714285716]

# Count unique participants
result = len(filtered['pid'].unique())
```

**Result:**
```
0
```

### Sensemaker Complete

## Final Answer

```
0 participants
```

## Verification

| Metric | Value |
|--------|-------|
| Complete | No |
| Accurate | No |
| Confidence | 0% |
| Recommendation | NEEDS_REVIEW |
