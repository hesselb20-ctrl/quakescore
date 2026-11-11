# Prior art and ground-truth data: smartphone modal identification of buildings

Compiled 2026-11-11. Every number below was read in a fetched page, abstract or PDF during this compilation, except where marked "NOT VERIFIED" or "DERIVED" (arithmetic done here from a verified number; the formula is stated). Quotations are kept to a minimum; most text is paraphrase.

Conventions: f1 = first-mode frequency; EW/NS = east-west/north-south (or L/T = longitudinal/transverse where the source uses those); zeta = damping ratio; "ambient" = wind/traffic/occupancy excitation only; "forced" = shaker; "EQ-level" = recorded during an earthquake (amplitude-dependent softening applies).

---

## 1. PRIOR ART: smartphones for building modal identification

### 1a. Kong, Allen, Kohler, Heaton, Bunn (2018)

- Citation: Kong, Q., Allen, R. M., Kohler, M. D., Heaton, T. H., Bunn, J. (2018). Structural health monitoring of buildings using smartphone sensors. Seismological Research Letters 89(2A), 594-602. DOI 10.1785/0220170111. https://doi.org/10.1785/0220170111 (bibliographic record: https://authors.library.caltech.edu/84498 ; full text read from https://rallen.berkeley.edu/pub/2018kong/KongEtAl-MyShake-StructuralHealthMonitoring-SRL-2018.pdf)
- Method: forced-vibration (roof shaker) test of Millikan Library, Pasadena. 25 smartphones of 18 listed models lay on the 9th (top) floor, NW corner, x axis roughly aligned E-W, compared with the permanent 3-component Episensor (station CI MIK) on the same floor. Phones recorded at 25 samples/s with a stated flat response over 0.1-12.5 Hz. Shaker swept 0.2-2.45 Hz in 0.05 Hz steps, 60 s holds, extended to 600 s near modes, first N-S then E-W, over about 2.5 h.
- Frequencies stated: fundamental E-W 1.2 Hz, N-S 1.7 Hz, torsion 2.4 Hz (test description); the results section gives N-S 1.7 Hz and torsion 2.35 Hz.
- Validated: phone vs Episensor waveforms highly correlated even when phones were not coupled to the floor; f1 EW, f1 NS and torsion extracted from single-phone records; double-integrated displacement matched the reference in phase and amplitude (peak about 0.05 cm in the plotted N-S window, high-pass 0.5 Hz). Stacking 7 phones (those with correlation above 0.6, mostly the phones with the best spec resolution) improved SNR; stated spectral noise level about 10e-5 for a single phone vs about 10e-6 for the stack (units not legible in the extracted text).
- Table 1 lists accelerometer vendor and spec resolution per model: spec resolution ranges from 5.99e-4 m/s^2 to 1.53e-1 m/s^2 (about 0.06 mg to 15.6 mg); chips named include InvenSense MPU6500/MPU6515, ST LSM330DLC/LIS3DH/K6DS3TR, Bosch BMA150/BMA222. Per-phone mapping of chip to model was not reliably recoverable from the extracted table. The paper says the resolution is the spec value and a best case.
- Stated limitations/challenges: single phone location, floor and orientation unknown; test used ideal placement (top floor, corner, phone flat on floor); other building types, floors and surfaces untested; ambient-vibration recovery from phones and the lower limits of useful earthquake shaking need more work. The excitation was a shaker, not ambient.
- Insurance / risk: no occurrence of "insurance". The word "risk" appears once, in the challenges/benefits discussion near the end (pp. 599-600; exact page not confirmed): monitoring millions of buildings "to reduce the earthquake risks" at city or national scale. No seismic-risk-assessment or insurance application is discussed.

### 1b. Patel et al. (2023), MyShake structural health monitoring

- Citation: Patel, S. C., Gunay, S., Marcou, S., Gou, Y., Kumar, U., Allen, R. M. (2023). Toward Structural Health Monitoring with the MyShake Smartphone Network. Sensors 23(21), 8668. DOI 10.3390/s23218668. https://doi.org/10.3390/s23218668 (full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC10650570/)
- Data: earthquake-triggered, not ambient. Forced vibration during shaking and free vibration (coda) after shaking. The authors state ambient-level measurement was not feasible with the phone noise floor.
- Shake-table validation: 3-storey steel frame on the PEER 6-DOF table, 9 phones plus TE Connectivity 3022 reference accelerometers (200 Hz); 1999 Kocaeli and 2006 Kobe inputs. Pre-event f1 3.50-3.52 Hz (Kocaeli) and 3.42-3.50 Hz (Kobe). Brace disengagement lowered frequency by up to 22%. Modes separated by more than about 0.4 Hz could be resolved. Phones slid/clipped above about 0.5 g without a noticeable effect on frequency.
- Real buildings: 7 structures (3 to 18 storeys), each from one earthquake recording (see table in section 3b); one L-shaped 5-storey building was recorded for three earthquakes over four months (4.85, 4.62, 4.50 Hz). Abstract-level accuracy claim: repeat measurements fall within 7% of each other. Most measured frequencies fell within about 41% of at least one ASCE-based estimate (the Conclusions say 40%).
- Phone performance (as measured by the authors): noise floor about -40 dB for 2010-2013 phones (2016 study) vs about -75 dB for 2017 and 2021 models. dB here is power spectral density relative to 1 (m/s^2)^2 per Hz. Low frequencies range from about -50 to -80 dB, high frequencies about -78 to -85 dB. Sampling 25 Hz (2016-2018 average) and 50 Hz (more recent). Timing: 50% of NTP offset changes under 32 ms, 85% under 111 ms. Location: analysis limited to phones reporting 30 m or better.
- Stated limits: one sensor per building, unknown height and orientation; lower sampling rate and higher noise than conventional sensors; forced-vibration frequencies may be biased low relative to ambient; framing type of buildings often unknown; waveform data not public (privacy).
- Insurance / risk: grep of the full text found no "insurance", "risk assessment" or "seismic risk". Nearest application sentence, near the end of the paper: a long-term database of "healthy" behaviour could give a remote diagnostic distributed to local engineering first responders to prioritize inspections of suspected-damage buildings. Section number not confirmed.

