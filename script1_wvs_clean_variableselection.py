import pandas as pd
import numpy as np
import os

RAW_FILE = "WVS_CrossNational_Wave_7_Sample_ANZData_v00.xlsx"

#load

if RAW_FILE.endswith(".xlsx"):
    df = pd.read_excel(RAW_FILE)
else:
    df = pd.read_csv(RAW_FILE, low_memory=False)

df.columns = df.columns.str.strip()


COUNTRY_COL = "B_COUNTRY_ALPHA"
AGE_COL = "Age"

#aus filter

before = len(df)
df = df[df[COUNTRY_COL].isin(["AUS", "AU", "Australia"])].copy()


#age 65+

df[AGE_COL] = pd.to_numeric(df[AGE_COL], errors="coerce")

MISSING_AGE_CODES = [-1, -2, -3, -4, -5]

before_age = len(df)
df = df[~df[AGE_COL].isin(MISSING_AGE_CODES)].copy()
df = df[df[AGE_COL].notna()].copy()
df = df[df[AGE_COL] >= 65].copy()


assert df[AGE_COL].min() >= 65, "ERROR: Age filter failed"

#replace with null

WVS_MISSING_CODES = [-1, -2, -3, -4, -5]

num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
replaced_numeric = 0

for col in num_cols:
    mask = df[col].isin(WVS_MISSING_CODES)
    replaced_numeric += mask.sum()
    df.loc[mask, col] = np.nan

WVS_MISSING_LABELS = [
    "Missing; Not available",
    "Not asked in this country",
    "No answer",
    "Don´t know",
    "Don't know",
    "Dont know",
    "Not asked",
    "Inapplicable",
    "Not applicable",
]

obj_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
replaced_text = 0

for col in obj_cols:
    df[col] = df[col].astype(str).str.strip()
    df[col] = df[col].str.replace(r"\s+", " ", regex=True)

    df[col] = df[col].replace({
        "nan": np.nan,
        "NaN": np.nan,
        "None": np.nan,
        "": np.nan
    })

    mask = df[col].isin(WVS_MISSING_LABELS)
    replaced_text += mask.sum()
    df.loc[mask, col] = np.nan

#nuemric columns

converted_cols = []

for col in df.columns:
    converted = pd.to_numeric(df[col], errors="coerce")

    original_non_missing = df[col].notna().sum()
    converted_non_missing = converted.notna().sum()

    if original_non_missing > 0 and converted_non_missing / original_non_missing >= 0.80:
        df[col] = converted
        converted_cols.append(col)


mixed_type_cols = []

for col in df.columns:
    types = df[col].dropna().apply(type).value_counts()
    if len(types) > 1:
        mixed_type_cols.append(col)


#candidates variabless

DROP_EXACT = [
    "B_COUNTRY", "B_COUNTRY_ALPHA", "B_COUNTRY_ALPHA_COW",
    "B_REGION", "B_SUBNATIONAL",
    "A_YEAR", "A_STUDY", "A_WAVE", "A_STUDYID",
    "A_SAMPLE", "A_VERSION",

    "D_INTERVIEW", "S018", "S018A", "S020", "S021",

    "S017", "S017A", "S018B", "W_WEIGHT", "WEIGHT",

    "J_INTDATE", "J_INTDATE_MONTH", "J_INTDATE_DAY", "J_INTDATE_YEAR",
    "J_INTLANGUAGE", "J_INTMODE",
]

DROP_KEYWORDS = [
    "COUNTRY", "REGION", "WAVE", "STUDY", "VERSION",
    "INTERVIEW", "INTERVIEWER", "DATE", "TIME",
    "WEIGHT", "SAMPLE", "MODE", "LANGUAGE",
    "PSU", "STRATA", "CLUSTER",
    "LATITUDE", "LONGITUDE"
]

cols_before = df.shape[1]

drop_cols = [col for col in DROP_EXACT if col in df.columns]

for col in df.columns:
    col_upper = str(col).upper()
    if any(keyword in col_upper for keyword in DROP_KEYWORDS):
        drop_cols.append(col)

drop_cols = sorted(set(drop_cols))

df_candidates = df.drop(columns=drop_cols, errors="ignore").copy()

MISSING_THRESHOLD = 0.40

missing_rate = df_candidates.isna().mean()
high_missing_cols = missing_rate[missing_rate > MISSING_THRESHOLD].index.tolist()
df_candidates = df_candidates.drop(columns=high_missing_cols)

low_variance_cols = [
    col for col in df_candidates.columns
    if df_candidates[col].nunique(dropna=True) <= 1
]
df_candidates = df_candidates.drop(columns=low_variance_cols)





#variable summary

candidate_summary = pd.DataFrame({
    "column": df_candidates.columns,
    "dtype": [df_candidates[col].dtype for col in df_candidates.columns],
    "missing_percent": [
        round(df_candidates[col].isna().mean() * 100, 2)
        for col in df_candidates.columns
    ],
    "unique_values": [
        df_candidates[col].nunique(dropna=True)
        for col in df_candidates.columns
    ],
    "sample_values": [
        ", ".join(map(str, df_candidates[col].dropna().unique()[:8]))
        for col in df_candidates.columns
    ]
})

candidate_summary.to_csv("candidate_variables_for_selection.csv", index=False)
candidate_summary.to_excel("candidate_variables_for_selection.xlsx", index=False)

print("  Saved: candidate_variables_for_selection.csv")
print("  Saved: candidate_variables_for_selection.xlsx")

print("\n" + "=" * 70)
print("STEP 8 – Exporting candidate dataset")
print("=" * 70)

CSV_FILE = "australia_65plus_candidate_variables.csv"
EXCEL_FILE = "australia_65plus_candidate_variables.xlsx"

df_candidates.to_csv(CSV_FILE, index=False)
df_candidates.to_excel(EXCEL_FILE, index=False)

csv_size = os.path.getsize(CSV_FILE) / 1024
excel_size = os.path.getsize(EXCEL_FILE) / 1024

print(f"  CSV saved   : {CSV_FILE} ({csv_size:.1f} KB)")
print(f"  Excel saved : {EXCEL_FILE} ({excel_size:.1f} KB)")
print(f"  Shape       : {df_candidates.shape}")



#next move is variable selection then do the encoding to that and we can start clustering
#maybe make another python file to do variable selection dropping other columns, and if there are any missing rows, you can deal with it however you like, then do the ordinal maps then encoding in another file?
#my recommandations for variabless wellbeing(all)  trust (4-5) social valuess (6-10)  work and moti (4-6) eco values (3-5) ethical valuess (optional 3-5) total would likely be (15-20) depending on the results 