### 1c. Kumar, Marcou, Allen (2025), Journal of Building Engineering

- Citation: Kumar, U., Marcou, S., Allen, R. M. (2025). Ambient vibration analysis of high-rise buildings using MyShake smartphone data. Journal of Building Engineering 106, 112496. DOI 10.1016/j.jobe.2025.112496. https://doi.org/10.1016/j.jobe.2025.112496 (PDF read: https://rallen.berkeley.edu/pub/2025Kumar/Kumar-MyShakeSHM-SF-JBuildEng-2025.pdf). Received 9 Oct 2024, accepted 24 Mar 2025.
- Data: ambient (wind-triggered) 5-minute recordings from phones left in 4 San Francisco Bay Area buildings (mid-rise to tall), about six months, phones triggered remotely daily and when regional wind exceeded 12 m/s. Phones: Google Pixel, Samsung Galaxy, Motorola Razr; some taped, some untaped. Sampling 50 Hz.
- Method: multitaper PSD, automated peak picking, half-power bandwidth damping. Simulation: 5-min segment of a Kinemetrics EpiSensor recording on the 34th floor of the 197 m Millennium Tower (three days of ambient data, windy), downsampled to 50 Hz, with MyShake-type noise added (average noise floor about -75 dB, -50 to -80 dB at low frequency, -78 to -85 dB at high frequency). Peaks at 0.26, 0.30 and 0.43 Hz survived in both versions.
- Field results (Table 1 and text; table damping units not stated in the extracted table, so use text values):
  - Millennium Tower, 301 Mission St, San Francisco (197 m, RC frame, 58 floors per table; the text once says 56-floor, inconsistent): phone on 56th floor f1 = 0.30 Hz (X) and 0.26 Hz (Y); EpiSensor on 34th floor 0.26, 0.30, 0.43 Hz. Mean zeta 0.7% (X) and 0.8% (Y) by half-power bandwidth, which the authors call exceptionally low.
  - 188 Minna St, San Francisco (138 m, RC frame, 42 floors), phone on 27th floor: about 0.33 +/- 0.12 and 0.40 +/- 0.13 Hz (table).
  - Pacific Park Plaza, 6363 Christie Ave, Emeryville (95 m, RC frame, 30 floors): about 0.47-0.48 Hz both axes (phones on 15th/16th floors).
  - SkyDeck, 2150 Shattuck Ave, Berkeley (54 m, lift-slab, 14 floors), phone on 13th floor: f1 0.70-0.85 Hz; text gives zeta "between 0.08 and 0.12" with no unit stated (NOT VERIFIED whether fraction or percent; 8-12% would be very high for ambient).
- Accuracy statement: phone results said to align with earlier traditional-sensor studies; for Pacific Park Plaza, 0.47 Hz vs Celebi et al. ambient 0.48 Hz.
- Stated limits: taller buildings give reliable estimates even in low wind; shorter buildings need stronger excitation and many recordings are rejected on low SNR (noise dominates). Only fundamental mode and damping handled; sensor placement and environmental noise limit accuracy; half-power method can err for closely spaced modes. Data not public.
- Insurance / risk: text search found no "insurance" and no "risk assessment". Stated aims are health monitoring, detecting deterioration, damage and retrofit effects.

### 1d. Kong, Allen, Schreier, Kwon (2016), MyShake (noise floors only)

- Citation: Kong, Q., Allen, R. M., Schreier, L., Kwon, Y.-W. (2016). MyShake: A smartphone seismic network for earthquake early warning and beyond. Science Advances 2(2). DOI 10.1126/sciadv.1501055 (article number e1501055 inferred from DOI suffix, not separately seen). https://doi.org/10.1126/sciadv.1501055 (full text read: https://escholarship.org/uc/item/4sn3n37r)
- Noise-floor content: phones were left in a quiet Berkeley basement for 1 month at 50 samples/s; noise floor computed by the McNamara and Buland method (Fig. 1, which shows phone curves color-coded by release date against a high-quality MEMS and the BKS force-balance station). The noise floor includes phone self-noise plus quiet-basement environment. All phones were sensitive to M5 or larger within 10 km at 1-10 Hz; newer phones were sensitive to M3.5 at 10 Hz. Fig. 1 axis values are not in the extracted text, so no numeric noise-floor values from this paper are reported (NOT VERIFIED).
- Shake-table: bolted phones recorded ground motion accurately between 0.5 and 10 Hz; free phones began sliding at about 0.3 g above about 3 Hz, clipping peaks (recorded amplitudes are lower bounds).
- Insurance / risk: no insurance. "Financial loss" is mentioned for earthquake impacts in general (introduction). No building risk assessment application.

### 1e. Other peer-reviewed work

1. Feng, M., Fukuda, Y., Mizuta, M., Ozer, E. (2015). "Citizen Sensors" for SHM: Use of Accelerometer Data from Smartphones. Sensors 15(2), 2980-2998. DOI 10.3390/s150202980. https://doi.org/10.3390/s150202980 (read: https://pmc.ncbi.nlm.nih.gov/articles/PMC4367344)
   - Phones: iPhone 3GS (LIS331DL), iPhone 5 (LIS331DLH), Samsung Galaxy S4 (Bosch SMB380), app "Seismometer" at 100 Hz; reference PCB 393B04.
   - Tests: small shake table sinusoids 0.5-20 Hz at 0.05-0.2 g; large shake table with a masonry column model (not a building); pre-stressed concrete pedestrian bridge, Princeton NJ, under ambient, random and synchronized jumping.
   - Numbers: column f1 reference vs phone: ambient 18.2 vs 18.4 Hz (1.10%), white noise 17.4 vs 17.2 (1.15%), earthquake 17.1 vs 17.5 (2.34%). Bridge f1: ambient 3.13 vs 3.16 Hz (0.96%), random 3.08 vs 3.11, jumping 3.00 vs 3.03. Bridge ambient response under 0.005 g. iPhone 5 amplitude error 0.45-17.4% over frequency (3.10% at 1 Hz); iPhone 3GS 17.5% at 1 Hz and 43.9% at 0.5 Hz.
   - Limits: phones not synchronized with the reference; less sensitive at low amplitude; coupling to structure unresolved; only 3 phones, 1 column model, 1 bridge. Not a building test.
   - Insurance: none. Mentions rapid post-event damage assessment in a large urban setting as motivation.
2. Mugabo, I., Barbosa, A. R., Riggio, M. (2019). Dynamic Characterization and Vibration Analysis of a Four-Story Mass Timber Building. Frontiers in Built Environment 5, 86. DOI 10.3389/fbuil.2019.00086 (not smartphone-based; used with conventional accelerometers; listed here as a ground-truth source, see 3a).

Not located/read in this pass: Ozer and Feng conference/book-chapter material on smartphone SHM (only seen as search-result summaries, not read); a smartphone-in-building ambient study by other groups. NOT VERIFIED: any further smartphone-in-building papers. Sarmadi et al. is cited in Kumar et al. as a review of smartphone SHM but the review itself was not opened.

---

## 2. PHONE ACCELEROMETER NOISE

### 2a. Measured / published values for phone MEMS accelerometers

| Sensor / phone | Quantity | Value | Bandwidth / ODR / conditions | Source |
|---|---|---|---|---|
| MyShake Android phones, 2017 and 2021 models | PSD noise floor | about -75 dB re 1 (m/s^2)^2/Hz (range -50 to -80 at low f, -78 to -85 at high f) | 25-50 Hz sampling | Patel et al. 2023, https://doi.org/10.3390/s23218668 |
| MyShake Android phones, 2010-2013 models | PSD noise floor | about -40 dB re 1 (m/s^2)^2/Hz | 2016 study, basement test | same (citing the 2016 study) |
| MyShake phones deployed in buildings | PSD noise level seen in field | near -70 dB; structural peaks often above -60 dB | 50 Hz, 5-min records | Kumar et al. 2025, https://doi.org/10.1016/j.jobe.2025.112496 (dB reference not restated in this paper; Patel et al. state it as 1 (m/s^2)^2/Hz) |
| (conversion, DERIVED) | -75 dB -> sqrt(10^(-7.5)) = 1.78e-4 m/s^2/sqrt(Hz) = 18 ug/sqrt(Hz) (g = 9.80665) | | | arithmetic from above |
| (conversion, DERIVED) | -70 dB -> 3.2e-4 m/s^2/sqrt(Hz) = 32 ug/sqrt(Hz); -60 dB -> 1.0e-3 = 102 ug/sqrt(Hz) | | | arithmetic |
| iPhone 4 (LIS331DLH) | datasheet noise density | 0.218 mg/sqrt(Hz) | chip data rate 0.5-1000 Hz | Kos et al. 2016, https://doi.org/10.3390/s16030301 (Table 1) |
| iPhone 4 (LIS331DLH), 6 units | measured velocity random walk | 0.25 mg/sqrt(Hz) average (reported as "VRW = 0.25 mg0/Hz") | Allan variance; bias tests at 60 Hz | same |
| iPhone 4 x 6 units | noise-induced bias variation | 0.4-0.5 mg | stable temperature | same |
| iPhone 5 (LIS331DLH) | noise density (as printed) | 0.218 mg/sqrt(Hz) | ODR 0.5-1000 Hz | Feng et al. 2015, https://doi.org/10.3390/s150202980 (Table 1; extracted text, unit symbol lost) |
| Galaxy S4 (Bosch SMB380) | noise density (as printed) | 0.5 mg/sqrt(Hz); 3.9 mg/digit | ODR 3000 | same |
| iPhone 3GS (LIS331DL) | noise density | N/A in table; 18 mg/digit | ODR 100, 400 | same |
| Reference PCB 393B04 | noise density (as printed) | 0.00004 mg/sqrt(Hz) | 0.05-750 Hz | same |
| 18 Android models used at Millikan | spec resolution (LSB) | 5.99e-4 to 1.53e-1 m/s^2 (0.06 to 15.6 mg) | spec values, best case | Kong et al. 2018, https://doi.org/10.1785/0220170111 (Table 1) |

Not found: a peer-reviewed measured noise-density spectrum in ug/sqrt(Hz) for a named modern phone (the search result mentioning Xiaomi Mi8 Allan-variance tests was only a snippet; not read, NOT VERIFIED). Phone-level RMS noise values were not found in a read source.

### 2b. Manufacturer datasheet values for common phone IMUs

| Sensor | Accel noise density | Bandwidth / ODR / conditions | Source (file actually read) |
|---|---|---|---|
| Bosch BMI160 | typ 180, max 300 ug/sqrt(Hz) (+/-8 g, normal mode, 25 C, nominal VDD); RMS noise, normal filter mode, +/-8 g: Z axis 0.5 mg at 12.5 Hz ODR rising to 3.7 mg at 1600 Hz (X,Y reach 3.6 and 5.2 mg at the highest two ODRs); ODR 12.5-1600 Hz; 16-bit, 16384 LSB/g at +/-2 g | data sheet revision 1.0, Nov 2020 | https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi160-ds000.pdf |
| Bosch BMI270 | typ 0.16 mg/sqrt(Hz) = 160 ug/sqrt(Hz) (normal mode, 25 C, +/-8 g; the extraction shows "0.16 mg/Hz", sqrt symbol lost); RMS noise typ at +/-8 g, normal/performance mode: 0.38 mg (12.5 Hz ODR), 1.06 mg (100 Hz), 1.51 mg (200 Hz), 4.35 mg (1600 Hz); 3 dB bandwidth 5.5 Hz at 12.5 Hz ODR, 44 Hz at 100 Hz, 89 Hz at 200 Hz | datasheet revision 1.6 | https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi270-ds000.pdf |
| ST LSM6DSO | 70 ug/sqrt(Hz) at +/-2 g, 75 at +/-4 g, 80 at +/-8 g, 110 at +/-16 g (high-performance mode); RMS noise normal/low-power mode 1.8 mg (+/-2 g) to 3.0 mg (+/-16 g); ODR 12.5-6664 Hz; sensitivity 0.061 mg/LSB at +/-2 g | DocID030608 Rev 1, Aug 2018 (read from a third-party mirror of the ST document: https://static.chipdip.ru/lib/918/DOC011918449.pdf; ST's own URL https://www.st.com/resource/en/datasheet/lsm6dso.pdf timed out) | |
| TDK ICM-42688-P | AXY 65, AZ 70 ug/sqrt(Hz) (comparison table in the product brief, ICM-42688-P column) | product brief PB-000072 Rev 1.0, 19 Apr 2020, ODR up to 32 kHz, 16/18-bit, +/-16 g (full datasheet DS-000347 could not be downloaded; its noise spec table and test conditions (low-noise mode bandwidth) were NOT VERIFIED) | https://www.farnell.com/datasheets/3045877.pdf |

Note on comparison (DERIVED): the derived field noise level of about 18-32 ug/sqrt(Hz) from the MyShake dB values is lower than the datasheet noise densities of 70-180 ug/sqrt(Hz) quoted above. The datasheet figures are at +/-2 g to +/-8 g full scale in high-performance modes of specific chips; the MyShake phones are mixed models and the PSD estimation method differs. The two sets are not directly reconcilable from the sources read; treat the dB phone values as empirical fleet numbers and the datasheet values as chip specs.

---

## 3. GROUND-TRUTH BUILDINGS

Notes: "amb" = ambient-level, "forced" = shaker at the stated weight setting, "EQ" = earthquake-level (frequencies lower). Heights as stated by source. Where a cell says NOT VERIFIED the value was not in the pages read.

### 3a. Main table

| # | Building | City | Storeys | Height (m) | System / material | f1 each horizontal direction (Hz) | f1 torsion (Hz) | Damping | Test type, year | Citation / URL |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Broad Center (Caltech) | Pasadena, CA | 3 (plus two deep basements) | NOT VERIFIED | Steel, stiff unbonded braced frame; completed 2002 | EW 2.67, NS 2.43 (the paper calls these preliminary, from 14 days of continuous data, Feb 2003; note EW and NS first overtones are close: 3.01, 2.81) | 3.65 (preliminary, tabulated in the torsional row, with a machine-noise caveat in the text) | NOT VERIFIED | amb, 2003 | Clinton et al. 2006, BSSA 96(1), 237-257, https://doi.org/10.1785/0120050052 |
| 2 | Albina Yard | Portland, OR | 4 | 15.39 | Mass timber: glulam and CLT floors, light-frame plywood shear walls with steel hold-downs; completed 2017 | NS 2.86, EW 4.20 (SSI) | 4.29 | EW f1: 1.38% (EFDD) vs 5.66% (SSI); other modes NOT VERIFIED | amb, Jan 2017 (about 2 h, weekend) | Mugabo, Barbosa, Riggio 2019, Front. Built Environ. 5:86, https://doi.org/10.3389/fbuil.2019.00086 |
| 3 | 9-storey RC dwelling (built 1939) | Grenoble, France | 9 | NOT VERIFIED | Poorly reinforced RC frames with shear walls, no seismic code | Transverse 2.28, Longitudinal 2.73 (FDD); bridge-demolition test gave 2.27 and 2.75 | 4.74 | 4% (random decrement, from the demolition test, "all modes") | amb (15 min, 200 Hz) plus small-amplitude demolition-induced excitation, year NOT VERIFIED | Michel, Gueguen, Bard, arXiv preprint (submitted to Soil Dyn. Earthq. Eng.), https://arxiv.org/abs/0710.1210 (final volume/pages NOT VERIFIED) |
| 4 | Millikan Library | Pasadena, CA | 9 (plus basement) | 43.9 above grade, 48.2 above basement | RC moment frame with RC shear walls (30.5 cm; E-W core and frame, N-S shear walls); completed 1967 | Ambient (2-yr average of continuous MIK data): EW 1.19, NS 1.72. Forced 2002 (half weights): EW 1.14, NS 1.67. Forced 1968: EW 1.45, NS 1.90 | amb 2.46; forced 2.38 | NOT VERIFIED in pages read | amb 2002-2004 and forced 2002 | Clinton et al. 2006, https://doi.org/10.1785/0120050052 (PDF read: https://authors.library.caltech.edu/records/pxezy-na460) |
| 5 | Grenoble City Hall | Grenoble, France | 13 | 52 | RC; two RC shear-wall cores; glass cladding; built 1967 | L 1.16, T 1.22 (Michel et al. 2010, cited by Mikael et al.); RDT one-year monitoring means L 1.162, T 1.224 (year NOT VERIFIED) | 1.45 (as cited) | RDT mean 1.03% (L), 1.03% (T) | amb, Mikael et al. one-year permanent monitoring | Mikael et al. 2013, BSSA 103(1), 236-246, https://doi.org/10.1785/0120120048 (arXiv: https://arxiv.org/abs/1303.2642) |
| 6 | Ophite Tower | Lourdes, France | 18 | about 59 (DERIVED: 18 x 3.3 m inter-storey, not stated) | RC shear-wall dwelling building, built 1972 | L 1.74, T 1.73 (mean 1.747, 1.741) | about 2.2 | 0.88% (L), 0.83% (T) | amb, permanent accelerometer, one year | Mikael et al. 2013 (same) |
| 7 | UCLA Factor Building | Los Angeles, CA | 17 | NOT VERIFIED in the paper read | Steel moment-resisting frame | Ambient 2002-2003: NS 0.58-0.60, EW 0.54-0.56 (3 a.m. recordings); earthquake-level (Encino 2003 EQ): NS 0.52 (about 12% lower than the 0.59 ambient mean) | amb 0.80-0.81; EQ 0.7 | NOT VERIFIED | amb and EQ-level, 2002-2003 | Kohler, Davis, Safak 2005, Earthquake Spectra 21(3), 715-736, https://doi.org/10.1193/1.1946707 |
| 8 | Belledonne and Mont-Blanc towers (Ile Verte) | Grenoble, France | 30 each | 100 | RC, two continuous walls over height plus small RC walls; built 1963-67; not seismically designed | Belledonne: T 0.67, L 0.89 (RDT means 0.672, 0.890); Mont-Blanc: T 0.65, L 0.84 (0.648, 0.837) | about 1 (both) | Belledonne 1.09% (L), 0.67% (T); Mont-Blanc 0.86% (L), 0.59% (T) | amb, one month, tops of both towers, year NOT VERIFIED | Mikael et al. 2013 (same) |
| 9 | Pacific Park Plaza | Emeryville, CA | 30 | 95 | RC frame | Most recent ambient: 0.48 (Celebi et al., as cited by Kumar et al.); MyShake phones 0.47 both axes. Range of ambient tests 0.48-0.54; forced vibration 1985: 0.58; Loma Prieta 1989 EQ: 0.38 | NOT VERIFIED | NOT VERIFIED here (phone half-power values about 0.06-0.12 per table, unit unclear) | amb and EQ-level; all values secondhand via Kumar et al. 2025 | Kumar et al. 2025, https://doi.org/10.1016/j.jobe.2025.112496 (primary Celebi paper NOT located) |
| 10 | Millennium Tower (301 Mission St) | San Francisco, CA | 58 (table) vs 56 (text) | 197 | RC frame | EpiSensor and phones: 0.26 and 0.30 (X, Y of the building axes); another peak at 0.43 attributed to a higher harmonic or other mode | NOT VERIFIED | mean 0.7% (X), 0.8% (Y), half-power | amb (wind), 2024, phones and EpiSensor | Kumar et al. 2025 (same) |

Gaps against the target: 10 buildings; spans 3 to 58 storeys; low-rise (3-6 storeys) rows: Broad Center (3) and Albina Yard (4); the Grenoble 9-storey is mid-rise. The 3, 4 and 5-storey rows with EQ-level phone measurements are in 3b. The CESMD/CSMIP search, Celebi USGS reports and Earthquake Spectra / EESD operational-modal studies were only searched at summary level; the NIST IR 4511 / USGS OFR 90-677 report (Marshall, Phan, Celebi, 1991) was opened but contains only building selection, no frequencies (https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir4511.pdf). Millikan damping values and the Bradford et al. 2004 Caltech EERL report were not read; Nayeri et al. 2008 (Factor building modal values) full text was not accessible.

### 3b. Earthquake-level phone-derived values (not ground truth, but useful low-rise reference points)

From Patel et al. 2023 (https://doi.org/10.3390/s23218668); all EQ-level, one phone, frequencies as stated by the authors.

| Location | Storeys | f1 (Hz) | Event |
|---|---|---|---|
| Berkeley, CA (hotel) | 8 | 2.08 | Mw 4.4 |
| Carson, CA (condo) | 14 | 1.42 | Mw 4.28 |
| Searles Valley, CA (apartments) | 18 | 0.82 | Mw 5.37 |
| Carson, CA (apartments) | 3 | 2.71 | Mw 4.28 |
| Tsukuba, Japan (apartments) | 5 | 3.05 | Mwr 4.7 |
| Ferndale, CA (hotel) | 3 | 4.26 | Mw 6.4 |
| Santa Rosa, CA (L-shaped apartments) | 5 | 4.85; 4.62 (Mw 5.06); 4.50 (Mw 3.57) | Ml 4.29 |

Further comparison point (shake table, not a building): 3-storey steel frame model f1 about 3.5 Hz (Patel et al. 2023).

Other values cited inside the sources read: MIT Green Building (Cambridge, MA) fundamental frequencies 0.75 (NS) and 0.67 (EW) Hz, from a USGS search-result summary only (NOT VERIFIED, not opened).

---

## 4. AMBIENT VIBRATION AMPLITUDES

Read and verified numbers:

| Item | Value | Conditions | Source |
|---|---|---|---|
| Millikan Library roof, ambient amplitude | order-of-magnitude statements only: daytime ambient excitation about 10 times the night level; during a Santa Ana windstorm the fundamental-mode amplitudes rose about 10 times and E-W f1 dropped about 3% | 43.9 m RC building | Clinton et al. 2006, https://doi.org/10.1785/0120050052. Absolute ambient RMS not extracted (NOT VERIFIED). |
| Millikan roof acceleration in earthquakes (EQ-level, for scale) | 2.8 cm/s^2 (Anza M6.1, 2001), 5 (Yorba Linda M4.8), 7 (Beverly Hills M4.2), 18 (Big Bear M5.4); 8 cm/s^2 generated at the N-S fundamental with full shaker weights | Figure caption | Clinton et al. 2006 |
| Millikan in earlier strong shaking | roof accelerations 49 cm/s^2 (Lytle Creek 1970) and 306-341 cm/s^2 (San Fernando 1971) | | Clinton et al. 2006 |
| Pedestrian bridge (not a building), ambient | peak response below 0.005 g | Princeton NJ | Feng et al. 2015, https://doi.org/10.3390/s150202980 |
| Millikan forced test, displacement | peak about 0.05 cm at 1.7 Hz (shaker, not ambient) | top floor | Kong et al. 2018 |
| Phone-detectable building signal | structural PSD peaks often above -60 dB and field phone noise near -70 dB re 1 (m/s^2)^2/Hz at 50 Hz sampling, in 54-197 m buildings under wind | | Kumar et al. 2025. DERIVED: -60 dB = 1.0e-3 m/s^2/sqrt(Hz) at the peak. |
| Shorter buildings under ambient/wind | many phone measurements rejected for low SNR | | Kumar et al. 2025 |

Not obtained (search snippets only, not opened, do not use as verified): a 167 m office building at about 2 mg RMS and a proposed 5 mg RMS limit; a Boston tower median wind-event RMS acceleration of about 0.46 mg; occupant-survey RMS 1-2 mg average, 2-5 mg storm peaks. NOT VERIFIED (original documents not read; two source files were unreachable or scanned).

### 4b. Urban ground noise levels

Peterson (1993) NHNM and NLNM (USGS Open-File Report 93-322, https://pubs.usgs.gov/publication/ofr93322). The USGS PDF returned HTTP 403 and was not read. The values below come from the Peterson model tables shipped as a data file inside the ObsPy 1.5.1 source distribution (obspy/signal/data/noise_models.npz), read directly and not through the report. Treat as a secondary copy of Peterson's curves; units dB re 1 (m/s^2)^2/Hz.

| Period (s) / frequency | NLNM (dB) | NHNM (dB) | NHNM as amplitude, DERIVED | NLNM as amplitude, DERIVED |
|---|---|---|---|---|
| 0.1 s / 10 Hz | -168.0 | -91.5 | 2.7e-5 m/s^2/sqrt(Hz) = 2.7 ug/sqrt(Hz) | 0.0004 ug/sqrt(Hz) |
| 0.2 s / 5 Hz | -166.7 | -96.7 | 1.5 ug/sqrt(Hz) | |
| 0.5 s / 2 Hz | -167.5 | -115.2 | 0.18 ug/sqrt(Hz) | |
| 1 s / 1 Hz | -166.3 | -116.8 | 0.15 ug/sqrt(Hz) | 0.0005 ug/sqrt(Hz) |
| 2 s / 0.5 Hz | -152.8 | -107.0 | | |
| 5 s / 0.2 Hz | -142.2 | -98.1 | | |

Values are the nearest tabulated points in the file (periods 0.1, 0.1995, 0.5035, 1.005, 2.004, 5.129 s).

Urban measurements read:
- Barcelona seismic stations, 2-20 Hz, business hours (Diaz, Ruiz, Jara 2021, Solid Earth 12, 725-739, https://doi.org/10.5194/se-12-725-2021): most stations peak around -90 to -95 dB re 1 m^2 s^-4 Hz^-1; the louder stations (PORT, R4B31) -80 to -90 dB; quiet ones (JPLA, RD3AF, CASN) -105 to -110 dB. Network-average day-night difference about 15 dB, more than 20 dB at some high-school sites.
- Central London, 5 broadband stations, summer 2015 (Green, Bastow, Dashwood, Nippress 2017, Seismological Research Letters 88(1), 113-124, https://doi.org/10.1785/0220160128; abstract and summary read from https://nora.nerc.ac.uk/id/eprint/516717/): traffic noise at periods below 0.4 s is about 20 dB above the new high-noise model; daytime RMS acceleration at 0.1 s about 1000 times that at the Eskdalemuir observatory in Scotland. Tabulated median PSDs are in the paper's supplement (not read; NOT VERIFIED).
- DERIVED: NHNM at 10 Hz (-91.5 dB) plus 20 dB gives about -71.5 dB, i.e. in the same range as the phone noise level near -70 to -75 dB noted in section 2a, so urban traffic noise at several Hz to 10 Hz can approach or exceed phone self-noise. This is an inference, not a statement from either source.

---

## 5. FREQUENCY VARIABILITY

All from Clinton et al. 2006 (BSSA 96(1), 237-257, https://doi.org/10.1785/0120050052) unless stated.

| Effect | Numbers | Building |
|---|---|---|
| Amplitude (forced shaker weights) | full weights 1.11 Hz vs 1.14 Hz with only four side weights: 0.03 Hz, 2.5%; a factor 2.23 in applied force | Millikan EW, July 2002 |
| Amplitude (EQ strong motion) | during strong motion frequencies temporarily drop about 20%; Big Bear 2003 (M5.4): f1 EW 1.06 Hz, 11% below the pre-event ambient 1.19 Hz and about 7% below forced values; second EW mode 6.2% below the 4.85 Hz ambient | Millikan |
| Amplitude (small EQ), Factor | EQ-level f1 about 0.05-0.1 Hz lower than ambient (Encino: 0.52 vs 0.59 Hz NS, about 12%; second modes about 7% lower); recovery within 5 minutes after Yorba Linda; Encino recovery after about 6 hours but low several hours before (wind) | Factor, Kohler et al. 2005 |
| Wind | Santa Ana windstorm (no rain): E-W f1 drops about 3%, others drop; mode amplitude rises about 10x; stiffness returns after the event | Millikan |
| Rain | immediate rise: a storm with over 100 mm in 2 days gave about +3% EW and torsion, slow decay over about 10 days; the second EW mode also rose about 3%; frequencies recover over about a week after a storm | Millikan |
| Temperature (diurnal) | at least 1% daily swing in all three fundamental frequencies in hot weather; frequency rises with daytime temperature even as ambient amplitude rises ten-fold | Millikan |
| Season | no long-term seasonal trend found in 2.5 years of data | Millikan |
| Broad Center | EW f1 varies from 2.55 Hz (mid-Oct) to 2.72 Hz (early Feb), 6.5%; NS 2.40 to 2.52 Hz, 4.9%; rain raises frequencies | Broad Center, 3 storey steel |
| Long-term range (2 years, daily means, Millikan) | EW 1.155-1.215 Hz (5.1%); NS 1.71-1.74 (1.7%); torsion 2.44-2.55 (4.4%) | Millikan |
| Occupancy / construction | partitions added 2004 gave a gradual 4% rise in EW f1 (equivalent to about 8% stiffness, since f scales with sqrt of stiffness) | Millikan |
| Temperature, long-term monitoring | coefficient of variation of f1 about 0.4% (City Hall) and 1.0% (Ophite Tower) over a year; about 0.3% for the Ile Verte towers over a month; correlation with temperature positive for the Ile Verte towers and Ophite (winter), negative for City Hall (correlation coefficient about -0.6); zeta scatter 9-14% (CV) in the towers and 12-14% in City Hall; the authors conclude changes under 0.5% cannot be tied to damage | Mikael et al. 2013 |
| Frequency drop after damaging EQs | Millikan EW: permanent 16.6% drop (to 1.21 Hz) after the 1970 Lytle Creek (10.3% drop in the strong-motion record) and 1971 San Fernando events; EW f1 forced in 2002 is 22% below that in 1968 (abstract); permanent drops after other strong events usually below 2.5%; after Big Bear (small) the structure regained stiffness within minutes; Pacific Park Plaza 1989 Loma Prieta EQ f1 0.38 Hz vs ambient 0.48-0.54 (softening, partly temporary) | Millikan; Kumar et al. 2025 |
| Smartphone repeat measurement | f1 4.85 to 4.50 Hz over 4 months (about 7%) in a 5-storey L-shaped building, from three different earthquakes (so amplitude differences contribute) | Patel et al. 2023 |
| Shake table | brace disengagement reduced f1 by up to 22% | Patel et al. 2023 |

Mikael 2013 reports rain and wind effects were not clearly visible in their Grenoble data; the temperature-frequency sign depends on the building (cladding, soil interaction, sun exposure). Nayeri et al. 2008 (Factor building) abstract-level summary read: temperature effects were examined and frequency estimates had a coefficient of variation of about 1-2% for most modes (full text not accessible; NOT VERIFIED beyond the abstract-level statement). Citation for Nayeri et al.: Nayeri, Masri, Ghanem, Nigbor (2008), Smart Materials and Structures 17(2), 025006, https://doi.org/10.1088/0964-1726/17/2/025006.

---

## Verification notes

Items that could not be confirmed, and what was tried:

1. Peterson (1993) report PDF: the USGS server returned 403; values in 4b come from the ObsPy data file, a secondary copy, not the report. Not cross-checked against the original tables.
2. Kong et al. 2016 noise-floor numeric values: only in a figure; the text gives no numbers.
3. Kong et al. 2018: units of the quoted spectral noise levels (10e-5 vs 10e-6) are not legible in the extracted text; per-phone chip mapping in Table 1 was scrambled in extraction.
4. Kumar et al. 2025: damping column units in Table 1 are not stated; the SkyDeck zeta "0.08 to 0.12" is unitless in the text; the dB reference for the noise values is not restated in the paper and is taken from Patel et al. 2023. Millennium Tower floor count is 58 in the table and 56 in the text.
5. Pacific Park Plaza frequencies and the 1985/1989 values are secondhand through Kumar et al.; the Celebi et al. paper itself was not located.
6. Heights: Broad Center, Grenoble 9-storey and Factor building heights were not found in the sources read.
7. Ophite Tower height is computed (18 x 3.3 m), not stated.
8. Millikan damping ratios, and Bradford et al. 2004 (Caltech EERL report), were not read; Table 2 in Clinton et al. gives forced frequencies only. Nayeri et al. 2008 full text not accessible.
9. Michel et al. 2008 (Grenoble 9-storey) is an arXiv submission preprint; the journal volume/pages were not verified. The City Hall values 1.16/1.22/1.45 Hz come from Michel et al. 2010 as cited by Mikael et al.; Michel 2010 itself was not read.
10. Mikael et al. 2013: Ile Verte test year not stated in the preprint read; volume/pages 103(1), 236-246 and DOI 10.1785/0120120048 are from the arXiv record, not from the BSSA page.
11. TDK ICM-42688-P: full datasheet (DS-000347) not downloadable; only the product brief comparison table (AXY 65, AZ 70 ug/sqrt(Hz)) was read.
12. Bosch BMI270 and BMI160: table text was extracted from PDFs with column layout partly scrambled; the typical values were read in the raw-order extraction (BMI160 180/300; BMI270 0.16 mg/sqrt(Hz)) and should be confirmed against the PDF tables before use.
13. Ambient RMS/peak accelerations on upper floors: no verified absolute ambient values for typical (non-wind-storm) conditions were obtained. Search-result figures for a 167 m office tower (about 2 mg RMS), a Boston tower (about 0.46 mg) and occupant-survey values (1-2 mg) were not opened or confirmed. The scanned AISC PDF could not be text-extracted.
14. Urban 0.5-20 Hz microtremor PSD: only the Barcelona (-80 to -110 dB) and London (+20 dB over NHNM at T<0.4 s) numbers were read; the London median table was not accessed.
15. MIT Green Building 0.75/0.67 Hz: search-result summary only.
16. Other smartphone building studies (for example Ozer and Feng conference and chapter material, other groups): not read. Kong 2016 article number "e1501055" inferred from the DOI.
17. Search tools returned page summaries; every number above comes from a PDF or HTML page that was opened and text-searched or read, except where flagged. Where a fetch tool summarized a page rather than returning text (Patel et al. 2023 building list, Feng et al. 2015 Table 1, Mugabo et al. 2019), the numbers were relayed from that summary; Patel et al. was additionally text-searched for insurance and risk terms.
